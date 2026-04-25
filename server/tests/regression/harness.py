"""
Sailly regression harness — JSONL-native, dual-protocol.

Replays caller scenarios against a running Sailly instance and verifies
specific bot behaviors. Scenarios come from:
  1. Inline SCENARIOS list (legacy)
  2. JSONL files in scenarios/ (new — one JSON object per line)

JSONL scenario format
─────────────────────
  {"meta": {"name": "...", "description": "...", "skip": false}}
  {"role": "user", "text": "Einen Bulgogi bitte"}
  {"role": "assert", "type": "contains", "text": "bulgogi", "turn": "last"}
  {"role": "assert", "type": "tool", "name": "get_menu"}
  {"role": "assert", "type": "forbid", "text": "technisches problem"}
  {"role": "user", "text": "Philipp Schneider"}
  {"role": "assert", "type": "tool", "name": "create_order", "at_end": true}

Assertion types:
  contains  — text appears (case-insensitive) in the latest bot turn
  forbid    — text must NEVER appear in any bot turn
  tool      — tool name fired during this session (from bot_text.tools_fired or DB)
  tool_not  — tool name must NOT have fired
  turn_count — number of non-greeting turns == N

WebSocket protocol (/ws/headless endpoint)
──────────────────────────────────────────
  Send: {"type": "user_text", "text": "..."} | {"type": "end_session"}
  Recv: {"type": "session_init", "call_sid": "..."}
        {"type": "bot_text", "text": "...", "tools_fired": [...], "turn_idx": N}
        {"type": "tool_event", "name": "...", "args": {...}, "turn_idx": N}
        {"type": "error", "message": "..."}
        {"type": "session_end", "turn_count": N}

The harness also still works against /ws/demo_text (old pipeline protocol)
via the --legacy-protocol flag.

Usage:
    python -m server.tests.regression.harness
    python -m server.tests.regression.harness --only philipp_stress_test
    python -m server.tests.regression.harness --scenarios-dir server/tests/regression/scenarios
    python -m server.tests.regression.harness --url ws://127.0.0.1:8080/ws/headless
    python -m server.tests.regression.harness --verbose --json-output results.json
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import json
import logging
import os
import pathlib
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

try:
    import asyncpg
    _HAS_ASYNCPG = True
except ImportError:
    asyncpg = None  # type: ignore
    _HAS_ASYNCPG = False

try:
    import websockets
    _HAS_WEBSOCKETS = True
except ImportError:
    websockets = None  # type: ignore
    _HAS_WEBSOCKETS = False

logger = logging.getLogger("sailly.regression")

DEFAULT_WS_URL = os.environ.get(
    "SAILLY_WS_URL",
    "ws://127.0.0.1:8080/ws/headless"
)

DEFAULT_PG_DSN = os.environ.get(
    "SAILLY_PG_DSN",
    "postgresql://sailly:sailly@localhost:5432/sailly"
)

SCENARIOS_DIR = pathlib.Path(__file__).parent / "scenarios"


# ─── Data structures ────────────────────────────────────────────────

@dataclass
class AssertionResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ScenarioResult:
    scenario_name: str
    passed: bool = False
    checks: List[AssertionResult] = field(default_factory=list)
    bot_responses: List[str] = field(default_factory=list)
    tools_fired: List[str] = field(default_factory=list)
    total_duration_s: float = 0.0
    per_turn_latency_ms: List[int] = field(default_factory=list)
    call_sid: str = ""
    harness_error: Optional[str] = None

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)


@dataclass
class ScenarioStep:
    """One parsed JSONL line during a scenario."""
    role: str                          # "user" | "assert"
    text: Optional[str] = None         # for role=user and type=contains/forbid
    assert_type: Optional[str] = None  # "contains" | "forbid" | "tool" | "tool_not" | "turn_count"
    tool_name: Optional[str] = None    # for type=tool / tool_not
    assert_at_end: bool = False        # evaluate at session end (not immediately)
    assert_turn: Optional[str] = None  # "last" | int | None
    expected_count: Optional[int] = None  # for turn_count


@dataclass
class Scenario:
    name: str
    description: str
    steps: List[ScenarioStep]
    turn_delay_s: float = 0.5
    inter_turn_timeout_s: float = 25.0
    # Legacy assertion functions (kept for SCENARIOS list compatibility)
    assertions: List[Callable[[ScenarioResult], AssertionResult]] = field(
        default_factory=list
    )

    @property
    def caller_script(self) -> List[str]:
        """For backward compat — return user utterances in order."""
        return [s.text for s in self.steps if s.role == "user" and s.text]


# ─── JSONL loader ───────────────────────────────────────────────────

def load_jsonl_scenario(path: pathlib.Path) -> Optional[Scenario]:
    """Parse a .jsonl file into a Scenario.

    Returns None if the scenario is marked skip=true.
    """
    steps: List[ScenarioStep] = []
    meta: Dict[str, Any] = {}

    try:
        with open(path) as f:
            for lineno, raw in enumerate(f, 1):
                raw = raw.strip()
                if not raw or raw.startswith("#"):
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError as exc:
                    logger.warning(f"{path}:{lineno} JSON parse error: {exc}")
                    continue

                if "meta" in obj:
                    meta = obj["meta"]
                    continue

                role = obj.get("role", "")
                if role == "user":
                    steps.append(ScenarioStep(role="user", text=obj.get("text", "")))
                elif role == "assert":
                    steps.append(ScenarioStep(
                        role="assert",
                        assert_type=obj.get("type", ""),
                        text=obj.get("text"),
                        tool_name=obj.get("name"),
                        assert_at_end=bool(obj.get("at_end", False)),
                        assert_turn=obj.get("turn"),
                        expected_count=obj.get("count"),
                    ))
    except OSError as exc:
        logger.error(f"Cannot open {path}: {exc}")
        return None

    if meta.get("skip"):
        logger.info(f"Skipping {path.stem} (skip=true in meta)")
        return None

    if not steps:
        return None

    return Scenario(
        name=meta.get("name", path.stem),
        description=meta.get("description", ""),
        steps=steps,
        turn_delay_s=float(meta.get("turn_delay_s", 0.5)),
        inter_turn_timeout_s=float(meta.get("turn_timeout_s", 25.0)),
    )


def load_all_jsonl_scenarios(directory: pathlib.Path) -> List[Scenario]:
    """Load all *.jsonl files from a directory."""
    scenarios = []
    for path in sorted(directory.glob("*.jsonl")):
        s = load_jsonl_scenario(path)
        if s is not None:
            scenarios.append(s)
    return scenarios


# ─── WebSocket protocol adapter ─────────────────────────────────────

class SaillyWebSocketClient:
    """
    Speaks Sailly's /ws/headless protocol (Phase 2).
    Sends user_text messages, receives bot_text + tool_event messages.
    """

    def __init__(self, url: str, legacy_protocol: bool = False):
        self.url = url
        self.legacy_protocol = legacy_protocol
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.call_sid: Optional[str] = None
        # Per-turn tool accumulator
        self._pending_tools: List[str] = []

    async def connect(self) -> None:
        self.ws = await websockets.connect(self.url)
        # Legacy /ws/demo_text requires a tenant handshake before sending session_init
        if self.legacy_protocol:
            await self.ws.send(json.dumps({"tenant": "doboo"}))
        # Both protocols send session_init first (skip any leading binary frames)
        deadline = time.monotonic() + 20.0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Timed out waiting for session_init")
            first_msg = await asyncio.wait_for(self.ws.recv(), timeout=remaining)
            if isinstance(first_msg, bytes):
                continue
            try:
                data = json.loads(first_msg)
            except (json.JSONDecodeError, ValueError):
                continue
            self.call_sid = data.get("call_sid") or data.get("session_id") or ""
            logger.info(f"Connected: call_sid={self.call_sid!r}")
            break

    async def receive_bot_turn(self, timeout_s: float) -> str:
        """Wait for the next complete bot turn.

        New protocol: waits for a single bot_text message.
        Legacy protocol: accumulates transcript messages.
        """
        assert self.ws is not None
        self._pending_tools = []

        if not self.legacy_protocol:
            return await self._recv_headless_turn(timeout_s)
        else:
            return await self._recv_legacy_turn(timeout_s)

    async def _recv_headless_turn(self, timeout_s: float) -> str:
        """New /ws/headless protocol: wait for bot_text."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                raw = await asyncio.wait_for(self.ws.recv(), timeout=min(remaining, 1.0))
            except asyncio.TimeoutError:
                continue
            data = json.loads(raw)
            msg_type = data.get("type", "")
            if msg_type == "bot_text":
                self._pending_tools = data.get("tools_fired", [])
                return data.get("text", "")
            if msg_type == "tool_event":
                name = data.get("name", "")
                if name and name not in self._pending_tools:
                    self._pending_tools.append(name)
            if msg_type == "session_end":
                return ""
            if msg_type == "error":
                logger.warning(f"Server error: {data.get('message')}")
                return ""
        return ""

    async def _recv_legacy_turn(self, timeout_s: float) -> str:
        """Old /ws/demo_text protocol: accumulate transcript messages."""
        accumulated = []
        deadline = time.monotonic() + timeout_s
        last_bot = time.monotonic()
        silence = 3.0

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            if accumulated and (time.monotonic() - last_bot) > silence:
                break
            try:
                raw = await asyncio.wait_for(self.ws.recv(), timeout=min(remaining, 0.5))
            except asyncio.TimeoutError:
                continue
            # Skip binary frames (TTS audio) — only process JSON text messages
            if isinstance(raw, bytes):
                continue
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                continue
            msg_type = data.get("type") or data.get("event")
            if msg_type == "transcript" and data.get("speaker") == "bot":
                text = data.get("text", "")
                if text:
                    accumulated.append(text)
                    last_bot = time.monotonic()
            elif msg_type == "call_ended":
                break

        return "".join(accumulated).strip()

    async def send_utterance(self, text: str) -> None:
        assert self.ws is not None
        await self.ws.send(json.dumps({"type": "user_text", "text": text}))

    async def end_session(self) -> None:
        if self.ws is not None:
            try:
                await self.ws.send(json.dumps({"type": "end_session"}))
            except Exception:
                pass

    async def close(self) -> None:
        if self.ws is not None:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None


# ─── DB helper ──────────────────────────────────────────────────────

async def fetch_tools_from_db(call_sid: str) -> List[str]:
    """Fetch tool names fired during a call, from postgres."""
    if not call_sid or not _HAS_ASYNCPG:
        return []
    try:
        conn = await asyncpg.connect(DEFAULT_PG_DSN)
        try:
            rows = await conn.fetch(
                """
                SELECT tools_called
                FROM google_turn_metrics
                WHERE call_sid = $1
                ORDER BY turn_number ASC
                """,
                call_sid,
            )
            all_tools: List[str] = []
            for row in rows:
                tools = row["tools_called"] or []
                if isinstance(tools, str):
                    try:
                        tools = json.loads(tools)
                    except json.JSONDecodeError:
                        tools = []
                if isinstance(tools, list):
                    all_tools.extend(tools)
            return all_tools
        finally:
            await conn.close()
    except Exception as e:
        logger.debug(f"DB fetch skipped for {call_sid}: {e}")
        return []


# ─── JSONL assertion runner ─────────────────────────────────────────

def _run_jsonl_assertions(
    steps: List[ScenarioStep],
    result: ScenarioResult,
) -> List[AssertionResult]:
    """Evaluate all assert steps from a JSONL scenario."""
    checks: List[AssertionResult] = []
    all_text = " ".join(result.bot_responses).lower()
    all_tools = set(result.tools_fired)

    for step in steps:
        if step.role != "assert":
            continue

        atype = step.assert_type or ""

        if atype == "contains":
            needle = (step.text or "").lower()
            # Determine which turn to check
            if step.assert_turn == "last":
                # Last non-empty bot response
                last = next(
                    (r for r in reversed(result.bot_responses) if r.strip()), ""
                )
                found = needle in last.lower()
                src = last[:80]
            else:
                found = needle in all_text
                src = "(all turns)"
            checks.append(AssertionResult(
                name=f"contains:{needle[:30]}",
                passed=found,
                detail="" if found else f"not found in {src!r}",
            ))

        elif atype == "forbid":
            needle = (step.text or "").lower()
            hits = [
                f"turn={i} {r[:60]!r}"
                for i, r in enumerate(result.bot_responses)
                if needle in r.lower()
            ]
            checks.append(AssertionResult(
                name=f"forbid:{needle[:30]}",
                passed=not hits,
                detail="; ".join(hits) if hits else "",
            ))

        elif atype == "tool":
            name = step.tool_name or ""
            found = name in all_tools
            checks.append(AssertionResult(
                name=f"tool:{name}",
                passed=found,
                detail="" if found else f"not in {sorted(all_tools)}",
            ))

        elif atype == "tool_not":
            name = step.tool_name or ""
            fired = name in all_tools
            checks.append(AssertionResult(
                name=f"tool_not:{name}",
                passed=not fired,
                detail=f"unexpectedly fired (all: {sorted(all_tools)})" if fired else "",
            ))

        elif atype == "turn_count":
            expected = step.expected_count
            actual = len(result.bot_responses) - 1  # subtract greeting
            checks.append(AssertionResult(
                name=f"turn_count:{expected}",
                passed=(actual == expected),
                detail="" if actual == expected else f"got {actual}",
            ))

    return checks


# ─── Scenario runner ────────────────────────────────────────────────

async def run_scenario(
    scenario: Scenario,
    ws_url: str,
    legacy_protocol: bool = False,
) -> ScenarioResult:
    result = ScenarioResult(scenario_name=scenario.name)
    start = time.perf_counter()
    client = SaillyWebSocketClient(ws_url, legacy_protocol=legacy_protocol)

    try:
        await client.connect()
        result.call_sid = client.call_sid or ""

        # Receive greeting (first bot turn)
        greeting = await client.receive_bot_turn(timeout_s=15.0)
        result.bot_responses.append(greeting)
        result.tools_fired.extend(client._pending_tools)

        # Drive turns from scenario steps
        for step in scenario.steps:
            if step.role != "user":
                continue
            turn_start = time.perf_counter()
            await client.send_utterance(step.text or "")
            bot_response = await client.receive_bot_turn(
                timeout_s=scenario.inter_turn_timeout_s
            )
            turn_end = time.perf_counter()
            result.bot_responses.append(bot_response)
            result.tools_fired.extend(client._pending_tools)
            result.per_turn_latency_ms.append(int((turn_end - turn_start) * 1000))
            await asyncio.sleep(scenario.turn_delay_s)

        await client.end_session()
        await client.close()

    except Exception as exc:
        result.harness_error = f"{type(exc).__name__}: {exc}"
        logger.exception(f"Harness error in {scenario.name}")
        await client.close()
        result.total_duration_s = time.perf_counter() - start
        return result

    result.total_duration_s = time.perf_counter() - start

    # Try DB enrichment (best-effort, non-fatal)
    db_tools = await fetch_tools_from_db(result.call_sid)
    if db_tools:
        # Merge without duplicates (preserve order)
        seen = set(result.tools_fired)
        for t in db_tools:
            if t not in seen:
                result.tools_fired.append(t)
                seen.add(t)

    # JSONL inline assertions
    jsonl_checks = _run_jsonl_assertions(scenario.steps, result)
    result.checks.extend(jsonl_checks)

    # Legacy callable assertions
    for fn in scenario.assertions:
        try:
            result.checks.append(fn(result))
        except Exception as exc:
            result.checks.append(AssertionResult(
                name=f"assertion_error_{getattr(fn, '__name__', '?')}",
                passed=False,
                detail=str(exc),
            ))

    result.passed = (
        result.harness_error is None
        and all(c.passed for c in result.checks)
    )
    return result


# ─── Legacy callable assertion helpers ──────────────────────────────

def assert_no_forbidden_phrases(forbidden: List[str], check_greeting: bool = False) -> Callable:
    def check(r: ScenarioResult) -> AssertionResult:
        responses = r.bot_responses if check_greeting else r.bot_responses[1:]
        hits = []
        for i, resp in enumerate(responses):
            for phrase in forbidden:
                if phrase.lower() in resp.lower():
                    hits.append(f"turn={i+1} phrase={phrase!r}")
        return AssertionResult(
            name=f"no_forbidden_phrases_{len(forbidden)}",
            passed=not hits,
            detail="; ".join(hits),
        )
    check.__name__ = "assert_no_forbidden_phrases"
    return check


def assert_tool_fired(tool_name: str, min_times: int = 1) -> Callable:
    def check(r: ScenarioResult) -> AssertionResult:
        count = r.tools_fired.count(tool_name)
        return AssertionResult(
            name=f"tool_fired_{tool_name}",
            passed=count >= min_times,
            detail=f"fired {count}x" if count >= min_times
                   else f"expected>={min_times} got={count} seen={r.tools_fired}",
        )
    check.__name__ = f"assert_tool_fired_{tool_name}"
    return check


def assert_tool_not_fired(tool_name: str) -> Callable:
    def check(r: ScenarioResult) -> AssertionResult:
        fired = tool_name in r.tools_fired
        return AssertionResult(
            name=f"tool_not_fired_{tool_name}",
            passed=not fired,
            detail=f"unexpectedly fired (all: {r.tools_fired})" if fired else "",
        )
    check.__name__ = f"assert_tool_not_fired_{tool_name}"
    return check


def assert_max_turn_latency(max_ms: int) -> Callable:
    def check(r: ScenarioResult) -> AssertionResult:
        if not r.per_turn_latency_ms:
            return AssertionResult(name=f"max_latency_{max_ms}ms", passed=False,
                                   detail="no turns captured")
        worst = max(r.per_turn_latency_ms)
        return AssertionResult(
            name=f"max_latency_{max_ms}ms",
            passed=worst <= max_ms,
            detail=f"worst={worst}ms" + (f" exceeded limit={max_ms}ms" if worst > max_ms else ""),
        )
    check.__name__ = f"assert_max_latency_{max_ms}"
    return check


def assert_min_response_length(min_chars: int) -> Callable:
    def check(r: ScenarioResult) -> AssertionResult:
        too_short = [
            (i + 1, len(resp.strip()))
            for i, resp in enumerate(r.bot_responses[1:])
            if len(resp.strip()) < min_chars
        ]
        return AssertionResult(
            name=f"min_response_length_{min_chars}",
            passed=not too_short,
            detail=f"{len(too_short)} turns too short: {too_short}" if too_short else "",
        )
    check.__name__ = f"assert_min_len_{min_chars}"
    return check


def assert_any_substring_present(required: List[str]) -> Callable:
    def check(r: ScenarioResult) -> AssertionResult:
        all_text = " ".join(r.bot_responses).lower()
        matched = [s for s in required if s.lower() in all_text]
        return AssertionResult(
            name=f"any_of_{len(required)}_substrings",
            passed=bool(matched),
            detail=f"matched: {matched}" if matched else f"none of {required} found",
        )
    check.__name__ = "assert_any_substring"
    return check


def assert_all_substrings_present(required: List[str]) -> Callable:
    def check(r: ScenarioResult) -> AssertionResult:
        all_text = " ".join(r.bot_responses).lower()
        missing = [s for s in required if s.lower() not in all_text]
        return AssertionResult(
            name=f"all_of_{len(required)}_substrings",
            passed=not missing,
            detail=f"missing: {missing}" if missing else "",
        )
    check.__name__ = "assert_all_substrings"
    return check


# ─── Universal forbidden phrases (applied to all scenarios) ─────────

UNIVERSAL_FORBIDDEN = [
    "technisches problem",
    "technischer fehler",
    "system-fehler",
    "system fehler",
    "ich habe einen fehler",
    "etwas ist schiefgelaufen",
    "das hat nicht funktioniert",
    "[tool:",
    "bekannte daten",
    "nächster schritt",
    "validierungsstatus",
    "letzte aussage",
    "noch fehlend",
    "{time}",
    "{date}",
    "{name}",
    "{{",
    "}}",
]


def universal_assertions() -> List[Callable]:
    return [
        assert_no_forbidden_phrases(UNIVERSAL_FORBIDDEN),
        assert_min_response_length(20),
        assert_max_turn_latency(15_000),
    ]


# ─── Inline scenarios (legacy) ───────────────────────────────────────

SCENARIOS: List[Scenario] = [
    Scenario(
        name="pizza_pivot",
        description="Caller asks for Pizza (not on menu). Bot must offer Korean alternative.",
        steps=[ScenarioStep(role="user", text="Ich möchte gerne eine Pizza Margherita bestellen.")],
        assertions=[
            assert_any_substring_present(["pizza"]),
            assert_any_substring_present(["bulgogi", "bibimbap", "japchae", "ähnlich", "beliebt"]),
        ],
    ),
    Scenario(
        name="wine_is_available",
        description="Wine IS on the Korean menu. Bot must not deny it.",
        steps=[ScenarioStep(role="user", text="Ich hätte gerne einen Bulgogi und eine Flasche Wein.")],
        assertions=[
            assert_no_forbidden_phrases([
                "keinen wein", "kein wein", "keine flasche wein",
                "wein haben wir nicht", "nicht auf unserer karte",
                "nicht auf unserer speisekarte",
            ]),
        ],
    ),
    Scenario(
        name="no_phantom_reservation",
        description="Takeaway order. Bot must fire create_order but NOT create_reservation.",
        steps=[
            ScenarioStep(role="user", text="Einen Bulgogi zum Abholen bitte."),
            ScenarioStep(role="user", text="Philipp Schneider, Friedrichstraße 20, Bonn."),
            ScenarioStep(role="user", text="Null eins sieben neun drei vier fünf sechs sieben acht neun."),
            ScenarioStep(role="user", text="Ja, stimmt."),
        ],
        assertions=[
            assert_tool_not_fired("create_reservation"),
            assert_tool_not_fired("check_availability"),
        ],
    ),
    Scenario(
        name="multi_item_coherent",
        description="Multi-item order. Bot must acknowledge items coherently.",
        steps=[
            ScenarioStep(role="user", text="Ich hätt gern zwei Bulgogi, eine Flasche Wein, und dreimal Dessert."),
        ],
        assertions=[
            assert_min_response_length(30),
            assert_any_substring_present(["bulgogi"]),
        ],
    ),
]


# ─── Main runner ────────────────────────────────────────────────────

def _print_result(r: ScenarioResult, verbose: bool) -> None:
    if r.harness_error:
        print(f"  HARNESS ERROR: {r.harness_error}")
        return
    status = "PASS" if r.passed else "FAIL"
    print(
        f"  [{status}] duration={r.total_duration_s:.1f}s "
        f"turns={len(r.bot_responses)-1} "
        f"tools={len(r.tools_fired)} "
        f"checks={r.passed_count}/{r.passed_count + r.failed_count}"
    )
    for check in r.checks:
        mark = "✓" if check.passed else "✗"
        line = f"    {mark} {check.name}"
        if check.detail:
            line += f" — {check.detail[:100]}"
        print(line)
    if verbose:
        for i, resp in enumerate(r.bot_responses):
            label = "greeting" if i == 0 else f"T{i}"
            print(f"    [{label}] {resp[:150]}")
        print(f"    tools: {r.tools_fired}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Sailly regression harness")
    parser.add_argument("--only", default=None, help="run single scenario by name")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--url", default=DEFAULT_WS_URL,
                        help=f"WebSocket URL (default: {DEFAULT_WS_URL})")
    parser.add_argument("--scenarios-dir", default=None,
                        help="load all .jsonl files from this directory")
    parser.add_argument("--legacy-protocol", action="store_true",
                        help="use old /ws/demo_text transcript protocol instead of /ws/headless")
    parser.add_argument("--json-output", default=None,
                        help="write full results to JSON file")
    parser.add_argument("--no-universal", action="store_true",
                        help="skip universal forbidden-phrase assertions")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Collect scenarios
    scenarios_to_run: List[Scenario] = list(SCENARIOS)

    # Load JSONL files if directory specified
    if args.scenarios_dir:
        jsonl_dir = pathlib.Path(args.scenarios_dir)
        jsonl_loaded = load_all_jsonl_scenarios(jsonl_dir)
        logger.info(f"Loaded {len(jsonl_loaded)} JSONL scenarios from {jsonl_dir}")
        scenarios_to_run.extend(jsonl_loaded)
    elif SCENARIOS_DIR.exists():
        jsonl_loaded = load_all_jsonl_scenarios(SCENARIOS_DIR)
        if jsonl_loaded:
            logger.info(f"Auto-loaded {len(jsonl_loaded)} JSONL scenarios from {SCENARIOS_DIR}")
            scenarios_to_run.extend(jsonl_loaded)

    if args.only:
        scenarios_to_run = [s for s in scenarios_to_run if s.name == args.only]
        if not scenarios_to_run:
            print(f"No scenario named {args.only!r}")
            print(f"Available: {[s.name for s in SCENARIOS]}")
            sys.exit(1)

    if not scenarios_to_run:
        print("No scenarios to run.")
        sys.exit(0)

    results: List[ScenarioResult] = []
    for scenario in scenarios_to_run:
        # Add universal assertions (unless suppressed)
        if not args.no_universal:
            scenario.assertions = list(scenario.assertions) + universal_assertions()

        print(f"\n=== {scenario.name} ===")
        if scenario.description:
            print(f"  {scenario.description}")

        result = await run_scenario(scenario, args.url, legacy_protocol=args.legacy_protocol)
        _print_result(result, args.verbose)
        results.append(result)

    # Summary
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    print(f"\n===== SUMMARY =====")
    print(f"Passed: {passed}/{len(results)}")
    if failed:
        print(f"Failed: {failed}/{len(results)}")
        failed_names = [r.scenario_name for r in results if not r.passed]
        print(f"  Failed scenarios: {failed_names}")

    if args.json_output:
        with open(args.json_output, "w") as f:
            json.dump(
                [
                    {
                        "name": r.scenario_name,
                        "passed": r.passed,
                        "duration_s": r.total_duration_s,
                        "call_sid": r.call_sid,
                        "harness_error": r.harness_error,
                        "checks": [
                            {"name": c.name, "passed": c.passed, "detail": c.detail}
                            for c in r.checks
                        ],
                        "bot_responses": r.bot_responses,
                        "tools_fired": r.tools_fired,
                        "per_turn_latency_ms": r.per_turn_latency_ms,
                    }
                    for r in results
                ],
                f,
                indent=2,
                default=str,
            )
        print(f"Full results written to {args.json_output}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
