"""
server/brain/stt/flux_adapter.py
----------------------------------
Flux EOT adapter — converts Deepgram ``SpeechFinalEvent`` / utterance-end metadata
into a structured turn-boundary decision that the VAD coordinator in main.py
can act on without understanding Deepgram's internals.

Key concepts:
- EOT confidence (``speech_final``) indicates how certain Deepgram is that the
  caller has finished speaking.  High confidence (≥ eot_threshold) → trigger
  immediately.  Low confidence → extend the stop timer by ``extend_stop_ms``.
- Disfluency endings ("äh", "und", "oder") signal the caller may still be
  mid-sentence → extend the stop timer to prevent premature cut-offs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# German disfluency tokens that suggest the caller hasn't finished speaking.
DISFLUENCY_ENDINGS: frozenset = frozenset({
    "äh", "ähm", "ehm", "und", "oder", "aber", "also", "nämlich",
    "beziehungsweise", "bzw", "d.h", "dh", "also", "quasi", "sozusagen",
})

# Default thresholds — can be overridden via tenant config audio.eot_threshold
DEFAULT_EOT_THRESHOLD: float = 0.7
DEFAULT_EAGER_EOT_THRESHOLD: float = 0.5
DEFAULT_DISFLUENCY_EXTEND_MS: int = 400  # extend stop timer by this many ms


@dataclass
class FluxTurnDecision:
    """Result of ``decide_turn_boundary()``.

    Attributes:
        is_end_of_turn: True → commit turn immediately (high-confidence EOT).
        extend_stop_ms: If > 0, dynamically extend the VAD stop timer by this many ms.
        confidence: Raw EOT confidence score from Deepgram (0.0–1.0), or None.
        reason: Human-readable explanation for the decision (for logging).
    """

    is_end_of_turn: bool = False
    extend_stop_ms: int = 0
    confidence: Optional[float] = None
    reason: str = "default"


def decide_turn_boundary(
    turninfo_event: Any,
    *,
    eot_threshold: float = DEFAULT_EOT_THRESHOLD,
    eager_eot_threshold: float = DEFAULT_EAGER_EOT_THRESHOLD,
    disfluency_extend_ms: int = DEFAULT_DISFLUENCY_EXTEND_MS,
) -> FluxTurnDecision:
    """Decide whether to commit a turn or extend the stop timer.

    Args:
        turninfo_event: A Deepgram ``SpeechFinalEvent`` or any dict/object that
            may carry ``speech_final`` (bool) and ``confidence`` (float).
            Also accepts raw Deepgram transcript result dicts.
        eot_threshold: Confidence above which we commit immediately.
        eager_eot_threshold: Confidence above which we signal early EOT for
            LLM pre-processing (not yet used in main.py but exposed for future).
        disfluency_extend_ms: How many ms to extend the stop timer when a
            disfluency is detected.

    Returns:
        FluxTurnDecision describing what the VAD coordinator should do.
    """
    confidence: Optional[float] = None
    transcript_text: str = ""

    # Accept both dict-style and attribute-style events
    if isinstance(turninfo_event, dict):
        confidence = turninfo_event.get("confidence") or turninfo_event.get("speech_confidence")
        transcript_text = turninfo_event.get("transcript", "") or ""
    else:
        confidence = getattr(turninfo_event, "confidence", None)
        if confidence is None:
            confidence = getattr(turninfo_event, "speech_confidence", None)
        transcript_text = getattr(turninfo_event, "transcript", "") or ""

    try:
        confidence = float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        confidence = None

    # Check for disfluency in the final word of transcript
    _trailing_word = (transcript_text.strip().split() or [""])[-1].lower().rstrip(".,!?")
    _is_disfluency = _trailing_word in DISFLUENCY_ENDINGS

    # If we can't read confidence, fall through to normal VAD behaviour
    if confidence is None:
        if _is_disfluency:
            return FluxTurnDecision(
                is_end_of_turn=False,
                extend_stop_ms=disfluency_extend_ms,
                confidence=None,
                reason=f"disfluency_no_conf:'{_trailing_word}'",
            )
        return FluxTurnDecision(
            is_end_of_turn=False,
            extend_stop_ms=0,
            confidence=None,
            reason="no_confidence_data",
        )

    # High-confidence EOT: commit immediately
    if confidence >= eot_threshold and not _is_disfluency:
        return FluxTurnDecision(
            is_end_of_turn=True,
            extend_stop_ms=0,
            confidence=confidence,
            reason=f"high_conf:{confidence:.2f}",
        )

    # Disfluency regardless of confidence: extend
    if _is_disfluency:
        return FluxTurnDecision(
            is_end_of_turn=False,
            extend_stop_ms=disfluency_extend_ms,
            confidence=confidence,
            reason=f"disfluency:'{_trailing_word}' conf:{confidence:.2f}",
        )

    # Low confidence: let VAD timer expire normally (no forced commit, no extension)
    return FluxTurnDecision(
        is_end_of_turn=False,
        extend_stop_ms=0,
        confidence=confidence,
        reason=f"low_conf:{confidence:.2f}",
    )
