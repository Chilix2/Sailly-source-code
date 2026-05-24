"""
Light validation loop for debugging.

Purpose:
  - Keep the real caller/persona execution path.
  - Avoid Grok audit and Haiku auto-fixer by default.
  - Score deterministically from Postgres transcripts/tool calls/Achtung flags.
  - Run one-persona smoke before a full 7-persona batch.
  - Emit compact evidence packs for Cursor GPT-5.5 / Codex review.

This is intentionally separate from scenario_based_loop.py so the heavy
validation contract remains unchanged.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from server.validation.phase_runner import run_one_scenario
from server.validation.postgres_metrics_fetcher import PostgresMetricsFetcher
from server.validation.scenario_generator import ScenarioMatrix
from server.validation.scenario_loader import ValidationScenario

logger = logging.getLogger(__name__)


_PERSONA_ORDER = ["neutral", "busy", "elderly", "skeptical", "impatient", "rude", "indecisive"]


@dataclass
class LightScenarioResult:
    scenario_id: str
    persona: str
    passed: bool
    deterministic_score: float
    call_sid: str = ""
    tools_called: list[str] = field(default_factory=list)
    tools_expected: list[str] = field(default_factory=list)
    tools_missing: list[str] = field(default_factory=list)
    failure_tags: list[str] = field(default_factory=list)
    achtung_flags: list[dict[str, Any]] = field(default_factory=list)
    failed_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    loop_detections: list[dict[str, Any]] = field(default_factory=list)
    transcript_excerpt: str = ""
    duration_s: float = 0.0


@dataclass
class LightBatchResult:
    batch_key: str
    phase: str
    attempt: int
    mode: str
    passed: bool
    deterministic_score: float
    pass_rate: float
    total: int
    scenario_results: list[LightScenarioResult] = field(default_factory=list)
    repeated_failure_signature: Optional[str] = None
    known_issues_advice: str = ""
    duration_s: float = 0.0
    artifact_path: str = ""


def _phase_to_num(phase: str) -> int:
    return ord(phase.strip().lower()) - ord("a")


def _batch_parts(batch_key: str) -> tuple[str, str]:
    if "_" not in batch_key:
        raise ValueError("batch key must look like B1.2_D2")
    base_id, difficulty = batch_key.split("_", 1)
    return base_id, difficulty


def _scenario_from_dict(sc_dict: dict[str, Any]) -> ValidationScenario:
    return ValidationScenario(
        id=sc_dict.get("id", "unknown"),
        phase=int(sc_dict.get("phase", 0)),
        description=sc_dict.get("script", sc_dict.get("caller_goal", "")),
        caller_goal=sc_dict.get("caller_goal", ""),
        caller_identity=sc_dict.get("caller_identity", {}),
        caller_patience_turns=int(sc_dict.get("caller_patience_turns", 15)),
        tenant_id=sc_dict.get("tenant_id", "doboo"),
        confirmation_phrases=sc_dict.get("confirmation_phrases", ["ja", "ja genau", "ja bitte", "passt so"]),
        expectations=sc_dict.get("expectations", {}),
        required_data=sc_dict.get("required_data", {}),
    )


def _failure_signature(result: LightBatchResult) -> str:
    """Compact signature used to stop repeated failed attempts."""
    bits: list[str] = []
    for sr in result.scenario_results:
        for flag in sr.achtung_flags:
            text = flag.get("flag", "")
            m = re.search(r"Achtung Sailly:\s*([A-ZÄÖÜ_]+)", text, re.IGNORECASE)
            if m:
                bits.append(m.group(1).upper())
        if sr.tools_missing:
            bits.extend(f"missing_tool:{t}" for t in sr.tools_missing)
        if sr.failed_tool_calls:
            bits.extend(f"failed_tool:{t.get('tool')}" for t in sr.failed_tool_calls)
        if sr.loop_detections:
            bits.append("loop")
        bits.extend(t for t in sr.failure_tags if t)
    return "|".join(sorted(set(bits))) or "no_failure_signature"


def _score_scenario(
    raw_result: Any,
    metrics: dict[str, Any],
    transcript: str,
) -> LightScenarioResult:
    call_sid = getattr(raw_result, "call_sid", "") or ""
    expected = list(getattr(raw_result, "tools_expected", []) or [])
    called = list(getattr(raw_result, "tools_called", []) or [])
    missing = list(getattr(raw_result, "tools_missing", []) or [])
    failure_tags = list(getattr(raw_result, "failure_tags", []) or [])

    flags = [f for f in metrics.get("achtung_flags", []) if f.get("call_sid") == call_sid]
    failed_tools = [f for f in metrics.get("failed_tool_calls", []) if f.get("call_sid") == call_sid]
    loops = [l for l in metrics.get("loop_detections", []) if l.get("call_sid") == call_sid]
    caller_errors = [t for t in failure_tags if t.startswith("caller_detected_error")]
    commit_missing = [t for t in failure_tags if t.startswith("commit_missing")]

    score = 100.0
    score -= 30.0 * len(missing)
    score -= 20.0 * len(failed_tools)
    score -= 25.0 * len(flags)
    score -= 15.0 * len(loops)
    score -= 25.0 * len(caller_errors)
    score -= 10.0 * len(commit_missing)
    if not transcript.strip():
        # Missing Postgres transcript rows are a harness observability gap, not
        # a product failure when the runner itself marked the scenario passed.
        score -= 10.0 if bool(getattr(raw_result, "passed", False)) else 50.0
    score = max(0.0, min(100.0, score))

    deterministic_pass = (
        score >= 80.0
        and not missing
        and not failed_tools
        and not flags
        and not loops
        and not caller_errors
        and not commit_missing
    )

    return LightScenarioResult(
        scenario_id=getattr(raw_result, "scenario_id", ""),
        persona=_persona_from_id(getattr(raw_result, "scenario_id", "")),
        passed=bool(getattr(raw_result, "passed", False)) and deterministic_pass,
        deterministic_score=round(score, 1),
        call_sid=call_sid,
        tools_called=called,
        tools_expected=expected,
        tools_missing=missing,
        failure_tags=failure_tags,
        achtung_flags=flags,
        failed_tool_calls=failed_tools,
        loop_detections=loops,
        transcript_excerpt=transcript[:2500],
        duration_s=float(getattr(raw_result, "duration_s", 0.0) or 0.0),
    )


def _persona_from_id(scenario_id: str) -> str:
    for persona in _PERSONA_ORDER:
        if scenario_id.endswith(f"_{persona}"):
            return persona
    return "unknown"


def _known_issues_advice(batch_key: str, scenario_results: list[LightScenarioResult]) -> str:
    """Use known_issues_advisor with a synthetic report, without invoking any model."""
    try:
        from server.validation.known_issues_advisor import KnownIssuesAdvisor
    except Exception as exc:
        return f"(known issues unavailable: {exc})"

    all_flags = []
    loop_detections = []
    failed_tools = []
    for sr in scenario_results:
        all_flags.extend(sr.achtung_flags)
        loop_detections.extend(sr.loop_detections)
        failed_tools.extend(sr.failed_tool_calls)

    synthetic_report = {
        "metric_scores": {
            "tool_accuracy": 40 if failed_tools or any(sr.tools_missing for sr in scenario_results) else 100,
            "flow": 40 if loop_detections else 100,
            "linguistic": 100,
            "deterministic": 40 if all_flags else 100,
        },
        "improvements": " ".join(
            flag.get("flag", "") for flag in all_flags[:10]
        ),
        "tool_analysis": json.dumps(failed_tools[:10], ensure_ascii=False),
        "achtung_flags": all_flags,
    }
    synthetic_metrics = {
        "achtung_flags": all_flags,
        "loop_detections": loop_detections,
        "failed_tool_calls": failed_tools,
    }
    try:
        return KnownIssuesAdvisor().get_advice_block(synthetic_report, synthetic_metrics, batch_key)
    except Exception as exc:
        return f"(known issues advice failed: {exc})"


class LightValidationLoop:
    def __init__(
        self,
        *,
        output_dir: Path,
        workers: int = 5,
        stagger_s: int = 3,
        max_attempts: int = 3,
        threshold: float = 80.0,
        sailly_ws_url: str = "ws://127.0.0.1:8080/ws/headless",
    ) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.workers = workers
        self.stagger_s = stagger_s
        self.max_attempts = max_attempts
        self.threshold = threshold
        self.sailly_ws_url = sailly_ws_url
        self.matrix = ScenarioMatrix()
        self.fetcher = PostgresMetricsFetcher()

    def select_scenarios(
        self,
        *,
        phase: str,
        batch_key: str,
        persona: Optional[str],
    ) -> list[dict[str, Any]]:
        base_id, difficulty = _batch_parts(batch_key)
        phase_num = _phase_to_num(phase)
        scenarios = [
            s for s in self.matrix.get_all_scenarios_for_phase(phase_num)
            if s.get("base_id") == base_id and s.get("difficulty") == difficulty
        ]
        if persona:
            scenarios = [s for s in scenarios if s.get("persona") == persona]
        return sorted(scenarios, key=lambda s: _PERSONA_ORDER.index(s.get("persona", "neutral")) if s.get("persona") in _PERSONA_ORDER else 999)

    async def run_batch(
        self,
        *,
        phase: str,
        batch_key: str,
        persona: Optional[str],
        attempt: int,
        mode: str,
    ) -> LightBatchResult:
        t0 = time.time()
        scenarios = self.select_scenarios(phase=phase, batch_key=batch_key, persona=persona)
        if not scenarios:
            raise RuntimeError(f"No scenarios found for {batch_key} persona={persona}")

        semaphore = asyncio.Semaphore(self.workers)

        async def run_one(idx: int, sc_dict: dict[str, Any]):
            if idx < self.workers:
                await asyncio.sleep(idx * self.stagger_s)
            async with semaphore:
                scenario = _scenario_from_dict(sc_dict)
                return await run_one_scenario(
                    scenario,
                    sailly_ws_url=self.sailly_ws_url,
                    max_duration_sec=180.0,
                )

        raw_results = await asyncio.gather(*(run_one(i, sc) for i, sc in enumerate(scenarios)))
        call_sids = [getattr(r, "call_sid", "") for r in raw_results if getattr(r, "call_sid", "")]
        metrics = await self.fetcher.fetch_batch_metrics(call_sids)

        transcripts_by_sid: dict[str, str] = {}
        for sid in call_sids:
            transcripts_by_sid[sid] = await self.fetcher.fetch_transcript(sid) or ""

        scenario_results = [
            _score_scenario(r, metrics, transcripts_by_sid.get(getattr(r, "call_sid", ""), ""))
            for r in raw_results
        ]

        total = len(scenario_results)
        passed_count = sum(1 for r in scenario_results if r.passed)
        avg_score = sum(r.deterministic_score for r in scenario_results) / total if total else 0.0
        batch_passed = avg_score >= self.threshold and passed_count == total
        result = LightBatchResult(
            batch_key=batch_key,
            phase=phase.lower(),
            attempt=attempt,
            mode=mode,
            passed=batch_passed,
            deterministic_score=round(avg_score, 1),
            pass_rate=(passed_count / total) if total else 0.0,
            total=total,
            scenario_results=scenario_results,
            known_issues_advice=_known_issues_advice(batch_key, scenario_results),
            duration_s=time.time() - t0,
        )
        result.repeated_failure_signature = _failure_signature(result)
        result.artifact_path = self._write_artifact(result)
        return result

    def _write_artifact(self, result: LightBatchResult) -> str:
        ts = int(time.time())
        persona_part = result.mode.replace(" ", "_")
        path = self.output_dir / f"light_result_{result.batch_key}_{persona_part}_attempt{result.attempt}_{ts}.json"
        path.write_text(json.dumps(asdict(result), indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)


async def _main_async(args: argparse.Namespace) -> int:
    loop = LightValidationLoop(
        output_dir=Path(args.output_dir),
        workers=args.workers,
        stagger_s=args.stagger_s,
        max_attempts=args.max_attempts,
        threshold=args.threshold,
        sailly_ws_url=args.sailly_ws_url,
    )

    previous_signature: Optional[str] = None
    final_result: Optional[LightBatchResult] = None

    for attempt in range(1, args.max_attempts + 1):
        if not args.skip_smoke:
            smoke = await loop.run_batch(
                phase=args.phase,
                batch_key=args.batch,
                persona=args.smoke_persona,
                attempt=attempt,
                mode=f"smoke_{args.smoke_persona}",
            )
            logger.info(
                "[light] smoke %s attempt=%d score=%.1f pass_rate=%.1f%% artifact=%s",
                args.batch, attempt, smoke.deterministic_score, smoke.pass_rate * 100, smoke.artifact_path,
            )
            final_result = smoke
            if not smoke.passed:
                if args.stop_on_repeat_failure and previous_signature == smoke.repeated_failure_signature:
                    logger.warning("[light] repeated smoke failure signature: %s", smoke.repeated_failure_signature)
                    return 2
                previous_signature = smoke.repeated_failure_signature
                continue

        if not args.all_personas:
            return 0 if final_result and final_result.passed else 1

        full = await loop.run_batch(
            phase=args.phase,
            batch_key=args.batch,
            persona=None,
            attempt=attempt,
            mode="all_personas",
        )
        logger.info(
            "[light] full %s attempt=%d score=%.1f pass_rate=%.1f%% artifact=%s",
            args.batch, attempt, full.deterministic_score, full.pass_rate * 100, full.artifact_path,
        )
        final_result = full
        if full.passed:
            return 0
        if args.stop_on_repeat_failure and previous_signature == full.repeated_failure_signature:
            logger.warning("[light] repeated full-batch failure signature: %s", full.repeated_failure_signature)
            return 2
        previous_signature = full.repeated_failure_signature

    return 0 if final_result and final_result.passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Light deterministic validation loop")
    parser.add_argument("--phase", required=True, help="Phase letter, e.g. b")
    parser.add_argument("--batch", required=True, help="Batch key, e.g. B1.2_D2")
    parser.add_argument("--output-dir", default="/tmp/scenario_validation_light")
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--stagger-s", type=int, default=3)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--threshold", type=float, default=80.0)
    parser.add_argument("--smoke-persona", default="neutral", choices=_PERSONA_ORDER)
    parser.add_argument("--skip-smoke", action="store_true", help="Run selected mode without smoke gate")
    parser.add_argument("--all-personas", action="store_true", help="After smoke passes, run all 7 personas")
    parser.add_argument("--no-stop-on-repeat-failure", dest="stop_on_repeat_failure", action="store_false")
    parser.add_argument("--sailly-ws-url", default=os.environ.get("SAILLY_WS_URL", "ws://127.0.0.1:8080/ws/headless"))
    parser.set_defaults(stop_on_repeat_failure=True)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.max_attempts > 3:
        raise SystemExit("light validation max-attempts must be <= 3")
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
