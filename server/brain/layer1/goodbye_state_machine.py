"""
End-of-call state machine.

Sequences the steps that must happen at the end of every call in the correct
order.  Writing to ConversationState is only done through advance() — the
rest of the codebase must not mutate end_call_stage directly.

States and transitions:
    IDLE → READY_FOR_SMS | READY_FOR_FAREWELL
    READY_FOR_SMS → SMS_SENT | READY_FOR_FAREWELL (skip SMS on failure)
    SMS_SENT → READY_FOR_FAREWELL
    READY_FOR_FAREWELL → FAREWELL_SPOKEN
    FAREWELL_SPOKEN → CALL_ENDED
    CALL_ENDED → (terminal — no further transitions)

Public API:
    advance(state, new_stage, reason)         — the only writer
    should_advance(state)                     → Optional[EndCallStage]
    InvalidEndCallTransition                  — raised on illegal moves
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from server.brain.conversation_state import ConversationState

logger = logging.getLogger(__name__)


class EndCallStage(str, Enum):
    IDLE = "idle"
    READY_FOR_SMS = "ready_for_sms"
    SMS_SENT = "sms_sent"
    READY_FOR_FAREWELL = "ready_for_farewell"
    FAREWELL_SPOKEN = "farewell_spoken"
    CALL_ENDED = "call_ended"


# Legal transitions: from_stage → set of allowed to_stages
_ALLOWED_TRANSITIONS: dict = {
    EndCallStage.IDLE: {
        EndCallStage.READY_FOR_SMS,
        EndCallStage.READY_FOR_FAREWELL,
    },
    EndCallStage.READY_FOR_SMS: {
        EndCallStage.SMS_SENT,
        EndCallStage.READY_FOR_FAREWELL,  # skip SMS on failure
    },
    EndCallStage.SMS_SENT: {
        EndCallStage.READY_FOR_FAREWELL,
    },
    EndCallStage.READY_FOR_FAREWELL: {
        EndCallStage.FAREWELL_SPOKEN,
    },
    EndCallStage.FAREWELL_SPOKEN: {
        EndCallStage.CALL_ENDED,
    },
    EndCallStage.CALL_ENDED: set(),  # terminal
}


class InvalidEndCallTransition(ValueError):
    """Raised when an illegal state machine transition is attempted."""


def advance(
    state: "ConversationState",
    new_stage: EndCallStage,
    reason: str = "",
) -> None:
    """
    Move the end-of-call state machine to new_stage.

    Raises InvalidEndCallTransition if the move is not permitted.
    Writes end_call_stage (and sets call_ended / farewell_spoken mirrors).
    """
    current_str = getattr(state, "end_call_stage", EndCallStage.IDLE.value)
    try:
        current = EndCallStage(current_str)
    except ValueError:
        current = EndCallStage.IDLE

    allowed = _ALLOWED_TRANSITIONS.get(current, set())
    if new_stage not in allowed:
        raise InvalidEndCallTransition(
            f"Cannot transition end_call_stage from {current!r} to {new_stage!r}"
            + (f" (reason: {reason})" if reason else "")
        )

    state.end_call_stage = new_stage.value
    logger.debug(
        "EndCallStage %s → %s%s",
        current.value,
        new_stage.value,
        f" [{reason}]" if reason else "",
    )

    # Keep boolean mirror fields in sync for backward-compat read paths
    if new_stage == EndCallStage.FAREWELL_SPOKEN:
        state.farewell_spoken = True
    elif new_stage == EndCallStage.CALL_ENDED:
        state.call_ended = True
        # Phase 9 A2 — derive and persist disposition label
        try:
            from server.brain.observability.disposition import compute_disposition
            state.disposition = compute_disposition(state)  # type: ignore[attr-defined]
            logger.info(
                "call_disposition_set",
                extra={"call_sid": getattr(state, "call_sid", ""), "disposition": state.disposition},
            )
        except Exception as _disp_err:
            logger.warning(f"[disposition] compute failed: {_disp_err}")


def should_advance(state: "ConversationState") -> Optional[EndCallStage]:
    """
    Read-only check: return the next EndCallStage if conditions are met,
    or None if the state machine should not move this turn.

    Called at the end of each turn by adk_turn_processor.
    """
    current_str = getattr(state, "end_call_stage", EndCallStage.IDLE.value)
    try:
        current = EndCallStage(current_str)
    except ValueError:
        current = EndCallStage.IDLE

    if current == EndCallStage.CALL_ENDED:
        return None  # already terminal

    if current == EndCallStage.IDLE:
        if _all_intents_terminal(state) or getattr(state, "caller_said_goodbye", False):
            # Decide whether to send an SMS first
            pending_sms = _has_pending_sms(state)
            if pending_sms:
                return EndCallStage.READY_FOR_SMS
            return EndCallStage.READY_FOR_FAREWELL

    if current == EndCallStage.READY_FOR_SMS:
        # SMS either sent or explicitly skipped
        if _sms_dispatched(state):
            return EndCallStage.SMS_SENT
        # SMS send failed / timed out → skip ahead
        if getattr(state, "sms_failed", False):
            return EndCallStage.READY_FOR_FAREWELL

    if current == EndCallStage.SMS_SENT:
        return EndCallStage.READY_FOR_FAREWELL

    if current == EndCallStage.READY_FOR_FAREWELL:
        if getattr(state, "farewell_spoken", False):
            return EndCallStage.FAREWELL_SPOKEN

    if current == EndCallStage.FAREWELL_SPOKEN:
        return EndCallStage.CALL_ENDED

    return None


# ── Private helpers ────────────────────────────────────────────────────────────

def _all_intents_terminal(state: "ConversationState") -> bool:
    """Return True when every CapturedIntent is in a terminal status."""
    ci = getattr(state, "captured_intents", None) or []
    if not ci:
        return False

    try:
        from server.brain.captured_intents import IntentStatus
        terminal = {IntentStatus.COMPLETED, IntentStatus.CANCELLED, IntentStatus.FAILED}
    except ImportError:
        return False

    return all(getattr(intent, "status", None) in terminal for intent in ci)


def _has_pending_sms(state: "ConversationState") -> bool:
    """Return True when a completed order or reservation exists that needs an SMS."""
    return bool(
        getattr(state, "order_created", False)
        and not getattr(state, "sms_sent", False)
    )


def _sms_dispatched(state: "ConversationState") -> bool:
    """Return True when the SMS has been sent for this call."""
    return bool(getattr(state, "sms_sent", False))
