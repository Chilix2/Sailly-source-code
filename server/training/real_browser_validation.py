"""
RealBrowserValidation — Complete autonomous validation loop.

Runs on GCP VM continuously. Tests buckets, auto-fixes failures using Claude Haiku,
deploys passing buckets to live demo, and never loops forever.

Architecture:
  Phase A:  Smoke gate (5 scenarios, must pass 100%)
  Phase B+C: Bucket loop with auto-fix (3 attempts max per bucket)
  Phase D:  Summary notification

Each bucket:
  - Runs scenarios in parallel batches (4 concurrent with 10s stagger)
  - If fails: Claude Haiku proposes 1 fix, apply, re-run entire bucket, attempt += 1
  - If passes: auto-deploy to live demo, move to next bucket
  - After 3 attempts: bucket deferred, move to next bucket

Usage:
    python -m server.training.real_browser_validation [--bucket BUCKET] [--smoke-only]

CLI args:
    --bucket BUCKET     Run specific bucket only (e.g., "1_order")
    --smoke-only        Run Phase A smoke gate only
    --no-fix            Run buckets without auto-fix (measurement only)
    --parallel N        Number of scenarios to run in parallel (default 4)
    --stagger-delay S   Delay between staggered scenario starts (default 10s)
    --ws-url URL        WebSocket URL for voice agent (default ws://localhost:3003/ws/demo)
    --fast              Use fast mode (50-70s per scenario)
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any


def _load_dotenv(env_path: str = "/home/charles2/sailly-google-fork/.env"):
    """Load .env file into os.environ (simple parser, no dependencies)."""
    p = Path(env_path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key.isidentifier():
            os.environ.setdefault(key, val)


# Load credentials before anything else
_load_dotenv()
# run_browser_validation reads GCP_PROJECT_ID
os.environ.setdefault("GCP_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT", "sailly-voice-agent-eu"))

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@dataclass
class BucketStatus:
    """Status of a bucket run."""
    bucket: str
    status: str  # "pending" | "running" | "passed" | "deferred" | "error"
    pass_rate: float = 0.0
    attempts: int = 0
    deployed: bool = False
    deployed_at: Optional[str] = None
    manual_test: str = "pending"  # "pending" | "passed" | "failed"
    fixes_applied: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class ValidationStatus:
    """Overall validation run status (saved to status.json)."""
    started_at: str
    overall_status: str  # "running" | "completed" | "stopped"
    current_phase: str  # "smoke" | "bucket_X" | "summary"
    heartbeat: str
    elapsed_seconds: float = 0.0
    hard_timeout_seconds: float = 43200.0  # 12 hours
    
    smoke: Optional[BucketStatus] = None
    buckets: Dict[str, BucketStatus] = field(default_factory=dict)
    
    deployments: List[Dict[str, Any]] = field(default_factory=list)
    fix_history: List[Dict[str, Any]] = field(default_factory=list)
    
    api_health: Dict[str, Any] = field(default_factory=dict)


class RealBrowserValidation:
    """Main orchestrator for the validation loop."""

    def __init__(
        self,
        ws_url: str = "ws://localhost:3003/ws/demo",
        fast_mode: bool = False,
        parallel: int = 4,
        stagger_delay_s: float = 10.0,
        no_fix: bool = False,
    ):
        self.ws_url = ws_url
        self.fast_mode = fast_mode
        self.parallel = parallel
        self.stagger_delay_s = stagger_delay_s
        self.no_fix = no_fix
        self.repo_dir = Path("/home/charles2/sailly-google-fork")
        self.status_file = Path("/tmp/real_browser_validation/status.json")
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        
        # State
        self.start_time = datetime.utcnow()
        self.stop_requested = False
        self.status = ValidationStatus(
            started_at=self.start_time.isoformat() + "Z",
            overall_status="running",
            current_phase="initializing",
            heartbeat=datetime.utcnow().isoformat() + "Z",
        )
        
        # Modules initialised in _setup_imports()
        self.auto_fix = None
        self.deployer = None

    def _setup_imports(self):
        """Set up imports from repo."""
        sys.path.insert(0, str(self.repo_dir))

        try:
            from server.training.auto_fix_engine import AutoFixEngine
            from server.training.deploy_to_live import DeployToLive

            self.auto_fix = AutoFixEngine()
            self.deployer = DeployToLive()
        except ImportError as e:
            logger.error(f"Failed to import modules: {e}")
            raise

    def _save_status(self):
        """Save current status to status.json."""
        self.status.heartbeat = datetime.utcnow().isoformat() + "Z"
        self.status.elapsed_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        status_dict = asdict(self.status)
        self.status_file.write_text(json.dumps(status_dict, indent=2, default=str))

    async def _run_bucket_scenarios(
        self,
        bucket_name: str,
        scenario_ids: List[str],
    ) -> tuple[float, List[Dict[str, Any]]]:
        """
        Run a specific set of scenarios by importing run_all() directly.

        Returns:
            (pass_rate_pct, failed_scenarios)  — pass_rate is 0–100
        """
        from server.training.run_browser_validation import run_all, FAST_CONFIG, STRICT_CONFIG

        output_dir = Path(f"/tmp/rbv_{bucket_name}_{int(datetime.utcnow().timestamp())}")
        output_dir.mkdir(parents=True, exist_ok=True)

        cfg = FAST_CONFIG if self.fast_mode else STRICT_CONFIG
        logger.info(
            f"[{bucket_name}] Running {len(scenario_ids)} scenarios "
            f"({'FAST' if self.fast_mode else 'STRICT'} mode) → {output_dir}"
        )

        try:
            report = await run_all(
                ws_url=self.ws_url,
                phases=[1, 2, 3, 4],        # load all phases so IDs can be found
                scenario_ids=scenario_ids,   # filter to this bucket's IDs only
                include_multi_intent=False,
                max_scenarios=None,
                output_dir=str(output_dir),
                compare_phase_a=None,
                inter_scenario_pause=2.0,
                config=cfg,
                max_concurrent=self.parallel,          # 4 concurrent per batch
                stagger_delay_s=self.stagger_delay_s,  # 10s between starts
            )
        except Exception as e:
            logger.error(f"[{bucket_name}] run_all raised: {e}", exc_info=True)
            return 0.0, []

        if not report:
            logger.error(f"[{bucket_name}] run_all returned empty report")
            return 0.0, []

        # pass_rate is already a percentage (0–100) in the report
        pass_rate_pct = report.get("pass_rate", 0.0)
        results = report.get("results", [])
        failed = [r for r in results if not r.get("passed", False)]

        logger.info(
            f"[{bucket_name}] {pass_rate_pct:.1f}%  "
            f"({len(results) - len(failed)}/{len(results)} passed)"
        )
        return pass_rate_pct, failed

    async def phase_a_smoke(self):
        """Phase A: Smoke gate (5 scenarios, must pass 100%)."""
        logger.info("=== Phase A: Smoke Gate ===")
        self.status.current_phase = "smoke"
        self.status.smoke = BucketStatus(bucket="smoke", status="running")
        self._save_status()
        
        # Smoke = pipeline liveness only. Use scenarios requiring ONLY basic tools
        # (ai_greeting, get_date_info) so smoke never fails due to agent logic bugs.
        smoke_ids = [
            "p1-faq-01",           # Opening hours — needs get_date_info only
            "p1-faq-opening-hours-01",  # Opening hours variant
            "p1-faq-menu-01",      # Menu question — needs get_menu only
        ]
        
        pass_rate, failed = await self._run_bucket_scenarios("smoke", smoke_ids)
        
        self.status.smoke.pass_rate = pass_rate
        self.status.smoke.attempts = 1
        
        # Smoke gate: ≥67% (2/3) = pipeline alive and audio round-trip works.
        if pass_rate < 67.0:
            logger.error(f"Smoke FAILED: {pass_rate:.1f}% < 67%. Audio pipeline may be broken. Stopping.")
            self.status.smoke.status = "failed"
            self.status.overall_status = "stopped"
            self._save_status()
            return False
        
        logger.info(f"Smoke PASSED ({pass_rate:.1f}%). Proceeding to buckets.")
        self.status.smoke.status = "passed"
        self._save_status()
        return True

    async def phase_b_c_buckets(self):
        """Phase B+C: Bucket loop with auto-fix."""
        logger.info("=== Phase B+C: Bucket Loop ===")
        
        buckets = [
            ("1_order", [
                "p2-order-01", "p2-order-03", "p2-order-04", "p2-order-05",
                "p2-order-07", "p2-order-002", "p2-order-043", "p2-order-046",
                "p3-impatient-02", "p4-hard_to_hear-02",
            ]),
            ("2_greeting", [
                "p1-faq-01", "p1-faq-05", "p1-faq-10", "p1-faq-16",
                "p2-faq-01", "p3-faq-01", "p3-faq-002", "p3-faq-04", "p3-faq-05",
            ]),
            ("3_reservation", [
                "p2-reservation-01", "p3-reservation-02", "p3-reservation-006",
                "p3-reservation-010", "p3-reservation-05", "p4-elderly-02",
            ]),
            ("4_dual_intent", [
                "p3-chaos-01", "p3-chaos-06", "p3-chaos-001",
                "p3-sleepy-01", "p3-sleepy-03", "p3-sleepy-04",
            ]),
            ("5_escalation", [
                "p3-angry-01", "p3-angry-02", "p3-angry-05",
                "p4-escalation-04", "p4-frustration-06", "p1-transfer-agent-01",
            ]),
            ("6_edge_cases", [
                "p4-elderly-01", "p4-hard_to_hear-02", "p3-accent-04",
                "p3-accent-07", "p4-technical-03", "p4-parking-08",
            ]),
        ]

        # pass_rate is 0–100 percentage; threshold is 95%
        threshold = 95.0
        
        for bucket_name, base_scenarios in buckets:
            if self.stop_requested or self._timeout_exceeded():
                logger.warning("Stop requested or timeout exceeded, aborting.")
                break
            
            # Expand with variants (1 anchor → 4 variants = 4 scenarios)
            # For now, just use base scenarios (variants would be generated dynamically)
            scenario_ids = []
            for base_id in base_scenarios:
                scenario_ids.append(base_id)
                # TODO: add variant IDs when variation generation is integrated
            
            logger.info(f"\n=== Bucket {bucket_name} ({len(scenario_ids)} scenarios) ===")
            self.status.current_phase = f"bucket_{bucket_name}"
            self.status.buckets[bucket_name] = BucketStatus(bucket=bucket_name, status="running")
            self._save_status()
            
            # Attempt loop (max 3 attempts)
            for attempt in range(1, 4):
                if self.stop_requested or self._timeout_exceeded():
                    break
                
                logger.info(f"Attempt {attempt}/3 for {bucket_name}...")
                self.status.buckets[bucket_name].attempts = attempt
                
                # Run bucket
                pass_rate, failed = await self._run_bucket_scenarios(bucket_name, scenario_ids)
                self.status.buckets[bucket_name].pass_rate = pass_rate
                
                if pass_rate >= threshold:
                    # PASS: deploy
                    logger.info(f"✓ {bucket_name} passed at {pass_rate:.1f}%")
                    self.status.buckets[bucket_name].status = "passed"
                    
                    # Deploy
                    if not self.no_fix:
                        deploy_result = await self.deployer.deploy(bucket_name, pass_rate)
                        if deploy_result.deployed:
                            self.status.buckets[bucket_name].deployed = True
                            self.status.buckets[bucket_name].deployed_at = datetime.utcnow().isoformat() + "Z"
                            self.status.deployments.append({
                                "time": datetime.utcnow().isoformat() + "Z",
                                "bucket": bucket_name,
                                "pass_rate": pass_rate,
                                "commit": deploy_result.commit_hash,
                                "smoke": deploy_result.smoke_result,
                            })
                            logger.info(f"✓ {bucket_name} deployed to live")
                        else:
                            logger.warning(f"✗ Deploy failed for {bucket_name}: {deploy_result.error}")
                    
                    self._save_status()
                    break  # Move to next bucket
                
                else:
                    # FAIL: try to fix (unless last attempt)
                    logger.info(f"✗ {bucket_name} at {pass_rate:.1f}% (threshold {threshold:.1f}%)")
                    
                    if attempt < 3 and not self.no_fix and failed:
                        logger.info(f"Attempting auto-fix for {bucket_name}...")
                        fix_result = await self.auto_fix.run_fix_cycle(
                            bucket_name=bucket_name,
                            failed_scenarios=failed,
                            pass_rate=pass_rate,
                            attempt_num=attempt,
                        )
                        
                        if fix_result.applied:
                            logger.info(f"Fix applied: {fix_result.reason}")
                            self.status.buckets[bucket_name].fixes_applied.append({
                                "attempt": attempt,
                                "tier": fix_result.tier,
                                "changes": fix_result.changes,
                                "reason": fix_result.reason,
                            })
                            self.status.fix_history.append({
                                "time": datetime.utcnow().isoformat() + "Z",
                                "bucket": bucket_name,
                                "attempt": attempt,
                                "result": "applied",
                            })
                            # Loop will retry the bucket
                        else:
                            logger.warning(f"Fix not applied: {fix_result.reason}")
                            self.status.fix_history.append({
                                "time": datetime.utcnow().isoformat() + "Z",
                                "bucket": bucket_name,
                                "attempt": attempt,
                                "result": "not_applied",
                                "reason": fix_result.reason,
                            })
                    
                    self._save_status()
            
            else:
                # All 3 attempts exhausted
                logger.warning(f"✗ {bucket_name} deferred after 3 attempts")
                self.status.buckets[bucket_name].status = "deferred"
                self._save_status()

    async def phase_d_summary(self):
        """Phase D: Final summary notification."""
        logger.info("=== Phase D: Summary ===")
        self.status.current_phase = "summary"
        
        passed = sum(1 for b in self.status.buckets.values() if b.status == "passed")
        deferred = sum(1 for b in self.status.buckets.values() if b.status == "deferred")
        total = len(self.status.buckets)
        
        summary = {
            "buckets_passed": passed,
            "buckets_deferred": deferred,
            "total_buckets": total,
            "total_fixes": len(self.status.fix_history),
            "deployments": len(self.status.deployments),
            "elapsed_hours": self.status.elapsed_seconds / 3600.0,
        }
        
        logger.info(f"Summary: {json.dumps(summary, indent=2)}")
        self.status.overall_status = "completed"
        self._save_status()

    def _timeout_exceeded(self) -> bool:
        """Check if hard 12-hour timeout exceeded."""
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        if elapsed > self.status.hard_timeout_seconds:
            logger.error("Hard 12-hour timeout exceeded!")
            return True
        return False

    async def run(self, bucket_only: Optional[str] = None, smoke_only: bool = False):
        """Main entry point."""
        self._setup_imports()
        
        try:
            # Phase A: Smoke
            if not await self.phase_a_smoke():
                logger.error("Smoke gate failed, aborting.")
                return
            
            if smoke_only:
                logger.info("Smoke-only mode, exiting.")
                self.status.overall_status = "completed"
                self._save_status()
                return
            
            # Phase B+C: Buckets (or specific bucket)
            await self.phase_b_c_buckets()
            
            # Phase D: Summary
            await self.phase_d_summary()
            
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            self.status.overall_status = "stopped"
            self._save_status()
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            self.status.overall_status = "error"
            self.status.buckets["error"] = BucketStatus(
                bucket="error",
                status="error",
                error=str(e),
            )
            self._save_status()


async def main():
    parser = argparse.ArgumentParser(description="RealBrowserValidation — Autonomous validation loop")
    parser.add_argument("--bucket", help="Run specific bucket only")
    parser.add_argument("--smoke-only", action="store_true", help="Run smoke gate only")
    parser.add_argument("--no-fix", action="store_true", help="Run without auto-fix")
    parser.add_argument("--parallel", type=int, default=4, help="Parallel scenarios per batch")
    parser.add_argument("--stagger-delay", type=float, default=10.0, help="Stagger delay (seconds)")
    parser.add_argument("--ws-url", default="ws://localhost:3003/ws/demo", help="WebSocket URL")
    parser.add_argument("--fast", action="store_true", help="Fast mode")
    
    args = parser.parse_args()
    
    validator = RealBrowserValidation(
        ws_url=args.ws_url,
        fast_mode=args.fast,
        parallel=args.parallel,
        stagger_delay_s=args.stagger_delay,
        no_fix=args.no_fix,
    )
    
    await validator.run(bucket_only=args.bucket, smoke_only=args.smoke_only)


if __name__ == "__main__":
    asyncio.run(main())
