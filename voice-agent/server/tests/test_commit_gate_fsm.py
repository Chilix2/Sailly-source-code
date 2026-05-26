from __future__ import annotations

import pytest


def test_order_commit_requires_readback_and_explicit_confirmation():
    from server.brain.conversation_state import ConversationState

    state = ConversationState(order_intent=True, selected_dish="Bibimbap")

    assert not state.ready_for_commit("create_order")

    state.mark_commit_readback_shown("create_order")
    assert not state.ready_for_commit("create_order")

    state.mark_commit_readback_confirmed("create_order")
    assert state.ready_for_commit("create_order")


def test_reservation_commit_requires_readback_and_explicit_confirmation():
    from server.brain.conversation_state import ConversationState

    state = ConversationState(
        reservation_intent=True,
        party_size=2,
        reservation_date="2026-05-29",
        reservation_time="19:00",
    )

    assert not state.ready_for_commit("create_reservation")

    state.mark_commit_readback_shown("create_reservation")
    assert not state.ready_for_commit("create_reservation")

    state.mark_commit_readback_confirmed("create_reservation")
    assert state.ready_for_commit("create_reservation")


def test_order_correction_resets_commit_gate():
    from server.brain.conversation_state import ConversationState

    state = ConversationState(order_intent=True, selected_dish="Bibimbap")
    state.mark_commit_readback_shown("create_order")
    state.mark_commit_readback_confirmed("create_order")

    assert state.ready_for_commit("create_order")

    state.reset_commit_readback("create_order", "items_corrected")

    assert not state.ready_for_commit("create_order")
    assert state.order_commit_state.reset_cause == "items_corrected"
    assert not getattr(state, "_readback_already_shown", False)
    assert not getattr(state, "_order_readback_confirmed", False)


def test_restored_v5_state_never_infers_confirmation():
    from server.brain.conversation_state import ConversationState

    restored = ConversationState.from_dict({
        "schema_version": 5,
        "order_intent": True,
        "selected_dish": "Bibimbap",
        "end_call_stage": "order_pre_commit_readback",
    })

    assert restored.order_commit_state.readback_shown
    assert not restored.order_commit_state.confirmed
    assert not restored.ready_for_commit("create_order")


@pytest.mark.asyncio
async def test_executor_blocks_commit_without_confirmed_state():
    from server.brain.conversation_state import ConversationState
    from tools.executor import execute_tool

    state = ConversationState(order_intent=True, selected_dish="Bibimbap")
    state.mark_commit_readback_shown("create_order")

    result = await execute_tool(
        "create_order",
        {"order_items": "Bibimbap"},
        call_sid="test-call",
        tenant_id="doboo",
        turn_number=5,
        conversation_state=state,
    )

    assert result["success"] is False
    assert result["blocked_by_guardian"] is True
    assert result["reason"] == "readback_not_confirmed"
