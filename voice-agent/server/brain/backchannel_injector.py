"""
server/brain/backchannel_injector.py — Phase 8.3: BackchannelInjector.

Detects hesitation pauses (200–500 ms of mid-utterance silence) and injects
a backchannel phrase at -10 dB without yielding the conversational floor.

Guard: if Flux has already emitted EagerEndOfTurn for this utterance,
suppress the backchannel (caller is done, not hesitating).

Kill switch: ENABLE_BACKCHANNEL=false env var.

False-positive monitoring: tracks backchannel_fired + eot_followed_immediately
metrics for google_turn_metrics.

Usage:
    injector = BackchannelInjector(audio_callback)
    await injector.on_silence_start()          # call when VAD goes low
    await injector.on_speech_resume()          # call when VAD goes high again
    injector.on_eager_eot()                    # call when EagerEndOfTurn fires
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Awaitable, Callable, Optional

from server.brain.audio_assets import ENABLE_BACKCHANNEL, get_backchannel

logger = logging.getLogger(__name__)

HESITATION_MIN_MS = int(os.environ.get("BACKCHANNEL_HESITATION_MIN_MS", "200"))
HESITATION_MAX_MS = int(os.environ.get("BACKCHANNEL_HESITATION_MAX_MS", "500"))

AudioCallback = Callable[[bytes], Awaitable[None]]


class BackchannelInjector:
    """Detects hesitation pauses and plays backchannels during caller speech."""

    def __init__(self, audio_callback: Optional[AudioCallback] = None) -> None:
        self._callback = audio_callback
        self._silence_start: Optional[float] = None
        self._task: Optional[asyncio.Task] = None
        self._eager_eot_fired = False

        # Metrics for this turn
        self.backchannel_fired = False
        self.eot_followed_immediately = False

    def reset_for_turn(self) -> None:
        """Call at the start of each user turn."""
        self._silence_start = None
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        self._eager_eot_fired = False
        self.backchannel_fired = False
        self.eot_followed_immediately = False

    async def on_silence_start(self) -> None:
        """Call when VAD detects silence onset during caller utterance."""
        if not ENABLE_BACKCHANNEL or self._eager_eot_fired:
            return
        self._silence_start = time.monotonic()
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = asyncio.create_task(self._wait_and_fire())

    # Backwards-compatible alias used by brain_service.on_user_silence_start.
    on_user_silence_start_safe = on_silence_start

    async def on_speech_resume(self) -> None:
        """Call when VAD detects speech resuming after a pause."""
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        # If we already fired a backchannel, reset for next pause
        self._silence_start = None

    def on_eager_eot(self) -> None:
        """Call when Flux emits EagerEndOfTurn — suppress backchannel."""
        self._eager_eot_fired = True
        if self.backchannel_fired:
            # Backchannel fired just before EagerEndOfTurn — false positive
            self.eot_followed_immediately = True
            logger.debug("[BackchannelInjector] false positive: EagerEndOfTurn immediately after backchannel")
        if self._task and not self._task.done():
            self._task.cancel()

    async def _wait_and_fire(self) -> None:
        """Wait HESITATION_MIN_MS then fire if still in hesitation window."""
        try:
            await asyncio.sleep(HESITATION_MIN_MS / 1000.0)

            if self._eager_eot_fired:
                return  # Suppressed

            # Check we're still in the hesitation window
            if self._silence_start is None:
                return
            elapsed_ms = (time.monotonic() - self._silence_start) * 1000
            if elapsed_ms > HESITATION_MAX_MS:
                # Silence too long — this is end-of-turn, not hesitation
                return

            pcm = get_backchannel()
            if pcm and self._callback:
                self.backchannel_fired = True
                logger.debug(
                    f"[BackchannelInjector] backchannel fired at {elapsed_ms:.0f}ms silence"
                )
                await self._callback(pcm)

        except asyncio.CancelledError:
            pass
