"""
server/brain/stt/watchdog.py
------------------------------
STTWatchdog dataclass — two-stage timeout watchdog for Deepgram STT.

Stage 1 (NOTIFY_AFTER_SECONDS): inject an apology and invite the caller to
  re-speak if no transcript has arrived within the notification window.
Stage 2 (RECONNECT_AFTER_SECONDS): signal that the STT session should be
  reconnected (caller experienced a longer silence without transcription).

This module defines the pure-logic dataclass; the actual Pipecat FrameProcessor
integration lives in ``server/main.py`` (``STTWatchdog`` class) to avoid
coupling this module to the Pipecat import chain.  The ``tick()`` method here
can be called from a monitoring loop to decide which action to take.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional


NOTIFY_AFTER_SECONDS: float = 5.0
RECONNECT_AFTER_SECONDS: float = 8.0


@dataclass
class STTWatchdog:
    """Pure-logic watchdog tracking last transcript / audio timestamps.

    Usage::

        watchdog = STTWatchdog()

        # Call on each incoming audio chunk:
        watchdog.on_audio_received()

        # Call on each confirmed transcript:
        watchdog.on_transcript_received()

        # Poll at regular intervals (e.g. every 1 s) in an async task:
        await watchdog.tick(
            on_notify=send_apology_frame,
            on_reconnect=trigger_stt_reconnect,
        )
    """

    notify_after_seconds: float = NOTIFY_AFTER_SECONDS
    reconnect_after_seconds: float = RECONNECT_AFTER_SECONDS

    _last_transcript_at: float = field(default_factory=time.monotonic, init=False)
    _last_audio_at: float = field(default_factory=lambda: 0.0, init=False)
    _last_notify_at: float = field(default_factory=lambda: 0.0, init=False)
    _first_transcript_received: bool = field(default=False, init=False)

    def on_transcript_received(self) -> None:
        """Call whenever a non-empty final transcript is received."""
        self._last_transcript_at = time.monotonic()
        self._first_transcript_received = True

    def on_audio_received(self) -> None:
        """Call whenever raw audio frames are flowing."""
        self._last_audio_at = time.monotonic()

    async def tick(
        self,
        on_notify: Optional[Callable[[], Awaitable[None]]] = None,
        on_reconnect: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> None:
        """Evaluate watchdog state and trigger callbacks if thresholds exceeded.

        Should be called from a periodic monitoring task (e.g. every 1 second).
        Only fires after the first transcript has been received (avoids spurious
        alerts at call start) and only when audio is actively flowing.
        """
        if not self._first_transcript_received:
            return
        if self._last_audio_at == 0.0:
            return

        now = time.monotonic()
        audio_age = now - self._last_audio_at
        if audio_age > 5.0:
            # No recent audio — caller is silent; don't alert
            return

        silence_duration = now - self._last_transcript_at
        since_last_notify = now - self._last_notify_at

        if silence_duration >= self.reconnect_after_seconds and on_reconnect is not None:
            if since_last_notify > self.reconnect_after_seconds:
                self._last_notify_at = now
                await on_reconnect()
        elif silence_duration >= self.notify_after_seconds and on_notify is not None:
            if since_last_notify > self.notify_after_seconds:
                self._last_notify_at = now
                await on_notify()
