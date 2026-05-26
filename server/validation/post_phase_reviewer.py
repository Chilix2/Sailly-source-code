"""
Post-phase external review pack generator.

Prepares structured evidence for an independent GPT-5.5 (or human) review after
a validation phase completes. Does NOT change validation loop behavior.

Usage:
  PYTHONPATH=. venv/bin/python3 -m server.validation.post_phase_reviewer \\
    --output-dir /tmp/scenario_validation_truth_1779453376 \\
    --phase a \\
    --sample-count 6
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from server.validation.postgres_metrics_fetcher import PostgresMetricsFetcher


@dataclass
class BatchSummary:
    batch_key: str
    base_script_id: str
    difficulty: str
    completion_status: str
    threshold_met: bool
    force_advanced: bool
    audit_failed: bool
    effective_score: Optional[float]
    pass_rate: float
    attempt: int
    call_sids: List[str] = field(default_factory=list)
    artifact_file: str = ""
    grok_composite: Optional[float] = None
    achtung_flag_count: int = 0


@dataclass
class SpotCheck:
    batch_key: str
    reason: str
    call_sid: str
    transcript: Optional[str]
    transcript_turns: int = 0


def _batch_key(data: Dict[str, Any]) -> str:
    return f"{data['base_script_id']}_{data['difficulty']}"


def _phase_prefix(phase: str) -> str:
    return phase.strip().upper()


def load_latest_batch_results(output_dir: Path, phase: str) -> Dict[str, Tuple[Path, Dict[str, Any]]]:
    """Return latest artifact per batch key for the given phase letter."""
    prefix = _phase_prefix(phase)
    latest: Dict[str, Tuple[Path, Dict[str, Any]]] = {}
    for path in sorted(output_dir.glob("batch_result_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        key = _batch_key(data)
        if not key.startswith(prefix):
            continue
        prev = latest.get(key)
        if prev is None or path.stat().st_mtime > prev[0].stat().st_mtime:
            latest[key] = (path, data)
    return latest


def summarize_batches(latest: Dict[str, Tuple[Path, Dict[str, Any]]]) -> List[BatchSummary]:
    rows: List[BatchSummary] = []
    for key in sorted(latest):
        path, data = latest[key]
        grok = data.get("grok_report") or {}
        rows.append(
            BatchSummary(
                batch_key=key,
                base_script_id=data.get("base_script_id", ""),
                difficulty=data.get("difficulty", ""),
                completion_status=data.get("completion_status", "unknown"),
                threshold_met=bool(data.get("threshold_met")),
                force_advanced=bool(data.get("force_advanced")),
                audit_failed=bool(data.get("audit_failed")),
                effective_score=data.get("effective_score") or data.get("composite_score"),
                pass_rate=float(data.get("pass_rate") or 0.0),
                attempt=int(data.get("attempt") or 0),
                call_sids=list(data.get("call_sids") or []),
                artifact_file=str(path),
                grok_composite=grok.get("composite_score"),
                achtung_flag_count=len(grok.get("achtung_flags") or []),
            )
        )
    return rows


def _pick_spot_checks(rows: List[BatchSummary], sample_count: int) -> List[Tuple[BatchSummary, str]]:
    """Select batches worth transcript spot-checking."""
    picks: List[Tuple[BatchSummary, str]] = []
    seen_keys: set[str] = set()

    def add(row: BatchSummary, reason: str) -> None:
        if row.batch_key in seen_keys:
            return
        seen_keys.add(row.batch_key)
        picks.append((row, reason))

    for row in rows:
        if row.threshold_met and not row.force_advanced:
            add(row, "truthful_pass")

    for row in rows:
        if row.force_advanced and (row.effective_score or 0) < 80:
            add(row, "force_advanced_low_score")

    for row in rows:
        if row.threshold_met and not row.force_advanced and row.pass_rate < 0.5:
            add(row, "passed_but_low_persona_pass_rate")

    for row in rows:
        if row.force_advanced and row.pass_rate >= 0.9:
            add(row, "force_advanced_high_persona_pass_rate")

    for row in rows:
        if row.audit_failed:
            add(row, "audit_failed")

    return picks[: max(sample_count, 1)]


async def _fetch_spot_checks(
    picks: List[Tuple[BatchSummary, str]],
    fetcher: PostgresMetricsFetcher,
) -> List[SpotCheck]:
    checks: List[SpotCheck] = []
    for row, reason in picks:
        sid = row.call_sids[0] if row.call_sids else ""
        transcript = await fetcher.fetch_transcript(sid) if sid else None
        turns = len(re.findall(r"^\[Turn ", transcript or "", re.MULTILINE))
        checks.append(
            SpotCheck(
                batch_key=row.batch_key,
                reason=reason,
                call_sid=sid,
                transcript=transcript,
                transcript_turns=turns,
            )
        )
    return checks


def build_review_pack(
    output_dir: Path,
    phase: str,
    rows: List[BatchSummary],
    spot_checks: List[SpotCheck],
) -> Dict[str, Any]:
    truthful_pass = [r for r in rows if r.threshold_met and not r.force_advanced]
    force_advanced = [r for r in rows if r.force_advanced]
    failed = [r for r in rows if not r.threshold_met and not r.force_advanced]

    return {
        "schema_version": "1.0",
        "review_type": "post_phase_evidence_pack",
        "external_auditor_model": "gpt-5.5",
        "generated_at_unix": int(time.time()),
        "output_dir": str(output_dir),
        "phase": _phase_prefix(phase),
        "summary": {
            "total_batches": len(rows),
            "truthful_pass_count": len(truthful_pass),
            "force_advanced_count": len(force_advanced),
            "failed_count": len(failed),
            "truthful_pass_rate": (len(truthful_pass) / len(rows)) if rows else 0.0,
            "avg_effective_score": (
                sum(r.effective_score or 0 for r in rows) / len(rows) if rows else 0.0
            ),
        },
        "batches": [asdict(r) for r in rows],
        "spot_checks": [asdict(s) for s in spot_checks],
        "review_questions": [
            "Do truthful_pass batches actually meet threshold without force-advance?",
            "Do force_advanced batches mask product failures the loop should not trust?",
            "Do Grok composite scores match transcript evidence in spot checks?",
            "Are harness flags (KEIN_READBACK, PREIS_FALSCH, persona pass rate) consistent with transcripts?",
            "Should this phase be trusted as done before continuing?",
        ],
        "verdict_fields": {
            "verifier_verdict": "pass | warn | block",
            "product_verdict": "pass | warn | block",
            "phase_trusted": "true | false",
            "notes": "free text",
        },
    }


async def generate_review_pack(
    output_dir: Path,
    phase: str,
    sample_count: int = 6,
) -> Path:
    latest = load_latest_batch_results(output_dir, phase)
    if not latest:
        raise SystemExit(f"No batch_result_* artifacts found for phase {phase.upper()} in {output_dir}")

    rows = summarize_batches(latest)
    picks = _pick_spot_checks(rows, sample_count)
    fetcher = PostgresMetricsFetcher()
    spot_checks = await _fetch_spot_checks(picks, fetcher)

    pack = build_review_pack(output_dir, phase, rows, spot_checks)
    out_path = output_dir / f"post_phase_review_{_phase_prefix(phase)}_{int(time.time())}.json"
    out_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate post-phase external review evidence pack")
    parser.add_argument("--output-dir", required=True, help="Validation output directory")
    parser.add_argument("--phase", required=True, help="Phase letter, e.g. a")
    parser.add_argument("--sample-count", type=int, default=6, help="Transcript spot-check count")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    if not output_dir.is_dir():
        raise SystemExit(f"Output dir not found: {output_dir}")

    out_path = asyncio.run(generate_review_pack(output_dir, args.phase, args.sample_count))
    print(out_path)


if __name__ == "__main__":
    main()
