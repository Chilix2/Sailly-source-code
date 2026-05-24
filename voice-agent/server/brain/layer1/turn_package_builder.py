"""
Layer 1 — TurnPackage builder.

Produces the canonical Layer 1 → Layer 2 handshake from the current
ConversationState and turn context. Layer 2 MUST NOT read ConversationState
directly — only the TurnPackage produced here.

This is the typed-package decision from la-inter-layer-interface.
Phase 3 will wire this into the live turn processor (replacing the
inline context building in MemoryManager).
"""
from __future__ import annotations

from typing import Dict, List, Optional, TYPE_CHECKING

from server.brain.captured_intents import sort_by_priority
from server.brain.contracts.turn_package import TurnPackage, IntentView, SlotView
from server.brain.layer1.voice_conditioning import detect_situation, detect_caller_mood

if TYPE_CHECKING:
    from server.brain.conversation_state import ConversationState


def build_turn_package(
    state: "ConversationState",
    node_name: str,
    node_prompt: str,
    tool_whitelist: List[str],
    last_utterance: str,
    asr_confidence: float,
    turn_idx: int,
    recent_turns: List[Dict[str, str]],
    history_summary: str = "",
    validator_lookup=None,
    utterance_word_count: int = 0,
) -> TurnPackage:
    """Produce the canonical Layer 1 → Layer 2 handshake.

    Never leaks ConversationState references; returns immutable views only.

    Args:
        state: current ConversationState (may use legacy or v2 schema)
        node_name: which node is active (e.g., "ORDERING", "RESERVATION")
        node_prompt: the node's system-prompt segment
        tool_whitelist: tools Layer 2 may suggest
        last_utterance: what the caller just said
        asr_confidence: ASR confidence score (0.0–1.0)
        turn_idx: current turn number
        recent_turns: list of {"user": ..., "bot": ...} dicts
        history_summary: optional compressed history string
        validator_lookup: optional (IntentKind, slot_name) -> bool
    """
    # Gather intents from state — support both old (list of raw CapturedIntent) and new
    raw_intents = getattr(state, "captured_intents", [])
    intents = sort_by_priority(raw_intents)

    # Build current and queued intent views
    current_idx = getattr(state, "current_intent_idx", None)
    current: Optional[IntentView] = None
    queued: List[IntentView] = []

    if current_idx is not None and 0 <= current_idx < len(intents):
        current = IntentView.from_intent(intents[current_idx], validator_lookup)
        queued = [
            IntentView.from_intent(intents[i], validator_lookup)
            for i in range(len(intents))
            if i != current_idx
        ]
    elif intents:
        # No explicit current_idx — use first after sorting
        current = IntentView.from_intent(intents[0], validator_lookup)
        queued = [
            IntentView.from_intent(intents[i], validator_lookup)
            for i in range(1, len(intents))
        ]

    # Shared slots (name, phone — asked once, used for all intents)
    shared_slots_raw = getattr(state, "shared_slots", {})
    shared: List[SlotView] = []
    if isinstance(shared_slots_raw, dict):
        for sv in shared_slots_raw.values():
            if hasattr(sv, "status"):
                shared.append(SlotView.from_slot(sv))

    # call_sid — may be on state or passed in
    call_sid = getattr(state, "call_sid", "")

    # Phase 7: voice conditioning — detect situation and mood for TTS
    voice_situation = detect_situation(state)
    voice_mood = detect_caller_mood(
        state,
        asr_confidence=asr_confidence,
        utterance_word_count=utterance_word_count,
    )

    return TurnPackage(
        schema_version=1,
        node_name=node_name,
        node_prompt=node_prompt,
        tool_whitelist=tool_whitelist,
        current_intent=current,
        queued_intents=queued,
        shared_slots=shared,
        last_utterance=last_utterance,
        asr_confidence=asr_confidence,
        recent_turns=recent_turns,
        history_summary=history_summary,
        turn_idx=turn_idx,
        call_sid=call_sid,
        voice_situation=voice_situation,
        voice_mood=voice_mood,
    )
