"""Tests for Builder Lab scenario promotion scaffolding."""

from datetime import datetime

from server.builder.scenario_promotion import (
    GATE_BLOCKED,
    GATE_NOT_STARTED,
    GATE_PASSED,
    GATE_READY,
    create_run_record,
    promotion_gates,
    scenario_requirements,
    update_run_record_from_regression_result,
)


def _takeaway_scenario():
    return {
        "id": "restaurant_takeaway_order_builder",
        "industry": "restaurant",
        "capability": "takeaway_order",
        "tenant_id": "doboo",
        "description": "Simple takeaway order should commit an order.",
        "caller_goal": "The caller orders Bulgogi for pickup.",
        "expectations": {"tools": ["create_order"]},
        "required_data": {"customer_name": "Muller", "order_items": ["Bulgogi"]},
    }


def test_scenario_requirements_merge_capability_and_scenario():
    requirements = scenario_requirements(_takeaway_scenario())

    assert requirements.industry == "restaurant"
    assert requirements.capability == "takeaway_order"
    assert requirements.required_tools == ["create_order"]
    assert requirements.expected_tools == ["create_order"]
    assert "order_items" in requirements.required_slots
    assert requirements.required_data_keys == ["customer_name", "order_items"]


def test_create_run_record_is_queued_and_non_executing():
    scenario = _takeaway_scenario()
    record = create_run_record(
        scenario,
        "run_test",
        now=datetime(2026, 5, 24, 10, 0, 0),
    )

    assert record["status"] == "queued"
    assert record["result"] == "not_run"
    assert record["expected_tools"] == ["create_order"]
    assert record["tools_seen"] == []
    assert record["requirements"]["capability"] == "takeaway_order"

    gates = {gate["stage"]: gate["status"] for gate in record["promotion_gates"]}
    assert gates == {
        "draft": GATE_READY,
        "validate": GATE_NOT_STARTED,
        "publish": GATE_BLOCKED,
    }


def test_regression_result_can_promote_validation_gate():
    scenario = _takeaway_scenario()
    record = create_run_record(scenario, "run_test")
    updated = update_run_record_from_regression_result(
        record,
        {
            "passed": True,
            "tools_fired": ["create_order"],
            "checks": [{"name": "tool:create_order", "passed": True}],
            "bot_responses": ["Hallo", "Gerne."],
            "call_sid": "call_123",
            "duration_s": 1.2,
        },
        scenario,
    )

    assert updated["status"] == "completed"
    assert updated["result"] == "pass"
    assert updated["call_sid"] == "call_123"

    gates = {gate["stage"]: gate["status"] for gate in updated["promotion_gates"]}
    assert gates["validate"] == GATE_PASSED
    assert gates["publish"] == GATE_READY


def test_missing_draft_fields_block_publish_even_without_execution():
    scenario = {
        "id": "thin_scenario",
        "industry": "restaurant",
        "capability": "takeaway_order",
    }

    gates = {gate["stage"]: gate["status"] for gate in promotion_gates(scenario)}

    assert gates["draft"] == GATE_BLOCKED
    assert gates["validate"] == GATE_NOT_STARTED
    assert gates["publish"] == GATE_BLOCKED
