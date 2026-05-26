"""
Per-stage timing context per decision per-stage (9.O2).

One TurnTimings instance is created at the start of each turn and passed
through the pipeline. Each stage records its completion timestamp. At the
end of the turn, the helper methods compute millisecond deltas for each stage.

Wire-up pattern (in adk_turn_processor or turn_runner):

    timings = TurnTimings()
    # ... STT already done upstream by Pipecat
    timings.stt_done_at = time.monotonic()

    await extractor.run(...)
    timings.extract_done_at = time.monotonic()

    await layer2.generate(...)
    timings.l2_done_at = time.monotonic()

    await dispatcher.run(...)
    timings.tool_done_at = time.monotonic()

    # tts_first_byte_at is set by TTS callback (sailly_gemini_tts.py)

    row = timings.to_metrics_dict()
    await write_turn_metrics(state, row)
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class TurnTimings:
    """Mutable timing accumulator for one turn."""

    turn_started_at: float = field(default_factory=time.monotonic)

    # Each field is 0.0 until the stage completes
    stt_done_at: float = 0.0
    extract_done_at: float = 0.0
    l2_done_at: float = 0.0
    tool_done_at: float = 0.0
    tts_first_byte_at: float = 0.0

    # Per-tool durations: {"create_order": 245, "send_sms": 88}
    tool_durations: dict[str, int] = field(default_factory=dict)

    # Token counts (populated from LLM response metadata)
    prompt_tokens_in: int = 0
    prompt_tokens_out: int = 0
    extract_tokens_in: int = 0
    extract_tokens_out: int = 0

    def record_tool(self, name: str, duration_ms: int) -> None:
        """Record the duration of a single tool call."""
        self.tool_durations[name] = duration_ms

    # ── Computed stage latencies ───────────────────────────────────────────────

    def stt_ms(self) -> int:
        if not self.stt_done_at:
            return 0
        return max(0, int((self.stt_done_at - self.turn_started_at) * 1000))

    def extract_ms(self) -> int:
        if not self.extract_done_at or not self.stt_done_at:
            return 0
        return max(0, int((self.extract_done_at - self.stt_done_at) * 1000))

    def l2_ms(self) -> int:
        if not self.l2_done_at:
            return 0
        ref = self.extract_done_at or self.stt_done_at or self.turn_started_at
        return max(0, int((self.l2_done_at - ref) * 1000))

    def tool_ms(self) -> int:
        if not self.tool_done_at or not self.l2_done_at:
            return 0
        return max(0, int((self.tool_done_at - self.l2_done_at) * 1000))

    def tts_first_byte_ms(self) -> int:
        if not self.tts_first_byte_at:
            return 0
        ref = self.l2_done_at or self.tool_done_at or self.turn_started_at
        return max(0, int((self.tts_first_byte_at - ref) * 1000))

    def total_ms(self) -> int:
        end = (
            self.tts_first_byte_at
            or self.tool_done_at
            or self.l2_done_at
            or self.extract_done_at
            or self.stt_done_at
        )
        if not end:
            return 0
        return max(0, int((end - self.turn_started_at) * 1000))

    def to_metrics_dict(self) -> dict:
        """Return a dict ready for insertion into google_turn_metrics."""
        return {
            "stt_ms": self.stt_ms() or None,
            "extract_ms": self.extract_ms() or None,
            "l2_ms": self.l2_ms() or None,
            "tool_ms": self.tool_ms() or None,
            "tts_first_byte_ms": self.tts_first_byte_ms() or None,
            "total_ms": self.total_ms() or None,
            "tool_durations": self.tool_durations or None,
            "prompt_tokens_in": self.prompt_tokens_in or None,
            "prompt_tokens_out": self.prompt_tokens_out or None,
            "extract_tokens_in": self.extract_tokens_in or None,
            "extract_tokens_out": self.extract_tokens_out or None,
        }
