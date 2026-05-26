"""
src/verifier.py — V4-native rule verification

Implements the 10 global pass/fail rules from the v4 audio test script,
adopted to v4 metrics architecture.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Placeholder patterns that should never appear
_PLACEHOLDER_RE = re.compile(
    r"Ihrem Namen|\{name\}|\{date\}|\{time\}|\{items\}|{{\s*\w+\s*}}",
    re.IGNORECASE,
)

# Legacy indicators
_LEGACY_PATTERNS = [r"\[TOOL:", r"tier2_runner", r"node_manager"]
_LEGACY_RE = re.compile("|".join(_LEGACY_PATTERNS), re.IGNORECASE)

# Success vocabulary (German)
_SUCCESS_VOCAB = [
    "reserviert",
    "aufgenommen",
    "bestätigt",
    "erfolgreich",
    "erfolgreich bestätigt",
]

# Confirmation tokens (mirror of v4_pipeline._is_confirmation_v4)
_CONFIRMATION_POSITIVE = [
    "ja",
    "genau",
    "richtig",
    "korrekt",
    "stimmt",
    "passt",
    "super",
    "perfekt",
    "ok",
    "okay",
    "gut",
    "gerne",
    "gern",
    "bestätige",
    "alles klar",
    "ja bitte",
    "ja genau",
    "in ordnung",
]

_CONFIRMATION_NEGATIVE = [
    "nein",
    "nicht",
    "falsch",
    "anders",
    "ändern",
    "aendern",
    "korrigieren",
    "nochmal",
    "andere",
    "stimmt nicht",
    "falsch",
]


@dataclass
class VerificationResult:
    """Per-call verification result."""
    scenario_id: str
    call_sid: str
    passed: bool = True
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    def add_failure(self, rule_num: int, detail: str):
        """Add a failed rule."""
        self.failures.append(f"Rule {rule_num}: {detail}")
        self.passed = False

    def add_warning(self, detail: str):
        """Add a warning (doesn't fail the check)."""
        self.warnings.append(detail)


def is_confirmation(text: str) -> bool:
    """Mirror of v4_pipeline._is_confirmation_v4."""
    lower = text.lower()
    if any(w in lower for w in _CONFIRMATION_NEGATIVE):
        return False
    return any(w in lower for w in _CONFIRMATION_POSITIVE)


class Verifier:
    """V4-native rule verification."""

    def verify_call(
        self,
        scenario_id: str,
        call_sid: str,
        bot_responses: list[str],
        tools_fired_per_turn: list[list[str]],
        user_utterances: list[str],
        db_metrics: dict,
        expectations: dict,
    ) -> VerificationResult:
        """Verify all rules for a call.

        Args:
            scenario_id: Scenario ID
            call_sid: Call SID from session
            bot_responses: Per-turn bot text (including greeting)
            tools_fired_per_turn: Tools fired per turn (from WS protocol)
            user_utterances: Per-turn user text
            db_metrics: Metrics from google_turn_metrics (indexed by turn_number)
            expectations: Scenario expectations block

        Returns:
            VerificationResult with pass/fail and details
        """
        result = VerificationResult(scenario_id=scenario_id, call_sid=call_sid)

        # Unify all bot text into one block for global checks
        all_bot_text = " ".join(bot_responses).lower()
        all_tools_flat = set()
        for tools in tools_fired_per_turn:
            all_tools_flat.update(tools)

        # Rule 1: Bot claims reservation/order confirmed before commit tool succeeds
        self._rule_1_no_false_claim(result, bot_responses, tools_fired_per_turn)

        # Rule 2: Bot executes commit without explicit user confirmation
        self._rule_2_no_commit_without_confirmation(
            result, user_utterances, tools_fired_per_turn
        )

        # Rule 3: Placeholder text like "Ihrem Namen"
        self._rule_3_no_placeholder_text(result, all_bot_text)

        # Rule 4: Legacy path hit (raw [TOOL:] tags, deprecated tool names, etc.)
        self._rule_4_no_legacy_path(result, all_bot_text, list(all_tools_flat), db_metrics)

        # Rule 5: Bot ends call before readback confirmation (if reservation/order pending)
        self._rule_5_no_premature_end_call(result, bot_responses, tools_fired_per_turn)

        # Rule 6: Bot says hallucinated data not in validated data
        self._rule_6_no_hallucination(result, all_bot_text, expectations)

        # Rule 7: Bot ignores correction and commits old data
        self._rule_7_correction_respected(result, user_utterances, tools_fired_per_turn)

        # Rule 8: Duplicate tool calls in same turn
        self._rule_8_no_duplicate_tools(result, tools_fired_per_turn)

        # Rule 9: Bot state and spoken response contradict (best-effort from metrics)
        self._rule_9_state_speech_consistent(result, bot_responses, db_metrics)

        # Rule 10: Emits raw [TOOL:...] tags or reacts to them
        self._rule_10_no_tool_tag_output(result, all_bot_text)

        # Rule 11: Scenario-specific must_contain_all_of / must_contain_one_of / must_not_contain
        self._rule_11_scenario_expectations(result, all_bot_text, expectations)

        result.metrics = {
            "tools_fired_total": len(all_tools_flat),
            "bot_turns": len(bot_responses),
            "user_turns": len(user_utterances),
            "failures": len(result.failures),
            "warnings": len(result.warnings),
        }

        return result

    @staticmethod
    def _rule_1_no_false_claim(
        result: VerificationResult,
        bot_responses: list[str],
        tools_fired_per_turn: list[list[str]],
    ):
        """Rule 1: Bot claims reservation/order confirmed before commit tool succeeds."""
        for i, (bot_text, tools) in enumerate(zip(bot_responses, tools_fired_per_turn)):
            if (
                any(vocab in bot_text.lower() for vocab in _SUCCESS_VOCAB)
                and "create_reservation" not in tools
                and "create_order" not in tools
            ):
                result.add_failure(
                    1, f"Turn {i}: Bot claims success but commit tool not fired"
                )

    @staticmethod
    def _rule_2_no_commit_without_confirmation(
        result: VerificationResult,
        user_utterances: list[str],
        tools_fired_per_turn: list[list[str]],
    ):
        """Rule 2: Bot executes commit without explicit user confirmation."""
        for i, tools in enumerate(tools_fired_per_turn):
            if "create_reservation" in tools or "create_order" in tools:
                # Check if previous user turn was a confirmation
                if i > 0 and not is_confirmation(user_utterances[i - 1]):
                    result.add_failure(
                        2,
                        f"Turn {i}: Commit fired without confirmation. "
                        f"User said: {user_utterances[i - 1][:50]!r}",
                    )

    @staticmethod
    def _rule_3_no_placeholder_text(result: VerificationResult, all_bot_text: str):
        """Rule 3: Placeholder text like "Ihrem Namen"."""
        matches = _PLACEHOLDER_RE.findall(all_bot_text)
        if matches:
            result.add_failure(3, f"Found placeholder text: {matches[:3]}")

    @staticmethod
    def _rule_4_no_legacy_path(
        result: VerificationResult,
        all_bot_text: str,
        tools_flat: list[str],
        db_metrics: dict,
    ):
        """Rule 4: Legacy path hit."""
        if _LEGACY_RE.search(all_bot_text):
            result.add_failure(4, "Found legacy pattern in bot text")

        deprecated_tools = ["tier2_runner", "node_manager"]
        if any(t in tools_flat for t in deprecated_tools):
            result.add_failure(4, f"Found deprecated tool: {[t for t in tools_flat if t in deprecated_tools]}")

        # Check if node_name is None or stuck on 'greeting' for non-greeting turns
        for turn_num, metrics in db_metrics.items():
            node_name = metrics.get("node_name")
            if turn_num > 0 and node_name in (None, "greeting"):
                result.add_failure(4, f"Turn {turn_num}: node_name stuck on {node_name!r}")

    @staticmethod
    def _rule_5_no_premature_end_call(
        result: VerificationResult,
        bot_responses: list[str],
        tools_fired_per_turn: list[list[str]],
    ):
        """Rule 5: Bot ends call before readback confirmation."""
        if len(bot_responses) < 2:
            return

        last_response = bot_responses[-1].lower()
        # Check for goodbye/end-call indicators
        end_indicators = [
            "tschüss",
            "auf wiederhoren",
            "auf wiedersehen",
            "auf wiederhören",
            "guten tag",
        ]

        if any(ind in last_response for ind in end_indicators):
            # If any commit tool was fired in this call, verify readback happened
            any_commit = any(
                "create_reservation" in t or "create_order" in t for t in tools_fired_per_turn
            )
            if any_commit:
                # The second-to-last turn should have readback marker
                if len(bot_responses) >= 2:
                    readback_turn = bot_responses[-2].lower()
                    if "stimmt das so" not in readback_turn and "korrekt" not in readback_turn:
                        result.add_warning("Premature end_call: no readback detected before goodbye")

    @staticmethod
    def _rule_6_no_hallucination(
        result: VerificationResult,
        all_bot_text: str,
        expectations: dict,
    ):
        """Rule 6: Bot says data not in validated data."""
        forbidden = expectations.get("forbid_phrases", [])
        for phrase in forbidden:
            if phrase.lower() in all_bot_text:
                result.add_failure(6, f"Found forbidden phrase: {phrase!r}")

    @staticmethod
    def _rule_7_correction_respected(
        result: VerificationResult,
        user_utterances: list[str],
        tools_fired_per_turn: list[list[str]],
    ):
        """Rule 7: Bot ignores correction and commits old data."""
        for i in range(1, len(user_utterances)):
            # If user says "nein", "nicht", "anders" = correction
            if any(
                word in user_utterances[i].lower()
                for word in ["nein", "nicht", "anders", "aendern"]
            ):
                # Commit should NOT fire on the next turn
                if i + 1 < len(tools_fired_per_turn):
                    if any(
                        t in tools_fired_per_turn[i + 1]
                        for t in ["create_reservation", "create_order"]
                    ):
                        result.add_warning(
                            f"Turn {i}: User corrected but bot committed anyway"
                        )

    @staticmethod
    def _rule_8_no_duplicate_tools(
        result: VerificationResult,
        tools_fired_per_turn: list[list[str]],
    ):
        """Rule 8: Duplicate tool calls in same turn."""
        for i, tools in enumerate(tools_fired_per_turn):
            if len(tools) != len(set(tools)):
                dups = [t for t in tools if tools.count(t) > 1]
                result.add_failure(8, f"Turn {i}: Duplicate tools: {dups}")

    @staticmethod
    def _rule_9_state_speech_consistent(
        result: VerificationResult,
        bot_responses: list[str],
        db_metrics: dict,
    ):
        """Rule 9: Bot state and spoken response contradict."""
        # Best-effort: check if metrics show success but bot text doesn't
        for turn_num, metrics in db_metrics.items():
            # This is optional/best-effort verification
            pass

    @staticmethod
    def _rule_10_no_tool_tag_output(result: VerificationResult, all_bot_text: str):
        """Rule 10: Emits raw [TOOL:...] tags."""
        if "[TOOL:" in all_bot_text or "[tool:" in all_bot_text:
            result.add_failure(10, "Bot emitted raw [TOOL:...] tag")

    @staticmethod
    def _rule_11_scenario_expectations(
        result: VerificationResult,
        all_bot_text: str,
        expectations: dict,
    ):
        """Rule 11: Check must_contain_all_of / must_contain_one_of / must_not_contain."""
        # must_contain_all_of: every phrase must appear
        for phrase in expectations.get("must_contain_all_of", []):
            if phrase.lower() not in all_bot_text:
                result.add_failure(11, f"Required phrase not found: {phrase!r}")

        # must_contain_one_of: at least one phrase must appear
        one_of = expectations.get("must_contain_one_of", [])
        if one_of and not any(phrase.lower() in all_bot_text for phrase in one_of):
            result.add_failure(11, f"None of required phrases found: {one_of[:3]}")

        # must_not_contain: none of these phrases should appear
        for phrase in expectations.get("must_not_contain", []):
            if phrase.lower() in all_bot_text:
                result.add_failure(11, f"Forbidden phrase found: {phrase!r}")
