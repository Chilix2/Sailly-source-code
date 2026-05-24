"""
Report Writer -- Generates per-phase JSON reports, summaries, heatmaps, and prompt patches.

Outputs:
  - phase{N}_{category}.json: Individual phase results
  - summary.json: Overall stats, cost, seeds, flaky list
  - latency_heatmap.json: P50/P95 per category
  - tier{N}_prompt_patch.diff: Unified diffs for failed prompts
  - competitor_comparison.json: Gemini vs OpenAI side-by-side
  - raw_transcripts/: Per-scenario turn transcripts
"""

import json
import os
import logging
from dataclasses import asdict, dataclass
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path
import difflib

logger = logging.getLogger(__name__)


@dataclass
class PhaseStats:
    """Per-phase aggregated statistics."""
    phase: str
    total_scenarios: int
    pass_count: int
    fail_count: int
    flaky_count: int
    pass_rate: float
    avg_latency_ms: float
    avg_overall_score: float
    categories: Dict[str, Dict[str, Any]]  # category -> {pass_rate, avg_score, ...}


@dataclass
class SummaryMetrics:
    """Top-level summary metrics."""
    test_run_id: str
    timestamp: str
    seed: int
    total_cost_usd: float
    total_scenarios_run: int
    total_passes: int
    total_failures: int
    total_flaky: int
    overall_pass_rate: float
    overall_avg_score: float
    phase_gates_passed: Dict[str, bool]  # phase -> gate_passed
    flaky_scenarios: List[str]  # List of flaky scenario IDs
    top_failure_reasons: Dict[str, int]  # reason -> count


class ReportWriter:
    """
    Generates comprehensive reports from test results.
    """

    def __init__(self, output_dir: str, run_id: str, seed: int = 42):
        """
        Args:
            output_dir: Base output directory for reports
            run_id: Unique test run identifier
            seed: Random seed for reproducibility
        """
        self.output_dir = output_dir
        self.run_id = run_id
        self.seed = seed
        self.timestamp = datetime.now().isoformat()

        # Create output directory structure
        self.base_path = Path(output_dir) / f"audio_training_loop_{run_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.transcripts_dir = self.base_path / "raw_transcripts"
        self.transcripts_dir.mkdir(exist_ok=True)

        logger.info(f"Report output directory: {self.base_path}")

    def write_phase_report(
        self,
        phase: str,
        aggregated_scores: Dict[str, Any],
        cost_usd: float,
    ) -> None:
        """
        Write per-phase JSON report.

        Args:
            phase: Phase name (e.g., "tier1", "tier2_reservations")
            aggregated_scores: Dict of scenario_id -> AggregatedScenarioScore
            cost_usd: Cost of running this phase
        """
        phase_file = self.base_path / f"phase_{phase}.json"

        def _sv(s, key, default=0):
            """Get a value from either a dict or dataclass safely."""
            if isinstance(s, dict):
                return s.get(key, default)
            return getattr(s, key, default)

        # Compute statistics
        pass_count  = sum(1 for s in aggregated_scores.values() if _sv(s, "pass_count") == _sv(s, "n_runs", 3))
        fail_count  = sum(1 for s in aggregated_scores.values() if _sv(s, "pass_count") == 0)
        flaky_count = sum(1 for s in aggregated_scores.values() if 0 < _sv(s, "pass_count") < _sv(s, "n_runs", 3))

        pass_rate = pass_count / len(aggregated_scores) if aggregated_scores else 0.0

        avg_overall = (
            sum(_sv(s, "overall_mean") for s in aggregated_scores.values())
            / len(aggregated_scores)
            if aggregated_scores else 0.0
        )

        # Group by category
        categories = {}
        for scenario_id, score in aggregated_scores.items():
            cat = _sv(score, "category", "unknown")
            if cat not in categories:
                categories[cat] = {"pass_count": 0, "fail_count": 0, "scores": []}
            if _sv(score, "pass_count") == _sv(score, "n_runs", 3):
                categories[cat]["pass_count"] += 1
            else:
                categories[cat]["fail_count"] += 1
            categories[cat]["scores"].append(_sv(score, "overall_mean"))

        report = {
            "phase": phase,
            "timestamp": self.timestamp,
            "cost_usd": cost_usd,
            "statistics": {
                "total_scenarios": len(aggregated_scores),
                "pass_count": pass_count,
                "fail_count": fail_count,
                "flaky_count": flaky_count,
                "pass_rate": pass_rate,
                "avg_overall_score": avg_overall,
            },
            "categories": {
                cat: {
                    "pass_count": stats["pass_count"],
                    "fail_count": stats["fail_count"],
                    "avg_score": sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0,
                }
                for cat, stats in categories.items()
            },
            "scenarios": aggregated_scores,
        }

        with open(phase_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"Wrote phase report: {phase_file}")

    def write_summary(
        self,
        all_aggregated: Dict[str, Any],
        phase_gates: Dict[str, bool],
        total_cost_usd: float,
        failure_reasons: Dict[str, int],
    ) -> None:
        """
        Write top-level summary.json.

        Args:
            all_aggregated: All scenario aggregated scores
            phase_gates: {phase: gate_passed}
            total_cost_usd: Total test run cost
            failure_reasons: {reason: count}
        """
        def _sv(s, key, default=0):
            if isinstance(s, dict):
                return s.get(key, default)
            return getattr(s, key, default)

        flaky_scenarios = [
            sid for sid, score in all_aggregated.items()
            if 0 < _sv(score, "pass_count") < _sv(score, "n_runs", 3)
        ]

        total_pass  = sum(1 for s in all_aggregated.values() if _sv(s, "pass_count") == _sv(s, "n_runs", 3))
        total_fail  = sum(1 for s in all_aggregated.values() if _sv(s, "pass_count") == 0)
        total_flaky = len(flaky_scenarios)

        overall_pass_rate = total_pass / len(all_aggregated) if all_aggregated else 0.0
        overall_avg_score = (
            sum(_sv(s, "overall_mean") for s in all_aggregated.values())
            / len(all_aggregated)
            if all_aggregated
            else 0.0
        )

        summary = {
            "test_run_id": self.run_id,
            "timestamp": self.timestamp,
            "seed": self.seed,
            "total_cost_usd": total_cost_usd,
            "statistics": {
                "total_scenarios_run": len(all_aggregated),
                "total_passes": total_pass,
                "total_failures": total_fail,
                "total_flaky": total_flaky,
                "overall_pass_rate": overall_pass_rate,
                "overall_avg_score": overall_avg_score,
            },
            "phase_gates": phase_gates,
            "flaky_scenarios": flaky_scenarios,
            "top_failure_reasons": dict(sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)[:10]),
        }

        summary_file = self.base_path / "summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info(f"Wrote summary report: {summary_file}")

    def write_latency_heatmap(
        self,
        all_aggregated: Dict[str, Any],
    ) -> None:
        """
        Write latency_heatmap.json with P50/P95 per category.

        Args:
            all_aggregated: All scenario aggregated scores
        """
        # Compute per-category latency percentiles
        latencies_by_category = {}
        for scenario_id, score in all_aggregated.items():
            cat = score.get("category", "unknown")
            if cat not in latencies_by_category:
                latencies_by_category[cat] = []
            latencies_by_category[cat].append(score.get("latency_mean", 0))

        heatmap = {}
        for cat, latencies in latencies_by_category.items():
            if latencies:
                sorted_latencies = sorted(latencies)
                p50 = sorted_latencies[len(sorted_latencies) // 2]
                p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
                heatmap[cat] = {
                    "p50_ms": p50,
                    "p95_ms": p95,
                    "count": len(latencies),
                }

        heatmap_file = self.base_path / "latency_heatmap.json"
        with open(heatmap_file, "w") as f:
            json.dump(heatmap, f, indent=2)

        logger.info(f"Wrote latency heatmap: {heatmap_file}")

    def write_prompt_patch(
        self,
        phase: str,
        original_prompt: str,
        suggested_prompt: str,
    ) -> None:
        """
        Write unified diff for prompt patches (manual apply only).

        Args:
            phase: Phase name (e.g., "tier1")
            original_prompt: Original prompt text
            suggested_prompt: Suggested updated prompt
        """
        diff = difflib.unified_diff(
            original_prompt.splitlines(keepends=True),
            suggested_prompt.splitlines(keepends=True),
            fromfile=f"{phase}_prompt_original.txt",
            tofile=f"{phase}_prompt_suggested.txt",
        )

        patch_file = self.base_path / f"{phase}_prompt_patch.diff"
        with open(patch_file, "w") as f:
            f.writelines(diff)

        logger.info(f"Wrote prompt patch: {patch_file}")

    def write_competitor_comparison(
        self,
        comparison_data: Dict[str, Any],
    ) -> None:
        """
        Write competitor_comparison.json with Gemini vs OpenAI metrics.

        Args:
            comparison_data: {metric: {gemini: value, openai: value}}
        """
        comparison_file = self.base_path / "competitor_comparison.json"

        with open(comparison_file, "w") as f:
            json.dump(comparison_data, f, indent=2)

        logger.info(f"Wrote competitor comparison: {comparison_file}")

    def write_raw_transcript(
        self,
        scenario_id: str,
        run_number: int,
        transcript_lines: List[str],
    ) -> None:
        """
        Write raw transcript for a scenario run.

        Args:
            scenario_id: Scenario ID
            run_number: Run number
            transcript_lines: Lines of conversation
        """
        transcript_file = self.transcripts_dir / f"{scenario_id}_run{run_number}.txt"

        with open(transcript_file, "w") as f:
            for line in transcript_lines:
                f.write(line + "\n")

        logger.debug(f"Wrote transcript: {transcript_file}")

    def finalize_report(self) -> str:
        """
        Finalize report and return output directory path.

        Returns:
            Path to report directory
        """
        # Create index.md for easy navigation
        index_file = self.base_path / "README.md"
        with open(index_file, "w") as f:
            f.write(f"# Audio Training Loop Test Report\n\n")
            f.write(f"**Run ID:** {self.run_id}\n")
            f.write(f"**Timestamp:** {self.timestamp}\n")
            f.write(f"**Seed:** {self.seed}\n\n")
            f.write("## Report Files\n\n")
            f.write("- `summary.json` - Top-level statistics and pass rates\n")
            f.write("- `phase_*.json` - Per-phase detailed results\n")
            f.write("- `latency_heatmap.json` - Latency P50/P95 by category\n")
            f.write("- `*_prompt_patch.diff` - Suggested prompt improvements (manual apply)\n")
            f.write("- `competitor_comparison.json` - Gemini vs OpenAI metrics\n")
            f.write("- `raw_transcripts/` - Detailed conversation logs\n")

        logger.info(f"Report finalized: {self.base_path}")
        return str(self.base_path)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    writer = ReportWriter(
        output_dir="/tmp",
        run_id="test_run_001",
        seed=42,
    )

    # Example aggregated scores
    mock_aggregated = {
        "t1-greeting-01": {
            "scenario_id": "t1-greeting-01",
            "category": "greeting",
            "overall_mean": 95.5,
            "latency_mean": 500,
            "pass_count": 3,
            "n_runs": 3,
        },
        "t1-greeting-02": {
            "scenario_id": "t1-greeting-02",
            "category": "greeting",
            "overall_mean": 92.0,
            "latency_mean": 600,
            "pass_count": 2,
            "n_runs": 3,
        },
    }

    # Write phase report
    writer.write_phase_report(
        phase="tier1",
        aggregated_scores=mock_aggregated,
        cost_usd=0.50,
    )

    # Write summary
    writer.write_summary(
        all_aggregated=mock_aggregated,
        phase_gates={"tier1": True, "tier2": False},
        total_cost_usd=0.50,
        failure_reasons={"missing_tool": 1, "wrong_language": 0},
    )

    # Write latency heatmap
    writer.write_latency_heatmap(mock_aggregated)

    # Finalize
    output_path = writer.finalize_report()
    print(f"✓ Report written to: {output_path}")
