"""
server/brain/speculative_executor.py — Phase 8.4: Speculative Worker Execution.

Fires Required workers speculatively on Flux EagerEndOfTurn events, before
the main LLM call. On EndOfTurn confirmation, reuses stable results.
On TurnResumed (user continued speaking), cancels all speculative tasks.

SAFETY RULE: Speculative workers MAY NEVER call commit tools
(create_order, create_reservation, send_sms). This is enforced by the
WorkerContext which does not expose commit-tool execution paths.

Usage:
    executor = SpeculativeExecutor(session_manager, worker_router)
    await executor.on_eager_eot(user_text_partial, turn_idx)
    # ... EagerEndOfTurn received ...
    result = await executor.on_end_of_turn(user_text_final, turn_idx)
    await executor.on_turn_resumed()  # if TurnResumed fires
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from server.brain.intent_classifier import classify
from server.brain.intent_session import TurnType
from server.brain.workers import ExecutionResult, Worker, WorkerContext, WorkerOutput

logger = logging.getLogger(__name__)

# Tools that speculative workers are NEVER allowed to call
_FORBIDDEN_SPECULATIVE_TOOLS = frozenset({
    "create_order", "create_reservation", "send_sms",
    "transfer_to_human", "transfer_to_tier2",
})


class SpeculativeExecutor:
    """Manages speculative worker execution on Flux EagerEndOfTurn events."""

    def __init__(self, worker_router=None) -> None:
        self._worker_router = worker_router
        self._speculative_tasks: dict[str, asyncio.Task] = {}
        self._cancel_tokens: dict[str, asyncio.Event] = {}
        self._partial_text: str = ""
        self._speculative_profile: Optional[str] = None
        self._results: dict[str, WorkerOutput] = {}
        self._t_start: Optional[float] = None

    async def on_eager_eot(
        self,
        partial_text: str,
        turn_idx: int,
        call_sid: str = "",
        tenant_id: str = "",
    ) -> None:
        """Called when Flux emits EagerEndOfTurn."""
        self._partial_text = partial_text
        self._t_start = time.monotonic()

        # Classify intent on the partial
        result = classify(partial_text, turn_idx=turn_idx)
        self._speculative_profile = result.worker_profile

        if self._worker_router is None:
            return

        # Get the plan for this profile
        try:
            from server.brain.worker_router import route
            plan = route(self._speculative_profile, result.turn_type)
        except Exception:
            return

        # Only start workers with high estimated latency
        ctx = WorkerContext(
            user_text=partial_text,
            turn_idx=turn_idx,
            call_sid=call_sid,
            tenant_id=tenant_id,
        )

        for worker in plan.required:
            if worker.estimated_latency_ms > 150 and worker.name not in self._speculative_tasks:
                token = asyncio.Event()
                self._cancel_tokens[worker.name] = token
                self._speculative_tasks[worker.name] = asyncio.create_task(
                    worker.run_with_cancel(ctx, token)
                )
                logger.debug(
                    f"[SpeculativeExecutor] started {worker.name} speculatively "
                    f"(estimated={worker.estimated_latency_ms}ms)"
                )

    async def on_end_of_turn(
        self,
        final_text: str,
        turn_idx: int,
        final_profile: Optional[str] = None,
    ) -> dict[str, WorkerOutput]:
        """Called when Flux emits final EndOfTurn.

        Returns dict of reusable worker outputs (empty if profile changed).
        """
        reusable: dict[str, WorkerOutput] = {}

        # If profile matches and text is similar enough, reuse results
        profiles_match = (final_profile == self._speculative_profile)
        text_stable = (
            self._partial_text and final_text and
            final_text.startswith(self._partial_text[:max(10, len(self._partial_text) - 5)])
        )

        if profiles_match and text_stable:
            # Await remaining tasks with short timeout
            remaining = {
                name: task
                for name, task in self._speculative_tasks.items()
                if not task.done()
            }
            if remaining:
                done, pending = await asyncio.wait(
                    remaining.values(), timeout=0.05  # 50ms to collect results
                )
                for t in pending:
                    t.cancel()

            # Collect completed results
            for name, task in self._speculative_tasks.items():
                if task.done() and not task.cancelled():
                    try:
                        result = task.result()
                        if result.success:
                            reusable[name] = result
                            logger.debug(
                                f"[SpeculativeExecutor] reusing {name} result "
                                f"(latency={result.latency_ms}ms)"
                            )
                    except Exception:
                        pass
        else:
            # Profile changed or text diverged — cancel all speculative tasks
            logger.debug(
                f"[SpeculativeExecutor] discarding speculative results "
                f"(profiles_match={profiles_match}, text_stable={text_stable})"
            )
            await self._cancel_all()

        self._results = reusable
        self._cleanup()
        return reusable

    async def on_turn_resumed(self) -> None:
        """Called when Flux emits TurnResumed (user continued speaking)."""
        logger.debug("[SpeculativeExecutor] TurnResumed — cancelling all speculative tasks")
        await self._cancel_all()
        self._cleanup()

    async def _cancel_all(self) -> None:
        for name, token in self._cancel_tokens.items():
            token.set()
        await asyncio.sleep(0.01)  # let cancellations propagate
        for task in self._speculative_tasks.values():
            if not task.done():
                task.cancel()

    def _cleanup(self) -> None:
        self._speculative_tasks = {}
        self._cancel_tokens = {}
        self._partial_text = ""
        self._speculative_profile = None
        self._t_start = None

    def consume_results(self) -> dict[str, WorkerOutput]:
        """Return reusable speculative outputs once, then clear them."""
        results = dict(self._results)
        self._results = {}
        return results
