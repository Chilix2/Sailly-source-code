"""
Turn runner — scaffolding for per-call ValidationRegistry instantiation
and per-stage timing (Phase 9 A1).

Phase 5.5: This module provides the `get_or_create_registry` helper that
returns the per-call ValidationRegistry for a given ConversationState, and
the `_make_trace_writer` factory used by Task A4 to wire per-validator events
into the LayerTrace.

Phase 9 A1: Adds `get_or_create_timings` which returns the singleton
TurnTimings accumulator for the current turn.  Each stage records its
completion timestamp via `timings.<stage>_done_at = time.monotonic()`.

The actual call flow wiring lives in adk_turn_processor.py; this file
provides the canonical, importable functions so future components (Phase 6
tool gating, Phase 9 observability) can reference them without circular imports.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Callable, Optional

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from server.brain.conversation_state import ConversationState
    from server.brain.contracts.trace import LayerTrace
    from server.brain.layer1.validation.registry import ValidationRegistry


def get_or_create_registry(
    state: "ConversationState",
    tenant_cfg: Optional[dict] = None,
) -> "ValidationRegistry":
    """
    Return the per-call ValidationRegistry for this state, creating it if missing.

    Per per-call-cache decision: one registry instance per call. The registry is
    stored as a transient attribute `_validation_registry` on state (not serialized).
    Validators are re-registered on every creation (idempotent).

    Args:
        state:       Live ConversationState for the current call.
        tenant_cfg:  Tenant configuration dict for the ValidationContext.

    Returns:
        The ValidationRegistry instance, ready for use.
    """
    from server.brain.layer1.validation.registry import ValidationContext, ValidationRegistry
    from server.brain.layer1.validation.validators import register_default_validators

    existing: Optional[ValidationRegistry] = getattr(state, "_validation_registry", None)
    if existing is not None:
        return existing

    ctx = ValidationContext(
        tenant_id=getattr(state, "tenant_id", "") or "",
        call_sid=getattr(state, "call_sid", "") or "",
        turn_idx=getattr(state, "turn_idx", 0) or 0,
        tenant_cfg=tenant_cfg or {},
    )
    registry = ValidationRegistry(ctx)
    register_default_validators(registry)

    # Reconnect path: prior entries from persisted state are intentionally
    # not restored per per-call-cache decision — reconnect re-validates.
    # (The validation_entries dict on state is kept for audit trail only.)

    state._validation_registry = registry  # type: ignore[attr-defined]
    logger.debug(
        "validation_registry_created",
        extra={"call_sid": ctx.call_sid, "tenant_id": ctx.tenant_id},
    )
    return registry


def _make_trace_writer(layer_trace: "LayerTrace") -> Callable[[dict], None]:
    """
    Return a trace-writer callback that appends validator events to layer_trace.

    Passed to `registry.attach_trace_writer()` at the start of each turn so
    per-validator timing tiles populate `layer1_decision.validators_run`.
    """
    def write(event: dict) -> None:
        event_name = event.get("event", "")
        if event_name == "validator_completed":
            layer_trace.validators_run.append({
                "slot": event["slot"],
                "status": event["status"],
                "duration_ms": event["duration_ms"],
                "retry": event.get("retry", 0),
            })
        elif event_name == "validator_error":
            layer_trace.validators_run.append({
                "slot": event["slot"],
                "status": "error",
                "duration_ms": event["duration_ms"],
                "error": event.get("error", "")[:80],
            })

    return write


def get_or_create_timings(state: "ConversationState") -> "TurnTimings":
    """
    Return the per-turn TurnTimings accumulator for this state.

    A fresh TurnTimings is created at the start of each turn by
    adk_turn_processor before the first downstream call.  Each stage then
    records its completion time:

        timings = get_or_create_timings(state)
        ...
        timings.stt_done_at = time.monotonic()
        ...
        timings.extract_done_at = time.monotonic()

    The accumulator is intentionally *not* persisted to Redis — it only
    lives for the duration of one turn.  persist.py reads it via
    `state._turn_timings` when writing the google_turn_metrics row.
    """
    from server.brain.contracts.turn_timings import TurnTimings

    existing: Optional[TurnTimings] = getattr(state, "_turn_timings", None)
    if existing is not None:
        return existing

    timings = TurnTimings()
    state._turn_timings = timings  # type: ignore[attr-defined]
    return timings


def reset_timings(state: "ConversationState") -> "TurnTimings":
    """
    Discard the previous turn's TurnTimings and start a fresh one.

    Call this at the very beginning of each new turn so the clock starts
    from the moment the user utterance arrives, not from any previous turn.
    """
    from server.brain.contracts.turn_timings import TurnTimings

    timings = TurnTimings()
    state._turn_timings = timings  # type: ignore[attr-defined]
    return timings
