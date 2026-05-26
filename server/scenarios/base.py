"""
Shared dataclasses for scenario definitions.

All phase scenario files import from here to avoid duplication.
AudioScenario and ScenarioTurn are the canonical definitions.

Reactive (goal-driven) vs scripted modes
-----------------------------------------
When `goal` is set on an AudioScenario the SyntheticBrowserClient uses a
Claude Haiku LLM to generate each caller utterance in real-time, reacting to
whatever the bot just said.  This produces realistic, multi-turn conversations
that actually follow the bot's prompts (e.g. NameGate, VerifyGate) instead of
dumping all information upfront and ignoring bot responses.

Leave `goal` empty to keep the old scripted (turns-list) behaviour, which is
still fine for FAQ / smoke scenarios where the caller flow is deterministic.
"""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ScenarioTurn:
    user_utterance: str
    expected_keywords: List[str] = field(default_factory=list)
    must_call_tool: Optional[str] = None
    must_not_call_tool: Optional[str] = None
    latency_budget_ms: int = 5000
    stt_min_accuracy: float = 0.80
    barge_in_at_ms: Optional[int] = None
    code_switch_words: List[str] = field(default_factory=list)


@dataclass
class AudioScenario:
    id: str
    phase: str
    category: str
    description: str
    turns: List[ScenarioTurn]
    expected_tools: List[str] = field(default_factory=list)
    forbidden_content: List[str] = field(default_factory=list)
    quality_dimensions: List[str] = field(
        default_factory=lambda: [
            "task", "language", "instruction",
            "latency", "audio_quality", "stt_accuracy",
        ]
    )
    noise_variant: str = "clean"
    n_runs: int = 3
    seed: int = 42
    persona: Optional[str] = None
    # Persona options:
    # "neutral"      — Normal, polite customer
    # "angry"        — Frustrated, complaining
    # "impatient"    — Cuts short, demands speed
    # "sleepy"       — Slow, slurred, trails off
    # "accent"       — Heavy non-native German accent
    # "hard_to_hear" — Background noise, speaks quietly
    # "chaos"        — Keeps changing mind, contradicts
    # "elderly"      — Slow, repeats, needs clarification

    # ── Reactive (goal-driven) mode ──────────────────────────────────────────
    # When goal is non-empty the SyntheticBrowserClient replaces the fixed
    # turns list with an LLM-powered caller that reacts to each bot response.
    goal: Optional[str] = None
    # caller_name / caller_phone / caller_address are injected into the LLM
    # system prompt so the AI knows which data to provide when asked.
    caller_name: Optional[str] = None
    caller_phone: Optional[str] = None
    caller_address: Optional[str] = None
    # hard cap on turns before the conversation is forced to end
    max_turns: int = 8
