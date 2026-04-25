"""
layer1/intent_advance.py — Multi-intent flow: post-tool advance + promotion.

Public API:
  advance_after_tool(state, tool_name)  → str  (action taken)
  end_of_call_summary_text(state)       → str  (German summary for TTS farewell)
  detect_promotion_to_multi(state)      → bool (True if single→multi transition needed)
  promote_to_multi_intent_flow(state)   → None (wire in, updates state in place)
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from server.brain.conversation_state import ConversationState

# ── Tools that signal an intent is done ───────────────────────────────────────
_COMPLETING_TOOLS = frozenset({
    "create_order",
    "create_reservation",
    "capture_catering_lead",
    "confirm_order",
    "cancel_order",
    "transfer_to_human",
})

# ── Tools that signal an intent failed ────────────────────────────────────────
_FAILING_TOOLS = frozenset({
    "transfer_to_human",
})


def advance_after_tool(state: "ConversationState", tool_name: str) -> str:
    """
    Called after a tool fires. Advances the multi-intent queue if the current
    intent is now terminal (completed or failed), and records failed intents.

    Returns a string describing the action taken.
    """
    if tool_name not in _COMPLETING_TOOLS:
        return "no_advance_needed"

    ci = getattr(state, "captured_intents", []) or []
    idx = getattr(state, "current_intent_idx", None)
    if not ci or idx is None or idx >= len(ci):
        return "no_active_intent"

    try:
        from server.brain.captured_intents import IntentStatus, transition_intent
    except ImportError:
        return "import_error"

    current = ci[idx]

    if tool_name in _FAILING_TOOLS:
        # Mark as FAILED, record summary
        try:
            transition_intent(current, IntentStatus.FAILED)
        except Exception:
            current.status = IntentStatus.FAILED
        _record_failed(state, current)
        action = "mark_failed"
    else:
        # Mark as COMPLETED
        try:
            transition_intent(current, IntentStatus.COMPLETED)
        except Exception:
            current.status = IntentStatus.COMPLETED
        action = "mark_completed"

    # Advance to the next pending intent
    next_idx = _find_next_pending(ci, idx)
    if next_idx is not None:
        state.current_intent_idx = next_idx
        logger.info(
            "[intent_advance] advanced to intent %d/%d after %s",
            next_idx + 1, len(ci), tool_name,
        )
        return f"{action}→advance_to_{next_idx}"

    # All intents handled
    logger.info("[intent_advance] all %d intents terminal after %s", len(ci), tool_name)
    return f"{action}→all_done"


def _find_next_pending(ci: list, current_idx: int) -> Optional[int]:
    """Return the index of the next non-terminal intent after current_idx."""
    try:
        from server.brain.captured_intents import IntentStatus
        terminal = {IntentStatus.COMPLETED, IntentStatus.FAILED}
    except ImportError:
        return None

    for i in range(current_idx + 1, len(ci)):
        if ci[i].status not in terminal:
            return i
    return None


def _record_failed(state: "ConversationState", intent) -> None:
    """Append a German summary of the failed intent to state.failed_intent_summaries."""
    try:
        label = getattr(intent, "label_de", str(getattr(intent, "kind", "?")))
        summaries = getattr(state, "failed_intent_summaries", None)
        if summaries is None:
            state.failed_intent_summaries = []
        state.failed_intent_summaries.append(
            f"{label} konnte nicht abgeschlossen werden."
        )
    except Exception as exc:
        logger.debug("[intent_advance] _record_failed error: %s", exc)


def end_of_call_summary_text(state: "ConversationState") -> str:
    """
    Produce a compact German farewell / summary sentence for TTS.

    Includes:
    - Completed intents (what was achieved)
    - Failed intents (what was not achieved + apology)
    """
    ci = getattr(state, "captured_intents", []) or []
    failed_summaries = getattr(state, "failed_intent_summaries", []) or []

    try:
        from server.brain.captured_intents import IntentStatus
        completed = [
            getattr(c, "label_de", str(getattr(c, "kind", "?")))
            for c in ci
            if c.status == IntentStatus.COMPLETED
        ]
    except ImportError:
        completed = []

    parts = []
    if completed:
        parts.append(
            "Wir haben folgendes erledigt: " + ", ".join(completed) + "."
        )
    if failed_summaries:
        parts.append(
            "Leider konnte Folgendes nicht abgeschlossen werden: "
            + " ".join(failed_summaries)
        )
    if parts:
        return " ".join(parts) + " Vielen Dank und auf Wiedersehen!"
    return "Vielen Dank für Ihren Anruf — auf Wiedersehen!"


# ── Single→multi promotion (Phase 4 C3) ──────────────────────────────────────

def detect_promotion_to_multi(state: "ConversationState") -> bool:
    """
    Return True when the extractor has appended a second intent to captured_intents
    while we were already processing the first one (single→multi transition).

    Condition: captured_intents has >1 entry AND current_intent_idx == 0 AND
    the new intents are in CAPTURED status (not yet confirmed).
    """
    ci = getattr(state, "captured_intents", []) or []
    idx = getattr(state, "current_intent_idx", None)
    if len(ci) <= 1 or idx is None:
        return False

    try:
        from server.brain.captured_intents import IntentStatus
        new_captured = [
            c for i, c in enumerate(ci)
            if i > 0 and c.status == IntentStatus.CAPTURED
        ]
        return len(new_captured) > 0
    except ImportError:
        return False


def promote_to_multi_intent_flow(state: "ConversationState") -> None:
    """
    Promote from single-intent to multi-intent flow.

    Actions:
    - Reset current_intent_idx to 0 (restart from confirmation gate)
    - All new intents remain CAPTURED (confirmation node will read them back)
    """
    state.current_intent_idx = 0
    logger.info(
        "[intent_advance] promoted to multi-intent flow: %d intents",
        len(getattr(state, "captured_intents", [])),
    )
