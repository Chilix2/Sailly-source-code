"""
server/brain/workers/ — Worker contract + Required/Optional/Background trichotomy (Phase 4.1).

A Worker is a typed, async callable that:
    - Takes a WorkerContext (user_text + state snapshots)
    - Returns a WorkerOutput (schema-typed dict + confidence)
    - Has a declared kind (Required / Optional / Background)
    - Has a declared estimated_latency_ms for speculative pre-warming decisions
    - Implements run_with_cancel for speculative execution (cancelable)

Required workers: generator will NOT run until all complete OR deadline (280ms) hits.
Optional workers: generator may run without them if they miss deadline (350ms).
Background workers: generator never waits; they update state for the NEXT turn.

Safety rule: no worker may call commit tools (create_order, create_reservation, send_sms).
This is enforced at the WorkerContext level — commit tools are not available in worker scope.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Worker kind ─────────────────────────────────────────────────────────────────

class WorkerKind(str, Enum):
    REQUIRED   = "required"
    OPTIONAL   = "optional"
    BACKGROUND = "background"


# ── Worker I/O ──────────────────────────────────────────────────────────────────

@dataclass
class WorkerContext:
    """Input to every worker. Intentionally narrow — no commit-tool access."""
    user_text: str
    turn_idx: int
    call_sid: str
    tenant_id: str
    # Snapshot of relevant state fields (read-only from worker perspective)
    party_size: Optional[int] = None
    reservation_date: Optional[str] = None
    reservation_time: Optional[str] = None
    customer_name: Optional[str] = None
    phone_number: Optional[str] = None
    selected_items: list = field(default_factory=list)
    recent_bot_texts: list[str] = field(default_factory=list)
    # Extra: arbitrary state snapshot for advanced workers
    extra: dict = field(default_factory=dict)


@dataclass
class WorkerOutput:
    """Output from every worker."""
    worker_name: str
    success: bool
    data: dict = field(default_factory=dict)       # structured output
    confidence: float = 1.0                         # 0.0–1.0
    latency_ms: Optional[int] = None
    error: Optional[str] = None


# ── Worker base class ───────────────────────────────────────────────────────────

class Worker:
    """Base class for all workers. Subclass and override run()."""

    name: str = "base_worker"
    kind: WorkerKind = WorkerKind.OPTIONAL
    estimated_latency_ms: int = 50
    timeout_ms: int = 350

    async def run(self, ctx: WorkerContext) -> WorkerOutput:
        raise NotImplementedError

    async def run_with_cancel(
        self,
        ctx: WorkerContext,
        cancel_token: asyncio.Event,
    ) -> WorkerOutput:
        """Run with cancellation support for speculative execution."""
        task = asyncio.create_task(self.run(ctx))
        cancel_task = asyncio.create_task(cancel_token.wait())
        done, pending = await asyncio.wait(
            [task, cancel_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
        if cancel_task in done:
            # Cancelled
            return WorkerOutput(
                worker_name=self.name,
                success=False,
                error="cancelled",
            )
        return task.result()


# ── Execution plan ──────────────────────────────────────────────────────────────

@dataclass
class ExecutionPlan:
    """Output of WorkerRouter: what to run this turn."""
    profile_name: str
    required: list[Worker] = field(default_factory=list)
    optional: list[Worker] = field(default_factory=list)
    background: list[Worker] = field(default_factory=list)
    scheduled_tools: list[str] = field(default_factory=list)  # info tools to call
    deadline_required_ms: int = 280
    deadline_optional_ms: int = 350


# ── Execution result ────────────────────────────────────────────────────────────

@dataclass
class ExecutionResult:
    """Output of WorkerExecutor.execute()."""
    required: dict[str, WorkerOutput] = field(default_factory=dict)
    required_failed: list[str] = field(default_factory=list)
    optional: dict[str, WorkerOutput] = field(default_factory=dict)
    background_tasks: dict[str, asyncio.Task] = field(default_factory=dict)

    @property
    def all_required_succeeded(self) -> bool:
        return len(self.required_failed) == 0

    @property
    def p50_latency_ms(self) -> Optional[int]:
        latencies = [
            o.latency_ms for o in list(self.required.values()) + list(self.optional.values())
            if o.latency_ms is not None
        ]
        if not latencies:
            return None
        latencies.sort()
        return latencies[len(latencies) // 2]

    @property
    def p95_latency_ms(self) -> Optional[int]:
        latencies = [
            o.latency_ms for o in list(self.required.values()) + list(self.optional.values())
            if o.latency_ms is not None
        ]
        if not latencies:
            return None
        latencies.sort()
        idx = int(len(latencies) * 0.95)
        return latencies[min(idx, len(latencies) - 1)]
