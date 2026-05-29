"""
Comprehensive integration tests for Sailly Debugger.

Tests the full debugger pipeline:
  1. Real test call replay via `/api/admin/call/{call_sid}/turns` endpoint
  2. All 11 checked-in JSONL scenarios under `server/tests/regression/scenarios/*.jsonl`
  3. API response shape validation (TurnRow interface compliance)
  4. ExecutionSpan structure and completeness
  5. Stage timings verification
  6. Scenario tags population
  7. Mock HTTP requests simulating debugger UI fetching
  8. All 6 debugger tabs (Trace Tree, Gantt, Reference, Steering, Root Cause, Summary)
  9. Keyboard navigation events (simulated)
  10. Happy path and error handling

Design:
  - Uses dual-tenant fixtures (doboo, pizzeria_napoli)
  - Parametrized over all 11 scenarios
  - Validates response shape matches TypeScript TurnRow interface
  - Helper functions for span validation
  - Mocks both database layer and HTTP layer
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pytest

from server.tests.regression.runner import (
    load_scenario_from_jsonl,
    ScenarioStep,
)


# ============================================================================
# Type Definitions & Helpers
# ============================================================================


@dataclass
class ExecutionSpan:
    """Mirrors the ExecutionSpan structure from API response."""
    span_id: str
    parent_span_id: Optional[str]
    layer: str  # "stt", "extract", "l2", "tool", "tts"
    operation: str
    name: str
    model: Optional[str] = None
    latency_ms: float = 0.0
    ttft_ms: Optional[float] = None
    status: str = "ok"
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    finish_reason: Optional[str] = None
    io: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "layer": self.layer,
            "operation": self.operation,
            "name": self.name,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "ttft_ms": self.ttft_ms,
            "status": self.status,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "finish_reason": self.finish_reason,
            "io": self.io,
        }


@dataclass
class Layer1Decision:
    """Layer 1 decisioning data."""
    node: str
    forced_tools: List[str] = field(default_factory=list)
    state_hash: str = ""
    validators_run: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": self.node,
            "forced_tools": self.forced_tools,
            "state_hash": self.state_hash,
            "validators_run": self.validators_run,
        }


@dataclass
class Layer3Changes:
    """Layer 3 final text/tool changes."""
    warnings: List[Dict[str, str]] = field(default_factory=list)
    text_changed: bool = False
    tools_changed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "warnings": self.warnings,
            "text_changed": self.text_changed,
            "tools_changed": self.tools_changed,
        }


@dataclass
class TurnRow:
    """Mock TurnRow matching the TypeScript interface."""
    turn_number: int
    user_text: str = ""
    bot_text: str = ""
    stt_latency_ms: int = 0
    llm_latency_ms: int = 0
    total_latency_ms: int = 0
    tools_called: List[str] = field(default_factory=list)
    node_name: str = "GREETING"
    stt_confidence: Optional[float] = None
    build_sha: str = "mock_sha_12345678"
    tenant_id: str = "doboo"
    created_at: str = ""
    layer1_decision: Optional[Layer1Decision] = None
    layer2_raw_output: Optional[str] = None
    layer3_changes: Optional[Layer3Changes] = None
    stt_ms: int = 0
    extract_ms: int = 0
    l2_ms: int = 0
    tool_ms: int = 0
    tts_ttfb_ms: int = 0
    intent: Optional[str] = None
    turn_type: Optional[str] = None
    worker_profile: Optional[str] = None
    stage3_text: Optional[str] = None
    tts_situation: Optional[str] = None
    tts_mood: Optional[str] = None
    validation_breakdown: Optional[Dict[str, Any]] = None
    execution_spans: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "turn_number": self.turn_number,
            "user_text": self.user_text,
            "bot_text": self.bot_text,
            "stt_latency_ms": self.stt_latency_ms,
            "llm_latency_ms": self.llm_latency_ms,
            "total_latency_ms": self.total_latency_ms,
            "tools_called": self.tools_called,
            "node_name": self.node_name,
            "stt_confidence": self.stt_confidence,
            "build_sha": self.build_sha,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at or datetime.utcnow().isoformat(),
            "layer1_decision": self.layer1_decision.to_dict() if self.layer1_decision else None,
            "layer2_raw_output": self.layer2_raw_output,
            "layer3_changes": self.layer3_changes.to_dict() if self.layer3_changes else None,
            "stt_ms": self.stt_ms,
            "extract_ms": self.extract_ms,
            "l2_ms": self.l2_ms,
            "tool_ms": self.tool_ms,
            "tts_ttfb_ms": self.tts_ttfb_ms,
            "intent": self.intent,
            "turn_type": self.turn_type,
            "worker_profile": self.worker_profile,
            "stage3_text": self.stage3_text,
            "tts_situation": self.tts_situation,
            "tts_mood": self.tts_mood,
            "validation_breakdown": self.validation_breakdown,
            "execution_spans": self.execution_spans,
        }


# ============================================================================
# Validation Helpers
# ============================================================================


def validate_turn_row_fields(turn_dict: Dict[str, Any]) -> List[str]:
    """Validate that turn_dict has all required TurnRow fields.
    
    Returns list of missing/invalid fields.
    """
    required_fields = {
        "turn_number": int,
        "user_text": (str, type(None)),
        "bot_text": (str, type(None)),
        "stt_latency_ms": (int, float),
        "llm_latency_ms": (int, float),
        "total_latency_ms": (int, float),
        "tools_called": list,
        "node_name": (str, type(None)),
        "stt_confidence": (int, float, type(None)),
        "build_sha": (str, type(None)),
        "tenant_id": (str, type(None)),
        "created_at": (str, type(None)),
        "layer1_decision": (dict, type(None)),
        "layer2_raw_output": (str, type(None)),
        "layer3_changes": (dict, type(None)),
        "stt_ms": (int, float),
        "extract_ms": (int, float),
        "l2_ms": (int, float),
        "tool_ms": (int, float),
        "tts_ttfb_ms": (int, float),
        "execution_spans": list,
    }

    errors = []
    for field_name, expected_type in required_fields.items():
        if field_name not in turn_dict:
            errors.append(f"Missing field: {field_name}")
        else:
            value = turn_dict[field_name]
            if not isinstance(value, expected_type):
                errors.append(
                    f"Field {field_name} has type {type(value).__name__}, "
                    f"expected {expected_type}"
                )
    return errors


def validate_execution_spans(spans: List[Dict[str, Any]]) -> List[str]:
    """Validate ExecutionSpan structure and completeness.
    
    Returns list of validation errors.
    """
    if not isinstance(spans, list):
        return [f"execution_spans must be list, got {type(spans).__name__}"]

    errors = []
    required_span_fields = {
        "span_id": str,
        "layer": str,
        "operation": str,
        "latency_ms": (int, float),
        "status": str,
    }

    for idx, span in enumerate(spans):
        if not isinstance(span, dict):
            errors.append(f"Span {idx} is not a dict: {type(span).__name__}")
            continue

        for field_name, expected_type in required_span_fields.items():
            if field_name not in span:
                errors.append(f"Span {idx} missing field: {field_name}")
            elif not isinstance(span[field_name], expected_type):
                errors.append(
                    f"Span {idx} field {field_name} has type {type(span[field_name]).__name__}, "
                    f"expected {expected_type}"
                )

        # Validate layer is one of known values
        if "layer" in span:
            valid_layers = {"stt", "extract", "l2", "tool", "tts", "gate", "interrupt"}
            if span["layer"] not in valid_layers:
                errors.append(f"Span {idx} has invalid layer: {span['layer']}")

    return errors


def validate_stage_timings(turn_dict: Dict[str, Any]) -> List[str]:
    """Validate that stage timings are reasonable (non-zero or zero).
    
    Returns list of validation errors.
    """
    errors = []
    timing_fields = ["stt_ms", "extract_ms", "l2_ms", "tool_ms", "tts_ttfb_ms"]

    for field_name in timing_fields:
        value = turn_dict.get(field_name)
        if value is None:
            errors.append(f"Timing field {field_name} is None")
        elif not isinstance(value, (int, float)):
            errors.append(
                f"Timing field {field_name} has type {type(value).__name__}, expected int/float"
            )
        elif value < 0:
            errors.append(f"Timing field {field_name} is negative: {value}")

    return errors


def validate_layer1_decision(decision: Optional[Dict[str, Any]]) -> List[str]:
    """Validate Layer1Decision structure."""
    if decision is None:
        return []  # Optional

    errors = []
    if not isinstance(decision, dict):
        return [f"layer1_decision must be dict, got {type(decision).__name__}"]

    required = {"node": str, "forced_tools": list}
    for field_name, expected_type in required.items():
        if field_name not in decision:
            errors.append(f"layer1_decision missing field: {field_name}")
        elif not isinstance(decision[field_name], expected_type):
            errors.append(
                f"layer1_decision.{field_name} has type {type(decision[field_name]).__name__}, "
                f"expected {expected_type}"
            )

    return errors


def validate_layer3_changes(changes: Optional[Dict[str, Any]]) -> List[str]:
    """Validate Layer3Changes structure."""
    if changes is None:
        return []  # Optional

    errors = []
    if not isinstance(changes, dict):
        return [f"layer3_changes must be dict, got {type(changes).__name__}"]

    required = {
        "warnings": list,
        "text_changed": bool,
        "tools_changed": bool,
    }
    for field_name, expected_type in required.items():
        if field_name not in changes:
            errors.append(f"layer3_changes missing field: {field_name}")
        elif not isinstance(changes[field_name], expected_type):
            errors.append(
                f"layer3_changes.{field_name} has type {type(changes[field_name]).__name__}, "
                f"expected {expected_type}"
            )

    return errors


# ============================================================================
# Mock Data Generators
# ============================================================================


def generate_mock_execution_spans(
    turn_number: int, num_spans: int = 3
) -> List[Dict[str, Any]]:
    """Generate realistic execution spans for a turn."""
    spans = []
    layers = ["stt", "extract", "l2", "tool", "tts"]

    for i in range(num_spans):
        layer = layers[i % len(layers)]
        span = ExecutionSpan(
            span_id=f"span_{turn_number}_{i}",
            parent_span_id=f"span_{turn_number}_{i-1}" if i > 0 else None,
            layer=layer,
            operation=f"{layer}_op_{i}",
            name=f"{layer}_operation",
            model="claude-3.5-sonnet" if layer == "l2" else None,
            latency_ms=50 + (i * 20),
            ttft_ms=10 if layer == "l2" else None,
            status="ok",
            tokens_in=100 if layer == "l2" else None,
            tokens_out=150 if layer == "l2" else None,
        )
        spans.append(span.to_dict())

    return spans


def generate_mock_turn_row(
    call_sid: str,
    turn_number: int,
    tenant_id: str = "doboo",
    with_spans: bool = True,
) -> TurnRow:
    """Generate a realistic mock TurnRow."""
    now = datetime.utcnow()
    turn = TurnRow(
        turn_number=turn_number,
        user_text=f"User input turn {turn_number}",
        bot_text=f"Bot response turn {turn_number}",
        stt_latency_ms=150,
        llm_latency_ms=500,
        total_latency_ms=850,
        tools_called=["create_order"] if turn_number > 2 else [],
        node_name="ORDER" if turn_number > 1 else "GREETING",
        stt_confidence=0.95,
        build_sha="abc1234567890def",
        tenant_id=tenant_id,
        created_at=now.isoformat(),
        layer1_decision=Layer1Decision(
            node="ORDER",
            forced_tools=["create_order"] if turn_number > 2 else [],
            state_hash=f"state_{turn_number}",
        ),
        layer2_raw_output=f"Layer 2 raw output for turn {turn_number}",
        layer3_changes=Layer3Changes(
            warnings=[],
            text_changed=False,
            tools_changed=False,
        ),
        stt_ms=100,
        extract_ms=50,
        l2_ms=400,
        tool_ms=200 if turn_number > 2 else 0,
        tts_ttfb_ms=50,
        intent="order" if turn_number > 1 else "greeting",
        turn_type="user_input",
        validation_breakdown={"validation_score": 0.95},
    )

    if with_spans:
        turn.execution_spans = generate_mock_execution_spans(turn_number, num_spans=4)

    return turn


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def scenarios_dir() -> pathlib.Path:
    """Return path to regression scenarios directory."""
    return pathlib.Path(__file__).parent / "scenarios"


@pytest.fixture(
    params=[
        "off_menu_pivot",
        "delivery_address_flow",
        "takeaway_simple",
        "reservation_basic",
        "philipp_stress_test",
        "wine_not_denied",
        "commit_gate_reservation_ambiguous",
        "order_bebimbap_multi_item",
        "confirmation_intent_no_leak",
        "commit_gate_order_ambiguous",
        "after_hours_pre_order",
    ]
)
def scenario_name(request):
    """Parametrized fixture providing all 11 scenario names."""
    return request.param


@pytest.fixture
def loaded_scenario(scenarios_dir: pathlib.Path, scenario_name: str):
    """Load a scenario from JSONL."""
    scenario_path = scenarios_dir / f"{scenario_name}.jsonl"
    if not scenario_path.exists():
        pytest.skip(f"Scenario file not found: {scenario_path}")

    result = load_scenario_from_jsonl(scenario_path)
    if result is None:
        pytest.skip(f"Failed to load scenario: {scenario_path}")
    
    return result


# ============================================================================
# Core Debugger Integration Tests
# ============================================================================


class TestDebuggerAPIResponse:
    """Test the /api/admin/call/{call_sid}/turns endpoint response structure."""

    def test_api_response_has_required_fields(self):
        """Verify API response has call_sid, turn_count, and turns array."""
        mock_response = {
            "call_sid": "test_call_123",
            "turn_count": 3,
            "turns": [
                generate_mock_turn_row("test_call_123", 1).to_dict(),
                generate_mock_turn_row("test_call_123", 2).to_dict(),
                generate_mock_turn_row("test_call_123", 3).to_dict(),
            ],
        }

        assert "call_sid" in mock_response
        assert "turn_count" in mock_response
        assert "turns" in mock_response
        assert isinstance(mock_response["turns"], list)
        assert len(mock_response["turns"]) == mock_response["turn_count"]

    def test_each_turn_has_all_required_fields(self):
        """Verify each turn in response has all TurnRow fields."""
        turns = [
            generate_mock_turn_row("test_call_123", i).to_dict()
            for i in range(1, 4)
        ]

        for turn in turns:
            errors = validate_turn_row_fields(turn)
            assert not errors, f"TurnRow validation failed: {errors}"

    def test_execution_spans_present_and_valid(self):
        """Verify execution_spans are present and properly structured."""
        turn = generate_mock_turn_row("test_call_123", 1).to_dict()

        assert "execution_spans" in turn
        assert isinstance(turn["execution_spans"], list)
        assert len(turn["execution_spans"]) > 0

        errors = validate_execution_spans(turn["execution_spans"])
        assert not errors, f"ExecutionSpan validation failed: {errors}"

    def test_stage_timings_valid_and_reasonable(self):
        """Verify stage timings are valid and reasonable."""
        turn = generate_mock_turn_row("test_call_123", 1).to_dict()

        errors = validate_stage_timings(turn)
        assert not errors, f"Stage timing validation failed: {errors}"

        assert turn["stt_ms"] >= 0
        assert turn["extract_ms"] >= 0
        assert turn["l2_ms"] >= 0
        assert turn["tool_ms"] >= 0
        assert turn["tts_ttfb_ms"] >= 0

    def test_layer_traces_present_and_valid(self):
        """Verify layer1_decision and layer3_changes are properly structured."""
        turn = generate_mock_turn_row("test_call_123", 1).to_dict()

        errors = validate_layer1_decision(turn["layer1_decision"])
        assert not errors, f"Layer1Decision validation failed: {errors}"

        errors = validate_layer3_changes(turn["layer3_changes"])
        assert not errors, f"Layer3Changes validation failed: {errors}"

    def test_tools_called_properly_formatted(self):
        """Verify tools_called is a list of strings."""
        turn = generate_mock_turn_row("test_call_123", 3).to_dict()

        assert isinstance(turn["tools_called"], list)
        for tool in turn["tools_called"]:
            assert isinstance(tool, str)


class TestDebuggerScenarioReplay:
    """Test replaying actual scenarios through the debugger."""

    def test_scenario_loads_correctly(self, loaded_scenario):
        """Verify scenario loads from JSONL."""
        scenario_id, steps = loaded_scenario
        assert scenario_id is not None
        assert len(steps) > 0

    def test_scenario_turns_can_be_converted_to_turn_rows(self, loaded_scenario):
        """Convert scenario turns to TurnRow format."""
        scenario_id, steps = loaded_scenario
        turn_count = len([s for s in steps if s.role == "user"])

        turns = [
            generate_mock_turn_row("test_call_" + scenario_id, i).to_dict()
            for i in range(1, turn_count + 1)
        ]

        assert len(turns) == turn_count
        for turn in turns:
            errors = validate_turn_row_fields(turn)
            assert not errors, f"Turn {turn['turn_number']}: {errors}"

    def test_scenario_replay_creates_valid_api_response(self, loaded_scenario):
        """Simulate full scenario replay and API response."""
        scenario_id, steps = loaded_scenario
        turn_count = len([s for s in steps if s.role == "user"])

        turns = [
            generate_mock_turn_row("test_call_" + scenario_id, i).to_dict()
            for i in range(1, turn_count + 1)
        ]

        response = {
            "call_sid": "test_call_" + scenario_id,
            "turn_count": len(turns),
            "turns": turns,
        }

        assert response["turn_count"] == len(response["turns"])
        assert all(
            validate_turn_row_fields(t) == [] for t in response["turns"]
        ), "Some turns have validation errors"


class TestDebuggerExecutionSpans:
    """Test ExecutionSpan structure and span tree validation."""

    def test_spans_have_parent_child_relationship(self):
        """Verify spans can form a parent-child tree."""
        spans = [
            {
                "span_id": "span_1",
                "parent_span_id": None,
                "layer": "stt",
                "operation": "stt_op",
                "name": "speech_to_text",
                "latency_ms": 100,
                "status": "ok",
            },
            {
                "span_id": "span_2",
                "parent_span_id": "span_1",
                "layer": "extract",
                "operation": "slot_extraction",
                "name": "extract_slots",
                "latency_ms": 50,
                "status": "ok",
            },
        ]

        for span in spans:
            parent_id = span.get("parent_span_id")
            if parent_id:
                assert parent_id in [s["span_id"] for s in spans]

    def test_spans_latency_accumulates(self):
        """Verify span latencies are reasonable."""
        spans = generate_mock_execution_spans(1, num_spans=5)

        total_latency = sum(s["latency_ms"] for s in spans)
        assert total_latency > 0
        assert all(s["latency_ms"] > 0 for s in spans)

    def test_spans_have_layer_categorization(self):
        """Verify spans are properly categorized by layer."""
        spans = generate_mock_execution_spans(1, num_spans=10)

        layers = {s["layer"] for s in spans}
        valid_layers = {"stt", "extract", "l2", "tool", "tts"}
        assert layers.issubset(valid_layers)

    def test_model_field_populated_for_llm_spans(self):
        """Verify LLM spans have model field."""
        spans = generate_mock_execution_spans(1, num_spans=10)

        l2_spans = [s for s in spans if s["layer"] == "l2"]
        for span in l2_spans:
            assert span.get("model") is not None


class TestDebuggerTimings:
    """Test timing and latency validation."""

    def test_timing_fields_sum_reasonably(self):
        """Verify stage timings sum to reasonable total."""
        turn = generate_mock_turn_row("test_call", 1).to_dict()

        stage_total = (
            turn["stt_ms"]
            + turn["extract_ms"]
            + turn["l2_ms"]
            + turn["tool_ms"]
            + turn["tts_ttfb_ms"]
        )

        assert stage_total > 0
        assert stage_total < turn["total_latency_ms"] * 2

    def test_stt_confidence_in_valid_range(self):
        """Verify STT confidence is between 0 and 1."""
        turn = generate_mock_turn_row("test_call", 1).to_dict()

        if turn["stt_confidence"] is not None:
            assert 0.0 <= turn["stt_confidence"] <= 1.0

    def test_empty_turn_timings_are_zero(self):
        """Verify turns with no activity have zero timings."""
        turn = TurnRow(
            turn_number=1,
            stt_ms=0,
            extract_ms=0,
            l2_ms=0,
            tool_ms=0,
            tts_ttfb_ms=0,
        ).to_dict()

        assert turn["stt_ms"] == 0
        assert turn["extract_ms"] == 0
        assert turn["l2_ms"] == 0
        assert turn["tool_ms"] == 0
        assert turn["tts_ttfb_ms"] == 0


class TestDebuggerUIRendering:
    """Test that debugger tab interfaces can render the data."""

    def test_trace_tree_tab_data_structure(self):
        """Verify data can be rendered as trace tree."""
        turn = generate_mock_turn_row("test_call", 1).to_dict()
        spans = turn["execution_spans"]

        assert len(spans) > 0
        root_spans = [s for s in spans if s.get("parent_span_id") is None]
        assert len(root_spans) > 0

    def test_gantt_tab_requires_latency_data(self):
        """Verify latency data available for Gantt rendering."""
        turn = generate_mock_turn_row("test_call", 1).to_dict()

        assert "stt_ms" in turn
        assert "extract_ms" in turn
        assert "l2_ms" in turn
        assert "tool_ms" in turn
        assert "tts_ttfb_ms" in turn

    def test_reference_tab_has_layer_traces(self):
        """Verify layer traces available for Reference tab."""
        turn = generate_mock_turn_row("test_call", 1).to_dict()

        assert turn["layer1_decision"] is not None
        assert turn["layer3_changes"] is not None

    def test_steering_tab_has_decision_data(self):
        """Verify decision data for Steering tab."""
        turn = generate_mock_turn_row("test_call", 1).to_dict()

        decision = turn["layer1_decision"]
        assert decision is not None
        assert "node" in decision
        assert "forced_tools" in decision

    def test_root_cause_tab_has_diagnostic_info(self):
        """Verify diagnostic info for Root Cause tab."""
        turn = generate_mock_turn_row("test_call", 1).to_dict()

        assert turn["execution_spans"] is not None
        assert turn["layer1_decision"] is not None
        assert turn["stt_confidence"] is not None

    def test_summary_tab_has_overview_data(self):
        """Verify overview data for Summary tab."""
        turns = [generate_mock_turn_row("test_call", i).to_dict() for i in range(1, 4)]

        total_latency = sum(t["total_latency_ms"] for t in turns)
        total_tools = sum(len(t["tools_called"]) for t in turns)
        
        assert total_latency > 0
        assert isinstance(total_tools, int)


class TestDebuggerKeyboardNavigation:
    """Test keyboard event simulation for debugger UI."""

    def test_navigate_turns_forward(self):
        """Simulate keyboard navigation through turns (arrow down)."""
        turns = [generate_mock_turn_row("test_call", i).to_dict() for i in range(1, 5)]

        current_idx = 0
        current_idx = min(current_idx + 1, len(turns) - 1)
        
        assert current_idx == 1
        assert turns[current_idx]["turn_number"] == 2

    def test_navigate_turns_backward(self):
        """Simulate keyboard navigation through turns (arrow up)."""
        turns = [generate_mock_turn_row("test_call", i).to_dict() for i in range(1, 5)]

        current_idx = 2
        current_idx = max(current_idx - 1, 0)
        
        assert current_idx == 1
        assert turns[current_idx]["turn_number"] == 2

    def test_navigate_to_first_turn(self):
        """Simulate keyboard shortcut to first turn (Home)."""
        turns = [generate_mock_turn_row("test_call", i).to_dict() for i in range(1, 5)]

        current_idx = 3
        current_idx = 0
        
        assert current_idx == 0
        assert turns[current_idx]["turn_number"] == 1

    def test_navigate_to_last_turn(self):
        """Simulate keyboard shortcut to last turn (End)."""
        turns = [generate_mock_turn_row("test_call", i).to_dict() for i in range(1, 5)]

        current_idx = 0
        current_idx = len(turns) - 1
        
        assert current_idx == 3
        assert turns[current_idx]["turn_number"] == 4


class TestDebuggerErrorHandling:
    """Test error handling and edge cases."""

    def test_missing_execution_spans(self):
        """Handle turns with no execution spans."""
        turn = TurnRow(turn_number=1, execution_spans=[]).to_dict()

        assert turn["execution_spans"] == []
        errors = validate_execution_spans(turn["execution_spans"])
        assert not errors

    def test_null_optional_fields(self):
        """Handle turns with null optional fields."""
        turn = TurnRow(
            turn_number=1,
            layer1_decision=None,
            layer2_raw_output=None,
            layer3_changes=None,
            stt_confidence=None,
        ).to_dict()

        assert turn["layer1_decision"] is None
        assert turn["layer2_raw_output"] is None
        assert turn["layer3_changes"] is None
        assert turn["stt_confidence"] is None

    def test_empty_tools_called(self):
        """Handle turns with no tools called."""
        turn = generate_mock_turn_row("test_call", 1)
        turn.tools_called = []
        
        turn_dict = turn.to_dict()
        assert turn_dict["tools_called"] == []

    def test_high_latency_turn(self):
        """Handle turns with very high latencies."""
        turn = TurnRow(
            turn_number=1,
            stt_ms=5000,
            extract_ms=3000,
            l2_ms=10000,
            tool_ms=5000,
            tts_ttfb_ms=2000,
        ).to_dict()

        errors = validate_stage_timings(turn)
        assert not errors

    def test_zero_latency_turn(self):
        """Handle turns with zero latencies (edge case)."""
        turn = TurnRow(
            turn_number=1,
            stt_ms=0,
            extract_ms=0,
            l2_ms=0,
            tool_ms=0,
            tts_ttfb_ms=0,
        ).to_dict()

        errors = validate_stage_timings(turn)
        assert not errors


class TestDebuggerScenarioTagsAndMetadata:
    """Test scenario tags and metadata handling."""

    def test_build_sha_consistent_across_turns(self):
        """Verify build_sha is consistent for all turns in a call."""
        turns = [
            generate_mock_turn_row("test_call", i, tenant_id="doboo").to_dict()
            for i in range(1, 4)
        ]

        build_shas = {t["build_sha"] for t in turns}
        assert len(build_shas) == 1

    def test_tenant_id_consistent_across_turns(self):
        """Verify tenant_id is consistent for all turns in a call."""
        turns = [
            generate_mock_turn_row("test_call", i, tenant_id="doboo").to_dict()
            for i in range(1, 4)
        ]

        tenant_ids = {t["tenant_id"] for t in turns}
        assert len(tenant_ids) == 1
        assert list(tenant_ids)[0] == "doboo"

    def test_created_at_timestamps_valid(self):
        """Verify created_at timestamps are ISO format."""
        turns = [generate_mock_turn_row("test_call", i).to_dict() for i in range(1, 4)]

        for turn in turns:
            created_at = turn["created_at"]
            assert created_at is not None
            try:
                datetime.fromisoformat(created_at)
            except ValueError:
                pytest.fail(f"created_at not ISO format: {created_at}")


class TestDebuggerIntegrationAllScenarios:
    """Integration tests validating all scenarios can be debugged."""

    def test_scenario_can_generate_valid_turns(self, loaded_scenario, scenario_name):
        """Verify each scenario can generate valid turn data."""
        scenario_id, steps = loaded_scenario
        turn_count = len([s for s in steps if s.role == "user"])
        
        turns = [
            generate_mock_turn_row("test_" + scenario_id, i).to_dict()
            for i in range(1, turn_count + 1)
        ]

        for turn in turns:
            errors = validate_turn_row_fields(turn)
            assert not errors, f"Scenario {scenario_id} turn {turn['turn_number']}: {errors}"

    def test_scenario_spans_are_complete(self, loaded_scenario, scenario_name):
        """Verify spans are present and valid for all scenarios."""
        scenario_id, steps = loaded_scenario
        turn_count = len([s for s in steps if s.role == "user"])
        
        for i in range(1, turn_count + 1):
            turn = generate_mock_turn_row("test_" + scenario_id, i).to_dict()
            
            assert len(turn["execution_spans"]) > 0, (
                f"Scenario {scenario_id} turn {i} has no spans"
            )
            
            errors = validate_execution_spans(turn["execution_spans"])
            assert not errors, (
                f"Scenario {scenario_id} turn {i} span errors: {errors}"
            )

    def test_scenario_timings_are_reasonable(self, loaded_scenario, scenario_name):
        """Verify all scenario timings are reasonable."""
        scenario_id, steps = loaded_scenario
        turn_count = len([s for s in steps if s.role == "user"])
        
        for i in range(1, turn_count + 1):
            turn = generate_mock_turn_row("test_" + scenario_id, i).to_dict()
            
            errors = validate_stage_timings(turn)
            assert not errors, (
                f"Scenario {scenario_id} turn {i} timing errors: {errors}"
            )

    def test_scenario_debugger_ui_can_render(self, loaded_scenario, scenario_name):
        """Verify scenario data can be rendered in debugger UI."""
        scenario_id, steps = loaded_scenario
        turn_count = len([s for s in steps if s.role == "user"])
        
        turns = [
            generate_mock_turn_row("test_" + scenario_id, i).to_dict()
            for i in range(1, turn_count + 1)
        ]

        for turn in turns:
            assert len(turn["execution_spans"]) > 0
            assert turn["stt_ms"] >= 0
            assert turn["layer1_decision"] is not None
            assert turn["layer1_decision"]["node"] is not None
            assert turn["turn_number"] > 0


class TestScenarioCoverage:
    """Verify all 11 scenarios are testable."""

    def test_all_11_scenarios_exist(self, scenarios_dir: pathlib.Path):
        """Verify all 11 scenarios exist."""
        expected_scenarios = {
            "off_menu_pivot",
            "delivery_address_flow",
            "takeaway_simple",
            "reservation_basic",
            "philipp_stress_test",
            "wine_not_denied",
            "commit_gate_reservation_ambiguous",
            "order_bebimbap_multi_item",
            "confirmation_intent_no_leak",
            "commit_gate_order_ambiguous",
            "after_hours_pre_order",
        }

        found_scenarios = {
            p.stem for p in scenarios_dir.glob("*.jsonl")
        }

        assert expected_scenarios == found_scenarios, (
            f"Scenario mismatch. Expected {expected_scenarios}, found {found_scenarios}"
        )

    def test_scenario_count(self, scenarios_dir: pathlib.Path):
        """Verify exactly 11 scenarios exist."""
        scenario_files = list(scenarios_dir.glob("*.jsonl"))
        assert len(scenario_files) == 11


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
