"""
Canonical vocabulary for Sailly architecture.

Three things were historically called "layer". They are now:

  ExecutionLayer.{ORCHESTRATOR, LLM, POLICY}
      — the three pipeline layers defined in the 3-layer architecture.
      — lives in server.brain.layer1 / layer2 / layer3.

  PromptSlot.{NODE, LAST_UTTERANCE, EXTRACTOR_STATUS, VALIDATION,
              ANTI_REPETITION, SLOT_CONTEXT, MULTI_INTENT, HISTORY}
      — the eight sections of the prompt assembled by MemoryManager.
      — NOT a layer in the architecture sense.

  VoiceTier.{PERSONA, SITUATION, CALLER_MIRROR}
      — the three tiers of TTS conditioning.
      — NOT a layer in the architecture sense.

When writing docstrings or code, use these exact names. Avoid the
bare word "layer" unless you mean ExecutionLayer.
"""
from enum import Enum


class ExecutionLayer(str, Enum):
    """The three ExecutionLayers — how requests flow through the system."""
    ORCHESTRATOR = "layer1"   # Layer 1 — deterministic code, state management
    LLM = "layer2"            # Layer 2 — language generation only
    POLICY = "layer3"         # Layer 3 — filter function, post-LLM guards


class PromptSlot(str, Enum):
    """The eight sections of the prompt assembled by MemoryManager."""
    NODE = "L1_node"
    LAST_UTTERANCE = "L2_last_utterance"
    EXTRACTOR_STATUS = "L3_extractor_status"
    VALIDATION = "L4_validation"
    ANTI_REPETITION = "L5_anti_repetition"
    SLOT_CONTEXT = "L6_slot_context"
    MULTI_INTENT = "L7_multi_intent"
    HISTORY = "L8_history"


class VoiceTier(str, Enum):
    """The three tiers of TTS conditioning (voice persona)."""
    PERSONA = "persona"
    SITUATION = "situation"
    CALLER_MIRROR = "caller_mirror"
