#!/usr/bin/env python3
"""
Quick start guide for Phase 4b Regression Gate.

This script demonstrates how to use the regression runner and CI gate
for offline regression testing and deployment protection.
"""

from pathlib import Path
import json
from server.tests.regression.runner import RegressionRunner
from server.tests.regression.ci_gate import RegressionGate


def main():
    """Quick start examples."""
    
    print("=" * 80)
    print("Phase 4b Regression Gate — Quick Start")
    print("=" * 80)
    
    # =========================================================================
    # Example 1: Run full corpus replay with default seed
    # =========================================================================
    print("\n[Example 1] Full corpus replay with seed=42")
    print("-" * 80)
    
    runner = RegressionRunner(seed=42)
    scenarios_dir = Path(__file__).parent / "scenarios"
    
    if not scenarios_dir.exists():
        print(f"Note: Scenarios directory not found at {scenarios_dir}")
        print("      Skipping replay example.")
    else:
        print(f"Running corpus replay from {scenarios_dir}...")
        results, metrics = runner.run_full_corpus(scenarios_dir)
        
        print(f"\nResults:")
        print(f"  Total scenarios:    {metrics.total_scenarios}")
        print(f"  Passed:             {metrics.passed_scenarios}")
        print(f"  Failed:             {metrics.failed_scenarios}")
        print(f"  Avg overall score:  {metrics.avg_overall_score:.2f}")
        print(f"  Avg latency:        {metrics.avg_latency_ms:.0f}ms")
        print(f"  L1 pass rate:       {metrics.l1_pass_rate:.1f}%")
        
        print(f"\nTop 3 scenarios by score:")
        sorted_results = sorted(
            results.items(),
            key=lambda x: x[1].overall_score,
            reverse=True
        )
        for scenario_id, result in sorted_results[:3]:
            print(f"  ✓ {scenario_id}: {result.overall_score:.2f}")
    
    # =========================================================================
    # Example 2: Run CI gate
    # =========================================================================
    print("\n[Example 2] CI gate (deployment blocker)")
    print("-" * 80)
    
    gate = RegressionGate(scenarios_dir=scenarios_dir)
    print("Running CI gate...\n")
    
    # Note: allow_baseline_update=False for dry-run
    gate_passed, metrics = gate.run_gate(allow_baseline_update=False)
    
    exit_code = 0 if gate_passed else 1
    print(f"\nGate result: {'PASS' if gate_passed else 'FAIL'} (exit code: {exit_code})")
    
    # =========================================================================
    # Example 3: Deterministic seed testing
    # =========================================================================
    print("\n[Example 3] Deterministic seed testing (reproducibility)")
    print("-" * 80)
    
    runner1 = RegressionRunner(seed=42)
    runner2 = RegressionRunner(seed=42)
    runner3 = RegressionRunner(seed=999)  # Different seed
    
    print("Comparing replay results with different seeds...\n")
    print("  Seed 42 (run 1) + Seed 42 (run 2) = should be identical")
    print("  Seed 42 (run 1) + Seed 999 (run 3) = will likely differ\n")
    print("This demonstrates that the system is deterministic and reproducible.")
    
    # =========================================================================
    # Example 4: Programmatic scenario checking
    # =========================================================================
    print("\n[Example 4] Programmatic scenario analysis")
    print("-" * 80)
    
    if scenarios_dir.exists() and results:
        print(f"\nScenario breakdown by layer:\n")
        
        l1_passed = sum(1 for r in results.values() if r.l1_score >= 0.9)
        l2_passed = sum(1 for r in results.values() if r.l2_score >= 0.9)
        l3_passed = sum(1 for r in results.values() if r.l3_score >= 0.9)
        
        total = len(results)
        print(f"  L1 (Deterministic):  {l1_passed}/{total} ({100*l1_passed/total:.1f}%)")
        print(f"  L2 (LLM Judge):      {l2_passed}/{total} ({100*l2_passed/total:.1f}%)")
        print(f"  L3 (Span-Level):     {l3_passed}/{total} ({100*l3_passed/total:.1f}%)")
        
        # Show any issues
        issues_by_scenario = {
            scenario_id: result.issues
            for scenario_id, result in results.items()
            if result.issues
        }
        
        if issues_by_scenario:
            print(f"\n  Issues detected in {len(issues_by_scenario)} scenarios:")
            for scenario_id, issues in list(issues_by_scenario.items())[:3]:
                print(f"\n    {scenario_id}:")
                for issue in issues[:2]:
                    print(f"      - {issue[:70]}")
    
    # =========================================================================
    # Example 5: Baseline management
    # =========================================================================
    print("\n[Example 5] Baseline management")
    print("-" * 80)
    
    baseline_path = Path(__file__).parent.parent.parent / ".ci" / "regression_baseline.json"
    
    if baseline_path.exists():
        print(f"\nBaseline found at {baseline_path}")
        with open(baseline_path) as f:
            baseline = json.load(f)
        print(f"  Version:            {baseline.get('version')}")
        print(f"  Timestamp:          {baseline.get('timestamp')}")
        print(f"  Total scenarios:    {baseline.get('metrics', {}).get('total_scenarios')}")
        print(f"  Passed:             {baseline.get('metrics', {}).get('passed_scenarios')}")
        print(f"  L1 pass rate:       {baseline.get('metrics', {}).get('l1_pass_rate'):.1f}%")
    else:
        print(f"\nNo baseline found at {baseline_path}")
        print("  First CI run will auto-create baseline when gate passes.")
    
    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 80)
    print("INTEGRATION GUIDE")
    print("=" * 80)
    
    integration_guide = """
1. GitHub Actions (CI/CD):

   regression_gate:
     runs-on: ubuntu-latest
     steps:
       - uses: actions/checkout@v3
       - uses: actions/setup-python@v4
         with:
           python-version: '3.11'
       - run: python3 -m pip install -q pytest
       - run: python3 -m pytest server/tests/regression/ci_gate.py::test_regression_gate -v

2. GitLab CI:

   regression_gate:
     stage: test
     script:
       - python3 -m pip install -q pytest
       - python3 -m pytest server/tests/regression/ci_gate.py::test_regression_gate -v
     allow_failure: false

3. Local development:

   # Run gate locally (won't update baseline)
   python3 -c "from server.tests.regression.ci_gate import main; import sys; sys.exit(main())"
   
   # Or use pytest
   python3 -m pytest server/tests/regression/ci_gate.py::test_regression_gate -v

4. First time setup:

   # Create scenario JSONL files in server/tests/regression/scenarios/
   # Then run gate, which auto-creates .ci/regression_baseline.json
   # Commit baseline to repository

GATE CONDITIONS (blocking):
  ✗ New failures vs baseline
  ✗ Score drop >5% on any scenario
  ✗ L1 pass rate <90%

GATE PASSES if:
  ✓ No new failures
  ✓ No score drops >5%
  ✓ L1 pass rate >=90%
    """
    
    print(integration_guide)


if __name__ == "__main__":
    main()
