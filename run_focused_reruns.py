#!/usr/bin/env python3
"""
Focused reruns on known failing/timeout batches from previous discovery.

Batches to rerun:
  - B2.3_D3 (timeout / delivery address loop?)
  - D6_D3 (timeout / dish extraction?)
  - G1.1_D2 (pickup time issue?)
  - H1.1_D1 (failed)
  - I1.1_D3 (timeout)

Each batch runs with smoke only (neutral persona) first to diagnose quickly.
Then full 7-persona if smoke passes.

Usage:
  cd /home/charles2/sailly-browser-demo
  PYTHONPATH=. python3 run_focused_reruns.py
"""

import asyncio
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Known problematic batches from previous discovery
KNOWN_BATCHES = [
    ("b", "B2.3_D3"),  # timeout - delivery address loop?
    ("d", "D6_D3"),    # timeout - dish extraction?
    ("g", "G1.1_D2"),  # pickup time?
    ("h", "H1.1_D1"),  # failed
    ("i", "I1.1_D3"),  # timeout
]

OUTPUT_DIR = Path("/tmp/scenario_validation_light")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RESULTS_FILE = OUTPUT_DIR / f"focused_reruns_{int(time.time())}.json"


async def run_light_batch(phase: str, batch_key: str, max_timeout: int = 300) -> dict:
    """Run a single batch with smoke only first, then full if smoke passes."""
    logger.info(f"\n{'='*80}")
    logger.info(f"[{phase.upper()}] Batch {batch_key} — SMOKE RUN (neutral persona, timeout={max_timeout}s)")
    logger.info(f"{'='*80}")
    
    # Smoke run with neutral persona
    smoke_cmd = [
        "python3",
        "server/validation/light_validation_loop.py",
        "--phase", phase,
        "--batch", batch_key,
        "--output-dir", str(OUTPUT_DIR),
        "--workers", "1",
        "--max-attempts", "1",
        "--smoke-persona", "neutral",
        "--no-stop-on-repeat-failure",
    ]
    
    try:
        result = subprocess.run(
            smoke_cmd,
            capture_output=True,
            text=True,
            timeout=max_timeout,
            cwd="/home/charles2/sailly-browser-demo",
        )
        
        smoke_passed = result.returncode == 0
        smoke_stderr = result.stderr[-300:] if result.stderr else ""
        
        logger.info(f"[{phase.upper()}] SMOKE result: {'PASS' if smoke_passed else 'FAIL'} (exit={result.returncode})")
        if not smoke_passed and smoke_stderr:
            logger.info(f"[{phase.upper()}] SMOKE error excerpt: {smoke_stderr}")
        
        if not smoke_passed:
            return {
                "phase": phase.upper(),
                "batch_key": batch_key,
                "smoke_passed": False,
                "full_passed": False,
                "smoke_exit_code": result.returncode,
                "smoke_error": smoke_stderr,
                "note": "Smoke failed, skipping full run",
            }
        
        # Smoke passed, now run full batch
        logger.info(f"[{phase.upper()}] SMOKE passed! Running FULL batch (all 7 personas)...")
        full_cmd = [
            "python3",
            "server/validation/light_validation_loop.py",
            "--phase", phase,
            "--batch", batch_key,
            "--output-dir", str(OUTPUT_DIR),
            "--workers", "3",
            "--max-attempts", "1",
            "--smoke-persona", "neutral",
            "--skip-smoke",
            "--all-personas",
            "--no-stop-on-repeat-failure",
        ]
        
        full_result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=max_timeout,
            cwd="/home/charles2/sailly-browser-demo",
        )
        
        full_passed = full_result.returncode == 0
        full_stderr = full_result.stderr[-300:] if full_result.stderr else ""
        
        logger.info(f"[{phase.upper()}] FULL result: {'PASS' if full_passed else 'FAIL'} (exit={full_result.returncode})")
        if not full_passed and full_stderr:
            logger.info(f"[{phase.upper()}] FULL error excerpt: {full_stderr}")
        
        return {
            "phase": phase.upper(),
            "batch_key": batch_key,
            "smoke_passed": True,
            "full_passed": full_passed,
            "smoke_exit_code": 0,
            "full_exit_code": full_result.returncode,
            "full_error": full_stderr,
        }
    
    except subprocess.TimeoutExpired:
        logger.error(f"[{phase.upper()}] TIMEOUT after {max_timeout}s")
        return {
            "phase": phase.upper(),
            "batch_key": batch_key,
            "smoke_passed": False,
            "full_passed": False,
            "error": f"timeout after {max_timeout}s",
        }
    except Exception as e:
        logger.error(f"[{phase.upper()}] Exception: {e}")
        return {
            "phase": phase.upper(),
            "batch_key": batch_key,
            "smoke_passed": False,
            "full_passed": False,
            "error": str(e),
        }


async def run_all_focused() -> None:
    """Run all focused reruns."""
    logger.info("\n" + "="*80)
    logger.info("FOCUSED RERUNS ON KNOWN PROBLEMATIC BATCHES")
    logger.info("="*80)
    
    start_time = time.time()
    results = []
    
    for phase, batch_key in KNOWN_BATCHES:
        result = await run_light_batch(phase, batch_key, max_timeout=300)
        results.append(result)
        
        # Small delay between batches
        await asyncio.sleep(3)
    
    total_duration = time.time() - start_time
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("FOCUSED RERUNS COMPLETE")
    logger.info("="*80)
    logger.info(f"Total duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")
    logger.info(f"Batches run: {len(results)}")
    
    passed_full = sum(1 for r in results if r.get("full_passed"))
    passed_smoke = sum(1 for r in results if r.get("smoke_passed"))
    
    logger.info(f"Smoke passed: {passed_smoke}/{len(results)}")
    logger.info(f"Full passed: {passed_full}/{len(results)}")
    
    # Write results
    summary = {
        "timestamp": int(time.time()),
        "total_duration_s": total_duration,
        "batches_run": len(results),
        "smoke_passed": passed_smoke,
        "full_passed": passed_full,
        "results": results,
    }
    
    with open(RESULTS_FILE, "w") as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"\nResults saved to: {RESULTS_FILE}")
    logger.info(f"Artifacts location: {OUTPUT_DIR}")
    logger.info("\nNext: Analyze results and apply targeted fixes based on failure patterns.")


def main() -> int:
    try:
        asyncio.run(run_all_focused())
        return 0
    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
