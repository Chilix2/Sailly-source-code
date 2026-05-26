"""
TTS client per Phase 7 decisions.

Per tts-model: gemini-flash   — engine is Gemini Flash.
Per tts-voice: kore           — default voice "Kore"; tenant-overridable via YAML.
Per tts-emotion-tags: gemini-only — emotion tags injected only when voice is one
    of the known Gemini voices. If tenant switches to Neural2/Chirp3, tags are
    stripped automatically so they don't appear as literal text.
Per tts-streaming: stream-on  — text arrives sentence-by-sentence from the main
    LLM; audio chunks are yielded as they arrive (see streaming.py).
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, AsyncIterator

logger = logging.getLogger(__name__)

# Known Gemini multi-speaker / style-capable voices.
# Only these accept [emotion] inline tags without treating them as literal text.
GEMINI_VOICES: frozenset[str] = frozenset(
    {"Kore", "Aoede", "Charon", "Fenrir", "Puck", "Zephyr", "Leda", "Orus"}
)

# Regex that matches any [tag] pattern so we can strip tags for non-Gemini voices.
_TAG_RE = re.compile(r"\[[\w\-]+\]")


def _strip_emotion_tags(text: str) -> str:
    """Remove all [emotion-tag] tokens from text."""
    return _TAG_RE.sub("", text).strip()


def prepare_text_for_tts(text: str, situation: str, voice: str) -> str:
    """
    Inject emotion tag if voice is Gemini-capable; strip otherwise.

    Per tts-emotion-tags: gemini-only.
    """
    from server.brain.tts.situation_styles import SITUATION_STYLES

    if voice in GEMINI_VOICES:
        style = SITUATION_STYLES.get(situation)
        tag = style["tag"] if style else "[friendly]"
        # Only prepend if the text doesn't already start with a tag
        if not text.startswith("["):
            return f"{tag} {text}"
        return text
    return _strip_emotion_tags(text)


async def _gemini_tts_stream(
    text: str,
    voice: str,
    rate: float,
) -> AsyncIterator[bytes]:
    """
    Thin async wrapper around the Gemini / Cloud TTS streaming API.

    In the live system this delegates to SaillyGeminiTTSService (server/sailly_gemini_tts.py).
    This function exists as the clean interface boundary so speak() is independently testable.
    Subclasses or tests override this via dependency injection on speak().
    """
    raise NotImplementedError(
        "Gemini TTS streaming is handled by SaillyGeminiTTSService via Pipecat. "
        "Use speak() only within the Pipecat pipeline where the TTS service is active."
    )
    # Unreachable; makes the type signature correct.
    yield b""  # noqa: unreachable


async def speak(
    text_iter: AsyncIterator[str],
    tenant_cfg: dict,
    situation: str,
    mood: str,
    *,
    _tts_backend=None,
) -> AsyncIterator[bytes]:
    """
    Stream TTS audio per sentence.

    Per tts-streaming: stream-on — receive text sentence-by-sentence; emit audio
    chunks as they arrive from the TTS backend.

    Args:
        text_iter:    Async iterator of text sentences from the main LLM.
        tenant_cfg:   Tenant config dict (reads tts.voice, tts.speed_multiplier).
        situation:    One of the 15 SITUATION_STYLES keys (e.g. "GREETING_FIRST").
        mood:         One of the 6 CALLER_MIRRORS keys (e.g. "NEUTRAL").
        _tts_backend: Optional injectable backend for testing; defaults to
                      _gemini_tts_stream (live Gemini path).
    """
    from server.brain.tts.tts_conditioning import compute_speaking_rate

    voice = tenant_cfg.get("tts", {}).get("voice", "Kore")
    rate = compute_speaking_rate(situation, mood, tenant_cfg)
    backend = _tts_backend or _gemini_tts_stream

    logger.debug("[TTS-CLIENT] voice=%s situation=%s mood=%s rate=%.2f", voice, situation, mood, rate)

    async for sentence in text_iter:
        prepared = prepare_text_for_tts(sentence, situation, voice)
        async for audio_chunk in backend(prepared, voice, rate):
            yield audio_chunk
