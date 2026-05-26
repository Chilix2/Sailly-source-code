"""
script_validator.py — Production fix-validation orchestrator for Sailly voice agent.

ONE FILE. SCRIPT-ONLY (no audio). Bucket-gated outside, cluster-fixing inside.

WHAT IT DOES
============
For each phase you give it (a, b, c, ...) it walks the 12 failure buckets in
priority order (Tier 1 first, then Tier 2), and for each bucket runs a 3-step
gated validation. If a gate fails, it enters a surgical fix loop that clusters
the failures by root cause, patches them one at a time, smoke-gates each
patch with a regression canary set, and restarts validation from Step 1.

The text path uses /ws/demo_text — NO Grok, NO TTS, NO STT, NO audio.

ARCHITECTURE
============
    PHASE (a → b → c …)
    └── BUCKET (12, priority order, T1 → T2)
        └── 3-STEP GATE  (max 3 attempts; retry from Step 1 on fail)
            ├─ Step 1: 10 scenarios → must pass tier threshold
            ├─ Step 2: 10 different → combined 1+2 must pass
            └─ Step 3: 10 different → combined 1+2+3 must pass
        └── On gate failure → FIX LOOP
            ├─ Cluster failures by cascade signature   (Latitude pattern)
            ├─ Sort by (count desc, dep-depth asc)     (surgical ordering)
            ├─ Per cluster, sequentially:
            │    1. Opus: propose minimal search-replace patch
            │    2. Haiku: judge the patch (LLM-as-Judge)
            │    3. Apply atomic patch (per-file backup)
            │    4. Restart agent → wait healthy
            │    5. Smoke gate: 3 canary scenarios from passing pool
            │    6. Revert if smoke regresses, commit otherwise
            └─ After fix: restart bucket from Step 1
        └── After max_attempts → mark UNRESOLVED, advance
    └── Validated bucket scenarios become regression canaries for next phase
        (Hamming: every fixed failure becomes a permanent regression test)

ISSUE LIFECYCLE (Latitude-style)
================================
Each cluster moves through:
    OBSERVED → TRIAGED → PATCHED → VERIFIED → CLOSED
                                 ↘ REGRESSED → REOPENED

USAGE
=====
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 -m server.validation.script_validator \\
        --phase a \\
        --workers 5 \\
        --max-attempts 3 \\
        --buckets all          # or: ai_greeting,create_order,...

ENV
===
    ANTHROPIC_API_KEY                # required for fix gen + judge
    SAILLY_WS_URL                    # default ws://127.0.0.1:8080/ws/headless
    SAILLY_PATCH_DIR                 # default /home/charles2/sailly-browser-demo/server
    SAILLY_RESTART_CMD               # default "sudo systemctl restart sailly-voice-agent"
    SAILLY_HEALTH_URL                # default http://localhost:8080/health
    SKIP_FIX_GENERATION=1            # disable Claude → manual loop only

EXIT CODES
==========
    0   all enabled buckets validated
    1   one or more buckets unresolved after max attempts
    2   fatal error (config, missing dependency, agent unreachable)
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import random
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import httpx

LOG = logging.getLogger("sailly.validator")


# ============================================================================
#  CONSTANTS
# ============================================================================
TIER_1_THRESHOLD = 1.00   # compliance-critical tools
TIER_2_THRESHOLD = 0.60   # quality / robustness

# 12 failure buckets — priority order matters (lower priority number runs first)
# Format: (name, priority, tier, baseline_fail_count, fix_description)
BUCKETS_DEF: list[tuple[str, int, int, int, str]] = [
    # --- Tier 1 (100% required) ---
    ("ai_greeting",         1, 1,  6, "Force ai_greeting on turn 0"),
    ("verify_address",      2, 1, 41, "Sticky flag + no node restriction"),
    ("create_order",        3, 1,  4, "Remove confirmation gate + partial dish"),
    ("send_sms",            4, 1,  0, "Auto-pair send_sms with create_order"),
    ("create_reservation",  5, 1, 31, "Remove confirmation gate + check_avail"),
    ("get_date_info",       6, 1, 13, "Remove turn==0 + add ordering node"),
    ("check_availability",  7, 1,  5, "Widen trigger to ordering + faq nodes"),
    ("get_weather",         8, 1,  0, "Add forced commit + state flag"),
    # --- Tier 2 (60% required) ---
    ("task_score",          9, 2, 38, "Expand _ORDER_KW + _RESERVATION_KW"),
    ("instruction_score",  10, 2,  6, "Escalation prompt German-only enforcement"),
    ("timeout",            11, 2,  8, "5-turn loop escape + stuck-loop detector"),
    ("conversation_loop",  12, 2,  3, "4-identical-response detector → end_call"),
]

# Dependency graph depth — lower number = closer to data layer = patch first.
# Adjust to your actual layout. Wrong depths just sub-optimise ordering, no break.
DEP_DEPTH: dict[str, int] = {
    "conversation_state.py":   0,   # data layer — leaf
    "captured_intents.py":     0,
    "order_slots.py":          0,
    "memory_manager.py":       1,
    "validation_registry.py":  1,
    "tools_definitions.py":    1,
    "slot_extractor.py":       1,
    "tools_executor.py":       2,
    "node_manager.py":         3,
    "conversation_nodes.py":   3,
    "response_variations.py":  3,
    "adk_turn_processor.py":   4,
    "tts_conditioning.py":     4,
    "v4_pipeline.py":          5,
    "main.py":                 6,   # orchestration — root
}
DEFAULT_DEPTH = 4


# ============================================================================
#  TYPES
# ============================================================================
class IssueState(Enum):
    """Issue lifecycle (Latitude / Hamming pattern)."""
    OBSERVED  = "observed"     # failures clustered, not yet acted on
    TRIAGED   = "triaged"      # patch proposed
    PATCHED   = "patched"      # patch applied, awaiting verification
    VERIFIED  = "verified"     # fix held under smoke gate
    CLOSED    = "closed"       # bucket validated end-to-end
    REGRESSED = "regressed"    # smoke gate or step 2/3 caught a regression
    UNFIXABLE = "unfixable"    # max attempts exhausted


class BucketStatus(Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    VALIDATED  = "validated"
    UNRESOLVED = "unresolved"
    SKIPPED    = "skipped"


@dataclass
class TurnLog:
    user: str
    bot: str
    latency_ms: int = 0
    tools: list[str] = field(default_factory=list)


@dataclass
class ScenarioOutcome:
    scenario_id: str
    bucket: str
    persona: str = "neutral"
    passed: bool = False
    failure_tags: list[str] = field(default_factory=list)
    failure_signature: str = ""
    composite_score: float = 0.0
    tools_called: list[str] = field(default_factory=list)
    tools_expected: list[str] = field(default_factory=list)
    tools_missing: list[str] = field(default_factory=list)
    last_turns: list[TurnLog] = field(default_factory=list)
    duration_s: float = 0.0
    call_sid: str = ""
    call_report_bundle: dict = field(default_factory=dict)


@dataclass
class FailureCluster:
    cluster_id: str
    bucket: str
    signature: str
    members: list[ScenarioOutcome]
    suspect_files: list[str] = field(default_factory=list)
    state: IssueState = IssueState.OBSERVED
    fix_attempts: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.members)

    @property
    def min_dep_depth(self) -> int:
        if not self.suspect_files:
            return DEFAULT_DEPTH
        return min(DEP_DEPTH.get(f, DEFAULT_DEPTH) for f in self.suspect_files)

    def priority_key(self) -> tuple[int, int]:
        # smaller key = higher priority
        return (-self.count, self.min_dep_depth)


@dataclass
class StepResult:
    step: int
    scenario_ids: list[str]
    outcomes: list[ScenarioOutcome]

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def passed(self) -> int:
        return sum(1 for o in self.outcomes if o.passed)

    @property
    def rate(self) -> float:
        return self.passed / max(1, self.total)


@dataclass
class GateAttempt:
    attempt_no: int
    started_at: str
    threshold: float
    steps: list[StepResult] = field(default_factory=list)
    final_state: str = ""             # passed_step1 | passed_combined | failed_step{N}
    fixes_applied: list[dict] = field(default_factory=list)
    duration_s: float = 0.0

    def combined_rate(self) -> float:
        total = sum(s.total for s in self.steps)
        passed = sum(s.passed for s in self.steps)
        return passed / max(1, total)


@dataclass
class BucketReport:
    name: str
    priority: int
    tier: int
    threshold: float
    status: str = BucketStatus.PENDING.value
    attempts: list[GateAttempt] = field(default_factory=list)
    final_combined_rate: float = 0.0
    canary_pool: list[str] = field(default_factory=list)
    skipped_reason: str = ""


@dataclass
class PhaseReport:
    phase: str
    started_at: str
    completed_at: str = ""
    duration_s: float = 0.0
    buckets: list[BucketReport] = field(default_factory=list)

    @property
    def validated(self) -> int:
        return sum(1 for b in self.buckets if b.status == BucketStatus.VALIDATED.value)

    @property
    def unresolved(self) -> int:
        return sum(1 for b in self.buckets if b.status == BucketStatus.UNRESOLVED.value)

    @property
    def total_enabled(self) -> int:
        return sum(1 for b in self.buckets if b.status != BucketStatus.SKIPPED.value)


# ============================================================================
#  CASCADE SIGNATURE — collapse same-root-cause failures into one cluster
# ============================================================================
_FAIL_PREFIX_RE = re.compile(r"^([a-z_]+):")


def cascade_signature(out: ScenarioOutcome) -> str:
    """
    Build a signature that collapses cascading symptoms back to root cause.

    Two scenarios that fail "for the same reason" must produce the same string.
    The signature uses:
      • root failure class (prefix of the FIRST failure tag — downstream tags
        are usually cascades of the first)
      • coarse bot-text context from the last turn (same upstream cause →
        very similar bot wording, e.g. "Wann moechten Sie reservieren")

    Score is intentionally NOT used — score is output noise, not root signal.
    """
    if not out.failure_tags:
        return ""
    root = out.failure_tags[0]
    m = _FAIL_PREFIX_RE.match(root)
    cls = m.group(1) if m else root
    # also record the missing-tool name if it's a missing_tool class —
    # different missing tools usually have different root causes
    if cls == "missing_tool" and ":" in root:
        cls = f"missing_tool:{root.split(':',1)[1]}"
    ctx = ""
    if out.last_turns:
        # bot reply truncated, lower-cased, alphanum-only
        ctx = (out.last_turns[-1].bot or "")[:60].lower()
        ctx = re.sub(r"[^a-z0-9 ]", "", ctx).strip()
    return f"{cls}|{ctx}"


# ============================================================================
#  SCENARIO RESULT ADAPTER (script-only path)
# ============================================================================
def _to_outcome(raw: Any, default_bucket: str = "unknown") -> ScenarioOutcome:
    """
    Adapt whatever phase_runner returns into a ScenarioOutcome.
    Tolerates both dataclass-style and dict-style results.
    """
    g = (lambda k, d=None: getattr(raw, k, d) if hasattr(raw, k) else
         (raw.get(k, d) if isinstance(raw, dict) else d))

    # bucket name — try several conventions
    bucket = (g("bucket") or g("bucket_name") or g("category") or
              g("scenario_bucket") or default_bucket)

    failure_tags: list[str] = list(g("failure_tags") or g("failure_reasons") or []) or []
    if g("error"):
        failure_tags.insert(0, f"harness:{g('error')}")

    # tools
    tools_called = list(g("tools_called") or g("tools_got") or []) or []
    tools_expected = list(g("tools_expected") or g("expected_tools") or []) or []
    tools_missing = list(g("tools_missing") or
                          [t for t in tools_expected if t not in tools_called]) or []

    # turns
    raw_turns = g("turns") or []
    last_turns: list[TurnLog] = []
    for t in (raw_turns[-3:] if isinstance(raw_turns, list) else []):
        if isinstance(t, dict):
            last_turns.append(TurnLog(
                user=t.get("user") or t.get("user_text") or t.get("user_utterance") or "",
                bot=t.get("bot")  or t.get("bot_text")  or t.get("llm_response")    or "",
                latency_ms=int(t.get("latency_ms") or t.get("total_latency_ms") or 0),
                tools=list(t.get("tools") or t.get("tools_called") or []),
            ))

    # functional pass: no missing tools AND no non-latency failures
    # (matches the existing run_browser_validation.py semantic)
    non_latency = [t for t in failure_tags if "latency" not in t.lower()]
    is_passed = bool(g("passed", g("functional_pass")))
    if is_passed is False and not failure_tags and not tools_missing:
        is_passed = True

    out = ScenarioOutcome(
        scenario_id=str(g("id") or g("scenario_id") or "unknown"),
        bucket=str(bucket),
        persona=str(g("persona") or "neutral"),
        passed=bool(is_passed) and not non_latency and not tools_missing,
        failure_tags=failure_tags,
        composite_score=float(g("composite_score") or g("composite") or 0.0),
        tools_called=tools_called,
        tools_expected=tools_expected,
        tools_missing=tools_missing,
        last_turns=last_turns,
        duration_s=float(g("duration_s") or g("elapsed_s") or 0.0),
        call_sid=str(g("call_sid") or ""),
    )
    out.failure_signature = cascade_signature(out)
    return out


# ============================================================================
#  PHASE RUNNER ADAPTER (script-only — text injection only)
# ============================================================================
async def _run_scenarios(
    phase: str,
    workers: int,
    *,
    scenario_ids: Optional[list[str]] = None,
    bucket_filter: Optional[str] = None,
    timeout_s: float = 180.0,
) -> list[ScenarioOutcome]:
    """
    Calls the script-path runner. We tolerate two backend conventions:
      1. server.validation.phase_runner.run_phase  (existing)
      2. server.validation.script_runner.run_script_phase  (if you split it out)

    Either one MUST hit /ws/demo_text — no audio. We force it via env var
    SKIP_AUDIO_BRIDGE=1 and SAILLY_WS_URL=ws://…/demo_text. If your phase
    runner ignores those, you'll need a tiny adapter — see README at top.
    """
    os.environ["SKIP_AUDIO_BRIDGE"] = "1"
    # default WS URL points at headless endpoint (records to Postgres via TextModeRunner)
    if "SAILLY_WS_URL" not in os.environ:
        os.environ["SAILLY_WS_URL"] = "ws://127.0.0.1:8080/ws/headless"

    try:
        from server.validation.phase_runner import run_phase as _run
    except ImportError:
        try:
            from server.validation.script_runner import run_script_phase as _run
        except ImportError as e:
            raise RuntimeError(
                "Cannot import phase_runner. Install one of:\n"
                "  - server.validation.phase_runner.run_phase\n"
                "  - server.validation.script_runner.run_script_phase"
            ) from e

    kwargs: dict[str, Any] = {
        "phase": phase,
        "max_concurrent": workers,
        "max_duration_sec": timeout_s,
    }
    if scenario_ids is not None:
        kwargs["scenario_ids"] = scenario_ids
    if bucket_filter is not None:
        # not all backends support this — pass anyway, they'll ignore
        kwargs["bucket"] = bucket_filter

    raw = await _run(**kwargs)
    outcomes = [_to_outcome(r, default_bucket=bucket_filter or "unknown") for r in raw]
    
    # Fetch call reports for each scenario (optional, graceful degradation)
    fetcher = CallReportFetcher()
    for outcome in outcomes:
        if outcome.call_sid:
            try:
                bundle = await fetcher.fetch_bundle(outcome.call_sid)
                if bundle:
                    outcome.call_report_bundle = bundle
            except Exception as e:
                LOG.debug(f"[call_report] Failed to fetch bundle for {outcome.call_sid}: {e}")
    
    return outcomes


# ============================================================================
#  CLUSTERING
# ============================================================================
def cluster_failures(outcomes: list[ScenarioOutcome], bucket: str) -> list[FailureCluster]:
    """Cascade-collapse failures, sort by priority."""
    by_sig: dict[str, list[ScenarioOutcome]] = defaultdict(list)
    for o in outcomes:
        if o.passed:
            continue
        by_sig[o.failure_signature].append(o)

    clusters: list[FailureCluster] = []
    for sig, members in by_sig.items():
        cid = hashlib.sha1(f"{bucket}|{sig}".encode()).hexdigest()[:10]
        clusters.append(FailureCluster(
            cluster_id=cid,
            bucket=bucket,
            signature=sig,
            members=members,
        ))
    clusters.sort(key=lambda c: c.priority_key())
    return clusters


# ============================================================================
#  CLAUDE BRIDGE — Opus for fix gen, Haiku for judging
# ============================================================================
class ClaudeBridge:
    def __init__(self):
        try:
            import anthropic  # type: ignore
        except ImportError as e:
            raise RuntimeError("pip install anthropic") from e
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY missing")
        self.cli = anthropic.Anthropic(api_key=api_key)

    def propose_fix(self, cluster: FailureCluster, patch_dir: Path,
                    max_loc: int, max_files: int) -> dict:
        examples = [
            {
                "scenario": m.scenario_id,
                "persona": m.persona,
                "failure_tags": m.failure_tags,
                "tools_missing": m.tools_missing,
                "tools_called": m.tools_called,
                "last_turns": [{"user": t.user[:200], "bot": t.bot[:200]} for t in m.last_turns],
            }
            for m in cluster.members[:5]
        ]
        leaf_first = sorted(DEP_DEPTH.items(), key=lambda kv: kv[1])
        file_index = "\n".join(f"  - {f} (depth {d})" for f, d in leaf_first[:12])

        sys_prompt = (
            "You are a senior backend engineer doing a SURGICAL fix on a "
            "German voice-agent codebase. You receive ONE failure cluster — "
            "all members share the same root cause. Output strict JSON only.\n"
            "\n"
            f"BUCKET: {cluster.bucket}  (failure category)\n"
            "\n"
            "RULES:\n"
            f"  1. Diagnose the SINGLE root cause. Prefer LOW-LAYER files "
            "(state, data) over HIGH-LAYER files (orchestration). A fix "
            "to conversation_state.py often dissolves symptoms in main.py.\n"
            f"  2. Patch must be MINIMAL: ≤ {max_loc} LOC delta, "
            f"≤ {max_files} files touched.\n"
            "  3. NO refactors. NO style changes. NO new imports unless "
            "strictly required to compile.\n"
            "  4. NO removal of validation, error handling, or security checks.\n"
            "  5. Search strings must appear EXACTLY ONCE in the target file.\n"
            "  6. If you cannot fix within those constraints, return "
            '{"patches":[],"reason":"requires-larger-change"}.\n'
            "\n"
            "OUTPUT SCHEMA (no prose, no markdown fences, no commentary):\n"
            "{\n"
            '  "root_cause": "one-sentence diagnosis",\n'
            '  "suspect_files": ["relative/path/from/patch_dir.py"],\n'
            '  "patches": [\n'
            '     {"file":"path", "search":"exact-text", '
            '"replace":"new-text", "why":"one line"}\n'
            "  ]\n"
            "}\n"
            f"\nFile index (depth = layer; lower = data, higher = orchestration):\n{file_index}\n"
            f"\nPatch root dir: {patch_dir}"
        )
        user_msg = json.dumps({
            "cluster_id": cluster.cluster_id,
            "failure_signature": cluster.signature,
            "occurrence_count": cluster.count,
            "examples": examples,
        }, ensure_ascii=False, indent=2)

        try:
            msg = self.cli.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                system=sys_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
        except Exception as e:
            LOG.error(f"[claude.propose] API error: {e}")
            return {"patches": [], "reason": f"api-error:{e}"}

        text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.M).strip()
        try:
            return json.loads(text)
        except Exception as e:
            LOG.error(f"[claude.propose] JSON parse fail: {e}\n{text[:400]}")
            return {"patches": [], "reason": f"json-parse-fail:{e}"}

    def judge_patch(self, cluster: FailureCluster, proposal: dict,
                    max_loc: int, max_files: int) -> dict:
        sys_prompt = (
            "You are a code-review assistant. Given a failure cluster and "
            "a proposed patch, return strict JSON only:\n"
            '{"approve": true|false, "reasons": ["..."]}\n'
            "Approve ONLY if ALL hold:\n"
            f"  • Total changed lines ≤ {max_loc}; files touched ≤ {max_files}.\n"
            "  • Patch addresses the cited root cause (not unrelated cleanup).\n"
            "  • No deletion of validation, error handling, or security checks.\n"
            "  • No new external dependencies.\n"
            "  • Search strings look like real code (not placeholder).\n"
            "  • Replace text doesn't introduce obvious bugs (unbalanced brackets, "
            "broken indentation, removed return statements)."
        )
        user_msg = json.dumps({
            "failure_signature": cluster.signature,
            "occurrence_count": cluster.count,
            "proposal": proposal,
        }, ensure_ascii=False)
        try:
            msg = self.cli.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=400,
                system=sys_prompt,
                messages=[{"role": "user", "content": user_msg}],
            )
        except Exception as e:
            LOG.error(f"[claude.judge] API error: {e}")
            return {"approve": False, "reasons": [f"api-error:{e}"]}

        text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.M).strip()
        try:
            return json.loads(text)
        except Exception:
            return {"approve": False, "reasons": ["judge-json-fail"]}


# ============================================================================
#  CALL REPORT FETCHER — fetch from Postgres after each scenario
# ============================================================================
class CallReportFetcher:
    """Fetch call report bundles from Postgres for a given call_sid."""

    async def fetch_bundle(self, call_sid: str) -> Optional[dict]:
        """
        Fetch structured call report bundle from Postgres.
        Returns None if DATABASE_URL not set, call_sid not found, or fetch fails.
        """
        if not call_sid:
            return None

        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            LOG.debug("[call_report] DATABASE_URL not set; skipping call report fetch")
            return None

        try:
            import asyncpg
            from server.call_report.builder import (
                fetch_call_report_bundle as _fetch_bundle,
            )
        except ImportError as e:
            LOG.warning(f"[call_report] Cannot import dependencies: {e}")
            return None

        try:
            conn = await asyncio.wait_for(asyncpg.connect(db_url), timeout=5.0)
            try:
                # Use the existing builder's fetch function
                bundle = await _fetch_bundle(call_sid)
                return bundle if bundle.get("found") else None
            finally:
                await conn.close()
        except Exception as e:
            LOG.debug(f"[call_report] Fetch failed for call_sid={call_sid}: {e}")
            return None

    async def fetch_markdown(self, call_sid: str) -> Optional[str]:
        """Fetch markdown call report from Postgres."""
        if not call_sid:
            return None

        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            return None

        try:
            from server.call_report.builder import build_call_report_markdown
        except ImportError:
            return None

        try:
            md = await asyncio.wait_for(
                build_call_report_markdown(call_sid),
                timeout=10.0,
            )
            return md
        except Exception as e:
            LOG.debug(f"[call_report] Markdown fetch failed for call_sid={call_sid}: {e}")
            return None


# ============================================================================
#  PATCH APPLICATOR — atomic, backup-and-revert
# ============================================================================
class PatchApplicator:
    def __init__(self, patch_dir: Path, max_loc: int, max_files: int):
        self.patch_dir = patch_dir.resolve()
        self.max_loc = max_loc
        self.max_files = max_files
        self.backups: dict[Path, bytes] = {}

    @staticmethod
    def _delta_loc(old: str, new: str) -> int:
        old_lines = old.count("\n") + 1
        new_lines = new.count("\n") + 1
        return abs(new_lines - old_lines) + min(old_lines, new_lines) // 4

    def apply(self, proposal: dict) -> tuple[bool, list[str], str]:
        """Returns (success, applied_files, error_msg)."""
        patches = proposal.get("patches", [])
        if not patches:
            return False, [], proposal.get("reason", "no-patches")
        if len(patches) > self.max_files:
            return False, [], f"too-many-files:{len(patches)}>{self.max_files}"

        plans: list[tuple[Path, str, str]] = []
        total_loc = 0
        for p in patches:
            rel = (p.get("file") or "").lstrip("/")
            if not rel:
                return False, [], "patch-missing-file"
            target = (self.patch_dir / rel).resolve()
            try:
                target.relative_to(self.patch_dir)
            except ValueError:
                return False, [], f"path-escape:{target}"
            if not target.is_file():
                return False, [], f"missing-file:{rel}"
            content = target.read_text(encoding="utf-8")
            search = p.get("search", "")
            replace = p.get("replace", "")
            if not search:
                return False, [], "empty-search"
            if search not in content:
                return False, [], f"search-not-found:{rel}"
            if content.count(search) > 1:
                return False, [], f"search-ambiguous:{rel}"
            new_content = content.replace(search, replace, 1)
            total_loc += self._delta_loc(search, replace)
            plans.append((target, content, new_content))

        if total_loc > self.max_loc:
            return False, [], f"too-many-loc:{total_loc}>{self.max_loc}"

        applied: list[str] = []
        for target, old, new in plans:
            self.backups[target] = old.encode("utf-8")
            target.write_text(new, encoding="utf-8")
            applied.append(str(target.relative_to(self.patch_dir)))
            LOG.info(f"[patch] wrote {target.name} (loc≈{self._delta_loc(old,new)})")
        return True, applied, ""

    def revert(self):
        for path, original in self.backups.items():
            path.write_bytes(original)
            LOG.warning(f"[patch] REVERTED {path.name}")
        self.backups.clear()

    def commit(self):
        self.backups.clear()


# ============================================================================
#  AGENT RESTART + HEALTH GATE
# ============================================================================
async def restart_and_wait_healthy(restart_cmd: str, health_url: str,
                                    timeout_s: int = 60) -> bool:
    LOG.info(f"[restart] cmd: {restart_cmd}")
    try:
        proc = await asyncio.create_subprocess_shell(
            restart_cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await asyncio.wait_for(proc.communicate(), timeout=30)
    except Exception as e:
        LOG.error(f"[restart] failed to exec: {e}")
        return False

    deadline = time.monotonic() + timeout_s
    async with httpx.AsyncClient(timeout=3.0) as cli:
        while time.monotonic() < deadline:
            try:
                r = await cli.get(health_url)
                if 200 <= r.status_code < 400:
                    LOG.info("[restart] agent healthy")
                    return True
            except Exception:
                pass
            await asyncio.sleep(2)
    LOG.error(f"[restart] agent did NOT come back healthy within {timeout_s}s")
    return False


# ============================================================================
#  HEARTBEAT
# ============================================================================
async def _heartbeat_writer(path: Path, interval_s: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            path.write_text(str(int(time.time())))
        except Exception:
            pass
        await asyncio.sleep(interval_s)


# ============================================================================
#  SCENARIO POOL — split into 3 disjoint chunks per bucket
# ============================================================================
async def _build_bucket_pool(phase: str, bucket: str, workers: int,
                              args: argparse.Namespace) -> list[ScenarioOutcome]:
    """
    Run *all* scenarios tagged with this bucket once to produce the pool.
    On subsequent attempts within the same bucket we slice this pool into
    3 disjoint chunks of step_size for the gate.

    Note: outcome rows are placeholders for 'discoverable scenario IDs' —
    we use them only for ID enumeration, not for pass/fail. The actual
    gate runs them again per-step.
    """
    LOG.info(f"[pool] enumerating scenarios for bucket={bucket}")
    outcomes = await _run_scenarios(
        phase, workers,
        bucket_filter=bucket,
        timeout_s=args.timeout_s,
    )
    LOG.info(f"[pool] bucket={bucket}: {len(outcomes)} scenarios discovered")
    return outcomes


def _slice_pool(pool_ids: list[str], step_size: int, attempt_no: int) -> list[list[str]]:
    """
    Deterministically slice the pool into 3 disjoint chunks of step_size.
    Different attempts get different shuffles (seeded by attempt_no) so
    you don't keep hitting the same 30 scenarios on every retry.
    """
    if len(pool_ids) < step_size * 3:
        LOG.warning(f"[gate] pool only has {len(pool_ids)} ids, "
                    f"need {step_size*3} for full 3-step gate — overlap may occur")
    rng = random.Random(hash((attempt_no, tuple(pool_ids))) & 0xFFFFFFFF)
    shuffled = pool_ids.copy()
    rng.shuffle(shuffled)
    chunks: list[list[str]] = []
    for i in range(3):
        chunks.append(shuffled[i*step_size : (i+1)*step_size])
    # if pool is too small, top up by reusing — every chunk still distinct subset
    for i, ch in enumerate(chunks):
        if len(ch) < step_size:
            extras = [x for x in shuffled if x not in ch][: step_size - len(ch)]
            chunks[i] = ch + extras
    return chunks


# ============================================================================
#  SURGICAL FIX LOOP — one cluster at a time, smoke-gated
# ============================================================================
async def _apply_fixes_sequentially(
    clusters: list[FailureCluster],
    smoke_pool_ids: list[str],
    bucket: str,
    args: argparse.Namespace,
    bridge: ClaudeBridge,
) -> list[dict]:
    fixes_log: list[dict] = []
    patch_dir = Path(args.patch_dir).resolve()

    for cluster in clusters:
        if cluster.fix_attempts >= args.max_fix_per_cluster:
            cluster.state = IssueState.UNFIXABLE
            cluster.notes.append("max-fix-per-cluster")
            fixes_log.append({"cluster": cluster.cluster_id,
                              "result": "skipped", "reason": "max-fix-per-cluster"})
            continue

        LOG.info(f"[fix] cluster={cluster.cluster_id} bucket={bucket} "
                 f"count={cluster.count} sig={cluster.signature!r}")
        cluster.fix_attempts += 1
        cluster.state = IssueState.TRIAGED

        # 1) propose
        proposal = bridge.propose_fix(cluster, patch_dir,
                                       args.max_loc, args.max_files)
        if not proposal.get("patches"):
            cluster.notes.append(f"no-patch:{proposal.get('reason')}")
            fixes_log.append({"cluster": cluster.cluster_id,
                              "result": "no-patch", "reason": proposal.get("reason")})
            continue
        cluster.suspect_files = proposal.get("suspect_files", [])

        # 2) judge
        verdict = bridge.judge_patch(cluster, proposal,
                                      args.max_loc, args.max_files)
        if not verdict.get("approve"):
            cluster.notes.append(f"judge-rejected:{verdict.get('reasons')}")
            fixes_log.append({"cluster": cluster.cluster_id,
                              "result": "judge-rejected",
                              "reasons": verdict.get("reasons")})
            continue

        # 3) apply
        applicator = PatchApplicator(patch_dir, args.max_loc, args.max_files)
        ok, files, err = applicator.apply(proposal)
        if not ok:
            cluster.notes.append(f"apply-failed:{err}")
            fixes_log.append({"cluster": cluster.cluster_id,
                              "result": "apply-failed", "error": err})
            continue
        cluster.state = IssueState.PATCHED

        # 4) restart + health gate
        if not await restart_and_wait_healthy(args.restart_cmd, args.health_url):
            applicator.revert()
            await restart_and_wait_healthy(args.restart_cmd, args.health_url)
            cluster.state = IssueState.REGRESSED
            cluster.notes.append("restart-failed-reverted")
            fixes_log.append({"cluster": cluster.cluster_id,
                              "result": "restart-failed-reverted",
                              "files": files})
            continue

        # 5) smoke gate — N canary scenarios from passing pool
        if args.smoke_canary > 0 and smoke_pool_ids:
            n = min(args.smoke_canary, len(smoke_pool_ids))
            smoke_ids = random.sample(smoke_pool_ids, n)
            LOG.info(f"[fix] smoke gate: {n} canaries → {smoke_ids}")
            smoke_outcomes = await _run_scenarios(
                args.phase, max(2, args.workers // 2),
                scenario_ids=smoke_ids,
                timeout_s=args.timeout_s,
            )
            regressed = [o.scenario_id for o in smoke_outcomes if not o.passed]
            if regressed:
                applicator.revert()
                await restart_and_wait_healthy(args.restart_cmd, args.health_url)
                cluster.state = IssueState.REGRESSED
                cluster.notes.append(f"smoke-regressed:{regressed}")
                fixes_log.append({"cluster": cluster.cluster_id,
                                  "result": "smoke-regressed-reverted",
                                  "files": files,
                                  "regressed_canary": regressed})
                continue

        # 6) commit
        applicator.commit()
        cluster.state = IssueState.VERIFIED
        fixes_log.append({"cluster": cluster.cluster_id,
                          "result": "applied",
                          "files": files,
                          "root_cause": proposal.get("root_cause", "")})
        LOG.info(f"[fix] cluster {cluster.cluster_id} fix COMMITTED")

    return fixes_log


# ============================================================================
#  3-STEP GATE PER BUCKET
# ============================================================================
async def _run_3step_gate(
    bucket: str,
    bucket_report: BucketReport,
    pool_ids: list[str],
    args: argparse.Namespace,
    bridge: Optional[ClaudeBridge],
    global_canary_pool: list[str],
) -> bool:
    """
    Returns True if bucket validates within max_attempts.
    """
    threshold = bucket_report.threshold

    for attempt_no in range(1, args.max_attempts + 1):
        att = GateAttempt(
            attempt_no=attempt_no,
            started_at=datetime.now(timezone.utc).isoformat(),
            threshold=threshold,
        )
        bucket_report.attempts.append(att)
        t0 = time.monotonic()

        chunks = _slice_pool(pool_ids, args.step_size, attempt_no)
        all_outcomes: list[ScenarioOutcome] = []
        gate_failed = False

        for step_idx, step_ids in enumerate(chunks, start=1):
            LOG.info(f"[gate] bucket={bucket} attempt={attempt_no} step={step_idx} "
                     f"({len(step_ids)} scenarios)")
            outcomes = await _run_scenarios(
                args.phase, args.workers,
                scenario_ids=step_ids,
                bucket_filter=bucket,
                timeout_s=args.timeout_s,
            )
            sr = StepResult(step=step_idx, scenario_ids=step_ids, outcomes=outcomes)
            att.steps.append(sr)
            all_outcomes.extend(outcomes)

            combined_so_far = sum(s.passed for s in att.steps) / max(1, sum(s.total for s in att.steps))
            LOG.info(f"[gate]   step {step_idx}: {sr.passed}/{sr.total} "
                     f"({sr.rate*100:.1f}%)  combined={combined_so_far*100:.1f}%")

            # Step 1: must alone pass threshold
            # Step 2/3: combined-so-far must pass threshold
            criterion = sr.rate if step_idx == 1 else combined_so_far
            if criterion < threshold:
                att.final_state = f"failed_step{step_idx}"
                gate_failed = True
                LOG.warning(f"[gate]   step {step_idx} FAILED criterion={criterion*100:.1f}% "
                            f"< threshold={threshold*100:.0f}%")
                break

        att.duration_s = time.monotonic() - t0

        if not gate_failed:
            att.final_state = "passed_combined"
            bucket_report.final_combined_rate = att.combined_rate()
            LOG.info(f"[gate] bucket={bucket} VALIDATED on attempt {attempt_no} "
                     f"(combined={att.combined_rate()*100:.1f}%)")
            # add validated bucket scenarios to global canary pool
            for o in all_outcomes:
                if o.passed and o.scenario_id not in global_canary_pool:
                    global_canary_pool.append(o.scenario_id)
            return True

        # GATE FAILED — fix loop (skip if last attempt)
        if attempt_no >= args.max_attempts:
            LOG.error(f"[gate] bucket={bucket} EXHAUSTED after {attempt_no} attempts")
            bucket_report.final_combined_rate = att.combined_rate()
            break

        # cluster + fix
        clusters = cluster_failures(all_outcomes, bucket)
        if not clusters:
            LOG.warning(f"[gate] no failure clusters but gate failed (timeouts?) — retrying")
            await asyncio.sleep(args.between_attempts_s)
            continue

        LOG.info(f"[gate] {len(clusters)} cluster(s) found; entering fix loop")
        for i, c in enumerate(clusters[:5], 1):
            LOG.info(f"[gate]   cluster #{i}: count={c.count} sig={c.signature!r}")

        if bridge is None:
            LOG.warning("[gate] no bridge → manual fix mode; "
                        f"touch {Path(args.ckpt_dir)/'fix_done'} when ready")
            wait = Path(args.ckpt_dir) / "fix_done"
            while not wait.exists():
                await asyncio.sleep(5)
            wait.unlink()
        else:
            # combine global canary pool + this bucket's previously-passing as smoke set
            smoke_pool = list(set(global_canary_pool) |
                              {o.scenario_id for o in all_outcomes if o.passed})
            fixes = await _apply_fixes_sequentially(
                clusters, smoke_pool, bucket, args, bridge)
            att.fixes_applied = fixes

        await asyncio.sleep(args.between_attempts_s)

    return False


# ============================================================================
#  MAIN ORCHESTRATION
# ============================================================================
async def main_loop(args: argparse.Namespace) -> int:
    Path(args.report_dir).mkdir(parents=True, exist_ok=True)
    Path(args.ckpt_dir).mkdir(parents=True, exist_ok=True)

    # heartbeat
    hb_task = asyncio.create_task(
        _heartbeat_writer(Path(args.ckpt_dir) / "heartbeat", args.heartbeat_s))

    bridge: Optional[ClaudeBridge] = None
    if not os.environ.get("SKIP_FIX_GENERATION"):
        try:
            bridge = ClaudeBridge()
            LOG.info("[init] Claude bridge ready (Opus + Haiku)")
        except Exception as e:
            LOG.warning(f"[init] Claude bridge unavailable: {e} — "
                        "running in validate-only mode")

    # pre-flight: agent must be reachable
    async with httpx.AsyncClient(timeout=5.0) as cli:
        try:
            r = await cli.get(args.health_url)
            if r.status_code >= 400:
                LOG.error(f"[init] health endpoint returned {r.status_code}")
                return 2
        except Exception as e:
            LOG.error(f"[init] cannot reach {args.health_url}: {e}")
            return 2

    # build bucket list
    enabled_set = (set(args.buckets.split(",")) if args.buckets and args.buckets != "all"
                   else {b[0] for b in BUCKETS_DEF})
    bucket_defs = sorted(
        [b for b in BUCKETS_DEF if b[0] in enabled_set],
        key=lambda b: (b[2], b[1]),  # tier first, then priority
    )

    phase_report = PhaseReport(
        phase=args.phase,
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    t_phase_start = time.monotonic()

    # global regression-canary pool grows as buckets get validated
    global_canary_pool: list[str] = []

    for name, priority, tier, baseline_fails, fix_desc in bucket_defs:
        threshold = TIER_1_THRESHOLD if tier == 1 else TIER_2_THRESHOLD
        rep = BucketReport(
            name=name, priority=priority, tier=tier, threshold=threshold,
            status=BucketStatus.RUNNING.value,
        )
        phase_report.buckets.append(rep)

        LOG.info("=" * 70)
        LOG.info(f"  BUCKET {priority}/{len(bucket_defs)}: {name}  (Tier {tier}, "
                 f"threshold {threshold*100:.0f}%)")
        LOG.info(f"  baseline failures: {baseline_fails} · fix scope: {fix_desc}")
        LOG.info("=" * 70)

        # build scenario pool for this bucket
        pool_outcomes = await _build_bucket_pool(args.phase, name, args.workers, args)
        pool_ids = [o.scenario_id for o in pool_outcomes]
        rep.canary_pool = pool_ids

        if len(pool_ids) < 3:
            LOG.warning(f"[orch] bucket={name} has only {len(pool_ids)} scenarios — skipping")
            rep.status = BucketStatus.SKIPPED.value
            rep.skipped_reason = f"pool-too-small:{len(pool_ids)}"
            continue

        # 3-step gate with fix loop
        ok = await _run_3step_gate(
            name, rep, pool_ids, args, bridge, global_canary_pool,
        )
        rep.status = (BucketStatus.VALIDATED if ok else BucketStatus.UNRESOLVED).value

        # write per-bucket checkpoint
        _write_bucket_checkpoint(rep, args)

        if not ok and args.stop_on_unresolved:
            LOG.error(f"[orch] bucket={name} unresolved → stopping (--stop-on-unresolved)")
            break

        # short cool-down between buckets so the agent settles
        await asyncio.sleep(args.between_buckets_s)

    phase_report.completed_at = datetime.now(timezone.utc).isoformat()
    phase_report.duration_s = time.monotonic() - t_phase_start

    _write_phase_report(phase_report, args)

    hb_task.cancel()

    # exit code
    if phase_report.unresolved == 0 and phase_report.validated > 0:
        return 0
    return 1


# ============================================================================
#  CHECKPOINT + REPORT WRITERS
# ============================================================================
def _write_bucket_checkpoint(rep: BucketReport, args: argparse.Namespace):
    p = Path(args.ckpt_dir) / f"bucket_{rep.name}.json"
    try:
        p.write_text(json.dumps(asdict(rep), indent=2, default=str))
    except Exception as e:
        LOG.warning(f"[ckpt] write failed: {e}")


def _write_phase_report(rep: PhaseReport, args: argparse.Namespace):
    out_json = Path(args.report_dir) / f"phase_{args.phase}_validator.json"
    out_json.write_text(json.dumps(asdict(rep), indent=2, default=str))

    md = [
        f"# Phase {args.phase.upper()} Validation Report",
        "",
        f"- **Started**:   {rep.started_at}",
        f"- **Completed**: {rep.completed_at}",
        f"- **Duration**:  {rep.duration_s:.0f}s ({rep.duration_s/60:.1f}m)",
        f"- **Validated**: {rep.validated}/{rep.total_enabled}",
        f"- **Unresolved**: {rep.unresolved}",
        "",
        "| # | Bucket | Tier | Threshold | Status | Combined % | Attempts | Fixes |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for b in rep.buckets:
        n_fixes = sum(len(a.fixes_applied) for a in b.attempts)
        md.append(
            f"| {b.priority} | {b.name} | T{b.tier} | "
            f"{b.threshold*100:.0f}% | {b.status} | "
            f"{b.final_combined_rate*100:.1f}% | "
            f"{len(b.attempts)} | {n_fixes} |"
        )
    
    # Add call reports section
    md.append("")
    md.append("## Call Reports")
    md.append("")
    md.append("Each scenario generated a call with a unique call_sid. Below are the aggregated metrics:")
    md.append("")
    
    # Collect all call reports and compute aggregate metrics
    all_call_bundles = []
    total_latency_sum = 0
    total_latency_count = 0
    total_tools_called = 0
    total_tools_expected = 0
    
    for b in rep.buckets:
        for attempt in b.attempts:
            for step in attempt.steps:
                for outcome in step.outcomes:
                    if outcome.call_report_bundle and outcome.call_report_bundle.get("found"):
                        all_call_bundles.append(outcome.call_report_bundle)
                        # Extract metrics
                        agg_health = outcome.call_report_bundle.get("aggregate_health", {})
                        if agg_health.get("total_latency_ms"):
                            total_latency_sum += agg_health["total_latency_ms"]
                            total_latency_count += 1
                        total_tools_called += len(outcome.tools_called)
                        total_tools_expected += len(outcome.tools_expected)
    
    if all_call_bundles:
        avg_latency = total_latency_sum / max(1, total_latency_count) if total_latency_count > 0 else 0
        md.append(f"**Total calls processed**: {len(all_call_bundles)}")
        md.append(f"**Average latency**: {avg_latency:.0f}ms")
        md.append(f"**Total tools called**: {total_tools_called}")
        md.append(f"**Total tools expected**: {total_tools_expected}")
        md.append("")
        md.append("### Call SID Summary")
        md.append("")
        md.append("| Call SID | Bucket | Latency (ms) | Tools | Status |")
        md.append("|----------|--------|--------------|-------|--------|")
        
        for bundle in all_call_bundles[:50]:  # Limit to first 50 for readability
            call_sid = bundle.get("call_sid", "unknown")
            call_data = bundle.get("call", {})
            agg_health = bundle.get("aggregate_health", {})
            latency_ms = agg_health.get("total_latency_ms", 0)
            tools_count = len(bundle.get("tool_calls", []))
            call_status = "passed" if not agg_health.get("issues", []) else "issues"
            
            md.append(f"| `{call_sid}` | {call_data.get('bucket_name', '—')} | {latency_ms} | {tools_count} | {call_status} |")
    else:
        md.append("No call reports available (DATABASE_URL not set or no calls found).")
    
    out_md = Path(args.report_dir) / f"phase_{args.phase}_validator.md"
    out_md.write_text("\n".join(md))
    LOG.info(f"[report] {out_json}\n         {out_md}")


# ============================================================================
#  CLI
# ============================================================================
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__.split("\n")[1] if __doc__ else "",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    # phase + buckets
    p.add_argument("--phase", default="a")
    p.add_argument("--buckets", default="all",
                   help="comma-separated bucket names, or 'all'")
    p.add_argument("--workers", type=int, default=5,
                   help="concurrent text scenarios per step")
    p.add_argument("--step-size", type=int, default=10,
                   help="scenarios per step (3 steps per attempt)")
    p.add_argument("--max-attempts", type=int, default=3,
                   help="max gate attempts per bucket")
    p.add_argument("--timeout-s", type=float, default=180.0,
                   help="per-scenario timeout")
    # fix loop
    p.add_argument("--max-fix-per-cluster", type=int, default=3)
    p.add_argument("--max-loc", type=int, default=50,
                   help="patch size guardrail (LOC delta)")
    p.add_argument("--max-files", type=int, default=2,
                   help="patch breadth guardrail")
    p.add_argument("--smoke-canary", type=int, default=3,
                   help="canary count after each patch (regression gate)")
    p.add_argument("--between-attempts-s", type=int, default=15)
    p.add_argument("--between-buckets-s", type=int, default=10)
    p.add_argument("--stop-on-unresolved", action="store_true",
                   help="halt entire phase if any bucket fails to validate")
    # paths + service
    p.add_argument("--patch-dir", default=os.environ.get(
        "SAILLY_PATCH_DIR", "/home/charles2/sailly-browser-demo/server"))
    p.add_argument("--report-dir", default=os.environ.get(
        "SAILLY_REPORT_DIR", "/home/charles2/sailly-browser-demo/reports"))
    p.add_argument("--ckpt-dir", default=os.environ.get(
        "SAILLY_CKPT_DIR", "/var/lib/sailly/test-ckpt"))
    p.add_argument("--restart-cmd", default=os.environ.get(
        "SAILLY_RESTART_CMD", "sudo systemctl restart sailly-voice-agent"))
    p.add_argument("--health-url", default=os.environ.get(
        "SAILLY_HEALTH_URL", "http://localhost:8080/health"))
    p.add_argument("--heartbeat-s", type=int, default=30)
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def _setup_logging(verbose: bool):
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    args = _parse_args()
    _setup_logging(args.verbose)
    sys.exit(asyncio.run(main_loop(args)))


if __name__ == "__main__":
    main()
