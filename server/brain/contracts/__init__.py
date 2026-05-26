"""Contracts — canonical interfaces between ExecutionLayers.

This module defines the data structures that flow between the three
execution layers, enabling independent testing and composition.
"""
from server.brain.contracts.turn_package import (
    TurnPackage,
    SlotView,
    IntentView,
    SCHEMA_VERSION,
)
from server.brain.contracts.vocab import (
    ExecutionLayer,
    PromptSlot,
    VoiceTier,
)
from server.brain.contracts.trace import (
    LayerTrace,
)

__all__ = [
    "TurnPackage",
    "SlotView",
    "IntentView",
    "SCHEMA_VERSION",
    "ExecutionLayer",
    "PromptSlot",
    "VoiceTier",
    "LayerTrace",
]
