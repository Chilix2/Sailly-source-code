"""
server/brain/layer1/confidence_guard.py
-----------------------------------------
Confidence guard: checks per-utterance ASR confidence from the rolling window
stored by ``STTConfidenceTracker`` and decides whether the turn processor should
skip Layer 2 and return a reprompt instead.

Design decisions:
- Fails open: missing or None confidences are treated as "good enough" — we
  never block a turn purely due to missing confidence data.
- Rolling window check: only fires if the LAST N_CONSECUTIVE low-confidence
  turns are all below LOW_CONFIDENCE_THRESHOLD, not just the most recent one.
- Response is short and in German to match the voice persona.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

LOW_CONFIDENCE_THRESHOLD: float = 0.70
N_CONSECUTIVE: int = 2  # require 2 consecutive low-confidence turns before reprompting

_REPROMPT_RESPONSES: List[str] = [
    "Entschuldigung, ich habe Sie leider nicht gut verstanden. Könnten Sie das bitte wiederholen?",
    "Ich bin mir nicht sicher, ob ich Sie richtig verstanden habe. Können Sie das nochmal sagen?",
    "Könnten Sie das bitte noch einmal wiederholen? Ich hatte Schwierigkeiten, Sie zu verstehen.",
]

_reprompt_idx: int = 0


def should_reprompt_for_confidence(
    ctx: Any,
    *,
    brain_service: Any = None,
    confidence_window: Optional[List[Optional[float]]] = None,
) -> bool:
    """Return True if the last N consecutive ASR confidences are below threshold.

    Args:
        ctx: Unused context dict (kept for call-site compatibility).
        brain_service: An object that may have ``asr_confidence_window`` attribute
                       (set by ``STTConfidenceTracker``).
        confidence_window: Explicit list of confidence floats (overrides brain_service
                           lookup; useful in tests).

    Returns:
        True if reprompt should be injected; False to proceed normally.
    """
    window: List[Optional[float]] = []

    if confidence_window is not None:
        window = confidence_window
    elif brain_service is not None:
        window = getattr(brain_service, "asr_confidence_window", []) or []

    if not window:
        return False

    recent = window[-N_CONSECUTIVE:]
    if len(recent) < N_CONSECUTIVE:
        return False

    # All recent scores must be non-None and below threshold
    for score in recent:
        if score is None or score >= LOW_CONFIDENCE_THRESHOLD:
            return False

    return True


def low_confidence_response() -> str:
    """Return a rotating German reprompt string."""
    global _reprompt_idx
    response = _REPROMPT_RESPONSES[_reprompt_idx % len(_REPROMPT_RESPONSES)]
    _reprompt_idx += 1
    return response
