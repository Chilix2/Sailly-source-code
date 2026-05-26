"""
server/brain/filler_scheduler.py — Phase 8.2: FillerScheduler (M-FILL).

Fires a pre-baked filler phrase via the TTS output path after FILLER_TRIGGER_MS
if the LLM stream hasn't emitted its first audible chunk yet AND the current
turn requires a slow tool.

Kill switch: ENABLE_PRE_LLM_FILLER=false env var.

Usage:
    scheduler = FillerScheduler(tts_callback)
    await scheduler.arm(requires_slow_tool=True)
    # ... LLM starts streaming ...
    scheduler.cancel()  # call when first LLM chunk arrives
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Awaitable, Callable, Optional

from server.brain.audio_assets import ENABLE_PRE_LLM_FILLER, get_filler

logger = logging.getLogger(__name__)

FILLER_TRIGGER_MS = int(os.environ.get("FILLER_TRIGGER_MS", "400"))

AudioCallback = Callable[[bytes], Awaitable[None]]


class FillerScheduler:
    """Arms a delayed filler phrase on slow-tool turns."""

    def __init__(self, audio_callback: Optional[AudioCallback] = None) -> None:
        self._callback = audio_callback
        self._task: Optional[asyncio.Task] = None
        self._fired = False

    async def arm(self, requires_slow_tool: bool = False) -> None:
        """Arm the filler. Does nothing if not enabled or no slow tool."""
        if not ENABLE_PRE_LLM_FILLER or not requires_slow_tool:
            return
        if self._task is not None:
            self._task.cancel()
        self._fired = False
        self._task = asyncio.create_task(self._delayed_fire())

    async def _delayed_fire(self) -> None:
        """Wait FILLER_TRIGGER_MS then play filler if not cancelled."""
        try:
            await asyncio.sleep(FILLER_TRIGGER_MS / 1000.0)
            pcm = get_filler()
            if pcm and self._callback and not self._fired:
                self._fired = True
                logger.debug(f"[FillerScheduler] filler fired after {FILLER_TRIGGER_MS}ms")
                await self._callback(pcm)
        except asyncio.CancelledError:
            pass  # LLM arrived in time

    def cancel(self) -> None:
        """Cancel the pending filler (LLM emitted first chunk)."""
        if self._task and not self._task.done():
            self._task.cancel()

    @property
    def fired(self) -> bool:
        return self._fired
