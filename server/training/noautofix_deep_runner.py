"""
noautofix_deep_runner.py — Tier 1 Deep Diagnostic Runner (No Auto-Fix)

Runs only the known-failing scenario IDs from the 5 Tier 1 tool-execution buckets,
repeating each ~102 times (3 noise variants × 34 seeds) to pinpoint exactly where
in the pipeline each failure occurs.

No auto-fixer, no Claude/Gemini patching, no phases.

Output per bucket:
  /tmp/noautofix_deep/<run_id>/bucket_<name>.json

Summary:
  /tmp/noautofix_deep/<run_id>/summary.json

Usage:
  python -m server.training.noautofix_deep_runner
  python -m server.training.noautofix_deep_runner --workers 20 --bucket verify_address
  python -m server.training.noautofix_deep_runner --failing-ids-file /tmp/failing.json
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import dataclasses
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ── Paths ─────────────────────────────────────────────────────────────────────

OUTPUT_ROOT = Path("/tmp/noautofix_deep")
RUNS_MANIFEST = Path("/tmp/validation_runs/runs_manifest.json")
RUNS_ROOT = Path("/tmp/validation_runs")
MODULE_ROOT = Path("/home/charles2/sailly-google-fork")
VENV_PYTHON = MODULE_ROOT / ".venv/bin/python3"

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [DeepRunner] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

TIER1_BUCKETS = ["ai_greeting", "verify_address", "create_order", "send_sms", "get_date_info"]
NOISE_VARIANTS = ["clean"]
# 5 repetitions × 1 noise = 5 runs per failing scenario (comprehensive verification)
N_REPS = 5
CALL_TIMEOUT = 120.0  # seconds per scenario

# Known failing IDs per Tier 1 bucket (from last Phase A baseline, 90.4%).
# Override via --failing-ids-file if you have fresh data.
DEFAULT_FAILING_IDS: Dict[str, List[str]] = {
    "ai_greeting":    ["p2-order-007"],          # broad TRANSFER_KW mutes greeting
    "verify_address": ["p3-angry-05", "p3-impatient-08", "p4-elderly-01", "p2-order-041"],
    "create_order":   ["p3-angry-01", "p2-order-007", "p2-order-004"],
    "send_sms":       ["p2-order-004", "p2-order-007"],
    "get_date_info":  ["p3-angry-02", "p3-faq-order-01", "p2-faq-006", "p2-faq-42"],
}

# ── Diagnosis patterns ────────────────────────────────────────────────────────
# (checked against the full pipeline_events_all list for a run)

DIAGNOSIS_PATTERNS = [
    # Order matters — most specific first
    (r"step2b SKIP.*TRANSFER_KW.*but already transferred",
     "repeat_transfer_suppressed", "node_manager.py step2b — duplicate transfer guard"),
    (r"step2b.*TRANSFER_KW.*ORDER_KW guard blocked",
     "transfer_blocked_by_order_kw", "node_manager.py step2b — ORDER_KW guard"),
    (r"step2b.*TRANSFER_KW.*RESERVATION_KW guard blocked",
     "transfer_blocked_by_reservation_kw", "node_manager.py step2b — RESERVATION_KW guard"),
    (r"Injected transfer_to_tier2",
     "early_transfer", "node_manager.py step2b — TRANSFER_KW broad match triggered escalation"),
    (r"step10 SKIP.*delivery_address_mentioned=False",
     "step10_skipped_no_delivery_mention", "node_manager.py step10 — delivery_address_mentioned never set"),
    (r"step10 SKIP.*verify_address_called=True",
     "step10_skipped_already_called", "node_manager.py step10 — verify_address_called was True"),
    (r"step11 SKIP.*delivery_address_mentioned=False",
     "step11_skipped_no_delivery_mention", "node_manager.py step11 — delivery_address_mentioned never set"),
    (r"step11 SKIP.*order_intent=False",
     "step11_skipped_no_order_intent", "node_manager.py step11 — order_intent never set"),
    (r"step11 SKIP.*selected_dish=None",
     "step11_skipped_no_dish", "node_manager.py step11 — selected_dish never populated"),
    (r"step2c SKIP.*get_date_info_called=True",
     "date_info_already_called", "node_manager.py step2c — get_date_info already fired"),
    (r"step2c SKIP.*no_trigger",
     "step2c_no_trigger", "node_manager.py step2c — no DATE_REL_KW match and no reservation_intent"),
    (r"POST-PARSE dedup send_sms",
     "send_sms_deduped", "adk_runner.py post-reparse dedup — send_sms stripped as duplicate"),
    (r"BLOCKED duplicate create_order",
     "create_order_blocked_dedup", "adk_runner.py dedup guard — create_order blocked"),
    (r"BLOCKED duplicate send_sms",
     "send_sms_blocked_dedup", "adk_runner.py dedup guard — send_sms blocked"),
    (r"TIMEOUT|0 turns \(crash",
     "crash_timeout", "runner infrastructure — call timed out or crashed"),
]


# ── Per-scenario log capture ──────────────────────────────────────────────────

class _ListLogHandler(logging.Handler):
    """Captures log records into a list during a single scenario run."""

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.records: List[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.records.append(self.format(record))
        except Exception:
            pass


# ── DeepADKRunner — exposes final state after run ────────────────────────────

class DeepADKRunner:
    """
    Thin wrapper around ADKRunner that:
    - Attaches a per-run log handler to capture all pipeline events
    - Exposes the final ConversationState after the run
    """

    def __init__(self, adk_runner, runner):
        self.adk = adk_runner
        self.runner = runner
        self._last_state = None
        self._last_node_history: List[str] = []

    async def run_deep(self, scenario, noise_override: Optional[str] = None) -> tuple:
        """
        Run scenario and return (ConvResult, log_lines).
        Temporarily overrides noise_variant on the scenario copy.
        """
        # Deep-copy scenario to avoid cross-contamination between concurrent runs
        scen = copy.copy(scenario)
        if noise_override:
            scen = dataclasses.replace(scen, noise_variant=noise_override)

        # Attach log capture handler to the key loggers
        handler = _ListLogHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        _loggers = [
            logging.getLogger("server.training.adk_runner"),
            logging.getLogger("server.training.node_manager"),
            logging.getLogger("server.training.adk_turn_processor"),
            logging.getLogger("server.training.conversation_loop"),
        ]
        for lg in _loggers:
            lg.addHandler(handler)
            lg.setLevel(logging.DEBUG)

        try:
            conv = await asyncio.wait_for(
                self.adk.run(scen, phase=2, run_number=1),
                timeout=CALL_TIMEOUT,
            )
        finally:
            for lg in _loggers:
                lg.removeHandler(handler)

        return conv, handler.records


# ── Diagnosis ─────────────────────────────────────────────────────────────────

def _diagnose(pipeline_events: List[str], tools_missing: List[str], end_reason: str) -> Dict:
    """
    Compute a structured diagnosis from log events.
    Returns dict with root_cause, culprit_code, first_deviation_turn.
    """
    all_text = "\n".join(pipeline_events)

    for pattern, root_cause, culprit_code in DIAGNOSIS_PATTERNS:
        if re.search(pattern, all_text, re.IGNORECASE):
            # Find the first turn where this event occurred
            first_turn = None
            for line in pipeline_events:
                if re.search(pattern, line, re.IGNORECASE):
                    m = re.search(r"T(\d+):", line)
                    if m:
                        first_turn = int(m.group(1))
                    break

            return {
                "root_cause": root_cause,
                "culprit_code": culprit_code,
                "first_deviation_turn": first_turn,
                "tools_missing": tools_missing,
            }

    # Fallback
    return {
        "root_cause": "unknown",
        "culprit_code": f"unknown — tools missing: {tools_missing}, end_reason: {end_reason}",
        "first_deviation_turn": None,
        "tools_missing": tools_missing,
    }


def _group_events_by_turn(log_lines: List[str]) -> Dict[int, List[str]]:
    """Group log lines by turn index (parsed from T{n}: prefix)."""
    by_turn: Dict[int, List[str]] = {}
    for line in log_lines:
        m = re.search(r"T(\d+):", line)
        if m:
            t = int(m.group(1))
            by_turn.setdefault(t, []).append(line)
    return by_turn


def _filter_diagnostic_events(log_lines: List[str]) -> List[str]:
    """Keep only lines relevant to pipeline decisions (skip STT/TTS noise)."""
    keep_patterns = [
        r"step2[bc] ",
        r"step10 ",
        r"step11 ",
        r"TRANSFER",
        r"FORCED ",
        r"BLOCKED",
        r"POST-PARSE",
        r"PRE-forced_commits",
        r"POST-forced_commits",
        r"ENDING",
        r"TIMEOUT",
        r"ERROR:",      # runner errors only, not STT errors
        r"dedup",
        r"AUTO-PAIRED",
        r"STALLED",
    ]
    combined = re.compile("|".join(keep_patterns), re.IGNORECASE)
    return [ln for ln in log_lines if combined.search(ln)]


# ── Single run ────────────────────────────────────────────────────────────────

async def _run_one_deep(
    deep_runner: DeepADKRunner,
    scenario,
    noise: str,
    rep_idx: int,
) -> Dict:
    """Run one scenario × noise variant, return full diagnostic dict."""
    from server.training.call_auditor_de import audit_call
    from server.training.cost_tracker import CostTracker
    from server.training.ab_test_loop import _conv_result_to_audit_turns

    sid = scenario.id
    expected = list(getattr(scenario, "expected_tools", []) or [])
    ct = CostTracker()
    deep_runner.runner.set_cost_tracker(ct)
    deep_runner.adk.cost_tracker = ct

    result = {
        "scenario_id": sid,
        "noise_variant": noise,
        "rep_idx": rep_idx,
        "passed": False,
        "tools_expected": expected,
        "tools_got": [],
        "tools_missing": [],
        "failure_reasons": [],
        "end_reason": "unknown",
        "n_turns": 0,
        "latency_ms": None,
        "cost_usd": 0.0,
        "final_state": {},
        "turns": [],
        "pipeline_events_all": [],
        "diagnosis": {},
    }

    try:
        conv, log_lines = await deep_runner.run_deep(scenario, noise_override=noise)

        audit_turns = _conv_result_to_audit_turns(conv)
        audit = audit_call(
            scenario_id=sid,
            phase=2,
            run_number=1,
            turns=audit_turns,
            expected_tools=expected,
            total_latency_ms=conv.total_latency_ms,
        )

        tools_missing = [t for t in expected if t not in conv.tools_called]
        diag_events = _filter_diagnostic_events(log_lines)
        by_turn = _group_events_by_turn(diag_events)

        # Per-turn detail
        turn_details = []
        for t in conv.turns:
            turn_details.append({
                "turn_idx": t.turn_idx,
                "caller_text": t.caller_text,
                "bot_response": t.bot_response,
                "tools_called": t.tools_called,
                "pipeline_events": by_turn.get(t.turn_idx, []),
                "error": t.error,
            })

        result.update({
            "passed": audit.passed,
            "tools_got": conv.tools_called,
            "tools_missing": tools_missing,
            "failure_reasons": list(audit.failure_reasons),
            "end_reason": conv.end_reason,
            "n_turns": len(conv.turns),
            "latency_ms": round(conv.total_latency_ms, 1),
            "turns": turn_details,
            "pipeline_events_all": diag_events,
            "diagnosis": _diagnose(diag_events, tools_missing, conv.end_reason)
            if not audit.passed else {"root_cause": "passed"},
        })

    except asyncio.TimeoutError:
        result["failure_reasons"] = [f"TIMEOUT (>{CALL_TIMEOUT:.0f}s)"]
        result["end_reason"] = "timeout"
        result["diagnosis"] = _diagnose(
            [f"TIMEOUT: scenario {sid} exceeded {CALL_TIMEOUT}s"],
            expected, "timeout",
        )
        logger.warning(f"  {sid} [{noise}] rep{rep_idx}: TIMEOUT")
    except Exception as e:
        result["failure_reasons"] = [f"ERROR: {str(e)[:200]}"]
        result["end_reason"] = "error"
        result["diagnosis"] = {"root_cause": "crash_timeout", "culprit_code": str(e)[:200]}
        logger.error(f"  {sid} [{noise}] rep{rep_idx}: ERROR — {e}")
    finally:
        result["cost_usd"] = round(ct.estimate_usd(), 4)
        deep_runner.runner.set_cost_tracker(None)
        deep_runner.adk.cost_tracker = None

    status = "✓" if result["passed"] else "✗"
    logger.info(
        f"  {status} {sid} [{noise}] rep{rep_idx} — "
        f"missing={result['tools_missing']} cause={result['diagnosis'].get('root_cause','?')}"
    )
    return result


# ── Worker pool ───────────────────────────────────────────────────────────────

def _make_runner_stack():
    """Build one (Tier2AudioRunner, ADKRunner) pair."""
    from server.training.tier2_runner import Tier2AudioRunner
    from server.training.adk_runner import ADKRunner

    project_id = os.environ.get("GCP_PROJECT_ID", "sailly-voice-agent-eu")
    deepgram_key = os.environ.get("DEEPGRAM_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    runner = Tier2AudioRunner(
        google_project_id=project_id,
        deepgram_api_key=deepgram_key,
        gemini_model="gemini-2.5-flash",
        temperature=0.0,
    )
    runner._init_clients()

    adk = ADKRunner(
        audio_injector=runner.audio_injector,
        gemini_runner=runner,
        openai_api_key=openai_key,
    )
    return runner, adk


# ── Bucket runner ─────────────────────────────────────────────────────────────

async def run_bucket_deep(
    bucket_name: str,
    failing_ids: List[str],
    all_scenarios: list,
    workers: int = 20,
) -> Dict:
    """
    For each failing scenario ID:
      - Run N_REPS × len(NOISE_VARIANTS) = 5 runs per scenario (N_REPS=5, NOISE_VARIANTS=["clean"])
      - Minimum 20 failing scenarios per bucket, max 100 runs per bucket
      - Collect full diagnostic JSON per run
    Returns bucket summary dict.
    """
    # Build scenario lookup
    by_id = {s.id: s for s in all_scenarios}
    missing = [sid for sid in failing_ids if sid not in by_id]
    if missing:
        logger.warning(f"  [{bucket_name}] Scenario IDs not found in bucket: {missing}")
    failing_scenarios = [by_id[sid] for sid in failing_ids if sid in by_id]

    if not failing_scenarios:
        logger.warning(f"  [{bucket_name}] No failing scenarios found — skipping bucket")
        return {
            "bucket": bucket_name,
            "total_runs": 0, "pass_count": 0, "fail_count": 0, "pass_rate": None,
            "skipped": True, "scenario_results": [],
        }

    # Build work queue: each item is (scenario, noise, rep_idx)
    work_items = []
    for scenario in failing_scenarios:
        for rep in range(N_REPS):
            for noise in NOISE_VARIANTS:
                work_items.append((scenario, noise, rep))

    MIN_SCENARIOS = 20  # Require at least 20 failing scenarios per bucket
    MAX_RUNS_PER_BUCKET = 100
    
    # If fewer than MIN_SCENARIOS, cap at available; if more, cap at MAX_RUNS_PER_BUCKET
    if len(work_items) > MAX_RUNS_PER_BUCKET:
        work_items = work_items[:MAX_RUNS_PER_BUCKET]
    total = len(work_items)
    logger.info(f"[{bucket_name}] {len(failing_scenarios)} failing scenarios × {N_REPS} reps × {len(NOISE_VARIANTS)} noise = {total} runs (min {MIN_SCENARIOS} scenarios, max {MAX_RUNS_PER_BUCKET} runs)")

    # Build worker pool
    pool_size = min(workers, total)
    pool: asyncio.Queue = asyncio.Queue()
    runner_stacks = []
    for _ in range(pool_size):
        runner, adk = _make_runner_stack()
        deep = DeepADKRunner(adk, runner)
        await pool.put(deep)
        runner_stacks.append((runner, adk))

    results_lock = asyncio.Lock()
    all_results: List[Dict] = []
    work_queue: asyncio.Queue = asyncio.Queue()
    for item in work_items:
        await work_queue.put(item)

    completed = 0

    async def worker():
        nonlocal completed
        while True:
            try:
                scenario, noise, rep_idx = work_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            deep = await pool.get()
            try:
                r = await _run_one_deep(deep, scenario, noise, rep_idx)
                async with results_lock:
                    all_results.append(r)
                    completed += 1
                    if completed % 20 == 0:
                        logger.info(f"  [{bucket_name}] progress: {completed}/{total}")
            finally:
                await pool.put(deep)

    await asyncio.gather(*[asyncio.create_task(worker()) for _ in range(pool_size)])

    # Aggregate
    pass_count = sum(1 for r in all_results if r["passed"])
    fail_count = len(all_results) - pass_count
    pass_rate = round(pass_count / len(all_results), 4) if all_results else None

    # Failure pattern counts
    pattern_counts: Dict[str, int] = {}
    for r in all_results:
        if not r["passed"]:
            cause = r.get("diagnosis", {}).get("root_cause", "unknown")
            pattern_counts[cause] = pattern_counts.get(cause, 0) + 1

    # Per-scenario pass rates
    scenario_stats: Dict[str, Dict] = {}
    for r in all_results:
        sid = r["scenario_id"]
        if sid not in scenario_stats:
            scenario_stats[sid] = {"total": 0, "pass": 0, "runs": []}
        scenario_stats[sid]["total"] += 1
        if r["passed"]:
            scenario_stats[sid]["pass"] += 1
        # Only store failed runs in detail to keep JSON manageable
        if not r["passed"]:
            scenario_stats[sid]["runs"].append(r)

    per_scenario = []
    for sid, stats in scenario_stats.items():
        per_scenario.append({
            "scenario_id": sid,
            "total_runs": stats["total"],
            "pass_count": stats["pass"],
            "fail_count": stats["total"] - stats["pass"],
            "pass_rate": round(stats["pass"] / stats["total"], 4),
            "failed_runs": stats["runs"],  # full diagnostic detail for each failure
        })

    return {
        "bucket": bucket_name,
        "total_runs": len(all_results),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": pass_rate,
        "failure_pattern_counts": pattern_counts,
        "scenarios": per_scenario,
    }


# ── Consolidated failure report generation ────────────────────────────────────

def _generate_consolidated_failures(run_dir: Path, bucket_results: List[Dict]) -> None:
    """Generate a consolidated JSON report of all failures across buckets."""
    consolidated = {
        "run_id": run_dir.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_failures": 0,
        "failures_by_bucket": {},
        "failures_by_scenario": {},
        "all_failures": []
    }
    
    for bucket_result in bucket_results:
        bucket_name = bucket_result.get("bucket", "unknown")
        bucket_file = run_dir / f"bucket_{bucket_name}.json"
        
        if not bucket_file.exists():
            continue
        
        try:
            data = json.loads(bucket_file.read_text())
            bucket_failures = []
            
            for scenario in data.get("scenarios", []):
                scen_id = scenario["scenario_id"]
                failed_runs = scenario.get("failed_runs", [])
                
                if failed_runs:
                    consolidated["total_failures"] += len(failed_runs)
                    
                    for run_idx, fail in enumerate(failed_runs):
                        failure = {
                            "scenario_id": scen_id,
                            "bucket": bucket_name,
                            "run_number": run_idx + 1,
                            "failure_reasons": fail.get("failure_reasons", []),
                            "missing_tools": fail.get("tools_missing", []),
                            "tools_got": fail.get("tools_got", []),
                            "end_reason": fail.get("end_reason", ""),
                            "hallucination_score": fail.get("hallucination_score"),
                            "pipeline_events": fail.get("pipeline_events", [])[:5],  # Last 5 events
                        }
                        
                        bucket_failures.append(failure)
                        
                        # Index by scenario
                        if scen_id not in consolidated["failures_by_scenario"]:
                            consolidated["failures_by_scenario"][scen_id] = []
                        consolidated["failures_by_scenario"][scen_id].append(failure)
                        
                        consolidated["all_failures"].append(failure)
            
            if bucket_failures:
                consolidated["failures_by_bucket"][bucket_name] = bucket_failures
        
        except Exception as e:
            logger.warning(f"Failed to process {bucket_file}: {e}")
    
    # Write consolidated report
    output_path = run_dir / "CONSOLIDATED_FAILURE_REPORT.json"
    try:
        output_path.write_text(json.dumps(consolidated, indent=2, default=str))
        logger.info(f"[Report] Consolidated failures: {output_path} ({consolidated['total_failures']} failures)")
    except Exception as e:
        logger.warning(f"Failed to write consolidated failures: {e}")


# ── Dashboard registration ────────────────────────────────────────────────────

def _register_dashboard(run_id: str, run_dir: Path, summary: Dict) -> None:
    """Add a NoAutoFix entry to runs_manifest.json and regenerate index.html."""
    manifest_path = RUNS_ROOT / "runs_manifest.json"
    try:
        data = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"runs": []}
        runs_list = data.get("runs", data) if isinstance(data, dict) else data

        # Auto-compute next index and code so the run appears correctly in both dashboards
        existing_indices = [r.get("index", 0) for r in runs_list if isinstance(r, dict)]
        next_index = (max(existing_indices) + 1) if existing_indices else 0
        existing_naf = [r for r in runs_list if isinstance(r, dict) and r.get("code", "").startswith("NOAUTOFIX")]
        next_naf_n = len(existing_naf) + 1

        entry = {
            "index": next_index,
            "code": f"NOAUTOFIX-{next_naf_n}",
            "run_id": run_id,
            "name": f"[NoAutoFix-Deep] Tier1 — {summary.get('total_runs', 0)} runs · Fix M+N",
            "type": "noautofix_deep",
            "status": "finished",
            "started_at": summary.get("started_at", ""),
            "finished_at": summary.get("finished_at", ""),
            "dir": str(run_dir),
            "output_dir": str(run_dir),
            "buckets": [
                {
                    "name": b["bucket"],
                    "pass_rate": b.get("pass_rate"),
                    "total_runs": b.get("total_runs", 0),
                    "failure_pattern_counts": b.get("failure_pattern_counts", {}),
                }
                for b in summary.get("buckets", [])
            ],
        }

        if isinstance(data, dict):
            data.setdefault("runs", []).append(entry)
            manifest_path.write_text(json.dumps(data, indent=2, default=str))
        else:
            runs_list.append(entry)
            manifest_path.write_text(json.dumps(runs_list, indent=2, default=str))

        logger.info(f"[Dashboard] Registered run '{run_id}' as index={next_index} code=NOAUTOFIX-{next_naf_n} in runs_manifest.json")
    except Exception as e:
        logger.error(f"[Dashboard] Failed to update manifest: {e}")

    # Regenerate index.html
    try:
        import subprocess
        subprocess.run(
            [str(VENV_PYTHON), "-c",
             "from server.training.unified_dashboard import write_dashboard;"
             f"from pathlib import Path; write_dashboard(Path('{RUNS_ROOT}'))"],
            cwd=str(MODULE_ROOT), capture_output=True, timeout=20,
        )
        logger.info("[Dashboard] index.html regenerated")
    except Exception as e:
        logger.warning(f"[Dashboard] Regen failed: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main_async(args):
    from server.scenarios.fix_validation_buckets import ALL_FIX_BUCKETS

    # Load failing IDs
    failing_ids: Dict[str, List[str]] = {}
    if args.failing_ids_file and Path(args.failing_ids_file).exists():
        failing_ids = json.loads(Path(args.failing_ids_file).read_text())
        logger.info(f"Loaded failing IDs from {args.failing_ids_file}")
    else:
        failing_ids = DEFAULT_FAILING_IDS
        logger.info("Using default known-failing IDs (from last Phase A baseline)")

    # Filter to requested buckets
    buckets_to_run = args.bucket.split(",") if args.bucket else TIER1_BUCKETS
    buckets_to_run = [b.strip() for b in buckets_to_run if b.strip() in TIER1_BUCKETS]
    if not buckets_to_run:
        logger.error(f"No valid Tier 1 buckets specified. Valid: {TIER1_BUCKETS}")
        sys.exit(1)

    # Prepare output directory
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_id = f"noautofix-deep-{ts}"
    run_dir = OUTPUT_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc).isoformat()
    logger.info(f"Starting NoAutoFix Deep Runner — run_id={run_id}")
    logger.info(f"Buckets: {buckets_to_run}")
    logger.info(f"Workers: {args.workers}")
    logger.info(f"Noise variants: {NOISE_VARIANTS}")
    logger.info(f"Reps per scenario: {N_REPS}")

    bucket_results = []

    for bucket_name in buckets_to_run:
        all_scens = ALL_FIX_BUCKETS.get(bucket_name, [])
        ids = failing_ids.get(bucket_name, [])
        if not ids:
            logger.warning(f"[{bucket_name}] No failing IDs configured — skipping")
            continue

        logger.info(f"\n{'='*60}")
        logger.info(f"Bucket: {bucket_name} | failing IDs: {ids}")
        logger.info(f"{'='*60}")

        t0 = time.time()
        bucket_result = await run_bucket_deep(
            bucket_name=bucket_name,
            failing_ids=ids,
            all_scenarios=all_scens,
            workers=args.workers,
        )
        elapsed = time.time() - t0

        bucket_result["elapsed_s"] = round(elapsed, 1)
        bucket_results.append(bucket_result)

        # Write per-bucket JSON immediately
        bucket_path = run_dir / f"bucket_{bucket_name}.json"
        bucket_path.write_text(json.dumps(bucket_result, indent=2, default=str))
        logger.info(
            f"[{bucket_name}] Done — pass_rate={bucket_result.get('pass_rate')} "
            f"({bucket_result.get('pass_count')}/{bucket_result.get('total_runs')}) "
            f"in {elapsed:.0f}s → {bucket_path}"
        )

    finished_at = datetime.now(timezone.utc).isoformat()

    # Summary
    summary = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "tier1_buckets_run": buckets_to_run,
        "total_runs": sum(b.get("total_runs", 0) for b in bucket_results),
        "noise_variants": NOISE_VARIANTS,
        "reps_per_scenario": N_REPS,
        "buckets": [
            {
                "bucket": b["bucket"],
                "pass_rate": b.get("pass_rate"),
                "pass_count": b.get("pass_count"),
                "fail_count": b.get("fail_count"),
                "total_runs": b.get("total_runs"),
                "failure_pattern_counts": b.get("failure_pattern_counts", {}),
            }
            for b in bucket_results
        ],
    }

    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, default=str))
    logger.info(f"\nSummary written to {summary_path}")

    # Generate consolidated failure report
    _generate_consolidated_failures(run_dir, bucket_results)

    # Print summary table
    logger.info("\n" + "="*60)
    logger.info("RESULTS SUMMARY")
    logger.info("="*60)
    for b in summary["buckets"]:
        rate_str = f"{b['pass_rate']*100:.1f}%" if b.get("pass_rate") is not None else "N/A"
        patterns = ", ".join(
            f"{k}={v}" for k, v in (b.get("failure_pattern_counts") or {}).items()
        )
        logger.info(f"  {b['bucket']:20s} {rate_str:7s}  ({b['pass_count']}/{b['total_runs']})  {patterns}")
    logger.info("="*60)

    _register_dashboard(run_id, run_dir, summary)

    return summary


def main():
    parser = argparse.ArgumentParser(description="NoAutoFix Deep Diagnostic Runner")
    parser.add_argument("--workers", type=int, default=20,
                        help="Number of concurrent scenario runners (default: 20)")
    parser.add_argument("--bucket", type=str, default="",
                        help="Comma-separated bucket names to run (default: all 5 Tier 1 buckets)")
    parser.add_argument("--failing-ids-file", type=str, default="",
                        help="JSON file mapping bucket→[scenario_id,...] of known failing IDs")
    args = parser.parse_args()

    # Set TTS engine
    os.environ.setdefault("TTS_ENGINE", "gemini-flash")

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
