"""
Situation + mood detection — Layer 1 produces these per turn for TTS.

Per VoiceTier.SITUATION + VoiceTier.CALLER_MIRROR (Phase 1 vocab).

detect_situation() maps the current ConversationState to one of the 15
SITUATION_STYLES keys. detect_caller_mood() maps extractor signals and ASR
confidence to one of the 6 CALLER_MIRRORS keys.

Both results are written into TurnPackage.voice_situation / voice_mood and
read by tts_client.speak() to select emotion tags and speaking rates.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from server.brain.conversation_state import ConversationState


# ── Frustration multi-signal keywords ─────────────────────────────────────────
# Per mood-frustrated: keep-multi-signal (Phase 7, Task 7.8).
# Mirrors and extends _FRUSTRATION_KW in tts_conditioning.py; this is the
# canonical Layer 1 list used in count_frustration_signals().

FRUSTRATION_KEYWORDS_DE: frozenset[str] = frozenset({
    "schon wieder", "zum dritten mal", "hab ich doch gesagt",
    "ich bin enttäuscht", "das ist unmöglich",
    "lächerlich", "frechheit", "unverschämt",
    "keine lust", "reicht mir", "habe genug",
    "nicht akzeptabel", "inakzeptabel",
    "wütend", "sauer", "ärgerlich",
    "was willst du", "was wollen sie",
    "ich hab schon gesagt", "ich habe doch gesagt",
    "vorhin gesagt", "wie oft noch",
    "verstehst du nicht", "verstehen sie nicht",
})

_HAB_ICH_PATTERNS: tuple[str, ...] = (
    "hab ich gesagt", "habe ich gesagt", "hab ich doch gesagt",
    "hab ich schon", "ich hab gesagt", "ich habe gesagt",
)


def _has_caller_history(caller_phone: str) -> bool:
    """True if the caller has called before (stub — Phase 9 CRM integration)."""
    return False


# ── Situation detection ────────────────────────────────────────────────────────

def detect_situation(
    state: "ConversationState",
    layer2_intent: Optional[str] = None,
) -> str:
    """
    Map current conversation state to one of the 15 SITUATION_STYLES keys.

    Priority order (highest → lowest):
      1. Terminal: FAREWELL_WARM if call ending.
      2. Waiting: WAITING_FILLER if filler turn.
      3. Reprompt: REPROMPT_UNDERSTOOD_NONE after 2+ consecutive reprompts.
      4. Escalation: ESCALATION_REASSURING if escalation requested.
      5. Greeting: GREETING_FIRST / GREETING_RETURNING on first turn.
      6. Tool outcome: CONFIRM_SUCCESS on order/reservation success.
      7. Tool failure: APOLOGY_SOFT / APOLOGY_SERIOUS.
      8. Readback: INFO_READBACK if address/order being read back.
      9. Clarify: CLARIFY_PATIENT on low ASR confidence.
      10. Default: INFO_NEUTRAL.
    """
    call_ended = getattr(state, "call_ended", False)
    caller_said_goodbye = getattr(state, "caller_said_goodbye", False)
    if call_ended or caller_said_goodbye:
        return "FAREWELL_WARM"

    is_waiting_filler = getattr(state, "is_waiting_filler", False)
    if is_waiting_filler:
        return "WAITING_FILLER"

    consecutive_reprompts = getattr(state, "consecutive_reprompts", 0)
    if consecutive_reprompts >= 2:
        return "REPROMPT_UNDERSTOOD_NONE"

    escalation_requested = getattr(state, "escalation_requested", False)
    if escalation_requested:
        return "ESCALATION_REASSURING"

    turn_idx = getattr(state, "turn_idx", 0)
    if turn_idx == 0:
        caller_phone = getattr(state, "caller_phone", None)
        if caller_phone and _has_caller_history(caller_phone):
            return "GREETING_RETURNING"
        return "GREETING_FIRST"

    # Tool outcome from previous turn
    tool_results: dict = getattr(state, "tool_results", {}) or {}
    last_tool = getattr(state, "last_tool_fired", None)
    if last_tool and last_tool in tool_results:
        result = tool_results[last_tool]
        ok = result.get("ok", False) if isinstance(result, dict) else False
        if ok and last_tool in ("create_order", "create_reservation"):
            return "CONFIRM_SUCCESS"
        if not ok:
            # Distinguish serious failures (no alternatives, technical error)
            error = result.get("error", "") if isinstance(result, dict) else ""
            if "no_alternatives" in (error or "") or last_tool == "verify_address":
                return "APOLOGY_SERIOUS"
            return "APOLOGY_SOFT"

    readback_pending = (getattr(state, "last_extraction", None) or {}).get(
        "readback_pending", False
    )
    if readback_pending:
        return "INFO_READBACK"

    is_upsell = getattr(state, "is_upsell_turn", False)
    if is_upsell:
        return "UPSELL_CURIOUS"

    asr_confidence = getattr(state, "last_asr_confidence", 1.0) or 1.0
    if asr_confidence < 0.70:
        return "CLARIFY_PATIENT"

    return "INFO_NEUTRAL"


# ── Caller mood detection ──────────────────────────────────────────────────────

def count_frustration_signals(
    state: "ConversationState",
    asr_confidence: float,
) -> int:
    """
    Multi-signal frustration scoring per mood-frustrated: keep-multi-signal.

    Returns integer signal count (threshold for FRUSTRATED is ≥ 2):
      +N  explicit frustration keywords from extractor
      +1  if extractor counted ≥ 2 repeated content words across last 3 turns
      +N  "hab ich gesagt" (or variant) occurrences in recent_utterances

    This function is the Layer 1 version; it reads pre-computed extractor
    flags rather than doing its own keyword scan, to avoid double-parsing.
    Falls back to scanning recent_utterances if extractor flags are absent.
    """
    extraction: dict = getattr(state, "last_extraction", None) or {}
    recent: list[str] = getattr(state, "recent_utterances", []) or []

    keyword_count: int = extraction.get("frustration_keyword_count", 0)
    repeated_count: int = extraction.get("repeated_content_words", 0)
    hab_ich_extractor: int = extraction.get("hab_ich_gesagt_pattern", 0)

    # Fallback: scan recent utterances directly if extractor flags are zero
    # (e.g., extractor timed out or is not yet wired for these signals)
    if keyword_count == 0 and recent:
        recent_text = " ".join(recent[-3:]).lower()
        keyword_count = sum(
            1 for kw in FRUSTRATION_KEYWORDS_DE if kw in recent_text
        )

    if hab_ich_extractor == 0 and recent:
        hab_ich_extractor = sum(
            1 for u in recent
            if any(p in (u or "").lower() for p in _HAB_ICH_PATTERNS)
        )

    return keyword_count + (1 if repeated_count >= 2 else 0) + hab_ich_extractor


def detect_caller_mood(
    state: "ConversationState",
    asr_confidence: float,
    utterance_word_count: int = 0,
) -> str:
    """
    Per tts-moods: moods-on with multi-signal detection.

    Priority order:
      FRUSTRATED  — escalation flag OR frustration_signals ≥ 2
      CONFUSED    — confusion keywords OR asr_confidence < 0.70
      IMPATIENT   — impatience keywords
      ELDERLY     — slow speech (< 100 WPM) with ≥ 15 words
      RELAXED     — relaxed signals
      NEUTRAL     — fallback
    """
    extraction: dict = getattr(state, "last_extraction", None) or {}
    escalation_requested = getattr(state, "escalation_requested", False)

    if escalation_requested:
        return "FRUSTRATED"

    frustration_count = count_frustration_signals(state, asr_confidence)
    if frustration_count >= 2:
        return "FRUSTRATED"

    if extraction.get("frustration_signals", 0) >= 2:
        return "FRUSTRATED"

    if extraction.get("confusion_signals", 0) >= 1:
        return "CONFUSED"
    if asr_confidence < 0.70:
        return "CONFUSED"

    if extraction.get("impatience_signals", 0) >= 1:
        return "IMPATIENT"

    wpm: float = extraction.get("words_per_minute", 200)
    if wpm < 100 and utterance_word_count >= 15:
        return "ELDERLY"

    if extraction.get("relaxed_signals", 0) >= 1:
        return "RELAXED"

    return "NEUTRAL"
