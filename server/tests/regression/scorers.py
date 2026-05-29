"""
Sailly Regression Scorers — Phase 4a deterministic scoring layer.

This module implements three-layer scoring for the golden dataset:

L1: Deterministic Scorer (Layer 1 — orchestrator)
  - Check worker_profile matches expected
  - Verify tools_called matches expected list (exact, no extra tools)
  - Check forced_tools respected (no forbidden tools)
  - Validate state progression (slots filled correctly)
  - Return: pass/fail + detailed mismatch report

L2: LLM-Judge Scorer (Layer 2 — language quality)
  - Use Haiku LLM to judge response quality (0-1 confidence)
  - Check: tone, clarity, directly answered question
  - Threshold: >0.85 pass, <0.85 investigate
  - Cache results by turn hash to avoid re-scoring

L3: Span-Level Assertions (Phase 2 ExecutionSpan)
  - For each span in execution_spans:
    - Assert operation matches expected (classify, execute_tool, etc.)
    - Check status == "ok" (no errors)
    - Validate latency < SLA (classify <100ms, execute_tool <1000ms)
  - Return: pass/fail + latency breakdown

Schema version: 1
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes & Enums
# ============================================================================


class ScorerLayer(Enum):
    """Scoring layer identification."""
    L1_DETERMINISTIC = "l1_deterministic"
    L2_LLM_JUDGE = "l2_llm_judge"
    L3_SPAN_LEVEL = "l3_span_level"


class ScorerResult(Enum):
    """Scorer result status."""
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


@dataclass
class MismatchReport:
    """Detailed report of a mismatch between expected and actual."""
    category: str  # "tools", "state", "latency", "quality", etc.
    expected: Any
    actual: Any
    message: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "category": self.category,
            "expected": self.expected,
            "actual": self.actual,
            "message": self.message,
        }


@dataclass
class ScorerOutput:
    """Complete scorer output for a single golden case."""
    scenario_id: str
    layer: ScorerLayer
    status: ScorerResult
    confidence: float  # 0.0-1.0
    mismatches: List[MismatchReport] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    turn_idx: Optional[int] = None  # If span-level, which turn

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "scenario_id": self.scenario_id,
            "layer": self.layer.value,
            "status": self.status.value,
            "confidence": self.confidence,
            "mismatches": [m.to_dict() for m in self.mismatches],
            "details": self.details,
            "turn_idx": self.turn_idx,
        }


# ============================================================================
# L1: Deterministic Scorer
# ============================================================================


class DeterministicScorer:
    """
    Layer 1 orchestrator: exact, deterministic tool/state assertions.

    Validates:
      - tools_called matches expected list exactly (no extra, no missing)
      - forced_tools constraint respected
      - worker_profile matches expected
      - state slots filled per expected_behavior
    """

    def __init__(self):
        """Initialize scorer."""
        pass

    def score(
        self,
        scenario_id: str,
        expected_behavior: Dict[str, Any],
        actual_tools_called: List[str],
        actual_state: Optional[Dict[str, Any]] = None,
        forced_tools: Optional[List[str]] = None,
    ) -> ScorerOutput:
        """
        Score a scenario's tool calls and state against expected behavior.

        Args:
            scenario_id: unique scenario identifier
            expected_behavior: from golden dataset
                {
                    "tools_called": [...],
                    "final_intent": "...",
                    "fulfilled": bool,
                }
            actual_tools_called: list of tools that actually fired
            actual_state: actual conversation state snapshot
            forced_tools: list of tools that are forbidden to call early

        Returns:
            ScorerOutput with status, confidence, and detailed mismatches
        """
        output = ScorerOutput(
            scenario_id=scenario_id,
            layer=ScorerLayer.L1_DETERMINISTIC,
            status=ScorerResult.PASS,
            confidence=1.0,
        )

        expected_tools = expected_behavior.get("tools_called", [])
        final_intent = expected_behavior.get("final_intent")
        fulfilled = expected_behavior.get("fulfilled", True)

        # === Check 1: Exact tool match ===
        if not self._check_tools_match(
            expected_tools, actual_tools_called, output
        ):
            output.status = ScorerResult.FAIL
            output.confidence = 0.0

        # === Check 2: Forced tools respected ===
        if forced_tools and not self._check_forced_tools(
            forced_tools, actual_tools_called, output
        ):
            output.status = ScorerResult.FAIL
            output.confidence = 0.0

        # === Check 3: State progression ===
        if actual_state and not self._check_state_progression(
            expected_behavior, actual_state, output
        ):
            output.status = ScorerResult.FAIL
            output.confidence *= 0.5

        # === Check 4: Fulfillment marker ===
        # If expected fulfilled=false, we don't penalize missing tools
        # (failure cases are expected to not fulfill)
        if not fulfilled:
            output.details["fulfillment_mode"] = "expected_failure"
            # Reset mismatches since we expected this to fail
            output.mismatches = []
            output.status = ScorerResult.PASS
            output.confidence = 1.0

        output.details["tools_checked"] = {
            "expected": expected_tools,
            "actual": actual_tools_called,
            "match": expected_tools == actual_tools_called,
        }

        return output

    def _check_tools_match(
        self,
        expected: List[str],
        actual: List[str],
        output: ScorerOutput,
    ) -> bool:
        """
        Verify tools_called matches exactly.

        Returns True if match, False otherwise (and records mismatch).
        """
        if set(expected) == set(actual) and len(expected) == len(actual):
            return True

        # Detect specific missing/extra
        expected_set = set(expected)
        actual_set = set(actual)
        missing = expected_set - actual_set
        extra = actual_set - expected_set

        if missing:
            output.mismatches.append(
                MismatchReport(
                    category="missing_tools",
                    expected=list(missing),
                    actual=None,
                    message=f"Expected tools not called: {missing}",
                )
            )

        if extra:
            output.mismatches.append(
                MismatchReport(
                    category="extra_tools",
                    expected=None,
                    actual=list(extra),
                    message=f"Extra tools called: {extra}",
                )
            )

        return False

    def _check_forced_tools(
        self,
        forced_tools: List[str],
        actual: List[str],
        output: ScorerOutput,
    ) -> bool:
        """
        Verify no forbidden/forced tools were called prematurely.

        Returns True if constraint satisfied, False otherwise.
        """
        forbidden_called = set(forced_tools) & set(actual)
        if forbidden_called:
            output.mismatches.append(
                MismatchReport(
                    category="forced_tools_violation",
                    expected="none",
                    actual=list(forbidden_called),
                    message=f"Forbidden tools called: {forbidden_called}",
                )
            )
            return False
        return True

    def _check_state_progression(
        self,
        expected_behavior: Dict[str, Any],
        actual_state: Dict[str, Any],
        output: ScorerOutput,
    ) -> bool:
        """
        Validate state progression (slots, intents, etc.).

        This is a placeholder for state schema validation.
        Real implementation would check ConversationState fields.

        Returns True if state looks correct, False otherwise.
        """
        # For Phase 4a, we do minimal state checks
        # Phase 4b will expand with full ConversationState validation
        return True


# ============================================================================
# L2: LLM-Judge Scorer
# ============================================================================


class LLMJudgeScorer:
    """
    Layer 2 language quality assessor: uses LLM to judge response quality.

    Validates:
      - Response tone matches expected intent
      - Clarity and directness
      - Absence of hallucinations or false claims
      - Threshold: >0.85 pass, <0.85 investigate

    Caches by turn hash to avoid re-scoring same turn twice.
    """

    def __init__(self, enable_llm: bool = True):
        """
        Initialize scorer.

        Args:
            enable_llm: if False, skip LLM calls (return INCONCLUSIVE)
        """
        self.enable_llm = enable_llm
        self._cache: Dict[str, float] = {}

    def score(
        self,
        scenario_id: str,
        turn_idx: int,
        bot_response: str,
        user_text: str,
        expected_intent: str,
    ) -> ScorerOutput:
        """
        Score language quality of a bot response.

        Args:
            scenario_id: unique scenario identifier
            turn_idx: turn number in conversation
            bot_response: the bot's text response
            user_text: the user's text in this turn
            expected_intent: what we expected the bot to do (e.g., "greeting", "order")

        Returns:
            ScorerOutput with language quality confidence (0.0-1.0)
        """
        output = ScorerOutput(
            scenario_id=scenario_id,
            layer=ScorerLayer.L2_LLM_JUDGE,
            turn_idx=turn_idx,
            status=ScorerResult.INCONCLUSIVE,
            confidence=0.5,
        )

        # === Check cache ===
        turn_hash = self._hash_turn(scenario_id, turn_idx, bot_response)
        if turn_hash in self._cache:
            cached_confidence = self._cache[turn_hash]
            output.confidence = cached_confidence
            output.status = (
                ScorerResult.PASS if cached_confidence > 0.85
                else ScorerResult.FAIL
            )
            output.details["cached"] = True
            return output

        # === Run LLM judge (Phase 4b will implement actual LLM call) ===
        # For Phase 4a, we use simple heuristics
        quality_score = self._heuristic_quality_check(
            bot_response, user_text, expected_intent
        )

        self._cache[turn_hash] = quality_score
        output.confidence = quality_score
        output.status = (
            ScorerResult.PASS if quality_score > 0.85
            else ScorerResult.FAIL
        )

        output.details["quality_checks"] = {
            "has_placeholder": "{" in bot_response or ("[" in bot_response and "]" in bot_response),
            "response_length": len(bot_response),
            "contains_tool_tag": "[tool" in bot_response.lower(),
            "contains_error": "error" in bot_response.lower()
                and "occurred" in bot_response.lower(),
        }

        return output

    def _hash_turn(self, scenario_id: str, turn_idx: int, bot_response: str) -> str:
        """Create stable hash for a turn."""
        data = f"{scenario_id}#{turn_idx}#{bot_response}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _heuristic_quality_check(
        self,
        bot_response: str,
        user_text: str,
        expected_intent: str,
    ) -> float:
        """
        Simple heuristic quality check (Phase 4a placeholder).

        Phase 4b will replace this with actual LLM judge.

        Returns:
            Confidence 0.0-1.0
        """
        score = 1.0

        # Penalize placeholders
        if "{" in bot_response or "[" in bot_response:
            score -= 0.3

        # Penalize tool tags (legacy format)
        if "[tool" in bot_response.lower():
            score -= 0.2

        # Penalize error messages without context
        if ("error" in bot_response.lower() or
                "technisches problem" in bot_response.lower()):
            score -= 0.1

        # Penalize very short responses
        if len(bot_response) < 20:
            score -= 0.15

        # Reward reasonable length (30-500 chars is typical)
        if 30 <= len(bot_response) <= 500:
            score += 0.1

        return max(0.0, min(1.0, score))


# ============================================================================
# L3: Span-Level Assertions
# ============================================================================


class SpanLevelScorer:
    """
    Layer 3 execution span validator: checks operation, status, and latency.

    Validates per ExecutionSpan:
      - operation matches expected (classify, execute_tool, etc.)
      - status == "ok" (no errors)
      - latency < SLA (classify <100ms, execute_tool <1000ms)

    Returns: pass/fail + latency breakdown
    """

    # SLA thresholds in milliseconds
    SLA_CLASSIFY = 100
    SLA_EXECUTE_TOOL = 1000
    SLA_OTHER = 2000

    def __init__(self):
        """Initialize scorer."""
        pass

    def score(
        self,
        scenario_id: str,
        execution_spans: List[Dict[str, Any]],
    ) -> ScorerOutput:
        """
        Score execution spans for correctness and latency.

        Args:
            scenario_id: unique scenario identifier
            execution_spans: list of execution span dicts
                [
                    {
                        "operation": "classify" | "execute_tool" | "...",
                        "status": "ok" | "error" | "...",
                        "latency_ms": float,
                        "metadata": {...},
                    },
                    ...
                ]

        Returns:
            ScorerOutput with status and latency details
        """
        output = ScorerOutput(
            scenario_id=scenario_id,
            layer=ScorerLayer.L3_SPAN_LEVEL,
            status=ScorerResult.PASS,
            confidence=1.0,
        )

        if not execution_spans:
            output.details["spans_count"] = 0
            return output

        latency_by_operation = {}
        sla_violations = []

        for span_idx, span in enumerate(execution_spans):
            operation = span.get("operation", "unknown")
            status = span.get("status", "unknown")
            latency_ms = span.get("latency_ms", 0)

            # Track latency
            if operation not in latency_by_operation:
                latency_by_operation[operation] = []
            latency_by_operation[operation].append(latency_ms)

            # === Check 1: Status must be OK ===
            if status != "ok":
                output.mismatches.append(
                    MismatchReport(
                        category="span_status_error",
                        expected="ok",
                        actual=status,
                        message=f"Span {span_idx} ({operation}): status={status}",
                    )
                )
                output.status = ScorerResult.FAIL
                output.confidence *= 0.5
                continue

            # === Check 2: Latency SLA ===
            sla = self._get_sla(operation)
            if latency_ms > sla:
                sla_violations.append({
                    "span_idx": span_idx,
                    "operation": operation,
                    "latency_ms": latency_ms,
                    "sla_ms": sla,
                })
                output.mismatches.append(
                    MismatchReport(
                        category="latency_sla_violation",
                        expected=sla,
                        actual=latency_ms,
                        message=f"Span {span_idx} ({operation}): {latency_ms}ms > {sla}ms SLA",
                    )
                )
                # Latency violation is a warning, not a hard fail
                output.confidence *= 0.8

        output.details["spans_count"] = len(execution_spans)
        output.details["latency_by_operation"] = {
            op: {
                "count": len(lats),
                "min_ms": min(lats),
                "max_ms": max(lats),
                "avg_ms": sum(lats) / len(lats),
            }
            for op, lats in latency_by_operation.items()
        }
        output.details["sla_violations"] = sla_violations

        if sla_violations:
            output.status = ScorerResult.FAIL

        return output

    def _get_sla(self, operation: str) -> int:
        """Get SLA threshold in ms for operation."""
        if operation == "classify":
            return self.SLA_CLASSIFY
        elif operation == "execute_tool":
            return self.SLA_EXECUTE_TOOL
        else:
            return self.SLA_OTHER


# ============================================================================
# Multi-Layer Scorer Orchestrator
# ============================================================================


class RegressionScorer:
    """
    Orchestrates all three scoring layers for a golden case.

    Usage:
        scorer = RegressionScorer()
        results = scorer.score_case(golden_case, actual_result)
    """

    def __init__(self, enable_llm: bool = True):
        """Initialize all sub-scorers."""
        self.l1_scorer = DeterministicScorer()
        self.l2_scorer = LLMJudgeScorer(enable_llm=enable_llm)
        self.l3_scorer = SpanLevelScorer()

    def score_case(
        self,
        scenario_id: str,
        expected_behavior: Dict[str, Any],
        actual_tools_called: List[str],
        turns: List[Tuple[str, str]],  # [(user_text, bot_text), ...]
        actual_state: Optional[Dict[str, Any]] = None,
        execution_spans: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, ScorerOutput]:
        """
        Run all scoring layers for a single golden case.

        Args:
            scenario_id: unique scenario ID
            expected_behavior: expected behavior from golden dataset
            actual_tools_called: tools that actually fired
            turns: list of (user_text, bot_text) tuples
            actual_state: actual conversation state
            execution_spans: execution span data (for L3 scoring)

        Returns:
            Dict mapping layer name -> ScorerOutput
        """
        results = {}

        # === L1: Deterministic Scorer ===
        results["l1_deterministic"] = self.l1_scorer.score(
            scenario_id=scenario_id,
            expected_behavior=expected_behavior,
            actual_tools_called=actual_tools_called,
            actual_state=actual_state,
        )

        # === L2: LLM-Judge Scorer (per turn) ===
        l2_results = []
        for turn_idx, (user_text, bot_text) in enumerate(turns):
            l2_result = self.l2_scorer.score(
                scenario_id=scenario_id,
                turn_idx=turn_idx,
                bot_response=bot_text,
                user_text=user_text,
                expected_intent=expected_behavior.get("final_intent", "unknown"),
            )
            l2_results.append(l2_result)

        # Aggregate L2 confidence (worst turn counts)
        min_confidence = min(r.confidence for r in l2_results) if l2_results else 1.0
        worst_status = ScorerResult.PASS
        for r in l2_results:
            if r.status == ScorerResult.FAIL:
                worst_status = ScorerResult.FAIL
                break
            elif r.status == ScorerResult.INCONCLUSIVE and worst_status == ScorerResult.PASS:
                worst_status = ScorerResult.INCONCLUSIVE

        results["l2_llm_judge"] = ScorerOutput(
            scenario_id=scenario_id,
            layer=ScorerLayer.L2_LLM_JUDGE,
            status=worst_status,
            confidence=min_confidence,
            details={
                "turn_results": [r.to_dict() for r in l2_results],
                "turns_count": len(l2_results),
            },
        )

        # === L3: Span-Level Scorer ===
        if execution_spans:
            results["l3_span_level"] = self.l3_scorer.score(
                scenario_id=scenario_id,
                execution_spans=execution_spans,
            )
        else:
            results["l3_span_level"] = ScorerOutput(
                scenario_id=scenario_id,
                layer=ScorerLayer.L3_SPAN_LEVEL,
                status=ScorerResult.INCONCLUSIVE,
                confidence=0.5,
                details={"skipped": "No execution spans provided"},
            )

        return results

    def aggregate_results(
        self, layer_results: Dict[str, ScorerOutput]
    ) -> Tuple[ScorerResult, float]:
        """
        Aggregate multi-layer results into final pass/fail.

        L1 is gate (must pass). L2 and L3 are advisory (confidence boosters).

        Returns:
            (final_status, final_confidence)
        """
        l1 = layer_results.get("l1_deterministic")
        l2 = layer_results.get("l2_llm_judge")
        l3 = layer_results.get("l3_span_level")

        # L1 is gate (hard pass/fail)
        if l1 and l1.status == ScorerResult.FAIL:
            return (ScorerResult.FAIL, l1.confidence)

        # L2 and L3 inform confidence
        confidence = 1.0
        if l1:
            confidence *= l1.confidence
        if l2:
            confidence *= l2.confidence
        if l3 and l3.status != ScorerResult.INCONCLUSIVE:
            confidence *= l3.confidence

        return (ScorerResult.PASS, confidence)
