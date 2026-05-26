#!/usr/bin/env python3
"""Quick smoke reruns on the 3 fixed batches after code changes."""

import asyncio
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Fixed batches to rerun (after code changes)
FIXED_BATCHES = [
    ("i", "I1.1_D3"),  # Address correction fix
    ("d", "D6_D3"),    # Readback loop fix
    ("g", "G1.1_D2"),  # Minor persona fix
]

OUTPUT_DIR = Path("/tmp/scenario_validation_light")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

async def run_smoke_batch(phase: str, batch_key: str) -> dict:
    """Run smoke (neutral persona) only for quick validation."""
    logger.info(f"\n{'='*60}")
    logger.info(f"[{phase.upper()}] {batch_key} SMOKE")
    logger.info(f"{'='*60}")
    
    cmd = [
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
            cmd, capture_output=True, text=True, timeout=300,
            cwd="/home/charles2/sailly-browser-demo",
        )
        passed = result.returncode == 0
        logger.info(f"[{phase.upper()}] Result: {'PASS ✅' if passed else 'FAIL ❌'}")
        
        return {
            "phase": phase.upper(),
            "batch_key": batch_key,
            "passed": passed,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        logger.error(f"[{phase.upper()}] TIMEOUT")
        return {
            "phase": phase.upper(),
            "batch_key": batch_key,
            "passed": False,
            "exit_code": -1,
            "error": "timeout",
        }

async def main():
    logger.info("="*60)
    logger.info("QUICK SMOKE RERUNS ON FIXED BATCHES")
    logger.info("="*60)
    
    results = []
    for phase, batch_key in FIXED_BATCHES:
        r = await run_smoke_batch(phase, batch_key)
        results.append(r)
        await asyncio.sleep(2)
    
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    passed = sum(1 for r in results if r["passed"])
    logger.info(f"Passed: {passed}/{len(results)}")
    for r in results:
        status = "✅" if r["passed"] else "❌"
        logger.info(f"  {status} {r['batch_key']}")
    
    return 0 if passed == len(results) else 1

sys.exit(asyncio.run(main()))
