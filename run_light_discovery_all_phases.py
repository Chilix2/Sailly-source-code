#!/usr/bin/env python3
"""
Orchestrator for comprehensive light validation discovery across all phases A-I.

Runs light validation loops for each phase, generating deterministic scores and artifacts.
No Grok audit, no Haiku fixer, focus on deterministic failures and tool calls.

Usage:
  cd /home/charles2/sailly-browser-demo
  PYTHONPATH=. python3 run_light_discovery_all_phases.py
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

# All phases and their batches (simplified; expand as needed)
PHASES = ["a", "b", "c", "d", "e", "f", "g", "h", "i"]

# Sample batches per phase (expand this based on actual scenario matrix)
PHASE_BATCHES = {
    "a": ["A1.1_D1", "A2.1_D1", "A3.1_D1"],
    "b": ["B1.1_D1", "B2.1_D1", "B2.3_D3"],
    "c": ["C1.1_D1", "C2.1_D1"],
    "d": ["D1.1_D1", "D2.1_D1", "D6_D3"],
    "e": ["E1.1_D1", "E2.1_D1"],
    "f": ["F1.1_D1", "F2.1_D1"],
    "g": ["G1.1_D1", "G1.1_D2"],
    "h": ["H1.1_D1"],
    "i": ["I1.1_D1", "I1.1_D3"],
}

OUTPUT_DIR = Path("/tmp/scenario_validation_light")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DISCOVERY_SUMMARY_FILE = OUTPUT_DIR / f"discovery_summary_{int(time.time())}.json"


async def run_light_batch(phase: str, batch_key: str) -> dict:
    """Run a single batch via light_validation_loop.py."""
    cmd = [
        "python3",
        "server/validation/light_validation_loop.py",
        "--phase", phase,
        "--batch", batch_key,
        "--output-dir", str(OUTPUT_DIR),
        "--workers", "3",
        "--max-attempts", "3",
        "--smoke-persona", "neutral",
        "--skip-smoke",  # For discovery, skip smoke; run all personas
        "--all-personas",
        "--no-stop-on-repeat-failure",
    ]
    
    logger.info(f"[{phase.upper()}] Starting batch {batch_key}...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min per batch
            cwd="/home/charles2/sailly-browser-demo",
        )
        
        if result.returncode != 0:
            logger.warning(f"[{phase.upper()}] Batch {batch_key} returned exit code {result.returncode}")
            logger.debug(f"stderr: {result.stderr}")
        else:
            logger.info(f"[{phase.upper()}] Batch {batch_key} completed successfully")
        
        return {
            "phase": phase.upper(),
            "batch_key": batch_key,
            "exit_code": result.returncode,
            "stdout": result.stdout[-500:] if result.stdout else "",  # last 500 chars
            "stderr": result.stderr[-500:] if result.stderr else "",
        }
    
    except subprocess.TimeoutExpired:
        logger.error(f"[{phase.upper()}] Batch {batch_key} timed out after 10 minutes")
        return {
            "phase": phase.upper(),
            "batch_key": batch_key,
            "exit_code": -1,
            "error": "timeout",
        }
    except Exception as e:
        logger.error(f"[{phase.upper()}] Batch {batch_key} failed: {e}")
        return {
            "phase": phase.upper(),
            "batch_key": batch_key,
            "exit_code": -1,
            "error": str(e),
        }


async def discover_all_phases() -> None:
    """Run discovery for all phases sequentially."""
    logger.info("=" * 80)
    logger.info("STARTING COMPREHENSIVE LIGHT DISCOVERY (All Phases A-I)")
    logger.info("=" * 80)
    
    start_time = time.time()
    all_results = []
    
    for phase in PHASES:
        phase_start = time.time()
        logger.info(f"\n>>> PHASE {phase.upper()} <<<")
        
        batches = PHASE_BATCHES.get(phase, [])
        if not batches:
            logger.warning(f"No batches defined for phase {phase}")
            continue
        
        phase_results = []
        for batch_key in batches:
            result = await run_light_batch(phase, batch_key)
            phase_results.append(result)
            all_results.append(result)
            
            # Small delay between batches
            await asyncio.sleep(2)
        
        phase_duration = time.time() - phase_start
        passed = sum(1 for r in phase_results if r.get("exit_code") == 0)
        logger.info(f"PHASE {phase.upper()} SUMMARY: {passed}/{len(phase_results)} passed in {phase_duration:.1f}s")
    
    total_duration = time.time() - start_time
    
    logger.info("\n" + "=" * 80)
    logger.info("DISCOVERY COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total duration: {total_duration:.1f}s")
    logger.info(f"Total batches run: {len(all_results)}")
    logger.info(f"Passed: {sum(1 for r in all_results if r.get('exit_code') == 0)}")
    logger.info(f"Failed: {sum(1 for r in all_results if r.get('exit_code') != 0)}")
    
    # Write summary
    summary = {
        "timestamp": int(time.time()),
        "total_duration_s": total_duration,
        "phases": PHASES,
        "total_batches": len(all_results),
        "passed": sum(1 for r in all_results if r.get("exit_code") == 0),
        "failed": sum(1 for r in all_results if r.get("exit_code") != 0),
        "results": all_results,
    }
    
    with open(DISCOVERY_SUMMARY_FILE, "w") as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"\nSummary saved to: {DISCOVERY_SUMMARY_FILE}")
    logger.info(f"Artifacts location: {OUTPUT_DIR}")
    logger.info("\nNext step: Analyze light_result_*.json files to identify remaining failure clusters.")


def main() -> int:
    try:
        asyncio.run(discover_all_phases())
        return 0
    except Exception as e:
        logger.error(f"Discovery failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
