"""
Parallel Scenario Runner — Execute 4 scenarios concurrently with staggered delays.

Within a bucket, runs multiple scenarios in parallel with staggered start times
to prevent simultaneous API hits (TTS, LLM, STT).

Stagger delay: 10-15 seconds between scenario starts (configurable).
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)


@dataclass
class ScenarioResult:
    """Result of a single scenario run."""
    scenario_id: str
    passed: bool
    pass_rate: float
    start_time: datetime
    end_time: datetime
    duration_ms: int
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ParallelScenarioRunner:
    """
    Runs scenarios in parallel batches with staggered start times.
    
    Example:
        runner = ParallelScenarioRunner(
            stagger_delay_s=10,
            max_concurrent=4,
        )
        results = await runner.run_batch(
            scenario_ids=["p2-order-01", "p2-order-02", "p2-order-03", "p2-order-04"],
            run_fn=run_single_scenario,
        )
    """

    def __init__(
        self,
        stagger_delay_s: float = 10.0,
        max_concurrent: int = 4,
    ):
        """
        Args:
            stagger_delay_s: Delay (seconds) between scenario start times.
            max_concurrent: Max scenarios running simultaneously.
        """
        self.stagger_delay_s = stagger_delay_s
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def _staggered_run(
        self,
        idx: int,
        scenario_id: str,
        run_fn: Callable,
        *args,
        **kwargs,
    ) -> ScenarioResult:
        """
        Run a scenario with staggered delay.
        
        Args:
            idx: Index in the batch (0-based).
            scenario_id: Scenario identifier.
            run_fn: Async function to run the scenario.
            *args, **kwargs: Arguments to pass to run_fn.
        
        Returns:
            ScenarioResult object.
        """
        # Stagger the start: idx * delay
        delay_s = idx * self.stagger_delay_s
        if delay_s > 0:
            logger.info(
                f"[Stagger] Scenario {scenario_id} waiting {delay_s:.1f}s "
                f"(batch position {idx+1}/{self.max_concurrent})"
            )
            await asyncio.sleep(delay_s)

        # Acquire semaphore slot
        async with self.semaphore:
            logger.info(f"[Start] Scenario {scenario_id}")
            start_time = datetime.utcnow()
            start_ms = time.time() * 1000

            try:
                result = await run_fn(scenario_id, *args, **kwargs)
                end_ms = time.time() * 1000
                end_time = datetime.utcnow()
                duration_ms = int(end_ms - start_ms)

                logger.info(
                    f"[Done] {scenario_id}: {result.get('passed', False)} "
                    f"({duration_ms}ms)"
                )

                return ScenarioResult(
                    scenario_id=scenario_id,
                    passed=result.get("passed", False),
                    pass_rate=result.get("pass_rate", 0.0),
                    start_time=start_time,
                    end_time=end_time,
                    duration_ms=duration_ms,
                    error=result.get("error"),
                    details=result,
                )

            except Exception as e:
                end_ms = time.time() * 1000
                end_time = datetime.utcnow()
                duration_ms = int(end_ms - start_ms)

                logger.error(f"[Error] {scenario_id}: {e}", exc_info=True)

                return ScenarioResult(
                    scenario_id=scenario_id,
                    passed=False,
                    pass_rate=0.0,
                    start_time=start_time,
                    end_time=end_time,
                    duration_ms=duration_ms,
                    error=str(e),
                )

    async def run_batch(
        self,
        scenario_ids: List[str],
        run_fn: Callable,
        *args,
        **kwargs,
    ) -> List[ScenarioResult]:
        """
        Run a batch of scenarios in parallel with staggered starts.
        
        Args:
            scenario_ids: List of scenario identifiers.
            run_fn: Async function signature: async def run_fn(scenario_id, *args, **kwargs) -> dict
            *args, **kwargs: Arguments to pass to run_fn.
        
        Returns:
            List of ScenarioResult objects (order may differ from input).
        """
        tasks = []
        for idx, scenario_id in enumerate(scenario_ids):
            task = self._staggered_run(idx, scenario_id, run_fn, *args, **kwargs)
            tasks.append(task)

        # Wait for all scenarios in the batch to complete
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Sort by start_time to get chronological order
        results = sorted(results, key=lambda r: r.start_time)

        return results

    async def run_batches(
        self,
        scenario_ids: List[str],
        run_fn: Callable,
        batch_size: int = 4,
        *args,
        **kwargs,
    ) -> List[ScenarioResult]:
        """
        Run scenarios in sequential batches (each batch runs in parallel).
        
        Example: 40 scenarios, batch_size=4
          - Batch 1: scenarios 0-3 (parallel with stagger)
          - Batch 2: scenarios 4-7 (parallel with stagger)
          - ...
          - Batch 10: scenarios 36-39 (parallel with stagger)
        
        Args:
            scenario_ids: List of scenario identifiers.
            run_fn: Async function to run each scenario.
            batch_size: How many scenarios to run in parallel.
            *args, **kwargs: Arguments to pass to run_fn.
        
        Returns:
            List of all ScenarioResult objects in chronological order.
        """
        all_results = []

        for batch_idx in range(0, len(scenario_ids), batch_size):
            batch_ids = scenario_ids[batch_idx : batch_idx + batch_size]
            batch_num = batch_idx // batch_size + 1
            total_batches = (len(scenario_ids) + batch_size - 1) // batch_size

            logger.info(
                f"[Batch {batch_num}/{total_batches}] Running {len(batch_ids)} scenarios"
            )

            batch_results = await self.run_batch(batch_ids, run_fn, *args, **kwargs)
            all_results.extend(batch_results)

            # Summary for this batch
            passed = sum(1 for r in batch_results if r.passed)
            total = len(batch_results)
            logger.info(
                f"[Batch {batch_num} done] {passed}/{total} passed "
                f"({passed/total*100:.1f}%)"
            )

        return all_results

    @staticmethod
    def aggregate_results(results: List[ScenarioResult]) -> Dict[str, Any]:
        """
        Aggregate results from a batch/batches.
        
        Returns:
            Dict with: passed, failed, pass_rate, duration_ms, results.
        """
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        # Total duration: from first start to last end
        if results:
            start = min(r.start_time for r in results)
            end = max(r.end_time for r in results)
            total_duration_ms = int((end - start).total_seconds() * 1000)
        else:
            total_duration_ms = 0

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "total_duration_ms": total_duration_ms,
            "results": results,
        }


async def demo_run_fn(scenario_id: str) -> Dict[str, Any]:
    """
    Demo run function (for testing).
    Simulates a scenario run with variable delay.
    """
    import random

    delay = random.uniform(5, 15)
    await asyncio.sleep(delay)

    passed = random.random() > 0.2  # 80% pass rate
    return {
        "scenario_id": scenario_id,
        "passed": passed,
        "pass_rate": 1.0 if passed else 0.0,
    }


async def demo():
    """Demo: run 40 scenarios in batches of 4."""
    runner = ParallelScenarioRunner(stagger_delay_s=10, max_concurrent=4)

    scenario_ids = [f"p2-order-{i:02d}" for i in range(1, 41)]

    results = await runner.run_batches(
        scenario_ids=scenario_ids,
        run_fn=demo_run_fn,
        batch_size=4,
    )

    summary = runner.aggregate_results(results)
    print(f"\nSummary: {summary['passed']}/{summary['total']} passed "
          f"({summary['pass_rate']*100:.1f}%)")
    print(f"Total duration: {summary['total_duration_ms']/1000:.1f}s")


if __name__ == "__main__":
    asyncio.run(demo())
