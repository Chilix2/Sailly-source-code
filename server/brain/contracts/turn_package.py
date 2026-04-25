"""
TurnPackage — the canonical handoff from Layer 1 to Layer 2.

Layer 1 (orchestrator) produces a TurnPackage containing everything
Layer 2 (LLM) needs to generate a response. Layer 2 does NOT read
ConversationState directly; it only reads the TurnPackage.

This indirection is what makes the layers independently testable.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from server.brain.captured_intents import SlotValue as _SlotValue
    from server.brain.captured_intents import CapturedIntent as _CapturedIntent

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SlotView:
    """A slot as Layer 2 sees it — value plus status and confidence, no internals."""
    name: str
    value: Optional[str]
    status: str       # SlotStatus.value: "missing" | "partial" | "filled" | "confirmed"
    confidence: str   # SlotConfidence.value: "low" | "medium" | "high"
    validated: bool = False

    @classmethod
    def from_slot(cls, s: "_SlotValue", validated: bool = False) -> "SlotView":
        """Project a CapturedIntent SlotValue into a read-only view."""
        return cls(
            name=s.name,
            value=s.value,
            status=s.status.value,
            confidence=s.confidence.value,
            validated=validated,
        )


@dataclass(frozen=True)
class IntentView:
    """An intent as Layer 2 sees it."""
    kind: str    # IntentKind.value
    status: str  # IntentStatus.value
    slots: List[SlotView]

    @classmethod
    def from_intent(
        cls,
        intent: "_CapturedIntent",
        validator_lookup=None,
    ) -> "IntentView":
        """Project a CapturedIntent into a read-only view.

        validator_lookup: optional callable (kind, slot_name) -> bool
            Returns True if the slot has been validated externally.
        """
        validator_lookup = validator_lookup or (lambda k, s: False)
        return cls(
            kind=intent.kind.value,
            status=intent.status.value,
            slots=[
                SlotView.from_slot(sv, validator_lookup(intent.kind, sv.name))
                for sv in intent.slots.values()
                if hasattr(sv, "status")  # guard: skip legacy raw values
            ],
        )


@dataclass(frozen=True)
class TurnPackage:
    """Everything Layer 2 needs to generate a response for this turn."""

    # Versioning for evolution (decision: la-layer-evolution = interface-versioning)
    schema_version: int = SCHEMA_VERSION

    # Node context
    node_name: str = ""
    node_prompt: str = ""
    tool_whitelist: List[str] = field(default_factory=list)

    # Conversation state view (what Layer 2 is allowed to see)
    current_intent: Optional[IntentView] = None
    queued_intents: List[IntentView] = field(default_factory=list)
    shared_slots: List[SlotView] = field(default_factory=list)

    # Caller signals
    last_utterance: str = ""
    caller_mood_hint: Optional[str] = None
    asr_confidence: float = 1.0

    # Memory
    recent_turns: List[Dict[str, str]] = field(default_factory=list)
    history_summary: str = ""

    # Metadata for observability (per-layer-trace)
    turn_idx: int = 0
    call_sid: str = ""

    # Voice conditioning — Phase 7 (populated by turn_package_builder via voice_conditioning.py)
    # Layer 2 prompt assembly reads voice_mood to apply skip_chitchat for IMPATIENT.
    voice_situation: str = "INFO_NEUTRAL"   # one of the 15 SITUATION_STYLES keys
    voice_mood: str = "NEUTRAL"             # one of the 6 CALLER_MIRRORS keys

    def redacted_for_logs(self) -> Dict[str, Any]:
        """Return a log-safe dict (no PII in slot values).

        Phase 8 PII redaction will implement this.
        """
        raise NotImplementedError("Implement in Phase 8")
