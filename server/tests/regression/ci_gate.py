"""
Sailly Regression CI Gate — Phase 4b: Deployment blocker with baseline management.

This module implements the regression gate that:
  1. Manages baseline metrics storage (.ci/regression_baseline.json)
  2. Runs full corpus replay
  3. Detects regressions vs baseline
  4. Produces exit code 0 (pass) or 1 (fail)
  5. Prints summary table + detailed issues

Usage (in CI/CD):
    python -m pytest server/tests/regression/ci_gate.py -v

Or standalone:
    python -c "from server.tests.regression.ci_gate import main; main()"

Schema version: 1
"""

from __future__ import annotations

import json
import logging
import pathlib
import sys
import time
from typing import Dict, Optional, Tuple

from server.tests.regression.runner import (
    RegressionResult,
    CorpusMetrics,
    RegressionRunner,
    ScenarioStatus,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Baseline Management
# ============================================================================


BASELINE_PATH = pathlib.Path(__file__).parent.parent.parent.parent / ".ci" / "regression_baseline.json"
SCENARIOS_DIR = pathlib.Path(__file__).parent / "scenarios"


def ensure_baseline_dir() -> None:
    """Create .ci directory if it doesn't exist."""
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_baseline() -> Optional[Dict[str, RegressionResult]]:
    """
    Load baseline metrics from .ci/regression_baseline.json.
    
    Returns: Dict[scenario_id] -> RegressionResult, or None if baseline doesn't exist
    """
    if not BASELINE_PATH.exists():
        logger.info(f"No baseline found at {BASELINE_PATH} (first run)")
        return None
    
    try:
        with open(BASELINE_PATH) as f:
            baseline_data = json.load(f)
        
        # Parse baseline results
        baseline_results = {}
        for scenario_id, result_dict in baseline_data.get("results", {}).items():
            baseline_results[scenario_id] = _dict_to_regression_result(result_dict)
        
        logger.info(f"Loaded baseline with {len(baseline_results)} scenarios")
        return baseline_results
    
    except Exception as exc:
        logger.warning(f"Failed to load baseline: {exc}")
        return None


def save_baseline(
    results: Dict[str, RegressionResult],
    metrics: CorpusMetrics,
) -> None:
    """
    Save baseline metrics to .ci/regression_baseline.json.
    
    This should only be called after a successful gate run.
    """
    ensure_baseline_dir()
    
    baseline_data = {
        "version": "1",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "metrics": {
            "total_scenarios": metrics.total_scenarios,
            "passed_scenarios": metrics.passed_scenarios,
            "failed_scenarios": metrics.failed_scenarios,
            "l1_pass_rate": metrics.l1_pass_rate,
            "l2_pass_rate": metrics.l2_pass_rate,
            "l3_pass_rate": metrics.l3_pass_rate,
            "avg_overall_score": metrics.avg_overall_score,
            "avg_latency_ms": metrics.avg_latency_ms,
        },
        "results": {
            scenario_id: result.to_dict()
            for scenario_id, result in results.items()
        },
    }
    
    with open(BASELINE_PATH, "w") as f:
        json.dump(baseline_data, f, indent=2)
    
    logger.info(f"Baseline saved to {BASELINE_PATH}")


def _dict_to_regression_result(d: Dict) -> RegressionResult:
    """Convert dict back to RegressionResult."""
    return RegressionResult(
        scenario_id=d["scenario_id"],
        overall_status=ScenarioStatus(d["overall_status"]),
        overall_score=d["overall_score"],
        l1_score=d.get("l1_score", 0.0),
        l2_score=d.get("l2_score", 0.0),
        l3_score=d.get("l3_score", 0.0),
        execution_spans=d.get("execution_spans", []),
        per_turn_latencies_ms=d.get("per_turn_latencies_ms", []),
        total_latency_ms=d.get("total_latency_ms", 0.0),
        issues=d.get("issues", []),
        bot_responses=d.get("bot_responses", []),
        tools_called=d.get("tools_called", []),
        timestamp=d.get("timestamp", ""),
        seed=d.get("seed", 0),
    )


# ============================================================================
# Gate Logic
# ============================================================================


class RegressionGate:
    """CI gate that blocks deployments on regressions."""
    
    REGRESSION_THRESHOLD_PCT = 5.0
    
    def __init__(self, scenarios_dir: Optional[pathlib.Path] = None):
        """Initialize gate with scenarios directory."""
        self.scenarios_dir = scenarios_dir or SCENARIOS_DIR
        self.runner = RegressionRunner(seed=42)
    
    def run_gate(self, allow_baseline_update: bool = False) -> Tuple[bool, CorpusMetrics]:
        """
        Run the regression gate.
        
        Args:
            allow_baseline_update: if True, save baseline after successful run
        
        Returns:
            (passed: bool, metrics: CorpusMetrics)
        """
        logger.info("=" * 80)
        logger.info("REGRESSION GATE: Starting full-corpus replay")
        logger.info("=" * 80)
        
        # Load baseline (if exists)
        baseline_results = load_baseline()
        
        # Run corpus replay
        current_results, metrics = self.runner.run_full_corpus(
            self.scenarios_dir,
            baseline_results=baseline_results,
        )
        
        # Determine gate result
        gate_passed = self._check_gate_conditions(metrics)
        
        # Print report
        self._print_report(current_results, metrics, baseline_results, gate_passed)
        
        # Save new baseline if gate passed and allowed
        if gate_passed and allow_baseline_update:
            save_baseline(current_results, metrics)
        
        return (gate_passed, metrics)
    
    def _check_gate_conditions(self, metrics: CorpusMetrics) -> bool:
        """
        Check gate conditions:
          - No new failures
          - No phase regressions >5%
        
        Returns: True if gate passes, False otherwise
        """
        # Check 1: No new failures
        if metrics.new_failures:
            logger.error(f"GATE FAIL: {len(metrics.new_failures)} new failures")
            return False
        
        # Check 2: No score drops >threshold
        if metrics.score_drops:
            worst_drop = max(metrics.score_drops.values())
            if worst_drop > self.REGRESSION_THRESHOLD_PCT:
                logger.error(f"GATE FAIL: Worst score drop {worst_drop:.1f}% (threshold {self.REGRESSION_THRESHOLD_PCT}%)")
                return False
        
        # Check 3: At least 90% scenarios passing L1
        if metrics.l1_pass_rate < 90.0:
            logger.error(f"GATE FAIL: L1 pass rate {metrics.l1_pass_rate:.1f}% (threshold 90%)")
            return False
        
        logger.info("GATE PASS: All conditions met")
        return True
    
    def _print_report(
        self,
        results: Dict[str, RegressionResult],
        metrics: CorpusMetrics,
        baseline_results: Optional[Dict[str, RegressionResult]],
        gate_passed: bool,
    ) -> None:
        """Print human-readable regression report."""
        print("\n" + "=" * 80)
        print("REGRESSION GATE REPORT")
        print("=" * 80)
        
        # Summary table
        print("\n[SUMMARY]")
        print(f"  Total scenarios:          {metrics.total_scenarios}")
        print(f"  Passed:                   {metrics.passed_scenarios} ({100*metrics.passed_scenarios/metrics.total_scenarios:.1f}%)")
        print(f"  Failed:                   {metrics.failed_scenarios} ({100*metrics.failed_scenarios/metrics.total_scenarios:.1f}%)")
        print(f"  Avg overall score:        {metrics.avg_overall_score:.2f}")
        print(f"  Avg latency:              {metrics.avg_latency_ms:.0f}ms")
        
        print("\n[LAYER PASS RATES]")
        print(f"  L1 (Deterministic):       {metrics.l1_pass_rate:.1f}%")
        print(f"  L2 (LLM Judge):           {metrics.l2_pass_rate:.1f}%")
        print(f"  L3 (Span-Level):          {metrics.l3_pass_rate:.1f}%")
        
        # Gate result
        gate_status = "✓ PASS" if gate_passed else "✗ FAIL"
        print(f"\n[GATE RESULT] {gate_status}")
        
        # New failures
        if metrics.new_failures:
            print(f"\n[NEW FAILURES] ({len(metrics.new_failures)})")
            for scenario_id in sorted(metrics.new_failures):
                result = results[scenario_id]
                issues_str = "; ".join(result.issues[:2])
                if len(result.issues) > 2:
                    issues_str += f"; +{len(result.issues)-2} more"
                print(f"  ✗ {scenario_id}")
                if issues_str:
                    print(f"    Issues: {issues_str}")
        
        # Score drops
        if metrics.score_drops:
            print(f"\n[SCORE DROPS] ({len(metrics.score_drops)})")
            for scenario_id, drop_pct in sorted(
                metrics.score_drops.items(),
                key=lambda x: -x[1]
            )[:5]:  # Top 5
                result = results[scenario_id]
                baseline = baseline_results.get(scenario_id) if baseline_results else None
                print(f"  ⬇ {scenario_id}: {drop_pct:+.1f}%")
                if baseline:
                    print(f"    Baseline score: {baseline.overall_score:.2f} → Current: {result.overall_score:.2f}")
        
        # Failed scenarios detail
        failed_by_layer = {"L1": [], "L2": [], "L3": []}
        for scenario_id, result in results.items():
            if result.overall_status == ScenarioStatus.FAIL:
                if result.l1_score < 0.9:
                    failed_by_layer["L1"].append(scenario_id)
                if result.l2_score < 0.9:
                    failed_by_layer["L2"].append(scenario_id)
                if result.l3_score < 0.9:
                    failed_by_layer["L3"].append(scenario_id)
        
        if any(failed_by_layer.values()):
            print(f"\n[FAILURES BY LAYER]")
            for layer in ["L1", "L2", "L3"]:
                if failed_by_layer[layer]:
                    print(f"  {layer}: {len(failed_by_layer[layer])} scenarios")
                    for scenario_id in failed_by_layer[layer][:3]:
                        result = results[scenario_id]
                        issues_str = "; ".join(result.issues[:1])
                        print(f"    - {scenario_id}")
                        if issues_str:
                            print(f"      {issues_str[:80]}")
        
        print("\n" + "=" * 80)


# ============================================================================
# Pytest Integration
# ============================================================================


def test_regression_gate(tmp_path=None):
    """
    Pytest test function for regression gate.
    
    Run with: pytest server/tests/regression/ci_gate.py -v
    
    This allows CI systems to easily integrate the gate as a test.
    """
    gate = RegressionGate()
    passed, metrics = gate.run_gate(allow_baseline_update=True)
    
    assert passed, (
        f"Regression gate failed: "
        f"{metrics.failed_scenarios} failures, "
        f"{len(metrics.new_failures)} new"
    )


# ============================================================================
# Standalone CLI
# ============================================================================


def main() -> int:
    """
    Standalone CLI entry point.
    
    Returns: 0 on pass, 1 on fail
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    
    gate = RegressionGate()
    passed, metrics = gate.run_gate(allow_baseline_update=False)
    
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
