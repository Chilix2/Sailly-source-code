"""
Per-call disposition labeling per decision rule-based (9.O5).

Derives a human-readable disposition string from the intent FSM terminal
states at call end.  Written to `google_calls.disposition` when the goodbye
state machine reaches CALL_ENDED.

Disposition values (exhaustive):
    resolved                      — all intents completed
    partially_resolved            — at least one completed + at least one failed
    transferred_to_human          — transfer tool succeeded
    transfer_failed_callback      — transfer tool fired but failed; callback queued
    cancelled_by_caller           — caller explicitly cancelled at least one intent
    abandoned                     — call ended with no completed intent
    no_intent                     — no intent was ever captured (e.g. silent hang-up)
    unknown                       — fallback

Called from goodbye_state_machine.advance() when new_stage == CALL_ENDED.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from server.brain.conversation_state import ConversationState


def compute_disposition(state: "ConversationState") -> str:
    """Return a disposition label for the call represented by `state`."""
    from server.brain.captured_intents import IntentStatus

    intents = getattr(state, "captured_intents", [])
    if not intents:
        return "no_intent"

    statuses = [getattr(i, "status", None) for i in intents]

    # All intents resolved — fully successful call
    if all(s == IntentStatus.COMPLETED for s in statuses):
        return "resolved"

    # Mix of completed + failed — partial success
    has_completed = any(s == IntentStatus.COMPLETED for s in statuses)
    has_failed = any(s == IntentStatus.FAILED for s in statuses)
    if has_completed and has_failed:
        return "partially_resolved"

    # Caller rescinded at least one intent
    if any(s == IntentStatus.CANCELLED for s in statuses):
        return "cancelled_by_caller"

    # Transfer path — check tool_results dict for outcome
    tool_results = getattr(state, "tool_results", {}) or {}
    transfer_result = tool_results.get("transfer_to_human")
    if transfer_result:
        if transfer_result.get("ok"):
            return "transferred_to_human"
        return "transfer_failed_callback"

    # Call ended with no useful outcome
    call_ended = getattr(state, "call_ended", False)
    if call_ended and not has_completed:
        return "abandoned"

    return "unknown"
