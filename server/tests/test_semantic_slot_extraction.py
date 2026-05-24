from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_semantic_layer_falls_back_to_deterministic_phone_and_confirmation():
    from server.brain.conversation_state import ConversationState
    from server.brain.slot_extraction_layer import SlotExtractionLayer

    state = ConversationState()
    layer = SlotExtractionLayer(slot_extractor=None)

    candidates = await layer.extract(
        user_utterance="Ja, passt. Meine Nummer ist 0179 1234567.",
        conversation_history=[],
        current_state=state,
        slots_to_extract=["confirmation_intent", "phone"],
    )

    assert candidates.confirmation_intent is not None
    assert candidates.confirmation_intent.value == "yes"
    assert candidates.phone is not None
    assert "0179" in candidates.phone.value
    assert state.last_extraction["candidate_count"] >= 2


def test_conversation_state_promotes_high_confidence_semantic_slots():
    from server.brain.conversation_state import ConversationState
    from server.brain.slot_extraction_layer import SlotCandidate, SlotCandidates

    state = ConversationState()
    candidates = SlotCandidates(
        customer_name=SlotCandidate(
            slot_name="customer_name",
            value="Julia Wagner",
            confidence=0.92,
            source="llm",
        ),
        delivery_address=SlotCandidate(
            slot_name="delivery_address",
            value="Bonner Bogen 20, Bonn",
            confidence=0.9,
            source="llm",
            validator_valid=True,
        ),
    )

    applied = state.update_state_from_extracted_slots(candidates)

    assert set(applied) == {"customer_name", "delivery_address"}
    assert state.customer_name == "Julia Wagner"
    assert state.delivery_address == "Bonner Bogen 20, Bonn"
    assert state.has_valid_address()
    assert state.semantic_slot_values["delivery_address"]["source"] == "llm"


def test_conversation_state_stages_medium_confidence_slots_for_readback():
    from server.brain.conversation_state import ConversationState
    from server.brain.slot_extraction_layer import SlotCandidate, SlotCandidates

    state = ConversationState()
    candidates = SlotCandidates(
        phone=SlotCandidate(
            slot_name="phone",
            value="+491791234567",
            confidence=0.7,
            source="llm",
            needs_readback=True,
        )
    )

    applied = state.update_state_from_extracted_slots(candidates)

    assert applied == []
    assert state.phone_number is None
    assert state.pending_readback_slots["phone"]["value"] == "+491791234567"
