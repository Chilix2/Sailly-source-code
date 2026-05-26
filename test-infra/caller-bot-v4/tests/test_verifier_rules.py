"""
tests/test_verifier_rules.py — Unit tests for verifier rules
"""
import unittest
from src.verifier import (
    Verifier,
    VerificationResult,
    is_confirmation,
    _PLACEHOLDER_RE,
    _LEGACY_RE,
)


class TestConfirmationDetection(unittest.TestCase):
    def test_confirmation_positive(self):
        self.assertTrue(is_confirmation("Ja, genau."))
        self.assertTrue(is_confirmation("Passt so."))
        self.assertTrue(is_confirmation("Ja bitte."))

    def test_confirmation_negative(self):
        self.assertFalse(is_confirmation("Nein, so nicht."))
        self.assertFalse(is_confirmation("Nein, das stimmt nicht."))
        self.assertFalse(is_confirmation("Warte, ich meinte etwas anderes."))

    def test_confirmation_ambiguous(self):
        self.assertTrue(is_confirmation("Alles klar, ja."))
        self.assertFalse(is_confirmation("Nein, alles klar."))


class TestPlaceholderDetection(unittest.TestCase):
    def test_placeholder_name(self):
        self.assertIsNotNone(_PLACEHOLDER_RE.search("Ihrem Namen"))
        self.assertIsNotNone(_PLACEHOLDER_RE.search("Auf den Namen {name}"))

    def test_placeholder_date_time(self):
        self.assertIsNotNone(_PLACEHOLDER_RE.search("für {date} um {time}"))

    def test_no_placeholder(self):
        self.assertIsNone(_PLACEHOLDER_RE.search("Auf den Namen Müller"))


class TestLegacyDetection(unittest.TestCase):
    def test_legacy_tool_tag(self):
        self.assertIsNotNone(_LEGACY_RE.search("[TOOL:create_reservation]"))

    def test_legacy_tier2_runner(self):
        self.assertIsNotNone(_LEGACY_RE.search("tier2_runner.call_gemini_stream"))

    def test_no_legacy(self):
        self.assertIsNone(_LEGACY_RE.search("v4_pipeline.process_turn"))


class TestVerifierRules(unittest.TestCase):
    def test_rule_1_false_claim(self):
        """Rule 1: False success claim without commit."""
        verifier = Verifier()
        result = VerificationResult(scenario_id="test", call_sid="test-123")

        bot_responses = ["Ihre Reservierung ist bestätigt!"]
        tools_fired = [[]]  # No tools fired

        verifier._rule_1_no_false_claim(result, bot_responses, tools_fired)
        self.assertFalse(result.passed)
        self.assertTrue(any("Rule 1" in f for f in result.failures))

    def test_rule_3_placeholder(self):
        """Rule 3: Placeholder detection."""
        verifier = Verifier()
        result = VerificationResult(scenario_id="test", call_sid="test-123")

        bot_text = "Reservierung auf den Namen {name} bestätigt."
        verifier._rule_3_no_placeholder_text(result, bot_text)
        self.assertFalse(result.passed)

    def test_rule_4_legacy_tag(self):
        """Rule 4: Legacy tag detection."""
        verifier = Verifier()
        result = VerificationResult(scenario_id="test", call_sid="test-123")

        bot_text = "Processing [TOOL:create_reservation] now."
        verifier._rule_4_no_legacy_path(result, bot_text, [], {})
        self.assertFalse(result.passed)

    def test_rule_8_duplicate_tools(self):
        """Rule 8: Duplicate tool detection."""
        verifier = Verifier()
        result = VerificationResult(scenario_id="test", call_sid="test-123")

        tools_fired = [[], ["create_reservation", "create_reservation"]]
        verifier._rule_8_no_duplicate_tools(result, tools_fired)
        self.assertFalse(result.passed)


if __name__ == "__main__":
    unittest.main()
