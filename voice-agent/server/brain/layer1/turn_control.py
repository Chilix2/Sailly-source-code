"""
layer1/turn_control.py — Adaptive turn control and safety nets.

Public API (in wiring order per plan):
  turn_cap_for_state(state)       → int  (15 single / 30 multi active intents)
  is_over_turn_cap(state, idx)    → bool
  force_end_for_turn_cap(state)   → str  (German response text)
  is_stuck_loop(state)            → bool (Jaccard 0.8 across last 3 bot responses)
  is_no_progress(state, idx)      → bool (8 turns, no new slot fills via source_turn)
  handle_abuse(state, extraction) → Optional[str]  (German warn/end text, or None)
  handle_out_of_scope(extraction) → Optional[str]  (German redirect text, or None)
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Optional, Set

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from server.brain.conversation_state import ConversationState

# ── Constants ──────────────────────────────────────────────────────────────────
# Dev mode: all caps are effectively disabled (set high so they never fire).
TURN_CAP_SINGLE = 999
TURN_CAP_MULTI  = 999

NO_PROGRESS_TURNS = 999  # disabled in dev mode

JACCARD_THRESHOLD  = 0.8   # similarity above this → stuck loop
STUCK_LOOP_WINDOW  = 3     # compare last N bot responses


# ── D1: Turn cap ──────────────────────────────────────────────────────────────

def turn_cap_for_state(state: "ConversationState") -> int:
    """Return the adaptive turn cap: 30 for multi-intent, 15 for single."""
    ci = getattr(state, "captured_intents", []) or []
    try:
        from server.brain.captured_intents import IntentStatus
        active_count = sum(
            1 for c in ci
            if c.status not in (IntentStatus.COMPLETED, IntentStatus.FAILED)
        )
    except ImportError:
        active_count = len(ci)
    return TURN_CAP_MULTI if active_count >= 2 else TURN_CAP_SINGLE


def is_over_turn_cap(state: "ConversationState", turn_idx: int) -> bool:
    """Return True when turn_idx has exceeded the adaptive cap."""
    return turn_idx >= turn_cap_for_state(state)


def force_end_for_turn_cap(state: "ConversationState") -> str:
    """
    German farewell text to use when turn cap is hit.
    Attempts to include a summary of what was accomplished.
    """
    try:
        from server.brain.layer1.intent_advance import end_of_call_summary_text
        summary = end_of_call_summary_text(state)
    except Exception:
        summary = "Vielen Dank für Ihren Anruf — auf Wiedersehen!"
    return (
        "Leider haben wir das Gesprächslimit für diesen Anruf erreicht. "
        + summary
    )


# ── D2: Stuck-loop Jaccard detector ───────────────────────────────────────────

def _jaccard_words(a: str, b: str) -> float:
    """
    Jaccard similarity between two strings, computed on word sets.
    Returns 0.0 for empty strings.
    """
    if not a or not b:
        return 0.0
    words_a: Set[str] = set(re.findall(r"\w+", a.lower()))
    words_b: Set[str] = set(re.findall(r"\w+", b.lower()))
    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def is_stuck_loop(state: "ConversationState") -> bool:
    """
    Return True when the last STUCK_LOOP_WINDOW bot responses are all
    pairwise similar (Jaccard ≥ JACCARD_THRESHOLD).

    Replaces the old exact-match `_is_stuck_loop` in adk_turn_processor.py.
    """
    recent = getattr(state, "recent_responses", []) or []
    window = [r for r in recent if r and r.strip()][-STUCK_LOOP_WINDOW:]
    if len(window) < STUCK_LOOP_WINDOW:
        return False

    for i in range(len(window)):
        for j in range(i + 1, len(window)):
            if _jaccard_words(window[i], window[j]) < JACCARD_THRESHOLD:
                return False
    return True


# ── D3: No-progress detector ──────────────────────────────────────────────────

def is_no_progress(state: "ConversationState", turn_idx: int) -> bool:
    """
    Return True when no slot has been filled in the last NO_PROGRESS_TURNS turns.

    Uses `source_turn` on SlotValue objects from captured_intents + shared_slots.
    Also checks legacy order_slots_ref if present.
    """
    if turn_idx < NO_PROGRESS_TURNS:
        return False

    cutoff = turn_idx - NO_PROGRESS_TURNS

    # Phase 2+ path: check CapturedIntent slots
    ci = getattr(state, "captured_intents", []) or []
    for intent in ci:
        for sv in (intent.slots or {}).values():
            source_turn = getattr(sv, "source_turn", None)
            if source_turn is not None and source_turn >= cutoff:
                return False

    # Also check shared_slots
    for sv in (getattr(state, "shared_slots", {}) or {}).values():
        source_turn = getattr(sv, "source_turn", None)
        if source_turn is not None and source_turn >= cutoff:
            return False

    # Legacy OrderSlots path: check slot timestamps
    slots = getattr(state, "order_slots_ref", None)
    if slots is not None:
        try:
            for slot in vars(slots).values():
                if hasattr(slot, "source_turn") and slot.source_turn is not None:
                    if slot.source_turn >= cutoff:
                        return False
        except Exception:
            pass

    return True


# ── D4: Abuse handler ─────────────────────────────────────────────────────────

def handle_abuse(state: "ConversationState", extraction: dict) -> Optional[str]:
    """
    Handle abuse detected by the slot extractor.

    - First strike: de-escalation + warning → returns a German de-escalation phrase.
    - Second strike: `state.call_ended = True` → returns the farewell handoff phrase.
    - Returns None if no abuse detected.

    Reads: extraction["abuse_detected"]
    Mutates: state.abuse_strikes, state.call_ended
    """
    if not extraction.get("abuse_detected"):
        return None

    strikes = getattr(state, "abuse_strikes", 0)
    strikes += 1
    state.abuse_strikes = strikes

    if strikes == 1:
        logger.warning("[turn_control] abuse detected — strike 1, de-escalating")
        return (
            "Ich verstehe, dass Sie gerade frustriert sind — lassen Sie uns das gemeinsam lösen. "
            "Wie kann ich Ihnen weiterhelfen?"
        )
    else:
        logger.warning("[turn_control] abuse detected — strike %d, ending call", strikes)
        state.call_ended = True
        return (
            "Da unser Gespräch leider nicht produktiv weitergeführt werden kann, "
            "beende ich diesen Anruf jetzt. Auf Wiederhören."
        )


def handle_out_of_scope(extraction: dict) -> Optional[str]:
    """
    Handle out-of-scope utterances.

    Returns a German redirect phrase if `extraction["out_of_scope"]` is True,
    otherwise returns None.  Does NOT mutate state — purely a response hint.
    """
    if not extraction.get("out_of_scope"):
        return None

    return (
        "Da bin ich leider nicht die Richtige — "
        "aber beim Essen oder Reservieren helfe ich Ihnen gerne!"
    )
