"""
Regression test for the Sprint-1 barge-in latency metric.

The intent of this test is NOT to validate end-to-end barge-in UX (that would
require a full WebSocket + audio roundtrip) — it is to guard the metric
instrumentation itself so we don't silently drop latency samples when
refactoring `BargeInHandler`.

Three scenarios:
  1. No bot speech → interruption is ignored for metric purposes.
  2. Barge-in while bot is speaking → sample recorded, p95 present.
  3. Multiple samples → p95 is the 95th percentile of the sorted list.
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipecat.frames.frames import (  # noqa: E402
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    UserStartedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection  # noqa: E402

from server.barge_in_handler import BargeInHandler  # noqa: E402


async def _feed(handler: BargeInHandler, frame):
    await handler.process_frame(frame, FrameDirection.DOWNSTREAM)


async def _drive_single_barge_in(delay_s: float) -> float | None:
    handler = BargeInHandler()
    # Unlock greeting protection by ending an initial bot turn.
    await _feed(handler, BotStartedSpeakingFrame())
    await _feed(handler, BotStoppedSpeakingFrame())
    # Start a fresh bot turn, wait `delay_s`, then simulate the caller speaking.
    await _feed(handler, BotStartedSpeakingFrame())
    await asyncio.sleep(delay_s)
    await _feed(handler, UserStartedSpeakingFrame())
    samples = handler.latency_samples_ms
    return samples[-1] if samples else None


def test_no_samples_before_first_barge_in():
    handler = BargeInHandler()
    assert handler.latency_samples_ms == []
    assert handler.latency_p95_ms is None


def test_barge_in_without_bot_speech_is_not_measured():
    async def _run():
        handler = BargeInHandler()
        await _feed(handler, BotStartedSpeakingFrame())
        await _feed(handler, BotStoppedSpeakingFrame())  # greeting done
        # Caller speaks but bot is NOT speaking — metric must skip
        await _feed(handler, UserStartedSpeakingFrame())
        return handler

    handler = asyncio.run(_run())
    assert handler.latency_samples_ms == []
    assert handler.latency_p95_ms is None


def test_single_barge_in_records_one_sample():
    latency = asyncio.run(_drive_single_barge_in(delay_s=0.05))
    assert latency is not None
    # 50ms delay — allow generous scheduling slack on CI runners.
    assert 20.0 < latency < 500.0


def test_p95_is_ordered_and_stable():
    # Feed synthetic samples directly to test the percentile logic.
    handler = BargeInHandler()
    handler._latency_samples_ms.extend(  # type: ignore[attr-defined]
        [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    )
    # With 10 samples sorted, index round(0.95 * 9) = 9 → 100.0
    assert handler.latency_p95_ms == 100.0

    # Adding a slow sample should lift p95.
    handler._latency_samples_ms.append(250.0)  # type: ignore[attr-defined]
    assert handler.latency_p95_ms >= 100.0


if __name__ == "__main__":
    test_no_samples_before_first_barge_in()
    test_barge_in_without_bot_speech_is_not_measured()
    test_single_barge_in_records_one_sample()
    test_p95_is_ordered_and_stable()
    print("ALL PASS")
