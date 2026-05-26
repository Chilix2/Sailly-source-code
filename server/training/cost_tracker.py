"""
Approximate API cost tracking for training / A/B runs.

Rates are **estimates** for budgeting; check your Google Cloud, OpenAI, and
Deepgram invoices for authoritative numbers. Update constants when pricing changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# --- USD per unit (approximate, Vertex EU / public list prices) ----------------
# Gemini 2.5 Flash (text) — order-of-magnitude for generateContent
_GEMINI_INPUT_PER_1M = 0.075
_GEMINI_OUTPUT_PER_1M = 0.30

# GPT-4o-mini (chat completions)
_OPENAI_INPUT_PER_1M = 0.15
_OPENAI_COMPLETION_PER_1M = 0.60

# Deepgram Nova-3 — per minute of audio processed
_DEEPGRAM_PER_MINUTE = 0.0077

# Google Cloud TTS — WaveNet class (caller side, de-DE-Wavenet-F)
_WAVENET_PER_1M_CHARS = 16.0

# Chirp3 HD (bot TTS) — higher than WaveNet; rough blend for budgeting
_CHIRP3_HD_PER_1M_CHARS = 32.0


@dataclass
class CostTracker:
    """Accumulates usage counters for one conversation arm (e.g. one scenario run)."""

    gemini_input_tokens: int = 0
    gemini_output_tokens: int = 0
    gemini_calls: int = 0

    openai_prompt_tokens: int = 0
    openai_completion_tokens: int = 0
    openai_calls: int = 0

    deepgram_audio_seconds: float = 0.0
    deepgram_requests: int = 0

    caller_tts_chars: int = 0
    bot_tts_chars: int = 0

    def add_gemini_usage(
        self,
        prompt_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        candidates_tokens: Optional[int] = None,
    ) -> None:
        """Record one Gemini generateContent call (tokens from usage_metadata)."""
        self.gemini_calls += 1
        if prompt_tokens is not None:
            self.gemini_input_tokens += int(prompt_tokens)
        out = output_tokens if output_tokens is not None else candidates_tokens
        if out is not None:
            self.gemini_output_tokens += int(out)

    def add_openai_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        self.openai_calls += 1
        self.openai_prompt_tokens += int(prompt_tokens)
        self.openai_completion_tokens += int(completion_tokens)

    def add_deepgram_turn(self, audio_duration_seconds: float) -> None:
        self.deepgram_requests += 1
        self.deepgram_audio_seconds += max(0.0, float(audio_duration_seconds))

    def add_caller_tts_chars(self, n: int) -> None:
        self.caller_tts_chars += max(0, int(n))

    def add_bot_tts_chars(self, n: int) -> None:
        self.bot_tts_chars += max(0, int(n))

    def estimate_usd(self) -> float:
        """Total estimated USD for everything recorded."""
        g_in = (self.gemini_input_tokens / 1_000_000.0) * _GEMINI_INPUT_PER_1M
        g_out = (self.gemini_output_tokens / 1_000_000.0) * _GEMINI_OUTPUT_PER_1M
        o_in = (self.openai_prompt_tokens / 1_000_000.0) * _OPENAI_INPUT_PER_1M
        o_out = (self.openai_completion_tokens / 1_000_000.0) * _OPENAI_COMPLETION_PER_1M
        dg = (self.deepgram_audio_seconds / 60.0) * _DEEPGRAM_PER_MINUTE
        ct = (self.caller_tts_chars / 1_000_000.0) * _WAVENET_PER_1M_CHARS
        bt = (self.bot_tts_chars / 1_000_000.0) * _CHIRP3_HD_PER_1M_CHARS
        return g_in + g_out + o_in + o_out + dg + ct + bt

    def to_dict(self) -> Dict[str, Any]:
        return {
            "usd": round(self.estimate_usd(), 5),
            "gemini_calls": self.gemini_calls,
            "gemini_input_tokens": self.gemini_input_tokens,
            "gemini_output_tokens": self.gemini_output_tokens,
            "openai_calls": self.openai_calls,
            "openai_prompt_tokens": self.openai_prompt_tokens,
            "openai_completion_tokens": self.openai_completion_tokens,
            "deepgram_requests": self.deepgram_requests,
            "deepgram_audio_seconds": round(self.deepgram_audio_seconds, 2),
            "caller_tts_chars": self.caller_tts_chars,
            "bot_tts_chars": self.bot_tts_chars,
        }
