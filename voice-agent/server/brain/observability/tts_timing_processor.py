"""
Phase 9 A1 — TTS first-byte latency instrumentation.

Observes ``TTSAudioRawFrame`` frames as they flow through the Pipecat pipeline
and stamps ``state._turn_timings.tts_first_byte_at`` the moment the first audio
chunk is emitted for each turn.

Insertion point (main.py):

    pipeline = Pipeline([
        ...
        tts,
        TTSTimingProcessor(state_provider=lambda: brain.turn_processor.state),
        tts_watchdog,
        transport.output(),
        ...
    ])

The ``state_provider`` callable must return the current ``ConversationState``
(or ``None``); the processor is a no-op when it returns ``None``.

Why stamp here and not inside the TTS service?
- The TTS service (SaillyGeminiTTSService) is a reusable component that should
  not carry observability state references.
- Placing the stamp in a thin observer after the TTS service gives a clean
  separation of concerns and survives any future TTS service swap.

Turn-boundary safety:
- ``_turn_timings`` is reset to a fresh ``TurnTimings()`` at the start of every
  turn, so ``tts_first_byte_at`` starts at ``0.0`` automatically.
- The ``== 0.0`` guard prevents subsequent audio chunks from re-stamping.
- Barge-in: if TTS is interrupted, the first chunk was already stamped —
  the abort timestamp is a separate metric (PR-5 note; tracked in barge_in_latency_ms).

Testing note:
- Pipecat v0.0.108's ``FrameProcessor.process_frame()`` requires a ``TaskManager``
  that is only available inside a running Pipeline.  Unit tests therefore test
  ``stamp_tts_first_byte()`` directly (the pure function below) rather than
  going through ``process_frame``.
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from pipecat.frames.frames import TTSAudioRawFrame
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection


def stamp_tts_first_byte(state_provider: Callable[[], Optional[object]]) -> None:
    """
    Core stamping logic — extracted for unit-testability.

    Calls ``state_provider()``, checks that the state has a ``_turn_timings``
    attribute with ``tts_first_byte_at == 0.0``, and stamps it with the current
    monotonic time.  All exceptions are suppressed — observability must never
    break the audio path.
    """
    try:
        state = state_provider()
        if state is not None:
            timings = getattr(state, "_turn_timings", None)
            if timings is not None and timings.tts_first_byte_at == 0.0:
                timings.tts_first_byte_at = time.monotonic()
    except Exception:
        pass


class TTSTimingProcessor(FrameProcessor):
    """
    Passive observer: stamps ``_turn_timings.tts_first_byte_at`` on the first
    ``TTSAudioRawFrame`` that passes through per turn, then forwards every frame
    unchanged.
    """

    def __init__(self, state_provider: Callable[[], Optional[object]]) -> None:
        super().__init__()
        self._state_provider = state_provider

    async def process_frame(self, frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, TTSAudioRawFrame):
            stamp_tts_first_byte(self._state_provider)

        await self.push_frame(frame, direction)
