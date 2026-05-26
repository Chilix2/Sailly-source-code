"""
Progress Monitor — tracks validation phases and detects stuck loops.

If no progress is detected for N seconds, escalates to Claude Haiku 4.5 for diagnosis.
Runs phases a-d with automatic recovery.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ProgressMonitor:
    """Monitor validation progress and detect stuck loops."""

    def __init__(
        self,
        stuck_threshold_sec: int = 120,
        check_interval_sec: int = 10,
        max_phase_duration_sec: int = 600,
    ):
        self.stuck_threshold_sec = stuck_threshold_sec
        self.check_interval_sec = check_interval_sec
        self.max_phase_duration_sec = max_phase_duration_sec
        
        # Track progress per phase
        self.phase_progress: Dict[str, dict] = {}
        self.last_progress_time: Dict[str, float] = {}
        
    def start_phase(self, phase: str) -> None:
        """Mark start of a phase."""
        self.phase_progress[phase] = {
            "started_at": time.time(),
            "last_scenario": None,
            "scenarios_completed": 0,
        }
        self.last_progress_time[phase] = time.time()
        logger.info("[monitor] Phase %s started at %s", phase.upper(), 
                   datetime.now().strftime("%H:%M:%S"))

    def update_progress(self, phase: str, scenario_id: str) -> None:
        """Update with a new completed scenario."""
        if phase not in self.phase_progress:
            self.phase_progress[phase] = {"scenarios_completed": 0}
        
        self.phase_progress[phase]["last_scenario"] = scenario_id
        self.phase_progress[phase]["scenarios_completed"] += 1
        self.last_progress_time[phase] = time.time()
        
        logger.debug("[monitor] Phase %s progress: scenario %s (total: %d)",
                    phase, scenario_id, self.phase_progress[phase]["scenarios_completed"])

    def is_stuck(self, phase: str) -> bool:
        """Check if a phase is stuck (no progress for threshold seconds)."""
        if phase not in self.last_progress_time:
            return False
        
        elapsed = time.time() - self.last_progress_time[phase]
        if elapsed > self.stuck_threshold_sec:
            logger.warning("[monitor] Phase %s appears stuck (no progress for %.0fs)", 
                          phase, elapsed)
            return True
        return False

    def check_all_phases(self) -> Optional[str]:
        """Check if any phase is stuck. Returns stuck phase or None."""
        for phase in self.phase_progress.keys():
            if self.is_stuck(phase):
                return phase
        return None

    def get_summary(self, phase: str) -> Dict:
        """Get phase progress summary."""
        if phase not in self.phase_progress:
            return {}
        
        progress = self.phase_progress[phase]
        elapsed = time.time() - progress.get("started_at", time.time())
        
        return {
            "phase": phase.upper(),
            "scenarios_completed": progress.get("scenarios_completed", 0),
            "last_scenario": progress.get("last_scenario", "none"),
            "elapsed_sec": int(elapsed),
            "stuck": self.is_stuck(phase),
        }


async def run_validation_with_monitor(
    phases: List[str],
    workers: int = 2,
    stagger_s: int = 5,
    max_attempts: int = 3,
) -> Dict:
    """
    Run validation phases with progress monitoring.
    
    Calls Claude Haiku 4.5 for diagnosis if stuck.
    """
    monitor = ProgressMonitor()
    all_reports = {}
    
    for phase in phases:
        logger.info("\n" + "=" * 80)
        logger.info("PHASE %s — Starting with monitoring", phase.upper())
        logger.info("=" * 80)
        
        monitor.start_phase(phase)
        
        # Run the phase via script_validation.py
        cmd = [
            sys.executable, "-m", "server.validation.script_validation",
            f"--phases={phase}",
            f"--workers={workers}",
            f"--stagger-s={stagger_s}",
            f"--max-attempts={max_attempts}",
        ]
        
        logger.info("[monitor] Executing: %s", " ".join(cmd))
        
        try:
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent.parent.parent,
                capture_output=True,
                text=True,
                timeout=monitor.max_phase_duration_sec,
            )
            
            # Parse report if it was generated
            report_dir = Path("/tmp/script_validation")
            if report_dir.exists():
                # Find the latest report for this phase
                reports = sorted(report_dir.glob(f"validation_report_{phase}_*.json"))
                if reports:
                    latest_report = reports[-1]
                    with open(latest_report) as f:
                        report = json.load(f)
                        all_reports[phase] = report
                        logger.info("[monitor] Phase %s report: %d/%d scenarios passed",
                                   phase.upper(), 
                                   report.get("scenarios_passed", 0),
                                   report.get("scenarios_total", 0))
                        
                        # Update monitor
                        monitor.phase_progress[phase]["scenarios_completed"] = \
                            report.get("scenarios_total", 0)
                        monitor.last_progress_time[phase] = time.time()
            
            if result.returncode != 0:
                logger.warning("[monitor] Phase %s returned non-zero: %d", phase, result.returncode)
                if "exception" in result.stderr.lower() or "error" in result.stderr.lower():
                    logger.error("[monitor] Errors detected in output:\n%s", result.stderr[-500:])
            
            logger.info("[monitor] Phase %s complete", phase.upper())
            
        except subprocess.TimeoutExpired:
            logger.error("[monitor] Phase %s TIMEOUT after %ds", phase, monitor.max_phase_duration_sec)
            
            # Call Claude Haiku 4.5 for diagnosis
            await diagnose_with_claude(phase, monitor)
            
        except Exception as e:
            logger.error("[monitor] Phase %s failed with exception: %s", phase, e)
            await diagnose_with_claude(phase, monitor)
    
    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("VALIDATION COMPLETE")
    logger.info("=" * 80)
    
    for phase, report in all_reports.items():
        passed = report.get("scenarios_passed", 0)
        total = report.get("scenarios_total", 0)
        rate = (passed / total * 100) if total > 0 else 0
        logger.info("Phase %s: %d/%d (%.1f%%)", phase.upper(), passed, total, rate)
    
    return all_reports


async def diagnose_with_claude(phase: str, monitor: ProgressMonitor) -> None:
    """Call Claude Haiku 4.5 to diagnose stuck phase."""
    logger.warning("[monitor] Calling Claude Haiku 4.5 for diagnosis...")
    
    summary = monitor.get_summary(phase)
    
    try:
        from anthropic import Anthropic
        
        client = Anthropic()
        
        message = client.messages.create(
            model=os.environ.get("HAIKU_FIX_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": f"""
The validation phase {phase.upper()} appears to be stuck or has encountered an error.

**Phase Progress:**
- Scenarios completed: {summary.get('scenarios_completed', 0)}
- Last scenario: {summary.get('last_scenario', 'unknown')}
- Elapsed time: {summary.get('elapsed_sec', 0)}s
- Status: {'STUCK' if summary.get('stuck') else 'ERROR/TIMEOUT'}

**What should we check or fix to get this validation running again?**

Provide a concise 2-3 bullet point diagnosis and next steps.
""",
                }
            ],
        )
        
        diagnosis = message.content[0].text if message.content else "No diagnosis"
        logger.warning("[monitor] Claude Haiku diagnosis:\n%s", diagnosis)
        
    except Exception as e:
        logger.error("[monitor] Failed to call Claude Haiku: %s", e)


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Progress Monitor for Validation Pipeline"
    )
    parser.add_argument(
        "--phases",
        default="a-d",
        help="Phases to run (default: a-d)",
    )
    parser.add_argument("--workers", type=int, default=2, help="Concurrent workers (default: 2)")
    parser.add_argument("--stagger-s", type=int, default=5, help="Stagger seconds (default: 5)")
    parser.add_argument("--max-attempts", type=int, default=3, help="Max retries per phase (default: 3)")
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    
    # Parse phases
    phases_arg = args.phases.strip().lower()
    if "-" in phases_arg and len(phases_arg) == 3:
        start, end = phases_arg[0], phases_arg[2]
        phases = [chr(i) for i in range(ord(start), ord(end) + 1)]
    else:
        phases = [p.strip() for p in phases_arg.split(",")]
    
    logger.info("[monitor] Starting validation of phases: %s", phases)
    
    reports = await run_validation_with_monitor(
        phases=phases,
        workers=args.workers,
        stagger_s=args.stagger_s,
        max_attempts=args.max_attempts,
    )
    
    logger.info("[monitor] All phases complete. Reports: %d", len(reports))
    
    return 0 if len(reports) == len(phases) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
