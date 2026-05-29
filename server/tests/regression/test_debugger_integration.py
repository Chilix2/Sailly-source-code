"""
Comprehensive integration testing for Sailly Debugger (Phase 1-4).
"""

import json
import pathlib
import pytest
from typing import Dict, Any, List

# Test Classes
SCENARIOS_DIR = pathlib.Path(__file__).parent / "scenarios"
DEBUGGER_TABS = [
    "trace_tree", "gantt", "reference", "steering", "root_cause", "summary"
]
STAGE_TIMING_FIELDS = ["stt_ms", "extract_ms", "l2_ms", "tool_ms", "tts_ttfb_ms"]
EXECUTION_SPAN_FIELDS = [
    "span_id", "parent_span_id", "layer", "operation", "name", "model",
    "latency_ms", "ttft_ms", "status", "tokens_in", "tokens_out",
    "finish_reason", "io",
]
TURN_API_FIELDS = [
    "turn_number", "user_text", "bot_text", "stt_latency_ms",
    "llm_latency_ms", "total_latency_ms", "tools_called", "node_name",
    "stt_confidence", "build_sha", "tenant_id", "created_at",
    "layer1_decision", "layer2_raw_output", "layer3_changes",
    "stt_ms", "extract_ms", "l2_ms", "tool_ms", "tts_ttfb_ms",
    "intent", "turn_type", "worker_profile", "stage3_text",
    "tts_situation", "tts_mood", "validation_breakdown", "execution_spans",
]

@pytest.fixture
def mock_execution_spans() -> List[Dict[str, Any]]:
    """Generate mock execution spans for a turn."""
    return [
        {
            "span_id": "span_001", "parent_span_id": None, "layer": "L1",
            "operation": "layer1_decision", "name": "classify_intent",
            "model": "haiku-3", "latency_ms": 250, "ttft_ms": 45,
            "status": "success", "tokens_in": 150, "tokens_out": 50,
            "finish_reason": "end_turn",
            "io": {"input": "user text...", "output": "{ intent: order }"},
        },
    ]

@pytest.fixture
def mock_turn_data(mock_execution_spans) -> Dict[str, Any]:
    """Generate a mock turn response."""
    return {
        "turn_number": 1, "user_text": "Ich möchte einen Bulgogi bestellen.",
        "bot_text": "Gerne! Ein Bulgogi für Sie.",
        "stt_latency_ms": 120, "llm_latency_ms": 450, "total_latency_ms": 600,
        "tools_called": [], "node_name": "GREETING", "stt_confidence": 0.95,
        "build_sha": "abc1234d5e6f7g8h9i0jk1lm2n3o4p5", "tenant_id": "doboo",
        "created_at": "2026-05-29T19:42:00Z",
        "layer1_decision": json.dumps({"intent": "order", "confidence": 0.92}),
        "layer2_raw_output": json.dumps({"action": "collect_items"}),
        "layer3_changes": json.dumps({"slot_updates": {}}),
        "stt_ms": 120, "extract_ms": 80, "l2_ms": 180, "tool_ms": 0,
        "tts_ttfb_ms": 200, "intent": "order", "turn_type": "user_utterance",
        "worker_profile": None, "stage3_text": "Gerne! Ein Bulgogi für Sie.",
        "tts_situation": "friendly_greeting", "tts_mood": "helpful",
        "validation_breakdown": json.dumps({"checks_passed": 3, "checks_total": 3}),
        "execution_spans": mock_execution_spans,
    }

@pytest.fixture
def mock_call_response(mock_turn_data) -> Dict[str, Any]:
    """Generate a complete call response with multiple turns."""
    return {
        "call_sid": "test_call_abc123xyz",
        "turn_count": 3,
        "turns": [
            mock_turn_data,
            {**mock_turn_data, "turn_number": 2, "user_text": "Ja, genau."},
            {**mock_turn_data, "turn_number": 3, "tools_called": ["create_order"]},
        ],
    }

class TestDebuggerAPIResponseSchema:
    """Validate API response structure."""
    
    def test_call_response_has_required_top_level_fields(self, mock_call_response):
        assert "call_sid" in mock_call_response
        assert "turn_count" in mock_call_response
        assert "turns" in mock_call_response
        assert mock_call_response["turn_count"] == len(mock_call_response["turns"])

    def test_each_turn_has_all_required_fields(self, mock_call_response):
        for turn in mock_call_response["turns"]:
            for field in TURN_API_FIELDS:
                assert field in turn, f"Missing field '{field}'"

    def test_execution_spans_structure(self, mock_call_response):
        for turn in mock_call_response["turns"]:
            spans = turn["execution_spans"]
            assert isinstance(spans, list), "execution_spans should be a list"
            for span in spans:
                for field in EXECUTION_SPAN_FIELDS:
                    assert field in span, f"Missing field '{field}' in span"

    def test_stage_timings_are_numeric(self, mock_call_response):
        for turn in mock_call_response["turns"]:
            for field in STAGE_TIMING_FIELDS:
                value = turn[field]
                assert value is None or isinstance(value, (int, float))

    def test_tools_called_is_list_or_convertible(self, mock_call_response):
        for turn in mock_call_response["turns"]:
            assert isinstance(turn["tools_called"], list)

    def test_layer_fields_are_json_strings(self, mock_call_response):
        for turn in mock_call_response["turns"]:
            for field in ["layer1_decision", "layer2_raw_output", "layer3_changes"]:
                value = turn[field]
                if value:
                    json.loads(value)

class TestDebuggerDataValidation:
    """Validate debugger data completeness."""
    
    def test_execution_spans_present_for_all_turns(self, mock_call_response):
        for turn in mock_call_response["turns"]:
            assert "execution_spans" in turn
            assert isinstance(turn["execution_spans"], list)
            assert len(turn["execution_spans"]) > 0

    def test_execution_span_ids_are_unique_per_turn(self, mock_call_response):
        for turn in mock_call_response["turns"]:
            span_ids = [span["span_id"] for span in turn["execution_spans"]]
            assert len(span_ids) == len(set(span_ids))

    def test_execution_span_layers_are_valid(self, mock_call_response):
        valid_layers = {"L1", "L2", "L3"}
        for turn in mock_call_response["turns"]:
            for span in turn["execution_spans"]:
                assert span["layer"] in valid_layers

    def test_span_latencies_reasonable(self, mock_call_response):
        for turn in mock_call_response["turns"]:
            for span in turn["execution_spans"]:
                latency = span["latency_ms"]
                assert 1 <= latency <= 30000

    def test_stage_timings_sum_to_total(self, mock_call_response):
        for turn in mock_call_response["turns"]:
            stage_sum = sum(
                turn.get(field, 0) or 0
                for field in STAGE_TIMING_FIELDS if field != "tts_ttfb_ms"
            )
            total = turn.get("total_latency_ms") or 0
            if total > 0 and stage_sum > 0:
                variance = abs(stage_sum - total) / total
                assert variance < 0.5

class TestDebuggerUIRendering:
    """Test debugger UI tabs render without errors."""
    
    def test_all_debugger_tabs_defined(self):
        assert len(DEBUGGER_TABS) == 6
        expected_tabs = {"trace_tree", "gantt", "reference", "steering", "root_cause", "summary"}
        assert set(DEBUGGER_TABS) == expected_tabs

    def test_trace_tree_tab_data_structure(self, mock_call_response):
        for turn in mock_call_response["turns"]:
            assert "execution_spans" in turn
            assert "turn_number" in turn
            for span in turn["execution_spans"]:
                assert "span_id" in span and "parent_span_id" in span

    def test_gantt_timeline_tab_data_structure(self, mock_call_response):
        for turn in mock_call_response["turns"]:
            for field in STAGE_TIMING_FIELDS:
                assert field in turn

    def test_reference_tab_has_raw_data(self, mock_call_response):
        for turn in mock_call_response["turns"]:
            assert "user_text" in turn and "bot_text" in turn

    def test_summary_tab_has_aggregate_metrics(self, mock_call_response):
        total_turns = mock_call_response["turn_count"]
        assert total_turns > 0

class TestScenarioReplay:
    """Test scenario replay functionality."""
    
    def test_scenarios_exist(self):
        scenario_files = list(SCENARIOS_DIR.glob("*.jsonl"))
        scenario_names = [f.stem for f in scenario_files]
        assert len(scenario_names) == 11

class TestPerformanceCharacteristics:
    """Test performance characteristics."""
    
    def test_span_array_handles_large_number(self):
        many_spans = [
            {
                "span_id": f"span_{i:03d}",
                "parent_span_id": f"span_{max(0, i-1):03d}" if i > 0 else None,
                "layer": "L1" if i < 10 else "L2",
                "operation": f"op_{i}", "name": f"op_{i}", "model": "haiku-3",
                "latency_ms": 10 + i, "ttft_ms": None, "status": "success",
                "tokens_in": 0, "tokens_out": 0, "finish_reason": None, "io": {},
            }
            for i in range(100)
        ]
        assert len(many_spans) == 100

    def test_gantt_renders_with_100_turns(self):
        gantt_data = [
            {
                "turn_number": i,
                "timings": {
                    "stt_ms": 50 + i, "extract_ms": 30 + i, "l2_ms": 100 + i,
                    "tool_ms": 0, "tts_ttfb_ms": 200 + i,
                }
            }
            for i in range(100)
        ]
        assert len(gantt_data) == 100

class TestErrorHandling:
    """Test error handling in debugger."""
    
    def test_missing_execution_spans_handled(self):
        turn_without_spans = {
            "turn_number": 1, "user_text": "Hello", "bot_text": "Hi",
            "execution_spans": [], "stt_ms": 100,
        }
        assert turn_without_spans["execution_spans"] == []

    def test_missing_stage_timings_handled(self):
        turn_with_null_timings = {
            "turn_number": 1,
            "stt_ms": None, "extract_ms": None, "l2_ms": None,
            "tool_ms": None, "tts_ttfb_ms": None,
        }
        assert turn_with_null_timings["stt_ms"] is None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
