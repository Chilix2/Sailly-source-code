"""
Pipecat's GeminiTTSService omits ``speaking_rate`` on StreamingAudioConfig; native Gemini Live
audio feels snappier. This subclass passes speaking_rate through to the Cloud TTS stream API.

Also provides normalize_digit_groups() — a pre-TTS text normalizer that spells out 5+ digit
strings (postcodes, phone numbers) character-by-character in German, so TTS renders them as
"fünf drei eins zwei sechs" rather than "dreiundfünfzigtausend…".
"""

from __future__ import annotations

import asyncio
import re
from typing import AsyncGenerator

from google.cloud import texttospeech_v1
from loguru import logger
from pipecat.frames.frames import ErrorFrame, Frame, TTSAudioRawFrame, TTSStoppedFrame
from pipecat.services.google.tts import GeminiTTSService
from pipecat.utils.tracing.service_decorators import traced_tts

# 429 retry config: up to 3 retries with exponential backoff (0.5s, 1s, 2s)
_TTS_429_MAX_RETRIES = 3
_TTS_429_BACKOFF_BASE_S = 0.5


def _make_silence_frames(duration_ms: int, sample_rate: int = 24000) -> list[TTSAudioRawFrame]:
    """Generate a list of silent PCM16 frames totalling approximately duration_ms milliseconds."""
    total_bytes = int(sample_rate * 2 * duration_ms / 1000)
    # Split into chunks of ~20ms to match normal audio frame size
    chunk_bytes = int(sample_rate * 2 * 0.02)
    frames = []
    remaining = total_bytes
    while remaining > 0:
        size = min(chunk_bytes, remaining)
        frames.append(TTSAudioRawFrame(audio=bytes(size), sample_rate=sample_rate, num_channels=1))
        remaining -= size
    return frames

_DIGIT_WORDS_DE = {
    "0": "null", "1": "eins", "2": "zwei", "3": "drei", "4": "vier",
    "5": "fünf", "6": "sechs", "7": "sieben", "8": "acht", "9": "neun",
}

# German integer words for 0–29 (covers all price values for a restaurant menu)
_INT_WORDS_DE: dict[int, str] = {
    0: "null", 1: "ein", 2: "zwei", 3: "drei", 4: "vier", 5: "fünf",
    6: "sechs", 7: "sieben", 8: "acht", 9: "neun", 10: "zehn",
    11: "elf", 12: "zwölf", 13: "dreizehn", 14: "vierzehn", 15: "fünfzehn",
    16: "sechzehn", 17: "siebzehn", 18: "achtzehn", 19: "neunzehn",
    20: "zwanzig", 21: "einundzwanzig", 22: "zweiundzwanzig", 23: "dreiundzwanzig",
    24: "vierundzwanzig", 25: "fünfundzwanzig", 26: "sechsundzwanzig",
    27: "siebenundzwanzig", 28: "achtundzwanzig", 29: "neunundzwanzig",
    30: "dreißig", 31: "einunddreißig", 32: "zweiundreißig", 33: "dreiunddreißig",
    34: "vierunddreißig", 35: "fünfunddreißig", 36: "sechsunddreißig",
    40: "vierzig", 41: "einundvierzig", 42: "zweiundvierzig", 45: "fünfundvierzig",
    50: "fünfzig", 51: "einundfünfzig", 55: "fünfundfünfzig",
    60: "sechzig", 70: "siebzig", 80: "achtzig", 90: "neunzig",
}


def _int_to_de(n: int) -> str:
    """Convert integer 0–99 to German word form."""
    if n in _INT_WORDS_DE:
        return _INT_WORDS_DE[n]
    tens, ones = divmod(n, 10)
    tens_word = _INT_WORDS_DE.get(tens * 10, str(tens * 10))
    ones_word = _INT_WORDS_DE.get(ones, str(ones))
    return f"{ones_word}und{tens_word}"


_QUANTITY_WORDS_DE: dict[int, str] = {
    1: "einmal",
    2: "zweimal",
    3: "dreimal",
    4: "viermal",
    5: "fünfmal",
    6: "sechsmal",
    7: "siebenmal",
    8: "achtmal",
    9: "neunmal",
    10: "zehnmal",
}


def normalize_item_quantities(text: str) -> str:
    """Convert item quantity prefixes like '1×' to natural German speech."""
    def _replace_quantity(match: re.Match) -> str:
        try:
            qty = int(match.group(1))
        except ValueError:
            return match.group(0)
        return _QUANTITY_WORDS_DE.get(qty, f"{_int_to_de(qty)}mal") + " "

    return re.sub(r"\b(\d{1,2})\s*[×x]\s+(?=\S)", _replace_quantity, text)


def normalize_prices(text: str) -> str:
    """Convert price patterns to natural German speech.

    Examples:
        "14,50"  → "vierzehn Euro fünfzig"
        "9,00"   → "neun Euro"
        "12,90"  → "zwölf Euro neunzig"
        "€14,50" → "vierzehn Euro fünfzig"
        "14.50"  → "vierzehn Euro fünfzig"
    """
    def _replace_price(m: re.Match) -> str:
        euros_str = m.group(1).lstrip("€").lstrip("€")
        cents_str = m.group(2)
        try:
            euros = int(euros_str)
            cents = int(cents_str)
        except ValueError:
            return m.group(0)
        euro_word = _int_to_de(euros) if euros <= 99 else str(euros)
        if cents == 0:
            return f"{euro_word} Euro"
        cent_word = _int_to_de(cents) if cents <= 99 else str(cents)
        return f"{euro_word} Euro {cent_word}"

    # Match patterns: (optional €)(1-3 digits),(2 digits) or (1-3 digits).(2 digits)
    # Also consume any trailing " Euro" or " €" that the LLM may have already appended,
    # so "16,50 Euro" → "sechzehn Euro fünfzig" (not "sechzehn Euro fünfzig Euro").
    return re.sub(r"€?(\d{1,3})[,.](\d{2})\b\s*(?:[Ee]uro|€)?", _replace_price, text)


def normalize_ranges(text: str) -> str:
    """Convert numeric ranges to natural German speech.

    Examples:
        "30-60 Minuten"  → "30 bis 60 Minuten"
        "15-20 Min"      → "15 bis 20 Min"
        "30-60"          → "30 bis 60"
    """
    return re.sub(r"\b(\d{1,3})-(\d{1,3})\b", r"\1 bis \2", text)


# Hallucination detector constants
# German speech at 1.3x speaking rate — scaled from 14 c/s @ 1.12x
_CHARS_PER_SEC_DE: float = 14.0 * (1.3 / 1.12)
_ANOMALY_LOW: float = 0.30   # < 30% of expected bytes → suspiciously silent / clipped
_ANOMALY_HIGH: float = 3.00  # > 300% of expected bytes → runaway generation


def normalize_digit_groups(text: str) -> str:
    """Spell out digit groups of 5+ consecutive digits character-by-character in German.

    Converts German postcodes (5 digits) and longer phone/account numbers into
    space-separated digit words so TTS renders them naturally:
        "53126"  → "fünf drei eins zwei sechs"
        "0221 12345678" → "null zwei zwei eins eins zwei drei vier fünf sechs sieben acht"
    Short numbers (prices, quantities, table numbers) are NOT touched.

    Each 3-4 digit chunk is separated by a comma to cue the TTS engine to
    insert a short pause — this is the closest we can get to SSML
    ``<break time="200ms"/>`` without leaving Gemini TTS's plain-text input.
    """
    def _spell_out(match: re.Match) -> str:
        digits = match.group(0)
        words = [_DIGIT_WORDS_DE[d] for d in digits]
        # Group into 3-4 digit chunks with commas for prosodic pauses.
        # Common German telephone cadence: prefix (3-4) / main (3-4) / suffix (2-4).
        groups: list[str] = []
        i = 0
        n = len(words)
        # Leading group of 3
        if n > 6:
            groups.append(" ".join(words[i:i + 3]))
            i += 3
        while i < n:
            take = min(4, n - i)
            groups.append(" ".join(words[i:i + take]))
            i += take
        return ", ".join(groups)

    return re.sub(r"\b\d{5,}\b", _spell_out, text)


class SaillyGeminiTTSService(GeminiTTSService):
    """Gemini 2.5 Flash TTS with explicit streaming speaking_rate."""

    def __init__(self, *, cascade_speaking_rate: float | None = None, **kwargs):
        super().__init__(**kwargs)
        self._cascade_speaking_rate = cascade_speaking_rate

    def update_for_turn(self, prompt: str, speaking_rate: float) -> None:
        """Update TTS style prompt and speaking rate for the upcoming turn.

        Called by BrainService before process_turn() so that every TTS
        synthesis call within that turn uses the situation-aware prompt
        and prosody rate. Safe to call because each WebSocket connection
        owns its own SaillyGeminiTTSService instance.
        """
        self._settings.prompt = prompt
        self._cascade_speaking_rate = speaking_rate

    def _build_voice_and_config(self):
        """Build (voice, streaming_config) for the current settings."""
        if self._settings.multi_speaker and self._settings.speaker_configs:
            speaker_voice_configs = [
                texttospeech_v1.MultispeakerPrebuiltVoice(
                    speaker_alias=sc["speaker_alias"],
                    speaker_id=sc.get("speaker_id", self._settings.voice),
                )
                for sc in self._settings.speaker_configs
            ]
            voice = texttospeech_v1.VoiceSelectionParams(
                language_code=self._settings.language,
                model_name=self._settings.model,
                multi_speaker_voice_config=texttospeech_v1.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=speaker_voice_configs
                ),
            )
        else:
            voice = texttospeech_v1.VoiceSelectionParams(
                language_code=self._settings.language,
                name=self._settings.voice,
                model_name=self._settings.model,
            )

        audio_cfg_kwargs: dict = {
            "audio_encoding": texttospeech_v1.AudioEncoding.PCM,
            "sample_rate_hertz": self.sample_rate,
        }
        if self._cascade_speaking_rate is not None:
            r = float(self._cascade_speaking_rate)
            if 0.25 <= r <= 2.0:
                audio_cfg_kwargs["speaking_rate"] = r

        streaming_config = texttospeech_v1.StreamingSynthesizeConfig(
            voice=voice,
            streaming_audio_config=texttospeech_v1.StreamingAudioConfig(**audio_cfg_kwargs),
        )
        return voice, streaming_config

    @traced_tts
    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame, None]:
        # Strip emotion tags (e.g., [warm], [empathetic]) before processing.
        # These tags are metadata for the TTS engine to apply emotional tone,
        # but they should NOT be included in the text that gets spoken aloud.
        # The emotional context is already provided via the global style_prompt in TTS settings.
        import re as _re_emotion
        text = _re_emotion.sub(r"^\s*\[[a-z]+\]\s*", "", text).strip()
        
        # Normalize quantities, prices ("14,50" → "vierzehn Euro fünfzig") and ranges ("30-60" → "30 bis 60")
        # before digit-group spelling, so the sub-patterns are handled correctly.
        text = normalize_item_quantities(text)
        text = normalize_prices(text)
        text = normalize_ranges(text)
        # Spell out 5+ digit strings digit-by-digit so postcodes/phone numbers
        # are pronounced "fünf drei eins zwei sechs" rather than "dreiundfünfzigtausend"
        text = normalize_digit_groups(text)

        logger.debug(f"{self}: Generating TTS [{text}]")

        # Skip trivially short inputs — single letters / punctuation arrive when the
        # sentence splitter clips the tail of a fragmented response (e.g. "W" from
        # "Womit…" cut mid-word). Sending them to the Gemini TTS API causes silent
        # timeouts (observed: 9+ seconds for a single character).
        stripped = text.strip()
        if len(stripped) < 3 and not stripped.endswith((".", "!", "?")):
            logger.debug(f"{self}: Skipping trivially short TTS input [{text!r}]")
            logger.info(f"[TTS_SUPPRESS] reason=text_too_short text='{text[:20]}'")
            return

        _, streaming_config = self._build_voice_and_config()

        # Expected audio byte count based on character count.
        # 16-bit PCM: 2 bytes/sample.  Guard with a 0.5s floor so short sentences
        # (e.g. "Ja.") are not falsely flagged as too silent.
        _sample_rate: int = int(self.sample_rate or 24000)
        _bytes_per_sec: float = float(_sample_rate * 2)
        _expected_secs: float = max(len(stripped) / _CHARS_PER_SEC_DE, 0.5)
        _expected_bytes: float = _expected_secs * _bytes_per_sec

        # Fix B: Skip buffering for most responses (<8s expected duration).
        # Raised from 4.0s to 8.0s so order readbacks stream immediately.
        # This reduces the "transcript visible but audio starts 1s later" gap
        # by streaming audio frames immediately instead of collecting all bytes first.
        # Only very long multi-sentence responses (>8s) still buffer for diagnostics.
        _skip_buffer = _expected_secs <= 8.0
        
        # Attempt 1: with style prompt
        # Attempt 2 (fallback): without style prompt — retried when attempt 1 produces
        #   zero frames, a 400 API error, or an anomalous audio duration.
        attempts = [self._settings.prompt, None]
        last_exc: Exception | None = None

        for attempt_idx, prompt in enumerate(attempts):
            try:
                # Fix B: Conditionally buffer for hallucination detection
                # Short responses (<2s) skip buffering to improve latency
                # Long responses continue to buffer for anomaly detection
                if _skip_buffer:
                    # Stream directly without buffering
                    import time as _time_mark
                    logger.info(f"[LAT-2026-04-20] call={context_id} turn=0 tts_buffer_done")
                    first_frame = True
                    async for frame in self._stream_tts(streaming_config, text, context_id, prompt):
                        if first_frame:
                            logger.info(f"[LAT-2026-04-20] call={context_id} turn=0 tts_buffer_done->tts_first_yield=instant")
                            first_frame = False
                        yield frame
                    return
                else:
                    # Buffer all frames so we can inspect total audio bytes before yielding.
                    # This prevents the user from hearing a hallucinated response that would
                    # already be playing by the time we detect the anomaly.
                    buffered: list[Frame] = []
                    audio_bytes: int = 0
                    async for frame in self._stream_tts(streaming_config, text, context_id, prompt):
                        buffered.append(frame)
                        if isinstance(frame, TTSAudioRawFrame) and frame.audio:
                            audio_bytes += len(frame.audio)

                    # Mark: TTS buffer done
                    import time as _time_mark
                    logger.info(f"[LAT-2026-04-20] call={context_id} turn=0 tts_buffer_done")

                    if not buffered:
                        if attempt_idx == 0:
                            logger.warning(f"{self}: No audio frames on attempt 1, retrying without style prompt")
                            continue
                        logger.info(f"[TTS_SUPPRESS] reason=empty_frames_retry turn={context_id}")
                        return

                    # Anomaly check: compare actual vs expected audio byte count
                    ratio = audio_bytes / _expected_bytes if _expected_bytes > 0 else 1.0
                    is_anomalous = ratio < _ANOMALY_LOW or ratio > _ANOMALY_HIGH

                    if is_anomalous and attempt_idx == 0:
                        logger.warning(
                            f"[TTSHallucDetect] Anomalous audio ratio {ratio:.2f} "
                            f"({audio_bytes} bytes vs {_expected_bytes:.0f} expected for "
                            f"{len(stripped)} chars) — retrying without style prompt"
                        )
                        continue  # retry without style prompt

                    if is_anomalous and attempt_idx == 1:
                        logger.error(
                            f"[TTSHallucDetect] Still anomalous after retry (ratio={ratio:.2f}). "
                            f"Bypassing suppression so the user still hears the bot. "
                            f"Transcript already pushed to browser."
                        )
                        logger.warning(f"[TTSHallucDetect] bypassed suppression, ratio={ratio:.2f}, text_len={len(text)}")

                    # Normal: yield buffered frames
                    first_frame = True
                    for frame in buffered:
                        if first_frame:
                            # Mark: first TTS audio frame yielding
                            logger.info(f"[LAT-2026-04-20] call={context_id} turn=0 tts_buffer_done->tts_first_yield=instant")
                            first_frame = False
                        yield frame
                    return

            except Exception as e:
                last_exc = e
                err_str = str(e)

                # 429 quota exceeded — retry with exponential back-off instead of
                # propagating an ErrorFrame that would stall / kill the pipeline.
                if "429" in err_str or "Quota exceeded" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    for retry_n in range(1, _TTS_429_MAX_RETRIES + 1):
                        wait_s = _TTS_429_BACKOFF_BASE_S * (2 ** (retry_n - 1))
                        logger.warning(
                            f"{self}: TTS 429 quota — retry {retry_n}/{_TTS_429_MAX_RETRIES} "
                            f"after {wait_s:.1f}s (call={context_id})"
                        )
                        await asyncio.sleep(wait_s)
                        try:
                            if _skip_buffer:
                                async for frame in self._stream_tts(streaming_config, text, context_id, prompt):
                                    yield frame
                            else:
                                async for frame in self._stream_tts(streaming_config, text, context_id, prompt):
                                    yield frame
                            return  # retry succeeded
                        except Exception as retry_exc:
                            retry_str = str(retry_exc)
                            if "429" in retry_str or "Quota exceeded" in retry_str or "RESOURCE_EXHAUSTED" in retry_str:
                                last_exc = retry_exc
                                continue  # try again
                            # Non-429 error during retry — fall through to ErrorFrame
                            last_exc = retry_exc
                            break
                    # All retries exhausted — emit ~500ms of silence so the pipeline
                    # stays alive and the caller hears a brief pause rather than disconnecting.
                    logger.error(
                        f"{self}: TTS 429 — all {_TTS_429_MAX_RETRIES} retries failed, "
                        f"emitting silence fallback (call={context_id})"
                    )
                    logger.info(f"[TTS_SUPPRESS] reason=quota_429 turn={context_id}")
                    _sample_rate = int(self.sample_rate or 24000)
                    for sf in _make_silence_frames(500, _sample_rate):
                        yield sf
                    return

                if attempt_idx == 0 and ("400" in err_str or "INVALID_ARGUMENT" in err_str or "cannot be empty" in err_str):
                    logger.warning(
                        f"{self}: TTS attempt 1 failed with 400 ({err_str[:120]}), "
                        "retrying without style prompt"
                    )
                    continue
                # Non-400/429 error or second attempt failed
                error_message = f"Gemini TTS generation error: {str(e)}"
                yield ErrorFrame(error=error_message)
                return

        if last_exc is not None:
            yield ErrorFrame(error=f"Gemini TTS generation error (both attempts): {last_exc}")
