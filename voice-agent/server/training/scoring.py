"""
Multi-Dimensional Scorer -- 6-dimension evaluation of scenario outcomes.

Scores: Task Completion, Language Compliance, Instruction Following, Latency, Audio Quality, STT Accuracy
Aggregates across N runs with mean and stddev.
Maps to call_auditor.py weights for restaurant domain.
"""

import re
import json
from dataclasses import dataclass, asdict
from typing import Optional, List
from statistics import mean, stdev
import logging

logger = logging.getLogger(__name__)

# Mapping of call_auditor.py weights to test dimensions
CALL_AUDITOR_WEIGHTS = {
    "task_completion": 0.35,
    "empathy": 0.20,
    "conversation_flow": 0.15,
    "safety": 0.15,
    "accuracy": 0.15,
}

# Test dimensions map to call_auditor weights
TEST_TO_AUDITOR_MAPPING = {
    "task": "task_completion",  # All expected_tools called with valid params
    "language": "accuracy",  # Zero English words, forbidden patterns
    "instruction": ("empathy", "conversation_flow"),  # Name ack, filler, max 2 sentences
    "latency": "conversation_flow",  # E2E within budget
    "audio_quality": "conversation_flow",  # TTS bytes, silence gaps, filler uniqueness
    "stt_accuracy": "accuracy",  # WER <= 20%
}


@dataclass
class DimensionScore:
    """Score for a single dimension."""
    name: str  # "task", "language", "instruction", "latency", "audio_quality", "stt_accuracy"
    value: float  # 0-100
    notes: str = ""


@dataclass
class ScenarioResult:
    """Complete scoring result for a single scenario run."""
    scenario_id: str
    phase: str
    category: str
    run_number: int
    timestamp: str

    # Dimension scores
    task_completion: float  # 0-100
    language_compliance: float
    instruction_following: float
    latency: float
    audio_quality: float
    stt_accuracy: Optional[float]  # None for Tier 1 text-mode

    # Raw metrics
    latency_ms: float
    audio_bytes_total: int
    wer: Optional[float]  # Word error rate (Tier 2/3 only)
    tools_called: List[str]
    tools_failed: List[str]
    error_messages: List[str]

    # Pass/fail
    passed: bool
    failure_reason: Optional[str] = None

    def aggregate_score(self, weights: Optional[dict] = None) -> float:
        """
        Aggregate all dimension scores into single 0-100 score.

        Args:
            weights: Optional custom weights {dimension: weight}
                    Default: equal weighting of all dimensions

        Returns:
            Weighted average score 0-100
        """
        if weights is None:
            # Equal weighting by default
            dimensions = [
                self.task_completion,
                self.language_compliance,
                self.instruction_following,
                self.latency,
                self.audio_quality,
            ]
            if self.stt_accuracy is not None:
                dimensions.append(self.stt_accuracy)
            return sum(dimensions) / len(dimensions)

        total = 0
        total_weight = 0
        for dim, weight in weights.items():
            if dim == "task_completion":
                total += self.task_completion * weight
            elif dim == "language_compliance":
                total += self.language_compliance * weight
            elif dim == "instruction_following":
                total += self.instruction_following * weight
            elif dim == "latency":
                total += self.latency * weight
            elif dim == "audio_quality":
                total += self.audio_quality * weight
            elif dim == "stt_accuracy" and self.stt_accuracy is not None:
                total += self.stt_accuracy * weight
            total_weight += weight

        return total / total_weight if total_weight > 0 else 0.0

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class AggregatedScenarioScore:
    """Aggregated score across N runs of a scenario."""
    scenario_id: str
    phase: str
    category: str

    # Per-dimension: mean and stddev across runs
    task_completion_mean: float
    task_completion_stddev: Optional[float]
    language_compliance_mean: float
    language_compliance_stddev: Optional[float]
    instruction_following_mean: float
    instruction_following_stddev: Optional[float]
    latency_mean: float
    latency_stddev: Optional[float]
    audio_quality_mean: float
    audio_quality_stddev: Optional[float]
    stt_accuracy_mean: Optional[float]
    stt_accuracy_stddev: Optional[float]

    # Overall aggregation
    overall_mean: float
    overall_stddev: Optional[float]

    # Pass/fail classification
    pass_count: int  # Number of runs that passed
    flaky: bool  # True if 1-2/3 runs pass
    failed_runs: List[int]  # Run numbers that failed

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class MultiDimensionalScorer:
    """
    Scores scenario results across 6 dimensions.
    Tracks mean/stddev across N runs.
    Maps to call_auditor.py weights.
    """

    def __init__(self):
        self.results: dict[str, list[ScenarioResult]] = {}  # scenario_id -> [results]

    def record_result(self, result: ScenarioResult) -> None:
        """Record a single scenario result."""
        if result.scenario_id not in self.results:
            self.results[result.scenario_id] = []
        self.results[result.scenario_id].append(result)

    def score_task_completion(
        self,
        tools_called: List[str],
        tools_failed: List[str],
        expected_tools: List[str],
        forbidden_tools: List[str] = None,
    ) -> float:
        """
        Score task completion: 0-100.
        - All expected_tools called successfully: 100
        - Missing any expected_tool: -30 each
        - Called forbidden tool: -40
        - Tool failed: -10 each

        Args:
            tools_called: Tools actually called
            tools_failed: Tools that failed
            expected_tools: Tools that should be called
            forbidden_tools: Tools that must not be called

        Returns:
            0-100 score
        """
        score = 100.0
        forbidden_tools = forbidden_tools or []

        # Check all expected tools were called
        for tool in expected_tools:
            if tool not in tools_called:
                score -= 30.0
                logger.debug(f"Missing expected tool: {tool}")

        # Check no forbidden tools were called
        for tool in forbidden_tools:
            if tool in tools_called:
                score -= 40.0
                logger.debug(f"Called forbidden tool: {tool}")

        # Penalize failed tool calls
        for tool in tools_failed:
            score -= 10.0
            logger.debug(f"Tool failed: {tool}")

        return max(0.0, min(100.0, score))

    def score_language_compliance(
        self,
        response_text: str,
        forbidden_patterns: List[str],
    ) -> float:
        """
        Score language compliance: 0-100.
        - No English words: +50
        - No forbidden patterns (emotional tags, etc.): +50

        Args:
            response_text: LLM or TTS response
            forbidden_patterns: Regex patterns to flag (emotional tags, etc.)

        Returns:
            0-100 score
        """
        score = 100.0

        # Check for English words (simple heuristic)
        english_words = [
            "and", "the", "is", "are", "you", "we", "have", "hello", "okay", "ok",
        ]
        response_lower = response_text.lower()
        for word in english_words:
            if re.search(r"\b" + word + r"\b", response_lower):
                score -= 20.0
                logger.debug(f"English word detected: {word}")

        # Check forbidden patterns
        for pattern in forbidden_patterns:
            try:
                if re.search(pattern, response_text, re.IGNORECASE):
                    score -= 25.0
                    logger.debug(f"Forbidden pattern detected: {pattern}")
            except re.error:
                logger.warning(f"Invalid regex pattern: {pattern}")

        return max(0.0, min(100.0, score))

    def score_instruction_following(
        self,
        response_text: str,
        has_filler_before_tool: bool,
        max_sentences: int = 2,
        has_confirmation: bool = True,
        has_name_ack: bool = True,
    ) -> float:
        """
        Score instruction following: 0-100.
        - Filler before tool call: +20
        - Max 2 sentences: +25
        - Confirmation before create: +25
        - Name acknowledgement: +30

        Args:
            response_text: Response to evaluate
            has_filler_before_tool: Whether filler was injected before tool
            max_sentences: Maximum allowed sentences
            has_confirmation: Whether confirmation was requested
            has_name_ack: Whether name was acknowledged

        Returns:
            0-100 score
        """
        score = 0.0

        # Filler before tool
        if has_filler_before_tool:
            score += 20.0

        # Sentence count
        sentences = re.split(r"[.!?]+", response_text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) <= max_sentences:
            score += 25.0
        else:
            score -= 10.0
            logger.debug(f"Too many sentences: {len(sentences)} > {max_sentences}")

        # Confirmation
        if has_confirmation:
            score += 25.0

        # Name acknowledgement
        if has_name_ack:
            score += 30.0

        return max(0.0, min(100.0, score))

    def score_latency(
        self,
        latency_ms: float,
        latency_budget_ms: int,
    ) -> float:
        """
        Score latency: 0-100.
        - Within budget: 100
        - 1-2x budget: 50
        - > 2x budget: 0

        Args:
            latency_ms: Actual latency
            latency_budget_ms: Allowed latency

        Returns:
            0-100 score
        """
        if latency_ms <= latency_budget_ms:
            return 100.0
        elif latency_ms <= 2 * latency_budget_ms:
            ratio = (latency_ms - latency_budget_ms) / latency_budget_ms
            return max(0.0, 100.0 - (50.0 * ratio))
        else:
            return 0.0

    def score_audio_quality(
        self,
        audio_bytes: int,
        silence_gaps_ms: List[float] = None,
        repeated_fillers: int = 0,
    ) -> float:
        """
        Score audio quality: 0-100.
        - Audio bytes > 200: +40
        - No silence gaps > 2000ms: +40
        - No repeated fillers: +20

        Args:
            audio_bytes: Total TTS audio bytes
            silence_gaps_ms: List of silence gaps
            repeated_fillers: Count of repeated filler phrases

        Returns:
            0-100 score
        """
        score = 0.0

        # Audio data present
        if audio_bytes > 200:
            score += 40.0
        else:
            logger.debug(f"Low audio data: {audio_bytes} bytes")

        # Silence gaps
        silence_gaps_ms = silence_gaps_ms or []
        if not any(gap > 2000 for gap in silence_gaps_ms):
            score += 40.0
        else:
            for gap in silence_gaps_ms:
                if gap > 2000:
                    logger.debug(f"Long silence gap: {gap}ms")

        # Repeated fillers
        if repeated_fillers == 0:
            score += 20.0
        else:
            score -= 10.0 * repeated_fillers
            logger.debug(f"Repeated fillers: {repeated_fillers}")

        return max(0.0, min(100.0, score))

    def score_stt_accuracy(
        self,
        wer: float,
        min_accuracy: float = 0.80,
    ) -> Optional[float]:
        """
        Score STT accuracy: 0-100 (Tier 2/3 only).
        - WER < (1 - min_accuracy): 100
        - Else: scale to 0

        Args:
            wer: Word error rate (0-1)
            min_accuracy: Minimum required accuracy (0.80 = max 20% WER)

        Returns:
            0-100 score, or None if not applicable
        """
        if wer is None:
            return None

        accuracy = 1.0 - wer
        if accuracy >= min_accuracy:
            return 100.0
        else:
            # Linear scale from 0 to min_accuracy
            return max(0.0, (accuracy / min_accuracy) * 100.0)

    def aggregate_scenario(
        self,
        scenario_id: str,
    ) -> AggregatedScenarioScore:
        """
        Aggregate scores across all runs of a scenario.

        Args:
            scenario_id: Scenario to aggregate

        Returns:
            AggregatedScenarioScore with mean/stddev
        """
        if scenario_id not in self.results or not self.results[scenario_id]:
            raise ValueError(f"No results for scenario {scenario_id}")

        results = self.results[scenario_id]

        def _agg(values: list) -> tuple[float, Optional[float]]:
            """Helper: return mean and stddev."""
            if not values:
                return 0.0, None
            m = mean(values)
            s = stdev(values) if len(values) > 1 else None
            return m, s

        # Aggregate each dimension
        task_values = [r.task_completion for r in results]
        lang_values = [r.language_compliance for r in results]
        instr_values = [r.instruction_following for r in results]
        latency_values = [r.latency for r in results]
        audio_values = [r.audio_quality for r in results]
        stt_values = [r.stt_accuracy for r in results if r.stt_accuracy is not None]

        task_m, task_s = _agg(task_values)
        lang_m, lang_s = _agg(lang_values)
        instr_m, instr_s = _agg(instr_values)
        lat_m, lat_s = _agg(latency_values)
        audio_m, audio_s = _agg(audio_values)
        stt_m, stt_s = _agg(stt_values)

        # Overall mean (average of all dimensions)
        overall_values = (
            task_values + lang_values + instr_values + latency_values + audio_values + stt_values
        )
        overall_m, overall_s = _agg(overall_values)

        # Pass/fail classification
        pass_count = sum(1 for r in results if r.passed)
        failed_runs = [i + 1 for i, r in enumerate(results) if not r.passed]
        flaky = 0 < pass_count < len(results)

        return AggregatedScenarioScore(
            scenario_id=scenario_id,
            phase=results[0].phase,
            category=results[0].category,
            task_completion_mean=task_m,
            task_completion_stddev=task_s,
            language_compliance_mean=lang_m,
            language_compliance_stddev=lang_s,
            instruction_following_mean=instr_m,
            instruction_following_stddev=instr_s,
            latency_mean=lat_m,
            latency_stddev=lat_s,
            audio_quality_mean=audio_m,
            audio_quality_stddev=audio_s,
            stt_accuracy_mean=stt_m,
            stt_accuracy_stddev=stt_s,
            overall_mean=overall_m,
            overall_stddev=overall_s,
            pass_count=pass_count,
            flaky=flaky,
            failed_runs=failed_runs,
        )

    def get_all_aggregated(self) -> dict[str, AggregatedScenarioScore]:
        """Get aggregated scores for all scenarios."""
        return {
            scenario_id: self.aggregate_scenario(scenario_id)
            for scenario_id in self.results.keys()
        }

    def export_json(self, output_path: str) -> None:
        """Export all results to JSON."""
        data = {
            "individual_runs": [asdict(r) for results in self.results.values() for r in results],
            "aggregated": {
                scenario_id: asdict(agg)
                for scenario_id, agg in self.get_all_aggregated().items()
            },
        }
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Exported scoring results to {output_path}")


if __name__ == "__main__":
    import datetime

    logging.basicConfig(level=logging.DEBUG)

    # Test scoring
    scorer = MultiDimensionalScorer()

    # Example result
    result = ScenarioResult(
        scenario_id="t1-greeting-01",
        phase="tier1",
        category="greeting",
        run_number=1,
        timestamp=datetime.datetime.now().isoformat(),
        task_completion=100.0,
        language_compliance=95.0,
        instruction_following=90.0,
        latency=95.0,
        audio_quality=85.0,
        stt_accuracy=None,  # Tier 1 is text-mode
        latency_ms=450,
        audio_bytes_total=5000,
        wer=None,
        tools_called=[],
        tools_failed=[],
        error_messages=[],
        passed=True,
    )

    scorer.record_result(result)
    scorer.record_result(
        ScenarioResult(
            scenario_id="t1-greeting-01",
            phase="tier1",
            category="greeting",
            run_number=2,
            timestamp=datetime.datetime.now().isoformat(),
            task_completion=100.0,
            language_compliance=100.0,
            instruction_following=95.0,
            latency=90.0,
            audio_quality=80.0,
            stt_accuracy=None,
            latency_ms=480,
            audio_bytes_total=5200,
            wer=None,
            tools_called=[],
            tools_failed=[],
            error_messages=[],
            passed=True,
        )
    )

    agg = scorer.aggregate_scenario("t1-greeting-01")
    print(f"✓ Aggregated score for t1-greeting-01:")
    print(f"  Overall: {agg.overall_mean:.1f}% ± {agg.overall_stddev:.1f}%")
    print(f"  Pass count: {agg.pass_count}/2")
    print(f"  Flaky: {agg.flaky}")
