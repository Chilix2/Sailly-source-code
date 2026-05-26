from __future__ import annotations

import pytest


def test_should_skip_semantic_on_pure_greeting():
    from server.brain.conversation_state import ConversationState
    from server.brain.slot_extraction_layer import should_run_semantic_extraction, slots_for_current_turn

    state = ConversationState()

    assert should_run_semantic_extraction(state, "Hallo") is False
    assert slots_for_current_turn(state, "Hallo") == ["confirmation_intent"]


def test_should_run_semantic_on_order_utterance():
    from server.brain.conversation_state import ConversationState
    from server.brain.slot_extraction_layer import should_run_semantic_extraction, slots_for_current_turn

    state = ConversationState()

    assert should_run_semantic_extraction(state, "Ich möchte ein Bibimbap bestellen") is True
    assert "order_items" in slots_for_current_turn(state, "Ich möchte ein Bibimbap bestellen")


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
    assert state.last_extraction["llm_skipped"] is True


@pytest.mark.asyncio
async def test_semantic_layer_extracts_bebimbap_deterministically_without_llm():
    from server.brain.conversation_state import ConversationState
    from server.brain.slot_extraction_layer import SlotExtractionLayer

    state = ConversationState()
    state.known_items = ["Kimchi", "Bibimbap Hähnchen", "Wasser"]
    layer = SlotExtractionLayer(slot_extractor=None)

    candidates = await layer.extract(
        user_utterance=(
            "Mijn naam is Markus Schneider. Ik shed gerne een kimchi, "
            "een bebimbap und ein wasser."
        ),
        conversation_history=[],
        current_state=state,
        slots_to_extract=["order_items"],
    )

    assert candidates.order_items
    assert candidates.order_items[0].value[0] == "Kimchi"
    assert candidates.order_items[0].value[1].startswith("Bibimbap")
    assert candidates.order_items[0].value[2] == "Wasser"
    assert state.last_extraction["llm_skipped"] is True


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


def test_conversation_state_merges_semantic_order_items_with_existing_cart():
    from server.brain.conversation_state import ConversationState
    from server.brain.slot_extraction_layer import SlotCandidate, SlotCandidates

    state = ConversationState(order_intent=True, selected_dish="Kimchi")
    state.order_items_extras = ["Wasser"]

    candidates = SlotCandidates(
        order_items=[
            SlotCandidate(
                slot_name="order_items",
                value=["Bibimbap", "Wasser"],
                confidence=0.95,
                source="llm",
            )
        ]
    )

    applied = state.update_state_from_extracted_slots(candidates)

    assert applied == ["order_items"]
    assert state.selected_items == ["Kimchi", "Wasser", "Bibimbap"]


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


@pytest.mark.asyncio
async def test_address_validator_understands_verify_address_contract(monkeypatch):
    from server.brain.slot_extraction_layer import SlotCandidate
    from server.brain.slot_validators import AddressValidator

    async def fake_execute_tool(tool_name, args, call_sid, tenant_id):
        assert tool_name == "verify_address"
        assert args["city"] == "Bonn"
        return {
            "success": True,
            "canonical_address": "Bonner Bogen 20, 53227 Bonn, Germany",
            "confidence": 0.8,
            "needs_caller_confirm": True,
            "readback_text": "Habe ich Sie richtig verstanden — Bonner Bogen 20?",
        }

    import tools.executor

    monkeypatch.setattr(tools.executor, "execute_tool", fake_execute_tool)

    result = await AddressValidator(
        call_sid="demo-test",
        tenant_id="doboo",
        city="Bonn",
    ).validate(
        SlotCandidate(
            slot_name="delivery_address",
            value="Bonner Bogen 20, Bonn",
            confidence=0.9,
        )
    )

    assert result.tool_called == "verify_address"
    assert result.is_valid is False
    assert result.corrected_value == "Bonner Bogen 20, 53227 Bonn, Germany"
    assert result.feedback == "Habe ich Sie richtig verstanden — Bonner Bogen 20?"


def test_address_denial_clears_stale_delivery_state():
    from server.brain.conversation_state import ConversationState
    from server.brain.v4_turn_processor import V4TurnProcessor

    processor = V4TurnProcessor.__new__(V4TurnProcessor)
    processor.state = ConversationState(
        delivery_address="Donnerbogen 20, Bonn",
        delivery_intended=True,
        delivery_address_mentioned=True,
        address_verified=True,
        address_confirmed=True,
        verify_address_called=True,
    )
    processor.state.pending_readback_slots["delivery_address"] = {
        "value": "Donnerbogen 20, Bonn",
        "confidence": 0.75,
    }
    processor.state._readback_already_shown = True
    processor.state._order_readback_confirmed = True

    processor._clear_delivery_address_state()

    assert processor.state.delivery_address is None
    assert processor.state.address_verified is False
    assert processor.state.address_confirmed is False
    assert processor.state.verify_address_called is False
    assert "delivery_address" not in processor.state.pending_readback_slots
    assert processor.state._readback_already_shown is False


def test_corrected_address_overwrites_old_address_and_resets_gates():
    from server.brain.conversation_state import ConversationState
    from server.brain.slot_extraction_layer import SlotCandidate, SlotCandidates

    state = ConversationState(
        delivery_address="Donnerbogen 20, Bonn",
        delivery_intended=True,
        address_verified=True,
        address_confirmed=True,
        verify_address_called=True,
    )
    state._readback_already_shown = True
    state._order_readback_confirmed = True

    candidates = SlotCandidates(
        delivery_address=SlotCandidate(
            slot_name="delivery_address",
            value="Bonner Bogen 20, Bonn",
            confidence=0.95,
            source="llm",
            validator_valid=True,
            correction=True,
        )
    )

    applied = state.update_state_from_extracted_slots(candidates)

    assert applied == ["delivery_address"]
    assert state.delivery_address == "Bonner Bogen 20, Bonn"
    assert state.address_verified is True
    assert state.address_confirmed is True
    assert state._readback_already_shown is False


def test_delivery_commit_guard_present_in_v4_pipeline_source():
    from pathlib import Path

    src = Path("server/brain/v4_pipeline.py").read_text(encoding="utf-8")

    assert "_delivery_order_needs_address_confirmation" in src
    assert '"delivery_address" in getattr(state, "pending_readback_slots", {})' in src
    assert "delivery order blocked until address confirmation" in src
