"""
server/brain/worker_executor.py — Stage 3: Parallel Worker Execution Engine (Phase 4.4).

Runs Required workers with a hard deadline (cancel after 280ms),
Optional workers with a soft deadline (cancel after 350ms from start),
and Background workers as fire-and-forget tasks.

Returns an ExecutionResult with outputs, failure lists, and latency stats.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from server.brain.workers import (
    ExecutionPlan,
    ExecutionResult,
    Worker,
    WorkerContext,
    WorkerOutput,
)

logger = logging.getLogger(__name__)


async def _run_timed(worker: Worker, ctx: WorkerContext) -> WorkerOutput:
    """Run a single worker, catching exceptions and recording latency."""
    t0 = time.monotonic()
    try:
        result = await asyncio.wait_for(
            worker.run(ctx),
            timeout=worker.timeout_ms / 1000.0,
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        result.latency_ms = elapsed_ms
        return result
    except asyncio.TimeoutError:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        logger.warning(
            f"[WorkerExecutor] {worker.name} timed out after {elapsed_ms}ms"
        )
        return WorkerOutput(
            worker_name=worker.name,
            success=False,
            error=f"timeout after {elapsed_ms}ms",
            latency_ms=elapsed_ms,
        )
    except Exception as err:
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        logger.warning(f"[WorkerExecutor] {worker.name} failed: {err}")
        return WorkerOutput(
            worker_name=worker.name,
            success=False,
            error=str(err),
            latency_ms=elapsed_ms,
        )


async def execute(plan: ExecutionPlan, ctx: WorkerContext) -> ExecutionResult:
    """Execute all workers in the plan according to deadline rules.

    Required workers: all fired concurrently; hard deadline cancels any still running.
    Optional workers: all fired concurrently; soft deadline cancels stragglers.
    Background workers: fire-and-forget; never block the result.
    """
    t_start = time.monotonic()

    # ── Required workers — hard deadline ────────────────────────────────────────
    required_tasks: dict[str, asyncio.Task] = {}
    for worker in plan.required:
        required_tasks[worker.name] = asyncio.create_task(_run_timed(worker, ctx))

    required_outputs: dict[str, WorkerOutput] = {}
    required_failed: list[str] = []

    if required_tasks:
        done, pending = await asyncio.wait(
            required_tasks.values(),
            timeout=plan.deadline_required_ms / 1000.0,
        )
        for name, task in required_tasks.items():
            if task in done:
                required_outputs[name] = task.result()
                if not task.result().success:
                    required_failed.append(name)
            else:
                task.cancel()
                required_failed.append(name)
                elapsed = int((time.monotonic() - t_start) * 1000)
                logger.warning(
                    f"[WorkerExecutor] Required worker '{name}' cancelled "
                    f"at hard deadline ({elapsed}ms)"
                )

    # ── Optional workers — soft deadline (remaining budget from t_start) ────────
    optional_tasks: dict[str, asyncio.Task] = {}
    for worker in plan.optional:
        optional_tasks[worker.name] = asyncio.create_task(_run_timed(worker, ctx))

    optional_outputs: dict[str, WorkerOutput] = {}

    if optional_tasks:
        elapsed_so_far = time.monotonic() - t_start
        remaining_budget = max(
            0.0,
            plan.deadline_optional_ms / 1000.0 - elapsed_so_far,
        )
        done_opt, pending_opt = await asyncio.wait(
            optional_tasks.values(),
            timeout=remaining_budget,
        )
        for name, task in optional_tasks.items():
            if task in done_opt:
                optional_outputs[name] = task.result()
            else:
                task.cancel()
                logger.debug(
                    f"[WorkerExecutor] Optional worker '{name}' skipped (soft deadline)"
                )

    # ── Background workers — fire-and-forget ────────────────────────────────────
    background_tasks: dict[str, asyncio.Task] = {}
    for worker in plan.background:
        background_tasks[worker.name] = asyncio.create_task(_run_timed(worker, ctx))

    total_ms = int((time.monotonic() - t_start) * 1000)
    logger.debug(
        f"[WorkerExecutor] profile={plan.profile_name} "
        f"required={len(required_outputs)}/{len(plan.required)} "
        f"optional={len(optional_outputs)}/{len(plan.optional)} "
        f"total_ms={total_ms}"
    )

    return ExecutionResult(
        required=required_outputs,
        required_failed=required_failed,
        optional=optional_outputs,
        background_tasks=background_tasks,
    )
