"""
Barge-in handling for real-time interruption detection.

When the caller starts speaking while the agent is playing TTS,
this handler immediately triggers interruption handling to stop playback
and queue new user utterance processing.
"""

import logging
import time
from typing import List, Optional

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    InterruptionFrame,
    UserStartedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

logger = logging.getLogger(__name__)


class BargeInHandler(FrameProcessor):
    """
    Handle user interruption during agent TTS playback.

    When UserStartedSpeakingFrame arrives (user started speaking), immediately:
    1. Push InterruptionFrame to signal interruption to the pipeline
    2. Log the interruption
    3. Allow new user utterance to be captured

    Greeting protection: the first bot utterance (greeting) is protected — any
    UserStartedSpeakingFrame that arrives before the first BotStoppedSpeakingFrame
    is silently dropped. After the greeting completes, barge-in is enabled for all
    subsequent turns.

    This enables natural conversation flow where callers can interrupt without waiting.
    The pipeline's turn-taking strategies will handle the actual TTS stop.
    """

    def __init__(self):
        super().__init__()
        self._turn_index = 0
        self._last_interrupt_time: Optional[float] = None
        # Greeting protection: suppress interruptions until first bot utterance completes
        self._greeting_complete = False
        # ── Barge-in latency instrumentation (Sprint 1) ────────────────────
        # Every InterruptionFrame we emit is time-stamped against the most
        # recent BotStartedSpeakingFrame, producing a latency sample in ms.
        # Samples are kept in memory for the call; tests and dashboards read
        # them via `latency_samples_ms` / `latency_p95_ms`.
        self._bot_speaking_since: Optional[float] = None
        self._latency_samples_ms: List[float] = []

    async def process_frame(self, frame, direction: FrameDirection):
        """Process frame — intercept UserStartedSpeakingFrame and trigger interruption."""
        await super().process_frame(frame, direction)

        if isinstance(frame, BotStartedSpeakingFrame):
            self._bot_speaking_since = time.monotonic()
        elif isinstance(frame, BotStoppedSpeakingFrame):
            self._bot_speaking_since = None
            if not self._greeting_complete:
                self._greeting_complete = True
                logger.info("[BARGE_IN] enabled — greeting complete, interruptions now active")

        if isinstance(frame, UserStartedSpeakingFrame):
            await self._on_user_started_speaking()

        await self.push_frame(frame, direction)

    async def _on_user_started_speaking(self):
        """
        Called when user starts speaking (detected by VAD or Deepgram).
        Signal interruption to pipeline to stop TTS playback.
        """
        # Greeting protection: suppress interruptions during the opening bot utterance
        if not self._greeting_complete:
            logger.debug("[BargeIn] Suppressed — greeting not yet complete")
            return

        current_time = time.monotonic()

        # Prevent rapid repeat interruptions (debounce)
        if self._last_interrupt_time and (current_time - self._last_interrupt_time) < 0.2:
            logger.debug("[BargeIn] Ignoring rapid re-interrupt (debounce)")
            return

        self._last_interrupt_time = current_time
        self._turn_index += 1

        # Latency metric — only meaningful if the bot was actually speaking.
        latency_ms: Optional[float] = None
        if self._bot_speaking_since is not None:
            latency_ms = (current_time - self._bot_speaking_since) * 1000.0
            self._latency_samples_ms.append(latency_ms)

        # Signal interruption to the pipeline — TTS will be stopped by turn-taking strategy
        await self.push_frame(InterruptionFrame())
        if latency_ms is not None:
            logger.info(
                f"[BargeIn] User interrupted agent speech (turn {self._turn_index}) — "
                f"latency_from_bot_start={latency_ms:.0f}ms n={len(self._latency_samples_ms)}"
            )
        else:
            logger.info(
                f"[BargeIn] User interrupted agent speech (turn {self._turn_index}) — "
                f"no active bot speech (metric skipped)"
            )

    @property
    def interrupt_count(self) -> int:
        """Number of times user has interrupted agent speech."""
        return self._turn_index

    @property
    def latency_samples_ms(self) -> List[float]:
        """Copy of per-barge-in latency samples (milliseconds)."""
        return list(self._latency_samples_ms)

    @property
    def latency_p95_ms(self) -> Optional[float]:
        """95th percentile of barge-in latency in ms, or None if no samples.

        Intended for post-call monitoring and for the Sprint 1 regression
        scenario that asserts the handler actually saw interruptions.
        """
        samples = self._latency_samples_ms
        if not samples:
            return None
        sorted_samples = sorted(samples)
        idx = min(len(sorted_samples) - 1, int(round(0.95 * (len(sorted_samples) - 1))))
        return sorted_samples[idx]
