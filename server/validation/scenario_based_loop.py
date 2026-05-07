"""
Per-Scenario Validation Loop with Grok Auditor & Haiku Fixer

A/B COMPARISON METHODOLOGY:
  ✓ Each batch runs the SAME 7 scenarios (personas: rude, neutral, indecisive, busy, elderly, skeptical, impatient)
  ✓ Audit Score = Baseline (Attempt 1)
  ✓ Haiku fixes = Prompt rewrites (< 90 score) or surgical fixes (≥ 90 score)
  ✓ Service restart with fixes applied
  ✓ RE-RUN THE SAME BATCH to measure A/B improvement (Attempt 2, 3)
  → This ensures identical inputs, fair comparison, and reproducible fixes

Architecture:
  Phase A (FAQs + Reservations)
    ├─ Base Script A1 (opening hours)
    │   ├─ Difficulty D1 (easy) → 7 personas → audit → [A] original score baseline
    │   │   → Haiku prompt rewrite → service restart
    │   │   → [B] re-run same 7 personas → measure improvement vs. [A]
    │   │   → Max 3 attempts of A/B cycles
    │   ├─ Difficulty D2 (normal) - same A/B cycle
    │   └─ ... D3, D4, D5
    ├─ Base Script A2 (multi-intent)
    └─ ... more base scripts
  Phase B, C, D (same structure)

Per-Scenario-Batch Loop (max 3 attempts — A/B cycles):
  1. Run scenario batch (7 personas for 1 base script + difficulty)
  2. Grok audits: fetch transcripts, score metrics (tool accuracy 40%, flow 30%, linguistic 15%, deterministic 15%)
  3. Haiku fixes: receives Grok report + Google call data + turn-by-turn metrics
     - If composite < 90: REWRITE system prompt/behavior instructions (layer2)
     - If composite ≥ 90: Apply surgical fixes to logic (layer1/layer3)
  4. Apply fixes & restart service
  5. RE-RUN THE SAME BATCH (A/B comparison)
  6. Audit again: Score improved to 80+? → advance
  7. Else attempt < 3? → retry A/B cycle
  8. Else → force advance to next batch
"""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class BatchResult:
    """Result from running a scenario batch."""
    base_script_id: str
    difficulty: str
    attempt: int
    passed: int
    total: int
    pass_rate: float
    call_sids: List[str] = field(default_factory=list)
    grok_report: Optional[Dict] = None
    haiku_fixes: Optional[Dict] = None
    fixes_applied: bool = False
    duration_s: float = 0.0


@dataclass
class PhaseProgress:
    """Track progress through a phase."""
    phase: str
    base_scripts: List[str]
    current_script_idx: int = 0
    completed_scripts: List[str] = field(default_factory=list)


class ScenarioBasedLoop:
    """Orchestrates per-scenario-batch validation with Grok & Haiku."""

    HEARTBEAT_FILE = "/tmp/sound_validation_heartbeat.json"

    def __init__(
        self,
        output_dir: str = "/tmp/scenario_validation",
        max_attempts: int = 3,
        score_threshold: float = 80.0,
        score_improvement: float = 10.0,
        workers: int = 5,
        stagger_s: int = 5,
        resume: bool = False,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_attempts = max_attempts
        self.score_threshold = score_threshold
        self.score_improvement = score_improvement
        self.workers = workers
        self.stagger_s = stagger_s
        self.resume = resume

        # Completed batches cache (populated from disk if resume=True)
        self._completed: set = set()
        if resume:
            self._load_completed_batches()

        # Import modules
        from server.validation.scenario_generator import ScenarioMatrix, Difficulty
        from server.validation.grok_auditor_integration import GrokAuditor
        from server.validation.haiku_fix_generator import HaikuFixGenerator
        from server.validation.fix_applier import FixApplier
        from server.validation.postgres_metrics_fetcher import PostgresMetricsFetcher

        self.scenario_matrix = ScenarioMatrix()
        self.grok_auditor = GrokAuditor()
        self.haiku_fixer = HaikuFixGenerator()
        self.fix_applier = FixApplier()
        self.postgres_fetcher = PostgresMetricsFetcher()

        self.Difficulty = Difficulty

    def _load_completed_batches(self) -> None:
        """Load already-completed batch keys from previous run reports."""
        completed = set()
        for report_file in self.output_dir.glob("batch_result_*.json"):
            try:
                data = json.loads(report_file.read_text())
                key = f"{data.get('base_script_id', '')}_{data.get('difficulty', '')}"
                if key:
                    completed.add(key)
            except Exception:
                pass
        self._completed = completed
        if completed:
            logger.info("[resume] Skipping %d already-completed batches: %s", len(completed), sorted(completed))

    def _write_heartbeat(self, phase: str, batch: str) -> None:
        """Write heartbeat for watchdog monitoring."""
        try:
            Path(self.HEARTBEAT_FILE).write_text(
                json.dumps({"ts": time.time(), "phase": phase, "batch": batch})
            )
        except Exception:
            pass

    async def run_full_validation(self, phases: List[str] = None) -> Dict:
        """Run full validation across all phases."""
        if phases is None:
            phases = ["a", "b", "c", "d"]
        
        logger.info("[loop] Starting full validation: phases %s", phases)
        all_results = {}
        
        for phase in phases:
            logger.info("\n" + "=" * 80)
            logger.info("PHASE %s", phase.upper())
            logger.info("=" * 80)
            
            phase_result = await self._run_phase(phase)
            all_results[phase] = phase_result
        
        return all_results

    async def _run_phase(self, phase: str) -> Dict:
        """Run single phase: iterate per (base_script, difficulty) batch."""
        phase_num = ord(phase.lower()) - ord("a")

        all_scenarios = self.scenario_matrix.get_all_scenarios_for_phase(phase_num)

        # Build ordered list of unique (base_id, difficulty) pairs that actually exist
        seen: dict = {}
        for sc in all_scenarios:
            bid = sc.get("base_id", "")
            diff = sc.get("difficulty", "")
            if bid and diff:
                key = (bid, diff)
                if key not in seen:
                    seen[key] = True

        batches = sorted(seen.keys())  # e.g. [("A1.1","D1"), ("A1.2","D2"), ...]
        logger.info("[phase] %s: %d batches found", phase.upper(), len(batches))

        phase_results = []

        for base_script_id, difficulty_str in batches:
            batch_key = f"{base_script_id}_{difficulty_str}"

            # Skip if already completed (resume mode)
            if self.resume and batch_key in self._completed:
                logger.info("[phase %s] SKIP %s (already completed)", phase.upper(), batch_key)
                continue

            logger.info("[scenario %s]", batch_key)
            self._write_heartbeat(phase, batch_key)

            batch_result = await self._run_scenario_batch_loop(
                base_script_id=base_script_id,
                difficulty=difficulty_str,
                phase=phase,
            )

            phase_results.append(asdict(batch_result))

            # Persist completed batch to disk
            batch_file = self.output_dir / f"batch_result_{batch_key}_{int(time.time())}.json"
            batch_file.write_text(json.dumps(asdict(batch_result), indent=2))
            self._completed.add(batch_key)

            if batch_result.pass_rate >= self.score_threshold / 100.0:
                logger.info("[scenario] %s PASSED (%.1f%%) → advancing",
                            batch_key, batch_result.pass_rate * 100)
            else:
                logger.warning("[scenario] %s FAILED after %d attempts → forced advance",
                               batch_key, batch_result.attempt)

        logger.info("[phase %s] COMPLETE: %d batches", phase.upper(), len(phase_results))
        return {
            "phase": phase,
            "batches_completed": len(phase_results),
            "results": phase_results,
        }

    async def _run_scenario_batch_loop(
        self,
        base_script_id: str,
        difficulty: str,
        phase: str,
    ) -> BatchResult:
        """
        Run scenario batch with up to max_attempts.

        Advancement rules:
          - Advance early: composite_score >= threshold (score_threshold)
          - Fix + retry:   composite_score < threshold, or (attempt > 1 and improvement < score_improvement)
          - Force advance: max_attempts exhausted
        """
        batch_key = f"{base_script_id}_{difficulty}"
        logger.info("[batch_loop] %s: starting (max %d attempts, threshold=%.0f)",
                    batch_key, self.max_attempts, self.score_threshold)

        baseline_score: Optional[float] = None
        last_result: Optional[BatchResult] = None

        for attempt in range(1, self.max_attempts + 1):
            logger.info(
                "[attempt %d/%d] %s %s",
                attempt, self.max_attempts, batch_key,
                "(A/B comparison: re-running same batch)" if attempt > 1 else "(Baseline run)"
            )
            t0 = time.time()

            # ── Step 1: Run scenarios ─────────────────────────────────────
            result = await self._run_scenario_batch(
                base_script_id=base_script_id,
                difficulty=difficulty,
                phase=phase,
            )
            result.attempt = attempt

            if not result.call_sids:
                logger.warning("[batch_loop] %s attempt %d produced 0 call_sids — skipping audit", batch_key, attempt)
                result.duration_s = time.time() - t0
                last_result = result
                if attempt == self.max_attempts:
                    return result
                await asyncio.sleep(5)
                continue

            # ── Step 2: Fetch metrics + Grok audit ───────────────────────
            logger.info("[audit] Fetching metrics for %d calls", len(result.call_sids))
            call_metrics = await self.postgres_fetcher.fetch_batch_metrics(result.call_sids)

            logger.info("[audit] Running Grok audit")
            grok_report = await self.grok_auditor.audit_scenario_batch(
                result.call_sids, batch_metrics=call_metrics
            )
            result.grok_report = grok_report

            composite_score = grok_report.get("composite_score", 0.0)
            n_achtung = len(call_metrics.get("achtung_flags", []))
            n_loops = len(call_metrics.get("loop_detections", []))

            if baseline_score is None:
                baseline_score = composite_score
                logger.info("[audit] Baseline score set: %.1f", baseline_score)

            improvement = composite_score - baseline_score
            meets_threshold = composite_score >= self.score_threshold

            logger.info(
                "[audit] %s | score=%.1f baseline=%.1f improvement=%.1f "
                "threshold=%.0f meets_thresh=%s flags=%d loops=%d",
                batch_key, composite_score, baseline_score, improvement,
                self.score_threshold, meets_threshold, n_achtung, n_loops,
            )

            # ── Early advance if quality is good (no +10 improvement threshold) ──
            if meets_threshold:
                logger.info("[batch_loop] %s PASSED (%.1f/%.0f) → advancing",
                            batch_key, composite_score, self.score_threshold)
                result.duration_s = time.time() - t0
                return result

            # ── Last attempt: force advance regardless ────────────────────
            if attempt == self.max_attempts:
                logger.warning("[batch_loop] %s max attempts reached — forced advance (score=%.1f)",
                               batch_key, composite_score)
                result.duration_s = time.time() - t0
                return result

            # ── Check for score regression before trying fixes ────────────
            regression = baseline_score - composite_score
            if regression > 3:
                logger.warning(
                    "[batch_loop] %s score REGRESSED: %.1f → %.1f (delta=%.1f) — reverting fixes and forced advance",
                    batch_key, baseline_score, composite_score, -regression
                )
                self.fix_applier.revert_last()
                result.duration_s = time.time() - t0
                return result

            # ── Steps 3 & 4: Generate + apply fixes ──────────────────────
            logger.info("[fix] %s: score %.1f < threshold %.0f — generating fixes (attempt %d)",
                        batch_key, composite_score, self.score_threshold, attempt)

            fix_plan = await self.haiku_fixer.generate_fixes(
                grok_report=grok_report,
                call_metrics=call_metrics,
                call_sids=result.call_sids,
            )
            result.haiku_fixes = fix_plan

            applied = await self.fix_applier.apply_fixes(fix_plan)
            result.fixes_applied = applied

            if applied:
                logger.info("[fix] %s: fixes applied — waiting for service restart", batch_key)
                # Service restart happens inside fix_applier; wait extra buffer
                await asyncio.sleep(10)
            else:
                logger.warning("[fix] %s: no fixes applied (exact matches failed or no fixes generated)", batch_key)

            result.duration_s = time.time() - t0
            last_result = result

            # Wait before next attempt (service may still be warming up)
            logger.info("[batch_loop] %s: waiting 45s before attempt %d", batch_key, attempt + 1)
            await asyncio.sleep(45)

        return last_result or result

    async def _run_scenario_batch(
        self,
        base_script_id: str,
        difficulty: str,
        phase: str,
    ) -> BatchResult:
        """Run all personas for a base script + difficulty with parallel workers."""
        from server.validation.phase_runner import run_one_scenario
        from server.validation.scenario_loader import ValidationScenario

        # Get scenarios for this batch
        phase_num = ord(phase.lower()) - ord("a")
        all_scenarios = self.scenario_matrix.get_all_scenarios_for_phase(phase_num)

        # Filter by base_id directly (not by parsing the scenario id string)
        batch_scenarios = [
            s for s in all_scenarios
            if s.get("base_id", "") == base_script_id and s.get("difficulty") == difficulty
        ]

        logger.info("[run_batch] %s_%s: %d scenarios, %d workers, %ds stagger",
                    base_script_id, difficulty, len(batch_scenarios), self.workers, self.stagger_s)

        semaphore = asyncio.Semaphore(self.workers)

        async def run_single(idx: int, sc_dict: dict):
            # Stagger the first `workers` launches; after that let semaphore control
            if idx < self.workers:
                await asyncio.sleep(idx * self.stagger_s)
            async with semaphore:
                try:
                    scenario = ValidationScenario(
                        id=sc_dict.get("id", "unknown"),
                        phase=phase_num,
                        description=sc_dict.get("script", sc_dict.get("caller_goal", "")),
                        caller_goal=sc_dict.get("caller_goal", ""),
                        caller_identity=sc_dict.get("caller_identity", {}),
                        caller_patience_turns=15,
                        tenant_id=sc_dict.get("tenant_id", "doboo"),
                        expectations=sc_dict.get("expectations", {}),
                    )
                    result = await run_one_scenario(
                        scenario,
                        sailly_ws_url=os.environ.get("SAILLY_WS_URL", "ws://127.0.0.1:8080/ws/headless"),
                        max_duration_sec=180.0,
                    )
                    status = "PASS" if result.passed else "FAIL"
                    logger.info("[scenario] %s: %s", sc_dict.get("id"), status)
                    return result
                except Exception as e:
                    logger.error("[scenario] %s failed: %s", sc_dict.get("id"), e, exc_info=True)
                    return None

        tasks = [run_single(i, sc) for i, sc in enumerate(batch_scenarios)]
        task_results = await asyncio.gather(*tasks)

        results = [r for r in task_results if r is not None]
        call_sids = [r.call_sid for r in results if hasattr(r, "call_sid") and r.call_sid]
        passed = sum(1 for r in results if r.passed)
        total = len(results)
        pass_rate = (passed / total) if total > 0 else 0.0

        return BatchResult(
            base_script_id=base_script_id,
            difficulty=difficulty,
            attempt=1,
            passed=passed,
            total=total,
            pass_rate=pass_rate,
            call_sids=call_sids,
        )


async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Per-Scenario Validation Loop")
    parser.add_argument("--phases", default="a-d", help="Phases to run (default: a-d)")
    parser.add_argument("--workers", type=int, default=5, help="Concurrent workers (default: 5)")
    parser.add_argument("--stagger-s", type=int, default=5, help="Stagger seconds between worker starts (default: 5)")
    parser.add_argument("--output-dir", default="/tmp/scenario_validation", help="Output directory")
    parser.add_argument("--resume", action="store_true", help="Resume: skip batches already recorded in output-dir")
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

    logger.info("[main] phases=%s workers=%d stagger=%ds output=%s resume=%s",
                phases, args.workers, args.stagger_s, args.output_dir, args.resume)

    # Verify env before running
    missing = [k for k in ("XAI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY") if not os.environ.get(k)]
    if missing:
        logger.error("[main] Missing required env vars: %s", missing)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    loop_runner = ScenarioBasedLoop(
        output_dir=str(output_dir),
        workers=args.workers,
        stagger_s=args.stagger_s,
        resume=args.resume,
    )

    results = await loop_runner.run_full_validation(phases=phases)

    # Save results
    report_path = output_dir / f"scenario_loop_report_{int(time.time())}.json"
    report_path.write_text(json.dumps(results, indent=2))
    logger.info("[main] Report saved to %s", report_path)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
