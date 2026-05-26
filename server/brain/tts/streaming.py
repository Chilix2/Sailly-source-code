"""
Sentence-streaming TTS coordinator.

Per tts-streaming: stream-on — Gemini main LLM yields sentences one at a time
(Phase 4 B1). TTS receives each sentence and starts speaking before the next
sentence arrives, reducing first-audio latency.

Per tts-barge-in-cut: fast-cut — when VAD signals that the user has started
speaking, immediately stop TTS audio output (target: within 100ms). Pipecat's
interrupt/VAD pipeline triggers on_user_speech_started(); this coordinator
propagates the cancel signal to the in-flight TTS task.
"""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, Callable, Optional

logger = logging.getLogger(__name__)


class TTSStreamCoordinator:
    """
    Bridges the main-LLM sentence stream to TTS audio output with barge-in support.

    Usage:
        coordinator = TTSStreamCoordinator()
        # In Pipecat VAD callback:
        coordinator.on_user_speech_started()
        # In TTS pipeline:
        async for chunk in coordinator.stream(sentence_iter, tts_speak_fn):
            write_audio(chunk)
    """

    def __init__(self) -> None:
        self._current_task: Optional[asyncio.Task] = None
        self._cut: bool = False

    def on_user_speech_started(self) -> None:
        """
        Called by the VAD start signal (Pipecat interrupt callback).

        Sets the cut flag and cancels any in-flight audio task so audio stops
        within one event-loop iteration (≈ 1–2ms internal latency; Pipecat adds
        audio-buffer flush time, targeting <100ms end-to-end per fast-cut).
        """
        self._cut = True
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            logger.debug("[TTS-STREAM] fast-cut: cancelled current_audio_task")

    def reset(self) -> None:
        """Reset coordinator for the next bot turn (call after barge-in resolves)."""
        self._cut = False
        self._current_task = None

    async def stream(
        self,
        sentence_iter: AsyncIterator[str],
        tts_speak: Callable[[str], AsyncIterator[bytes]],
    ) -> AsyncIterator[bytes]:
        """
        Consume sentences from sentence_iter and yield audio chunks.

        For each sentence:
          1. Wrap the TTS call in an asyncio.Task so it can be cancelled.
          2. Yield audio chunks as they arrive.
          3. If _cut is set (VAD start), break immediately.

        Args:
            sentence_iter: Async iterator of text sentences from the LLM.
            tts_speak:     Async callable (sentence: str) -> AsyncIterator[bytes].
                           Typically a bound method of SaillyGeminiTTSService.
        """
        async for sentence in sentence_iter:
            if self._cut:
                logger.debug("[TTS-STREAM] cut flag set before sentence, stopping")
                break

            self._current_task = asyncio.ensure_future(
                _collect_audio(tts_speak, sentence)
            )
            try:
                chunks: list[bytes] = await self._current_task
                for chunk in chunks:
                    if self._cut:
                        logger.debug("[TTS-STREAM] cut flag set mid-sentence, stopping")
                        break
                    yield chunk
            except asyncio.CancelledError:
                logger.info("[TTS-STREAM] audio task cancelled (barge-in fast-cut)")
                break
            finally:
                self._current_task = None

        if self._cut:
            logger.info("[TTS-STREAM] stream ended due to barge-in fast-cut")


async def _collect_audio(
    tts_speak: Callable[[str], AsyncIterator[bytes]],
    sentence: str,
) -> list[bytes]:
    """Collect all audio chunks for one sentence into a list."""
    chunks: list[bytes] = []
    async for chunk in tts_speak(sentence):
        chunks.append(chunk)
    return chunks
