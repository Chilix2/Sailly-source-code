"""
TurnContext — re-export shim (FINDING-014 fix).

The `TurnContext` dataclass historically lived in
`server/brain/tts_conditioning.py` because TTS conditioning was its first
consumer. As of Phase 4, TurnContext is the canonical per-turn transient
state container shared by all layers.

This module is the canonical import path per the Phase 4 architecture docs:
    from server.brain.contracts.turn_context import TurnContext

`tts_conditioning.py` is the historical home and remains the definition site
for backward compatibility. Future cleanup: move the class definition here and
have `tts_conditioning.py` import from this module instead.
"""
from server.brain.tts_conditioning import TurnContext  # noqa: F401

__all__ = ["TurnContext"]
