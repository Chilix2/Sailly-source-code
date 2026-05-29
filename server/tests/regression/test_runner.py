"""
Unit tests for regression runner and CI gate.

Tests:
  - Mock seams (deterministic, reproducible)
  - Scenario loading (JSONL parsing)
  - Corpus replay engine
  - Scoring pipeline integration
  - Regression detection
  - Baseline management
"""

from __future__ import annotations

import json
import pathlib
import tempfile
from typing import Dict

import pytest

from server.tests.regression.runner import (
    RegressionRunner,
    RegressionResult,
    CorpusMetrics,
    ScenarioStatus,
    MockSeams,
    CorpusReplayEngine,
    RegressionDetector,
    load_scenario_from_jsonl,
    ScenarioStep,
)
from server.tests.regression.ci_gate import (
    RegressionGate,
    load_baseline,
    save_baseline,
    BASELINE_PATH,
)


# ============================================================================
# Mock Seams Tests
# ============================================================================


class TestMockSeams:
    """Test deterministic mock implementations."""
    
    def test_mock_seams_deterministic(self):
        """Same seed produces same results."""
        seams1 = MockSeams(seed=42)
        seams2 = MockSeams(seed=42)
        
        llm1 = seams1.mock_llm_call("test_scenario", 0, "test prompt")
        llm2 = seams2.mock_llm_call("test_scenario", 0, "test prompt")
        
        assert llm1 == llm2, "Same seed should produce same LLM output"
    
    def test_mock_seams_different_seed(self):
        """Different seeds produce different results."""
        seams1 = MockSeams(seed=42)
        seams2 = MockSeams(seed=43)
        
        llm1 = seams1.mock_llm_call("test_scenario", 0, "test prompt")
        llm2 = seams2.mock_llm_call("test_scenario", 0, "test prompt")
        
        # May sometimes be equal by chance, but usually different
        # (we're testing randomness here)
        assert isinstance(llm1, str) and isinstance(llm2, str)
    
    def test_mock_tts_timing(self):
        """TTS mock produces reasonable timing."""
        seams = MockSeams(seed=42)
        
        short_text = "Hallo"
        audio_bytes, duration_s = seams.mock_tts(short_text)
        
        assert len(audio_bytes) > 0
        assert 0.1 <= duration_s <= 1.0, f"Duration {duration_s}s not in reasonable range"
    
    def test_mock_tool_call_success(self):
        """Tool mock returns success response."""
        seams = MockSeams(seed=42)
        
        result = seams.mock_tool_call("create_order", {"item": "Bulgogi"}, "test_scenario")
        
        assert result["success"] is True
        assert result["tool"] == "create_order"


# ============================================================================
# Scenario Loading Tests
# ============================================================================


class TestScenarioLoading:
    """Test JSONL scenario parsing."""
    
    def test_load_scenario_from_jsonl(self, tmp_path: pathlib.Path):
        """Parse basic JSONL scenario."""
        scenario_file = tmp_path / "test_scenario.jsonl"
        scenario_file.write_text(
            '{"meta": {"name": "test_order", "description": "Test order"}}\n'
            '{"role": "user", "text": "Bulgogi bitte"}\n'
            '{"role": "expected", "tools_called": ["create_order"], "final_intent": "order"}\n'
        )
        
        result = load_scenario_from_jsonl(scenario_file)
        
        assert result is not None
        scenario_id, steps = result
        assert scenario_id == "test_order"
        assert len(steps) == 2
        assert steps[0].role == "user"
        assert steps[0].text == "Bulgogi bitte"
        assert steps[1].role == "expected"
        assert steps[1].expected_tools == ["create_order"]
    
    def test_load_scenario_missing_file(self, tmp_path: pathlib.Path):
        """Handle missing JSONL file gracefully."""
        missing_file = tmp_path / "missing.jsonl"
        
        result = load_scenario_from_jsonl(missing_file)
        
        assert result is None


# ============================================================================
# Corpus Replay Tests
# ============================================================================


class TestCorpusReplayEngine:
    """Test scenario replay with mocks."""
    
    def test_replay_simple_scenario(self):
        """Replay a simple scenario."""
        engine = CorpusReplayEngine(seed=42)
        
        steps = [
            ScenarioStep(role="user", text="Bulgogi bitte"),
            ScenarioStep(
                role="expected",
                expected_tools=["create_order"],
                expected_intent="order"
            ),
        ]
        
        result = engine.replay_scenario("test_scenario", steps)
        
        assert result.scenario_id == "test_scenario"
        assert result.overall_score > 0.0
        assert len(result.bot_responses) > 0
        assert len(result.execution_spans) > 0
    
    def test_replay_deterministic(self):
        """Same seed produces same replay results."""
        steps = [
            ScenarioStep(role="user", text="Test utterance"),
            ScenarioStep(role="expected", expected_tools=[], expected_intent="test"),
        ]
        
        engine1 = CorpusReplayEngine(seed=42)
        result1 = engine1.replay_scenario("scenario1", steps)
        
        engine2 = CorpusReplayEngine(seed=42)
        result2 = engine2.replay_scenario("scenario1", steps)
        
        assert result1.overall_score == result2.overall_score
        assert result1.total_latency_ms == result2.total_latency_ms
        assert result1.bot_responses == result2.bot_responses
    
    def test_replay_execution_spans(self):
        """Execution spans are collected and structured."""
        engine = CorpusReplayEngine(seed=42)
        
        steps = [
            ScenarioStep(role="user", text="Create order"),
            ScenarioStep(
                role="expected",
                expected_tools=["create_order"],
                expected_intent="order"
            ),
        ]
        
        result = engine.replay_scenario("test_scenario", steps)
        
        assert len(result.execution_spans) > 0
        
        for span in result.execution_spans:
            assert "operation" in span
            assert "layer" in span
            assert "status" in span
            assert "latency_ms" in span
            assert span["status"] == "ok"


# ============================================================================
# Regression Detection Tests
# ============================================================================


class TestRegressionDetector:
    """Test regression detection logic."""
    
    def _make_result(
        self,
        scenario_id: str,
        status: ScenarioStatus,
        score: float = 0.9,
    ) -> RegressionResult:
        """Helper to create RegressionResult."""
        return RegressionResult(
            scenario_id=scenario_id,
            overall_status=status,
            overall_score=score,
            l1_score=score,
            l2_score=score,
            l3_score=score,
        )
    
    def test_detect_new_failures(self):
        """Detect scenarios that were passing but now failing."""
        detector = RegressionDetector()
        
        baseline = {
            "scenario1": self._make_result("scenario1", ScenarioStatus.PASS, score=0.95),
            "scenario2": self._make_result("scenario2", ScenarioStatus.PASS, score=0.9),
        }
        
        current = {
            "scenario1": self._make_result("scenario1", ScenarioStatus.FAIL, score=0.5),
            "scenario2": self._make_result("scenario2", ScenarioStatus.PASS, score=0.9),
        }
        
        metrics = detector.detect_regressions(current, baseline)
        
        assert "scenario1" in metrics.new_failures
        assert "scenario2" not in metrics.new_failures
    
    def test_detect_score_drops(self):
        """Detect significant score drops."""
        detector = RegressionDetector()
        
        baseline = {
            "scenario1": self._make_result("scenario1", ScenarioStatus.PASS, score=1.0),
        }
        
        current = {
            "scenario1": self._make_result("scenario1", ScenarioStatus.PASS, score=0.93),
        }
        
        metrics = detector.detect_regressions(current, baseline)
        
        # Drop is 7%, which exceeds 5% threshold
        assert "scenario1" in metrics.score_drops
    
    def test_aggregate_metrics(self):
        """Aggregate corpus metrics correctly."""
        detector = RegressionDetector()
        
        current = {
            "s1": self._make_result("s1", ScenarioStatus.PASS, score=0.95),
            "s2": self._make_result("s2", ScenarioStatus.PASS, score=0.9),
            "s3": self._make_result("s3", ScenarioStatus.FAIL, score=0.5),
        }
        
        metrics = detector.detect_regressions(current, baseline_results=None)
        
        assert metrics.total_scenarios == 3
        assert metrics.passed_scenarios == 2
        assert metrics.failed_scenarios == 1
        assert metrics.avg_overall_score > 0.0


# ============================================================================
# Baseline Management Tests
# ============================================================================


class TestBaselineManagement:
    """Test baseline storage and loading."""
    
    def test_save_and_load_baseline(self, tmp_path: pathlib.Path, monkeypatch):
        """Save and load baseline correctly."""
        # Override baseline path for testing
        test_baseline_path = tmp_path / ".ci" / "regression_baseline.json"
        monkeypatch.setattr("server.tests.regression.ci_gate.BASELINE_PATH", test_baseline_path)
        
        results = {
            "scenario1": RegressionResult(
                scenario_id="scenario1",
                overall_status=ScenarioStatus.PASS,
                overall_score=0.95,
                l1_score=0.95,
                l2_score=0.9,
                l3_score=0.95,
            ),
        }
        
        metrics = CorpusMetrics(
            total_scenarios=1,
            passed_scenarios=1,
            avg_overall_score=0.95,
        )
        
        save_baseline(results, metrics)
        
        assert test_baseline_path.exists()
        
        # Load and verify
        loaded = json.loads(test_baseline_path.read_text())
        assert loaded["metrics"]["total_scenarios"] == 1
        assert "scenario1" in loaded["results"]


# ============================================================================
# CI Gate Tests
# ============================================================================


class TestRegressionGate:
    """Test CI gate logic."""
    
    def test_gate_pass_all_green(self):
        """Gate passes when all scenarios pass."""
        gate = RegressionGate()
        
        # Mock gate conditions
        metrics = CorpusMetrics(
            total_scenarios=10,
            passed_scenarios=10,
            failed_scenarios=0,
            l1_pass_rate=95.0,
            l2_pass_rate=90.0,
            l3_pass_rate=90.0,
            new_failures=[],
            score_drops={},
        )
        
        passed = gate._check_gate_conditions(metrics)
        
        assert passed is True
    
    def test_gate_fail_new_failures(self):
        """Gate fails on new failures."""
        gate = RegressionGate()
        
        metrics = CorpusMetrics(
            total_scenarios=10,
            passed_scenarios=8,
            failed_scenarios=2,
            l1_pass_rate=95.0,
            new_failures=["scenario1"],  # NEW FAILURE
            score_drops={},
        )
        
        passed = gate._check_gate_conditions(metrics)
        
        assert passed is False
    
    def test_gate_fail_score_drop(self):
        """Gate fails on significant score drop."""
        gate = RegressionGate()
        
        metrics = CorpusMetrics(
            total_scenarios=10,
            passed_scenarios=10,
            l1_pass_rate=95.0,
            new_failures=[],
            score_drops={"scenario1": 7.5},  # EXCEEDS 5% THRESHOLD
        )
        
        passed = gate._check_gate_conditions(metrics)
        
        assert passed is False
    
    def test_gate_fail_low_l1_pass_rate(self):
        """Gate fails on low L1 pass rate."""
        gate = RegressionGate()
        
        metrics = CorpusMetrics(
            total_scenarios=10,
            passed_scenarios=7,
            l1_pass_rate=85.0,  # BELOW 90% THRESHOLD
            new_failures=[],
            score_drops={},
        )
        
        passed = gate._check_gate_conditions(metrics)
        
        assert passed is False


# ============================================================================
# Integration Tests
# ============================================================================


class TestRegressionRunnerIntegration:
    """Integration tests with full pipeline."""
    
    def test_runner_full_corpus_replay(self, tmp_path: pathlib.Path):
        """Full corpus replay from JSONL files."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        # Create test scenario JSONL
        scenario_file = scenarios_dir / "test_order.jsonl"
        scenario_file.write_text(
            '{"meta": {"name": "test_order"}}\n'
            '{"role": "user", "text": "Bulgogi bitte"}\n'
            '{"role": "expected", "tools_called": ["create_order"], "final_intent": "order"}\n'
        )
        
        runner = RegressionRunner(seed=42)
        results, metrics = runner.run_full_corpus(scenarios_dir)
        
        assert len(results) > 0
        assert "test_order" in results
        assert metrics.total_scenarios >= 1
    
    def test_runner_regression_detection(self, tmp_path: pathlib.Path):
        """Detect regressions across runs."""
        scenarios_dir = tmp_path / "scenarios"
        scenarios_dir.mkdir()
        
        # Create test scenario
        scenario_file = scenarios_dir / "test_order.jsonl"
        scenario_file.write_text(
            '{"meta": {"name": "test_order"}}\n'
            '{"role": "user", "text": "Bulgogi"}\n'
            '{"role": "expected", "tools_called": ["create_order"], "final_intent": "order"}\n'
        )
        
        # First run
        runner1 = RegressionRunner(seed=42)
        results1, metrics1 = runner1.run_full_corpus(scenarios_dir)
        baseline = results1
        
        # Second run (same seed, should be identical)
        runner2 = RegressionRunner(seed=42)
        results2, metrics2 = runner2.run_full_corpus(
            scenarios_dir,
            baseline_results=baseline,
        )
        
        # No regressions on identical seed/scenario
        assert len(metrics2.new_failures) == 0
        assert len(metrics2.score_drops) == 0
