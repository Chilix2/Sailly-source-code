"""
server/brain/audio_assets.py — Phase 8.1: Pre-baked filler + backchannel audio assets.

Pre-bakes 12 filler phrases and 6 backchannel phrases as PCM at startup.
Both pools use the Kore voice (Gemini 2.5 Flash / Chirp3HD) for consistency.

Filler phrases: played at normal volume after 400ms when Required workers
haven't finished (M-FILL). Rotation window = 5 (never repeat in last 5 turns).

Backchannel phrases: played at -10 dB during 200-500ms hesitation pauses
within caller utterances (never at turn end). Rotation window = 2.

Usage:
    from server.brain.audio_assets import get_filler, get_backchannel
    filler_pcm = await get_filler()
    backchannel_pcm = await get_backchannel()
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import struct
from typing import Optional

logger = logging.getLogger(__name__)

# ── Phrase pools ────────────────────────────────────────────────────────────────

FILLER_PHRASES = [
    "Einen Moment bitte.",
    "Ganz kurz.",
    "Augenblick bitte.",
    "Ich schaue kurz nach.",
    "Einen kleinen Augenblick.",
    "Ja, bin gleich bei Ihnen.",
    "Moment bitte.",
    "Ich sehe sofort nach.",
    "Kurz nachschauen.",
    "Gerne, einen Moment.",
    "Ich prüfe das gleich.",
    "Einen Moment, ich schaue das nach.",
]

BACKCHANNEL_PHRASES = [
    "Mhm.",
    "Ja.",
    "Verstehe.",
    "Aha.",
    "Ich höre.",
    "Natürlich.",
]

# ── In-process audio cache ──────────────────────────────────────────────────────

_filler_cache: dict[str, bytes] = {}          # phrase → PCM bytes at 24kHz
_backchannel_cache: dict[str, bytes] = {}     # phrase → PCM bytes at 24kHz (−10 dB)

_filler_history: list[str] = []               # last 5 played fillers
_backchannel_history: list[str] = []          # last 2 played backchannels

_FILLER_VARIATION_WINDOW = 5
_BACKCHANNEL_VARIATION_WINDOW = 2

# Kill switches (from env)
ENABLE_PRE_LLM_FILLER = os.environ.get("ENABLE_PRE_LLM_FILLER", "true").lower() != "false"
ENABLE_BACKCHANNEL = os.environ.get("ENABLE_BACKCHANNEL", "true").lower() != "false"


def _apply_gain(pcm_bytes: bytes, gain_db: float) -> bytes:
    """Apply a gain in dB to PCM16LE audio bytes."""
    if gain_db == 0:
        return pcm_bytes
    factor = 10 ** (gain_db / 20.0)
    samples = struct.unpack(f"<{len(pcm_bytes) // 2}h", pcm_bytes)
    adjusted = bytes(struct.pack(
        f"<{len(samples)}h",
        *[max(-32768, min(32767, int(s * factor))) for s in samples],
    ))
    return adjusted


async def _synthesise_phrase(phrase: str, gain_db: float = 0) -> Optional[bytes]:
    """Synthesise a phrase to PCM using the active TTS service.

    Falls back to silence if TTS is unavailable (e.g. during tests).
    """
    try:
        from google.cloud import texttospeech_v1 as tts
        client = tts.TextToSpeechAsyncClient()
        synthesis_input = tts.SynthesisInput(text=phrase)
        voice = tts.VoiceSelectionParams(
            language_code="de-DE",
            name="de-DE-Chirp3-HD-Kore",
        )
        audio_config = tts.AudioConfig(
            audio_encoding=tts.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000,
            speaking_rate=1.1,
        )
        response = await client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        pcm = response.audio_content
        if gain_db != 0:
            pcm = _apply_gain(pcm, gain_db)
        return pcm
    except Exception as err:
        logger.warning(f"[AudioAssets] TTS synthesis failed for '{phrase}': {err}")
        return None


async def prebake_all() -> None:
    """Pre-synthesise all filler and backchannel phrases at startup."""
    if not ENABLE_PRE_LLM_FILLER and not ENABLE_BACKCHANNEL:
        return

    logger.info("[AudioAssets] Pre-baking filler and backchannel phrases...")
    tasks = []

    if ENABLE_PRE_LLM_FILLER:
        for phrase in FILLER_PHRASES:
            tasks.append(_prebake_filler(phrase))

    if ENABLE_BACKCHANNEL:
        for phrase in BACKCHANNEL_PHRASES:
            tasks.append(_prebake_backchannel(phrase))

    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info(
        f"[AudioAssets] Pre-bake complete: "
        f"{len(_filler_cache)} fillers, {len(_backchannel_cache)} backchannels"
    )


async def _prebake_filler(phrase: str) -> None:
    pcm = await _synthesise_phrase(phrase, gain_db=0)
    if pcm:
        _filler_cache[phrase] = pcm


async def _prebake_backchannel(phrase: str) -> None:
    pcm = await _synthesise_phrase(phrase, gain_db=-10)
    if pcm:
        _backchannel_cache[phrase] = pcm


def get_filler() -> Optional[bytes]:
    """Return PCM bytes for a filler phrase, respecting variation window."""
    if not ENABLE_PRE_LLM_FILLER or not _filler_cache:
        return None

    available = [p for p in _filler_cache if p not in _filler_history[-_FILLER_VARIATION_WINDOW:]]
    if not available:
        available = list(_filler_cache.keys())

    phrase = random.choice(available)
    _filler_history.append(phrase)
    if len(_filler_history) > _FILLER_VARIATION_WINDOW + 2:
        _filler_history.pop(0)

    return _filler_cache.get(phrase)


def get_backchannel() -> Optional[bytes]:
    """Return PCM bytes for a backchannel phrase at -10 dB."""
    if not ENABLE_BACKCHANNEL or not _backchannel_cache:
        return None

    available = [
        p for p in _backchannel_cache
        if p not in _backchannel_history[-_BACKCHANNEL_VARIATION_WINDOW:]
    ]
    if not available:
        available = list(_backchannel_cache.keys())

    phrase = random.choice(available)
    _backchannel_history.append(phrase)
    if len(_backchannel_history) > _BACKCHANNEL_VARIATION_WINDOW + 2:
        _backchannel_history.pop(0)

    return _backchannel_cache.get(phrase)
