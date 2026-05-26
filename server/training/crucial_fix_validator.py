"""
crucial_fix_validator.py — Crucial Fix Validation (CFV) phase.

Activated after the standard 8-iteration fix loop when buckets remain unresolved.
Uses Gemini 2.5 Flash (with Google Search grounding) for deep per-bucket analysis —
forcing orthogonal reasoning by injecting real-world patterns and docs.
Gemini 2.5 Pro (with Google Search grounding) is used for the human review plan.

Algorithm per bucket:
  1. Call analyze_and_fix_deep() — Gemini 2.5 Flash with Google Search proposes a patch
  2. Apply patches
  3. Run fix_validation_loop for ONLY this bucket (single-bucket mode)
  4. If bucket passes → resolved; move to next bucket
  5. If not → revert patches; record attempt; retry up to max_attempts (10)
  6. After max_attempts failures → mark "needs_human_investigation"

After all buckets processed:
  - Re-run fix_validation_loop with all-bucket best-state to confirm combined rate
  - Estimate projected_pass_rate
  - Return result dict for validation_heal_loop.py to act on

Live progress is written to cfv_state.json inside the run directory.
"""

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional

from .claude_fixer import (
    FixProposal,
    Patch,
    analyze_and_fix_deep,
    apply_patches,
    revert_patches,
    create_human_review_plan,
    _validate_proposal,
)

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

CFV_MAX_ATTEMPTS = 5           # Max deep-fix attempts per bucket
CFV_RUNS_ROOT = Path("/tmp/validation_runs")
FIX_VAL_OUTPUT_DIR = Path("/tmp/validation_runs/fix_validation")

PYTHON = str(Path(__file__).resolve().parents[2] / ".venv" / "bin" / "python3")
TRAINING_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TRAINING_DIR.parent.parent


# ── State helpers ──────────────────────────────────────────────────────────────

def _write_cfv_state(run_dir: Path, state: dict) -> None:
    state_path = run_dir / "cfv_state.json"
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str))
    tmp.replace(state_path)


def _build_initial_state(bucket_names: List[str]) -> dict:
    return {
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "current_bucket": None,
        "current_attempt": 0,
        "max_attempts": CFV_MAX_ATTEMPTS,
        "buckets": [
            {
                "name": name,
                "status": "pending",
                "attempts": 0,
                "web_search_queries": [],
                "web_search_insights": [],
                "attempt_records": [],
                "final_combined_rate": None,
                "resolution": None,
                "started_at": None,
                "finished_at": None,
                "selected_attempt": None,
            }
            for name in bucket_names
        ],
        "resolved_count": 0,
        "unresolved_count": 0,
        "projected_pass_rate": None,
        "cost_usd": 0.0,
    }


# ── Human review package ──────────────────────────────────────────────────────

def _generate_human_review_package(
    run_dir: Path,
    bucket_name: str,
    bucket_state: dict,
    all_failed_ids: List[str],
    prior_cfv_attempts: List[dict],
    prior_fix_val_history: Optional[List[dict]] = None,
) -> Path:
    """
    Collect all context about a failed bucket into a comprehensive JSON file.
    Returns the path to the written file.
    """
    # Collect per-attempt validation outputs
    attempt_validation_details = []
    for attempt in range(1, len(prior_cfv_attempts) + 1):
        attempt_dir = run_dir / f"bucket_{bucket_name}_attempt_{attempt}"
        state_path = attempt_dir / "fix_validation_state.json"
        results_path = attempt_dir / "fix_scenario_results.json"
        val_detail: dict = {"attempt": attempt, "scenarios": []}
        if state_path.exists():
            try:
                val_state = json.loads(state_path.read_text())
                for b in val_state.get("buckets", []):
                    if b.get("name") == bucket_name:
                        val_detail["bucket_state"] = b
                        break
            except Exception:
                pass
        if results_path.exists():
            try:
                val_detail["scenarios"] = json.loads(results_path.read_text())
            except Exception:
                pass
        attempt_validation_details.append(val_detail)

    # Build failure summary
    failures_by_scenario: dict = {}
    for avd in attempt_validation_details:
        for sc in avd.get("scenarios", []):
            sid = sc.get("scenario_id", "")
            if not sc.get("pass") and sid:
                if sid not in failures_by_scenario:
                    failures_by_scenario[sid] = []
                failures_by_scenario[sid].append({
                    "attempt": avd["attempt"],
                    "failures": sc.get("failures", []),
                    "tools_expected": sc.get("expected_tools", []),
                    "tools_got": sc.get("tools_called", []),
                    "composite_score": sc.get("composite"),
                })

    review_package = {
        "bucket_name": bucket_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": (
            f"Bucket '{bucket_name}' failed all {len(prior_cfv_attempts)} CFV attempts. "
            f"{len(all_failed_ids)} failing scenario IDs. "
            f"All automated fixes exhausted — requires expert remediation."
        ),
        "failures_summary": (
            f"{len(failures_by_scenario)} distinct scenarios fail persistently across attempts"
        ),
        "failing_scenario_ids": all_failed_ids,
        "persistent_failures": failures_by_scenario,
        "total_cfv_attempts": len(prior_cfv_attempts),
        "cfv_attempt_records": prior_cfv_attempts,
        "attempt_validation_details": attempt_validation_details,
        "prior_fix_validation_history": prior_fix_val_history or [],
        "bucket_state": bucket_state,
        "code_context": {
            "training_dir": str(TRAINING_DIR),
            "allowed_files": [
                "conversation_nodes.py",
                "node_manager.py",
                "adk_turn_processor.py",
                "response_variations.py",
            ],
            "note": (
                "These files contain the ADK brain prompts, intent routing, "
                "hallucination filters, and response variations. The root cause "
                "is almost certainly in one of these files."
            ),
        },
    }

    # Attach snippet of relevant source files for context
    from .claude_fixer import TRAINING_DIR as TRAIN_DIR, ALLOWED_FILES
    file_snippets: dict = {}
    for fname in ALLOWED_FILES:
        fpath = TRAIN_DIR / fname
        if fpath.exists():
            try:
                content = fpath.read_text(encoding="utf-8")
                file_snippets[fname] = content[:3000]  # first 3000 chars for context
            except Exception:
                pass
    review_package["source_file_snippets"] = file_snippets

    out_path = run_dir / f"human_review_{bucket_name}.json"
    out_path.write_text(json.dumps(review_package, indent=2, default=str))
    logger.info(f"[CFV] Human review package written: {out_path}")
    return out_path


# ── Single-bucket fix_validation_loop ─────────────────────────────────────────

async def _run_fix_validation_single_bucket(
    bucket_name: str,
    failed_ids: List[str],
    workers: int,
    run_dir: Path,
    attempt: int,
) -> dict:
    """
    Run fix_validation_loop for ONE bucket only (CFV single-bucket mode).
    Returns the bucket's result dict.
    """
    iter_output = run_dir / f"bucket_{bucket_name}_attempt_{attempt}"
    iter_output.mkdir(parents=True, exist_ok=True)

    failed_ids_path = iter_output / "failed_ids.json"
    failed_ids_path.write_text(json.dumps(failed_ids))

    cmd = [
        PYTHON, "-m", "server.training.fix_validation_loop",
        "--output", str(iter_output),
        "--workers", str(min(workers, 5)),
        "--failed-ids-file", str(failed_ids_path),
        "--bucket", bucket_name,
    ]

    logger.info(
        f"[CFV] Bucket '{bucket_name}' attempt {attempt}: "
        f"running fix_validation_loop with {len(failed_ids)} scenarios..."
    )
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(PROJECT_ROOT),
        env=env,
    )
    async for line in proc.stdout:
        decoded = line.decode("utf-8", errors="replace").rstrip()
        if any(k in decoded for k in [
            "Bucket", "Step", "PASS", "FAIL", "threshold",
            "VALIDATED", "UNRESOLVED", "attempt", "CFV", "✅", "❌"
        ]):
            logger.info(f"  [cfv-val] {decoded}")
    await proc.wait()

    state_path = iter_output / "fix_validation_state.json"
    if not state_path.exists():
        logger.warning(f"[CFV] No state file for bucket '{bucket_name}' attempt {attempt}")
        return {"name": bucket_name, "status": "unresolved", "combined_rate": 0.0}

    state = json.loads(state_path.read_text())
    buckets = state.get("buckets", [])
    matching = [b for b in buckets if b.get("name") == bucket_name]
    if not matching:
        return {
            "name": bucket_name,
            "status": "unresolved",
            "combined_rate": 0.0,
            "step1_rate": 0.0,
            "step2_rate": 0.0,
            "step3_rate": 0.0,
            "step1_count": 0,
            "step2_count": 0,
            "step3_count": 0,
        }

    b = matching[0]
    # Ensure all step fields are present with defaults
    b.setdefault("step1_rate", 0.0)
    b.setdefault("step2_rate", 0.0)
    b.setdefault("step3_rate", 0.0)
    b.setdefault("step1_count", 0)
    b.setdefault("step2_count", 0)
    b.setdefault("step3_count", 0)
    return b


async def _run_fix_validation_all_buckets(
    failed_ids: List[str],
    workers: int,
    run_dir: Path,
    label: str = "final",
) -> dict:
    """
    Run fix_validation_loop for ALL remaining buckets (confirmation run after CFV).
    """
    iter_output = run_dir / f"all_buckets_{label}"
    iter_output.mkdir(parents=True, exist_ok=True)

    failed_ids_path = iter_output / "failed_ids.json"
    failed_ids_path.write_text(json.dumps(failed_ids))

    cmd = [
        PYTHON, "-m", "server.training.fix_validation_loop",
        "--output", str(iter_output),
        "--workers", str(workers),
        "--failed-ids-file", str(failed_ids_path),
    ]

    logger.info(f"[CFV] Running all-bucket confirmation fix_validation_loop ({label})...")
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(PROJECT_ROOT),
        env=env,
    )
    async for line in proc.stdout:
        decoded = line.decode("utf-8", errors="replace").rstrip()
        if any(k in decoded for k in [
            "Bucket", "Step", "PASS", "FAIL", "VALIDATED", "UNRESOLVED", "✅", "❌"
        ]):
            logger.info(f"  [cfv-all] {decoded}")
    await proc.wait()

    state_path = iter_output / "fix_validation_state.json"
    if not state_path.exists():
        return {"passed_buckets": 0, "failed_buckets": [], "bucket_details": [], "cost_usd": 0.0}

    state = json.loads(state_path.read_text())
    buckets_data = state.get("buckets", [])
    passed = [b for b in buckets_data if b.get("status") == "validated"]
    failed_b = [b for b in buckets_data if b.get("status") not in ("validated", "pending")]

    cost = 0.0
    for b in buckets_data:
        for r in b.get("step1_results", []) + b.get("step2_results", []) + b.get("step3_results", []):
            cost += r.get("cost_usd", r.get("one_live_cost_usd", 0.0))

    return {
        "passed_buckets": len(passed),
        "failed_buckets": [b.get("name") for b in failed_b],
        "bucket_details": buckets_data,
        "cost_usd": cost,
    }


# ── Projected pass rate estimate ───────────────────────────────────────────────

def estimate_projected_pass_rate(
    phase_a_total_scenarios: int,
    phase_a_passed_scenarios: int,
    resolved_scenario_ids: List[str],
) -> float:
    """
    Estimate projected pass rate if all resolved scenarios now pass.
    resolved_scenario_ids = IDs of scenarios in buckets that CFV resolved.
    """
    if phase_a_total_scenarios == 0:
        return 0.0
    projected_passed = phase_a_passed_scenarios + len(resolved_scenario_ids)
    return min(1.0, projected_passed / phase_a_total_scenarios)


# ── Main CFV orchestrator ──────────────────────────────────────────────────────

async def run_crucial_fix_validation(
    unresolved_bucket_names: List[str],
    all_failed_ids: List[str],
    phase_a_total_scenarios: int,
    phase_a_passed_scenarios: int,
    iteration_offset: int,
    workers: int,
    register_run: Callable,
    finish_run: Callable,
    api_key: Optional[str] = None,
    max_attempts: int = CFV_MAX_ATTEMPTS,
) -> dict:
    """
    Run the Crucial Fix Validation phase — deep per-bucket analysis with web search.

    Args:
        unresolved_bucket_names: Names of buckets still failing after the fix loop
        all_failed_ids: All scenario IDs still failing (across all unresolved buckets)
        phase_a_total_scenarios: Total scenarios in Phase A (for projected pass rate)
        phase_a_passed_scenarios: Scenarios that passed in Phase A
        iteration_offset: Used to create unique run directory names
        workers: Parallel workers for fix_validation_loop
        register_run: Callable from validation_heal_loop to add entry to dashboard manifest
        finish_run: Callable from validation_heal_loop to finalize manifest entry
        api_key: Deprecated — kept for backward-compat, ignored (uses Vertex AI service account)
        max_attempts: Max deep-fix attempts per bucket (default 10)

    Returns:
        {
            "resolved_buckets": [...],
            "unresolved_buckets": [...],   # needs_human_investigation
            "cfv_iterations": [...],
            "cost_usd": float,
            "projected_pass_rate": float,
            "resolved_scenario_ids": [...],
        }
    """
    run_dir = CFV_RUNS_ROOT / f"cfv_iter_{iteration_offset}"
    # Clean up any pre-existing directory to avoid permission conflicts from previous runs
    if run_dir.exists():
        import shutil
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    # Ensure permissive permissions to avoid cross-user issues
    run_dir.chmod(0o777)

    # Register this CFV run in the unified dashboard manifest
    # Store a relative path (relative to RUNS_ROOT) so the dashboard can fetch files correctly
    _cfv_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    _bucket_count = len(unresolved_bucket_names)
    cfv_run_idx = register_run(
        run_dir=f"cfv_iter_{iteration_offset}",
        name=f"[{_cfv_date} UTC] CFV — {_bucket_count} bucket{'s' if _bucket_count != 1 else ''}: {', '.join(unresolved_bucket_names[:3])}{'…' if _bucket_count > 3 else ''}",
        code=f"CFV-{iteration_offset}",
        run_type="cfv",
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    state = _build_initial_state(unresolved_bucket_names)
    state["max_attempts"] = max_attempts
    state["current_bucket"] = []  # list — shown as "running" set for concurrent display
    _write_cfv_state(run_dir, state)

    resolved_buckets: List[str] = []
    unresolved_buckets: List[str] = []
    cfv_iterations: List[dict] = []
    total_cost = 0.0
    resolved_scenario_ids: List[str] = []

    # ── Shared mutable state (thread-safe for concurrent bucket processing) ────
    _state_lock = asyncio.Lock()

    async def _process_bucket(bucket_name: str, bucket_idx: int) -> None:
        """Process one bucket: run up to max_attempts, then mark human_review."""
        nonlocal total_cost, resolved_scenario_ids

        async with _state_lock:
            bucket_state = state["buckets"][bucket_idx]
            bucket_state["status"] = "running"
            bucket_state["started_at"] = datetime.now(timezone.utc).isoformat()
            if isinstance(state.get("current_bucket"), list):
                state["current_bucket"].append(bucket_name)
            else:
                state["current_bucket"] = [bucket_name] if state.get("current_bucket") else [bucket_name]
            _write_cfv_state(run_dir, state)

        logger.info(
            f"[CFV] ═══ Bucket {bucket_idx + 1}/{len(unresolved_bucket_names)}: "
            f"'{bucket_name}' (max {max_attempts} attempts) ═══"
        )

        prior_cfv_attempts: List[dict] = []
        bucket_resolved = False

        for attempt in range(1, max_attempts + 1):
            async with _state_lock:
                state["current_attempt"] = attempt
                bucket_state["attempts"] = attempt
                _write_cfv_state(run_dir, state)

            logger.info(f"[CFV] Bucket '{bucket_name}' — attempt {attempt}/{max_attempts}")

            # Check for human instruction file (written by dashboard server)
            instr_file = run_dir / f"human_instruction_{bucket_name}.json"
            human_instr: Optional[str] = None
            if instr_file.exists():
                try:
                    instr_data = json.loads(instr_file.read_text())
                    human_instr = instr_data.get("instruction", "")
                    if human_instr:
                        logger.info(f"[CFV] Using human instruction for '{bucket_name}': {human_instr[:80]}...")
                except Exception:
                    pass

            # Step 1: Deep analysis (Gemini web research) + patch generation (Claude)
            try:
                proposal: FixProposal = await analyze_and_fix_deep(
                    bucket_name=bucket_name,
                    failing_scenarios=[{"scenario_id": sid} for sid in all_failed_ids],
                    prior_cfv_attempts=prior_cfv_attempts,
                    cost_spent=total_cost,
                    api_key=api_key,
                    human_instruction=human_instr,
                )
            except Exception as e:
                logger.error(f"[CFV] analyze_and_fix_deep failed for '{bucket_name}': {e}")
                attempt_record = {
                    "attempt": attempt,
                    "outcome": "error",
                    "error": str(e),
                    "web_search_queries": [],
                    "patches": [],
                }
                prior_cfv_attempts.append(attempt_record)
                async with _state_lock:
                    bucket_state["attempt_records"].append(attempt_record)
                    cfv_iterations.append({"bucket": bucket_name, **attempt_record})
                    _write_cfv_state(run_dir, state)
                continue

            async with _state_lock:
                total_cost += proposal.cost_usd
                if proposal.web_search_queries:
                    bucket_state["web_search_queries"].extend(proposal.web_search_queries)
                if proposal.web_search_insights:
                    bucket_state["web_search_insights"].append(proposal.web_search_insights)
                _write_cfv_state(run_dir, state)

            if proposal.rejected:
                logger.warning(f"[CFV] Attempt {attempt} rejected: {proposal.rejection_reason}")
                attempt_record = {
                    "attempt": attempt,
                    "outcome": "rejected",
                    "rejection_reason": proposal.rejection_reason,
                    "web_search_queries": proposal.web_search_queries,
                    "patches": [p.__dict__ if hasattr(p, "__dict__") else p for p in proposal.patches],
                    "analysis": proposal.analysis,
                }
                prior_cfv_attempts.append(attempt_record)
                async with _state_lock:
                    bucket_state["attempt_records"].append(attempt_record)
                    cfv_iterations.append({"bucket": bucket_name, **attempt_record})
                    _write_cfv_state(run_dir, state)
                continue

            # Step 2: Apply patches (serialised to avoid cross-bucket file conflicts)
            async with _state_lock:
                patch_errors = apply_patches(proposal)
                if patch_errors:
                    logger.warning(f"[CFV] Patch apply errors: {patch_errors}")

            # Step 3: Validate this single bucket
            bucket_result = await _run_fix_validation_single_bucket(
                bucket_name=bucket_name,
                failed_ids=all_failed_ids,
                workers=workers,
                run_dir=run_dir,
                attempt=attempt,
            )

            bucket_status = bucket_result.get("status", "unresolved")
            combined_rate = bucket_result.get("combined_rate", 0.0)

            attempt_record = {
                "attempt": attempt,
                "outcome": bucket_status,
                "combined_rate": combined_rate,
                "step1_rate": bucket_result.get("step1_rate", 0.0),
                "step2_rate": bucket_result.get("step2_rate", 0.0),
                "step3_rate": bucket_result.get("step3_rate", 0.0),
                "step1_count": bucket_result.get("step1_count", 0),
                "step2_count": bucket_result.get("step2_count", 0),
                "step3_count": bucket_result.get("step3_count", 0),
                "source": "claude_cfv" if proposal.patches else "cfv",
                "web_search_queries": proposal.web_search_queries,
                "patches": [
                    {"file": p.file, "description": p.description,
                     "old_text": p.old_text, "new_text": p.new_text}
                    for p in proposal.patches
                ],
                "analysis": proposal.analysis,
                "web_search_insights": proposal.web_search_insights,
            }
            if human_instr:
                attempt_record["human_instruction"] = human_instr[:200]
                attempt_record["source"] = "manual_instruction"

            prior_cfv_attempts.append(attempt_record)

            async with _state_lock:
                bucket_state["attempt_records"].append(attempt_record)
                cfv_iterations.append({"bucket": bucket_name, **attempt_record})
                _write_cfv_state(run_dir, state)

            if bucket_status == "validated":
                logger.info(
                    f"[CFV] ✅ Bucket '{bucket_name}' RESOLVED on attempt {attempt} "
                    f"(combined={combined_rate:.0%})"
                )
                async with _state_lock:
                    bucket_state["status"] = "resolved"
                    bucket_state["final_combined_rate"] = combined_rate
                    bucket_state["resolution"] = "resolved"
                    bucket_state["finished_at"] = datetime.now(timezone.utc).isoformat()
                    resolved_buckets.append(bucket_name)
                    for step_key in ("step1_results", "step2_results", "step3_results"):
                        for r in bucket_result.get(step_key, []):
                            sid = r.get("scenario_id", r.get("id", ""))
                            if sid and sid in all_failed_ids:
                                resolved_scenario_ids.append(sid)
                    resolved_scenario_ids = list(set(resolved_scenario_ids))
                    _write_cfv_state(run_dir, state)
                bucket_resolved = True
                break
            else:
                logger.info(
                    f"[CFV] ❌ Bucket '{bucket_name}' attempt {attempt} FAILED "
                    f"(combined={combined_rate:.0%}) — reverting patches"
                )
                async with _state_lock:
                    revert_errors = revert_patches(proposal)
                    if revert_errors:
                        logger.warning(f"[CFV] Revert errors: {revert_errors}")
                    _write_cfv_state(run_dir, state)

        if not bucket_resolved:
            logger.error(
                f"[CFV] ⚠️  Bucket '{bucket_name}' exhausted {max_attempts} attempts "
                f"— generating human review package and marking for manual input..."
            )
            async with _state_lock:
                bucket_state["status"] = "human_review"
                bucket_state["resolution"] = "awaiting_manual_input"
                bucket_state["finished_at"] = datetime.now(timezone.utc).isoformat()
                _write_cfv_state(run_dir, state)

            # Generate human review package (context for operator)
            review_path = _generate_human_review_package(
                run_dir=run_dir,
                bucket_name=bucket_name,
                bucket_state=bucket_state,
                all_failed_ids=all_failed_ids,
                prior_cfv_attempts=prior_cfv_attempts,
            )
            async with _state_lock:
                bucket_state["human_review_file"] = review_path.name
                _write_cfv_state(run_dir, state)

            # Generate Gemini Flash-Lite analysis plan (cheap, for dashboard display)
            try:
                review_json = json.loads(review_path.read_text())
                gemini_plan = await create_human_review_plan(review_json, api_key=api_key)
                async with _state_lock:
                    total_cost += gemini_plan.get("cost_usd", 0.0)
                plan_path = run_dir / f"human_review_{bucket_name}_plan.json"
                plan_path.write_text(json.dumps(gemini_plan, indent=2, default=str))
                async with _state_lock:
                    bucket_state["human_review_plan_file"] = plan_path.name
                    bucket_state["gemini_fix_plan"] = {
                        "root_cause_analysis": gemini_plan.get("root_cause_analysis", ""),
                        "primary_failure_mode": gemini_plan.get("primary_failure_mode", ""),
                        "estimated_confidence": gemini_plan.get("estimated_confidence", 0.0),
                        "fix_steps_count": len(gemini_plan.get("fix_plan", [])),
                        "web_searches": gemini_plan.get("web_search_queries", []),
                    }
                    _write_cfv_state(run_dir, state)
                    unresolved_buckets.append(bucket_name)
                    logger.info(
                        f"[CFV] Analysis plan for '{bucket_name}': '{gemini_plan.get('primary_failure_mode')}' "
                        f"confidence={gemini_plan.get('estimated_confidence', 0):.0%}"
                    )
            except Exception as e:
                logger.error(f"[CFV] Analysis plan call failed for '{bucket_name}': {e}")
                async with _state_lock:
                    bucket_state["gemini_pro_error"] = str(e)
                    unresolved_buckets.append(bucket_name)
                    _write_cfv_state(run_dir, state)

        # Remove from running set
        async with _state_lock:
            if isinstance(state.get("current_bucket"), list):
                try:
                    state["current_bucket"].remove(bucket_name)
                except ValueError:
                    pass
            _write_cfv_state(run_dir, state)

    # ── Run buckets with concurrency (2 slots) ─────────────────────────────────
    CONCURRENT_BUCKETS = 2
    bucket_queue: asyncio.Queue = asyncio.Queue()
    for idx, name in enumerate(unresolved_bucket_names):
        await bucket_queue.put((idx, name))

    async def slot_worker():
        while True:
            try:
                bucket_idx, bucket_name = bucket_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            try:
                await _process_bucket(bucket_name, bucket_idx)
            except Exception as e:
                logger.error(f"[CFV] Slot worker error for '{bucket_name}': {e}")
            finally:
                bucket_queue.task_done()

    await asyncio.gather(*[slot_worker() for _ in range(CONCURRENT_BUCKETS)])

    # Update summary counts
    state["resolved_count"] = len(resolved_buckets)
    state["unresolved_count"] = len(unresolved_buckets)
    state["current_bucket"] = []
    state["current_attempt"] = 0

    # Run all-bucket confirmation if at least some were resolved
    confirmation_cost = 0.0
    if resolved_buckets:
        logger.info(
            f"[CFV] Running all-bucket confirmation fix_validation_loop "
            f"({len(resolved_buckets)} buckets resolved, {len(unresolved_buckets)} unresolved)..."
        )
        confirmation = await _run_fix_validation_all_buckets(
            failed_ids=all_failed_ids,
            workers=workers,
            run_dir=run_dir,
            label="confirmation",
        )
        confirmation_cost = confirmation.get("cost_usd", 0.0)
        total_cost += confirmation_cost
        logger.info(
            f"[CFV] Confirmation: {confirmation['passed_buckets']} buckets validated, "
            f"still failing: {confirmation['failed_buckets'] or 'none'}"
        )

    # Estimate projected pass rate
    projected_pass_rate = estimate_projected_pass_rate(
        phase_a_total_scenarios=phase_a_total_scenarios,
        phase_a_passed_scenarios=phase_a_passed_scenarios,
        resolved_scenario_ids=resolved_scenario_ids,
    )
    state["projected_pass_rate"] = projected_pass_rate
    state["cost_usd"] = total_cost
    state["status"] = "finished"
    state["finished_at"] = datetime.now(timezone.utc).isoformat()
    _write_cfv_state(run_dir, state)

    logger.info(
        f"[CFV] ══════════════════════════════════════════════════\n"
        f"[CFV]  CRUCIAL FIX VALIDATION COMPLETE\n"
        f"[CFV]  Resolved:   {len(resolved_buckets)} buckets: {resolved_buckets or 'none'}\n"
        f"[CFV]  Unresolved: {len(unresolved_buckets)} buckets: {unresolved_buckets or 'none'}\n"
        f"[CFV]  Projected pass rate: {projected_pass_rate:.1%}\n"
        f"[CFV]  Total CFV cost: ${total_cost:.2f}\n"
        f"[CFV] ══════════════════════════════════════════════════"
    )

    # Finalize dashboard manifest entry
    finish_run(
        cfv_run_idx,
        finished_at=datetime.now(timezone.utc).isoformat(),
        status="finished" if not unresolved_buckets else "partial",
    )

    return {
        "resolved_buckets": resolved_buckets,
        "unresolved_buckets": unresolved_buckets,
        "cfv_iterations": cfv_iterations,
        "cost_usd": total_cost,
        "projected_pass_rate": projected_pass_rate,
        "resolved_scenario_ids": resolved_scenario_ids,
        "run_dir": str(run_dir),
    }
