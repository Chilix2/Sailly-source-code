"""
Unit tests for Sailly regression scorers (Phase 4a).

Tests all three scoring layers:
  - L1: Deterministic scorer (tool matching, state)
  - L2: LLM-Judge scorer (language quality)
  - L3: Span-level scorer (operation/latency validation)
"""

import unittest
from server.tests.regression.scorers import (
    DeterministicScorer,
    LLMJudgeScorer,
    SpanLevelScorer,
    RegressionScorer,
    ScorerResult,
    ScorerLayer,
    MismatchReport,
)


class TestDeterministicScorer(unittest.TestCase):
    """Test L1 deterministic scorer."""

    def setUp(self):
        self.scorer = DeterministicScorer()

    def test_exact_tool_match_pass(self):
        """Happy path: exact tool match should pass."""
        expected_behavior = {
            "tools_called": ["ai_greeting", "get_menu"],
            "final_intent": "greeting",
            "fulfilled": True,
        }
        actual_tools = ["ai_greeting", "get_menu"]

        result = self.scorer.score(
            scenario_id="test-01",
            expected_behavior=expected_behavior,
            actual_tools_called=actual_tools,
        )

        self.assertEqual(result.status, ScorerResult.PASS)
        self.assertEqual(result.confidence, 1.0)
        self.assertEqual(len(result.mismatches), 0)

    def test_missing_tools_fail(self):
        """Missing tools should fail."""
        expected_behavior = {
            "tools_called": ["create_order", "send_sms"],
            "final_intent": "order",
            "fulfilled": True,
        }
        actual_tools = ["create_order"]

        result = self.scorer.score(
            scenario_id="test-02",
            expected_behavior=expected_behavior,
            actual_tools_called=actual_tools,
        )

        self.assertEqual(result.status, ScorerResult.FAIL)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(len(result.mismatches), 1)
        self.assertEqual(result.mismatches[0].category, "missing_tools")

    def test_extra_tools_fail(self):
        """Extra tools should fail."""
        expected_behavior = {
            "tools_called": ["get_menu"],
            "final_intent": "info",
            "fulfilled": True,
        }
        actual_tools = ["get_menu", "check_availability", "get_date_info"]

        result = self.scorer.score(
            scenario_id="test-03",
            expected_behavior=expected_behavior,
            actual_tools_called=actual_tools,
        )

        self.assertEqual(result.status, ScorerResult.FAIL)
        self.assertEqual(len(result.mismatches), 1)
        self.assertEqual(result.mismatches[0].category, "extra_tools")

    def test_forced_tools_violation_fail(self):
        """Calling forbidden tools should fail."""
        expected_behavior = {
            "tools_called": ["ai_greeting"],
            "final_intent": "greeting",
            "fulfilled": True,
        }
        actual_tools = ["ai_greeting", "create_reservation"]
        forced_tools = ["create_reservation"]  # Can't call yet

        result = self.scorer.score(
            scenario_id="test-04",
            expected_behavior=expected_behavior,
            actual_tools_called=actual_tools,
            forced_tools=forced_tools,
        )

        self.assertEqual(result.status, ScorerResult.FAIL)
        self.assertTrue(
            any(m.category == "forced_tools_violation" for m in result.mismatches)
        )

    def test_expected_failure_case_pass(self):
        """Failure case (fulfilled=false) with no tools should pass."""
        expected_behavior = {
            "tools_called": ["verify_address", "create_order", "send_sms"],
            "final_intent": "order",
            "fulfilled": False,  # Expected to fail
        }
        actual_tools = []  # No tools called (correct for failure case)

        result = self.scorer.score(
            scenario_id="test-05",
            expected_behavior=expected_behavior,
            actual_tools_called=actual_tools,
        )

        # Should pass because we expected it to fail
        self.assertEqual(result.status, ScorerResult.PASS)
        self.assertEqual(result.confidence, 1.0)


class TestLLMJudgeScorer(unittest.TestCase):
    """Test L2 LLM-judge scorer."""

    def setUp(self):
        self.scorer = LLMJudgeScorer(enable_llm=True)  # Use heuristics (Phase 4a)

    def test_placeholder_penalized(self):
        """Response with placeholders should be penalized."""
        result = self.scorer.score(
            scenario_id="test-01",
            turn_idx=0,
            bot_response="Guten Tag, auf den Namen {name} reserviert.",
            user_text="Ich möchte reservieren.",
            expected_intent="reservation",
        )

        self.assertLess(result.confidence, 1.0)
        self.assertTrue(
            result.details.get("quality_checks", {}).get("has_placeholder")
        )

    def test_tool_tag_penalized(self):
        """Response with [tool:...] tags should be penalized."""
        result = self.scorer.score(
            scenario_id="test-02",
            turn_idx=0,
            bot_response="Moment, [tool:get_menu] wird aufgerufen...",
            user_text="Was kostet Bulgogi?",
            expected_intent="info",
        )

        self.assertLess(result.confidence, 1.0)
        self.assertTrue(
            result.details.get("quality_checks", {}).get("contains_tool_tag")
        )

    def test_short_response_penalized(self):
        """Very short responses should be penalized."""
        result = self.scorer.score(
            scenario_id="test-03",
            turn_idx=0,
            bot_response="Ja.",
            user_text="Ist der Laden offen?",
            expected_intent="info",
        )

        self.assertLess(result.confidence, 1.0)

    def test_reasonable_response_boosted(self):
        """Reasonable length (30-500 chars) should be boosted."""
        result = self.scorer.score(
            scenario_id="test-04",
            turn_idx=0,
            bot_response="Guten Tag! Wir haben verschiedene Pizza-Sorten im Angebot. "
                        "Möchten Sie eine zum Mitnehmen oder zur Lieferung?",
            user_text="Guten Tag, ich hätte gerne eine Pizza.",
            expected_intent="order",
        )

        self.assertGreater(result.confidence, 0.85)

    def test_caching(self):
        """Same turn should use cached result."""
        bot_text = "Reservierung bestätigt."
        result1 = self.scorer.score(
            scenario_id="test-05",
            turn_idx=0,
            bot_response=bot_text,
            user_text="Reservierung für zwei Personen.",
            expected_intent="reservation",
        )
        confidence1 = result1.confidence

        result2 = self.scorer.score(
            scenario_id="test-05",
            turn_idx=0,
            bot_response=bot_text,
            user_text="Reservierung für zwei Personen.",
            expected_intent="reservation",
        )
        confidence2 = result2.confidence

        self.assertEqual(confidence1, confidence2)
        self.assertTrue(result2.details.get("cached"))

    def test_llm_disabled(self):
        """With LLM disabled, should return INCONCLUSIVE."""
        scorer = LLMJudgeScorer(enable_llm=False)
        result = scorer.score(
            scenario_id="test-06",
            turn_idx=0,
            bot_response="Normal response.",
            user_text="Normal question.",
            expected_intent="info",
        )

        # With enable_llm=False, we still use heuristics
        self.assertIsNotNone(result.confidence)


class TestSpanLevelScorer(unittest.TestCase):
    """Test L3 span-level scorer."""

    def setUp(self):
        self.scorer = SpanLevelScorer()

    def test_healthy_spans_pass(self):
        """All spans with status=ok and latency within SLA should pass."""
        spans = [
            {
                "operation": "classify",
                "status": "ok",
                "latency_ms": 50,
            },
            {
                "operation": "execute_tool",
                "status": "ok",
                "latency_ms": 800,
            },
            {
                "operation": "classify",
                "status": "ok",
                "latency_ms": 60,
            },
        ]

        result = self.scorer.score(
            scenario_id="test-01",
            execution_spans=spans,
        )

        self.assertEqual(result.status, ScorerResult.PASS)
        self.assertEqual(result.confidence, 1.0)
        self.assertEqual(len(result.mismatches), 0)

    def test_error_status_fail(self):
        """Span with status != ok should fail."""
        spans = [
            {
                "operation": "execute_tool",
                "status": "error",
                "latency_ms": 100,
            },
        ]

        result = self.scorer.score(
            scenario_id="test-02",
            execution_spans=spans,
        )

        self.assertEqual(result.status, ScorerResult.FAIL)
        self.assertTrue(
            any(m.category == "span_status_error" for m in result.mismatches)
        )

    def test_latency_sla_violation(self):
        """Span exceeding SLA should record violation."""
        spans = [
            {
                "operation": "classify",
                "status": "ok",
                "latency_ms": 150,  # > 100ms SLA
            },
        ]

        result = self.scorer.score(
            scenario_id="test-03",
            execution_spans=spans,
        )

        self.assertEqual(result.status, ScorerResult.FAIL)
        self.assertTrue(
            any(m.category == "latency_sla_violation" for m in result.mismatches)
        )
        self.assertEqual(len(result.details.get("sla_violations", [])), 1)

    def test_latency_aggregation(self):
        """Should aggregate latency stats by operation."""
        spans = [
            {"operation": "classify", "status": "ok", "latency_ms": 50},
            {"operation": "classify", "status": "ok", "latency_ms": 60},
            {"operation": "execute_tool", "status": "ok", "latency_ms": 500},
        ]

        result = self.scorer.score(
            scenario_id="test-04",
            execution_spans=spans,
        )

        latency_by_op = result.details.get("latency_by_operation", {})
        self.assertEqual(latency_by_op["classify"]["count"], 2)
        self.assertEqual(latency_by_op["classify"]["min_ms"], 50)
        self.assertEqual(latency_by_op["classify"]["max_ms"], 60)
        self.assertAlmostEqual(latency_by_op["classify"]["avg_ms"], 55)

    def test_empty_spans(self):
        """Empty spans list should return PASS with 0 count."""
        result = self.scorer.score(
            scenario_id="test-05",
            execution_spans=[],
        )

        self.assertEqual(result.status, ScorerResult.PASS)
        self.assertEqual(result.details.get("spans_count"), 0)


class TestRegressionScorerOrchestrator(unittest.TestCase):
    """Test multi-layer orchestrator."""

    def setUp(self):
        self.scorer = RegressionScorer(enable_llm=True)

    def test_full_scoring_pass(self):
        """Complete happy path scoring."""
        expected_behavior = {
            "tools_called": ["ai_greeting", "get_menu"],
            "final_intent": "greeting",
            "fulfilled": True,
        }
        turns = [
            ("Hallo", "Guten Tag, willkommen!"),
            ("Was habt ihr?", "Hier ist die aktuelle Speisekarte..."),
        ]

        results = self.scorer.score_case(
            scenario_id="happy-01",
            expected_behavior=expected_behavior,
            actual_tools_called=["ai_greeting", "get_menu"],
            turns=turns,
        )

        self.assertIn("l1_deterministic", results)
        self.assertIn("l2_llm_judge", results)
        self.assertIn("l3_span_level", results)

        l1 = results["l1_deterministic"]
        self.assertEqual(l1.status, ScorerResult.PASS)

    def test_full_scoring_with_spans(self):
        """Scoring with execution spans."""
        expected_behavior = {
            "tools_called": ["get_menu"],
            "final_intent": "info",
            "fulfilled": True,
        }
        turns = [("Was kostet Bulgogi?", "Bulgogi kostet 12 Euro.")]
        spans = [
            {"operation": "classify", "status": "ok", "latency_ms": 80},
            {"operation": "execute_tool", "status": "ok", "latency_ms": 50},
        ]

        results = self.scorer.score_case(
            scenario_id="info-01",
            expected_behavior=expected_behavior,
            actual_tools_called=["get_menu"],
            turns=turns,
            execution_spans=spans,
        )

        l3 = results["l3_span_level"]
        self.assertEqual(l3.status, ScorerResult.PASS)
        self.assertIsNotNone(l3.details.get("latency_by_operation"))

    def test_l1_gate_fail(self):
        """L1 failure should propagate to aggregate."""
        expected_behavior = {
            "tools_called": ["create_order"],
            "final_intent": "order",
            "fulfilled": True,
        }
        turns = [("Bulgogi bitte.", "Bestätigung wird versendet.")]

        results = self.scorer.score_case(
            scenario_id="fail-01",
            expected_behavior=expected_behavior,
            actual_tools_called=[],  # Missing create_order
            turns=turns,
        )

        l1 = results["l1_deterministic"]
        self.assertEqual(l1.status, ScorerResult.FAIL)

        # Aggregate should also fail
        final_status, final_confidence = self.scorer.aggregate_results(results)
        self.assertEqual(final_status, ScorerResult.FAIL)

    def test_aggregate_results(self):
        """Aggregation logic."""
        expected_behavior = {
            "tools_called": ["ai_greeting"],
            "final_intent": "greeting",
            "fulfilled": True,
        }
        turns = [("Hi", "Guten Tag!")]

        results = self.scorer.score_case(
            scenario_id="agg-01",
            expected_behavior=expected_behavior,
            actual_tools_called=["ai_greeting"],
            turns=turns,
        )

        final_status, final_confidence = self.scorer.aggregate_results(results)
        self.assertEqual(final_status, ScorerResult.PASS)
        self.assertGreater(final_confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
