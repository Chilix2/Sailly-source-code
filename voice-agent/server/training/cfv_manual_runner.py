"""
cfv_manual_runner.py — Manual CFV bucket re-runner.

Spawned by validation_dashboard_server.py when a user:
  1. Provides a manual instruction and clicks "Re-run with Instruction"
  2. Clicks "Deploy selected version" for cherry-pick deployment

Usage:
  # Re-run one more attempt with optional human instruction:
  python -m server.training.cfv_manual_runner \\
      --bucket verify_address \\
      --run-dir /tmp/validation_runs/cfv_iter_8 \\
      [--instruction "Try removing verify_address from GREETING tools list"]

  # Deploy a specific previously-attempted patch set:
  python -m server.training.cfv_manual_runner \\
      --bucket verify_address \\
      --run-dir /tmp/validation_runs/cfv_iter_8 \\
      --deploy-attempt 3
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CFVRunner] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.replace(path)


async def run_rerun(bucket_name: str, run_dir: Path, instruction: str | None) -> None:
    """Run one additional CFV attempt for this bucket, with optional human instruction."""
    from .claude_fixer import (
        FixProposal, Patch,
        analyze_and_fix_deep, apply_patches, revert_patches, _validate_proposal,
    )

    state_file = run_dir / "cfv_state.json"
    state = _read_json(state_file)

    bucket_state = None
    for b in state.get("buckets", []):
        if b.get("name") == bucket_name:
            bucket_state = b
            break

    if not bucket_state:
        logger.error(f"Bucket '{bucket_name}' not found in cfv_state.json")
        return

    # Determine next attempt number
    existing_records = bucket_state.get("attempt_records", [])
    next_attempt = max((r.get("attempt", 0) for r in existing_records), default=0) + 1

    # Load failed IDs from human_review file or instruction file
    failed_ids: list[str] = []
    review_file = run_dir / f"human_review_{bucket_name}.json"
    if review_file.exists():
        review_data = _read_json(review_file)
        failed_ids = review_data.get("failing_scenario_ids", [])
    if not failed_ids:
        # Try to find from bucket_state or attempt dirs
        for attempt_dir in sorted(run_dir.glob(f"bucket_{bucket_name}_attempt_*")):
            ids_file = attempt_dir / "failed_ids.json"
            if ids_file.exists():
                failed_ids = json.loads(ids_file.read_text())
                break

    logger.info(f"Manual re-run: bucket='{bucket_name}' attempt={next_attempt} failed_ids={len(failed_ids)}")

    # Update state to show this bucket is running
    bucket_state["status"] = "running"
    bucket_state["pending_instruction"] = None
    state["status"] = "running"
    state["current_bucket"] = bucket_name
    state["current_attempt"] = next_attempt
    _write_json(state_file, state)

    # Build prior_cfv_attempts context for the model
    prior_cfv_attempts = existing_records[-5:]  # last 5 to stay within token budget

    # Call analyze_and_fix_deep (Claude for patches, Gemini for web research)
    try:
        proposal: FixProposal = await analyze_and_fix_deep(
            bucket_name=bucket_name,
            failing_scenarios=[{"scenario_id": sid} for sid in failed_ids],
            prior_cfv_attempts=prior_cfv_attempts,
            cost_spent=state.get("cost_usd", 0.0),
            human_instruction=instruction,
        )
    except Exception as e:
        logger.error(f"analyze_and_fix_deep failed: {e}")
        bucket_state["status"] = "human_review"
        state["current_bucket"] = None
        _write_json(state_file, state)
        return

    state["cost_usd"] = state.get("cost_usd", 0.0) + proposal.cost_usd

    if proposal.rejected:
        logger.warning(f"Proposal rejected: {proposal.rejection_reason}")
        attempt_record = {
            "attempt": next_attempt,
            "outcome": "rejected",
            "rejection_reason": proposal.rejection_reason,
            "source": "manual_instruction",
            "human_instruction": instruction or "",
            "web_search_queries": proposal.web_search_queries,
            "patches": [],
            "analysis": proposal.analysis,
        }
        existing_records.append(attempt_record)
        bucket_state["status"] = "human_review"
        state["current_bucket"] = None
        _write_json(state_file, state)
        return

    # Apply patches
    patch_errors = apply_patches(proposal)
    if patch_errors:
        logger.warning(f"Patch apply errors: {patch_errors}")

    # Run fix_validation_loop for this bucket
    iter_output = run_dir / f"bucket_{bucket_name}_attempt_{next_attempt}"
    iter_output.mkdir(parents=True, exist_ok=True)
    failed_ids_path = iter_output / "failed_ids.json"
    failed_ids_path.write_text(json.dumps(failed_ids))

    cmd = [
        PYTHON, "-m", "server.training.fix_validation_loop",
        "--output", str(iter_output),
        "--workers", "10",
        "--failed-ids-file", str(failed_ids_path),
        "--bucket", bucket_name,
    ]

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
        if any(k in decoded for k in ["Bucket", "Step", "PASS", "FAIL", "threshold", "VALIDATED", "UNRESOLVED"]):
            logger.info(f"  [val] {decoded}")
    await proc.wait()

    # Parse result
    state_path = iter_output / "fix_validation_state.json"
    if state_path.exists():
        val_state = json.loads(state_path.read_text())
        bucket_result = next(
            (b for b in val_state.get("buckets", []) if b.get("name") == bucket_name),
            {"status": "unresolved", "combined_rate": 0.0, "step1_rate": 0.0, "step1_count": 0}
        )
    else:
        bucket_result = {"status": "unresolved", "combined_rate": 0.0, "step1_rate": 0.0, "step1_count": 0}

    bucket_status = bucket_result.get("status", "unresolved")
    combined_rate = float(bucket_result.get("combined_rate", 0.0))

    attempt_record = {
        "attempt": next_attempt,
        "outcome": bucket_status,
        "combined_rate": combined_rate,
        "step1_rate": bucket_result.get("step1_rate", 0.0),
        "step2_rate": bucket_result.get("step2_rate", 0.0),
        "step3_rate": bucket_result.get("step3_rate", 0.0),
        "step1_count": bucket_result.get("step1_count", 0),
        "step2_count": bucket_result.get("step2_count", 0),
        "step3_count": bucket_result.get("step3_count", 0),
        "source": "manual_instruction",
        "human_instruction": (instruction or "")[:200],
        "web_search_queries": proposal.web_search_queries,
        "patches": [{"file": p.file, "description": p.description, "old_text": p.old_text, "new_text": p.new_text} for p in proposal.patches],
        "analysis": proposal.analysis,
    }
    existing_records.append(attempt_record)
    bucket_state["attempts"] = next_attempt

    if bucket_status == "validated":
        logger.info(f"✅ Bucket '{bucket_name}' RESOLVED by manual re-run attempt {next_attempt}")
        bucket_state["status"] = "resolved_manual"
        bucket_state["resolution"] = "resolved_by_manual_instruction"
        bucket_state["final_combined_rate"] = combined_rate
    else:
        logger.info(f"❌ Attempt {next_attempt} failed (combined={combined_rate:.0%}) — reverting")
        revert_patches(proposal)
        bucket_state["status"] = "human_review"

    state["current_bucket"] = None
    state["current_attempt"] = 0
    _write_json(state_file, state)
    logger.info(f"Manual re-run complete: bucket='{bucket_name}' outcome={bucket_status} combined={combined_rate:.0%}")


async def run_deploy(bucket_name: str, run_dir: Path, deploy_attempt: int) -> None:
    """Apply the patches from a selected attempt and mark the bucket as resolved_manual."""
    from .claude_fixer import apply_patches, FixProposal, Patch

    state_file = run_dir / "cfv_state.json"
    state = _read_json(state_file)

    bucket_state = None
    for b in state.get("buckets", []):
        if b.get("name") == bucket_name:
            bucket_state = b
            break

    if not bucket_state:
        logger.error(f"Bucket '{bucket_name}' not found in cfv_state.json")
        return

    # Find the attempt record
    attempt_record = next(
        (r for r in bucket_state.get("attempt_records", []) if r.get("attempt") == deploy_attempt),
        None
    )
    if not attempt_record:
        logger.error(f"Attempt #{deploy_attempt} not found for bucket '{bucket_name}'")
        return

    patches_data = attempt_record.get("patches", [])
    if not patches_data:
        logger.error(f"Attempt #{deploy_attempt} has no patch data (only description stored)")
        return

    # Build FixProposal from stored patch data
    patches = []
    for p in patches_data:
        if isinstance(p, dict) and p.get("old_text") and p.get("new_text"):
            patches.append(Patch(
                file=p.get("file", ""),
                description=p.get("description", ""),
                old_text=p.get("old_text", ""),
                new_text=p.get("new_text", ""),
            ))

    if not patches:
        logger.error(f"Attempt #{deploy_attempt} patches have no old_text/new_text — cannot apply")
        # Mark anyway as manually selected (user is responsible)
        bucket_state["status"] = "resolved_manual"
        bucket_state["resolution"] = f"manual_selection_attempt_{deploy_attempt}_no_patch_data"
        bucket_state["selected_attempt"] = deploy_attempt
        _write_json(state_file, state)
        logger.warning("Marked as resolved_manual without applying patches (no patch data).")
        return

    proposal = FixProposal(
        analysis=attempt_record.get("analysis", f"Cherry-pick of attempt #{deploy_attempt}"),
        patches=patches,
        confidence=float(attempt_record.get("combined_rate", 0.5)),
        affected_scenarios=[],
        iteration=deploy_attempt,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    patch_errors = apply_patches(proposal)
    if patch_errors:
        logger.warning(f"Patch apply errors: {patch_errors}")

    bucket_state["status"] = "resolved_manual"
    bucket_state["resolution"] = f"manual_selection_attempt_{deploy_attempt}"
    bucket_state["selected_attempt"] = deploy_attempt
    bucket_state["final_combined_rate"] = float(attempt_record.get("combined_rate", 0.0))

    # Update overall state counts
    resolved = sum(1 for b in state.get("buckets", []) if b.get("status") in ("resolved", "resolved_manual", "resolved_by_gemini_pro"))
    state["resolved_count"] = resolved

    _write_json(state_file, state)
    logger.info(f"✅ Deployed attempt #{deploy_attempt} for bucket '{bucket_name}' — marked as resolved_manual")


def main():
    parser = argparse.ArgumentParser(description="CFV manual runner — re-run or deploy for a single bucket")
    parser.add_argument("--bucket", required=True, help="Bucket name")
    parser.add_argument("--run-dir", required=True, help="Path to the cfv_iter_N directory")
    parser.add_argument("--instruction", default="", help="Human instruction text")
    parser.add_argument("--deploy-attempt", type=int, default=0, help="If set, deploy this attempt number instead of running new")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        logger.error(f"run_dir does not exist: {run_dir}")
        sys.exit(1)

    if args.deploy_attempt > 0:
        asyncio.run(run_deploy(args.bucket, run_dir, args.deploy_attempt))
    else:
        asyncio.run(run_rerun(args.bucket, run_dir, args.instruction or None))


if __name__ == "__main__":
    main()
