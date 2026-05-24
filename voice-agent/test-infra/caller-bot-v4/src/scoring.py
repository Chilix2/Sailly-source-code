"""
src/scoring.py — Per-call scoring and aggregate reporting

Generates the Final Scoring Sheet per call and aggregate thresholds.
"""
import json
import logging
from dataclasses import asdict
from typing import Optional

logger = logging.getLogger(__name__)


class Scorer:
    """Produces scoring sheets and aggregate reports."""

    @staticmethod
    def generate_call_report_md(result: dict) -> str:
        """Generate per-call markdown report (Final Scoring Sheet format)."""
        verification = result.get("verification_result")
        signals = result.get("signals", {})

        lines = [
            "# Sailly v4 Caller-Bot Scoring Sheet",
            "",
            f"## Call Summary",
            f"- **Call ID**: {result.get('call_sid', 'N/A')}",
            f"- **Scenario ID**: {result.get('scenario_id', 'N/A')}",
            f"- **Pass/Fail**: {'PASS' if result.get('passed') else 'FAIL'}",
            f"- **Turn Count**: {result.get('turn_count', 0)}",
            f"- **Error**: {result.get('error', 'None')}",
            "",
            "## Verification Results",
        ]

        if verification:
            lines.extend([
                f"- **Status**: {'PASS' if verification.passed else 'FAIL'}",
                f"- **Failures**: {len(verification.failures)}",
                f"- **Warnings**: {len(verification.warnings)}",
                "",
                "### Failures",
            ])
            if verification.failures:
                for failure in verification.failures:
                    lines.append(f"  - {failure}")
            else:
                lines.append("  (none)")

            lines.append("")
            lines.append("### Warnings")
            if verification.warnings:
                for warning in verification.warnings:
                    lines.append(f"  - {warning}")
            else:
                lines.append("  (none)")

        lines.extend([
            "",
            "## Signals",
            f"- **One LLM per turn**: {signals.get('one_llm_per_turn', 'N/A')}",
            f"- **Readback present**: {signals.get('has_readback', 'N/A')}",
            f"- **Commit gate timing ok**: {signals.get('commit_gate_timing_ok', 'N/A')}",
            f"- **Latency acceptable**: {signals.get('latency_acceptable', 'N/A')}",
            "",
            "## Latencies (ms)",
        ])

        if result.get("latencies_ms"):
            latencies = result["latencies_ms"]
            lines.extend([
                f"- **Min**: {min(latencies)}",
                f"- **Max**: {max(latencies)}",
                f"- **Mean**: {sum(latencies) // len(latencies)}",
            ])
        else:
            lines.append("  (no latency data)")

        lines.extend([
            "",
            "## Tools Fired",
            f"- **Total**: {len(result.get('tools_fired', []))}",
            f"- **Tools**: {', '.join(set(result.get('tools_fired', [])))}",
            "",
            "## Transcript",
        ])

        bot_responses = result.get("bot_responses", [])
        user_utterances = result.get("user_utterances", [])

        if bot_responses:
            lines.append("### Greeting")
            lines.append(f"**Bot**: {bot_responses[0][:120]}")

            for i, (user, bot) in enumerate(
                zip(user_utterances, bot_responses[1:] if len(bot_responses) > 1 else [])
            ):
                lines.append("")
                lines.append(f"### Turn {i + 1}")
                lines.append(f"**User**: {user[:120]}")
                lines.append(f"**Bot**: {bot[:120]}")

        return "\n".join(lines)

    @staticmethod
    def generate_aggregate_report_md(results: list[dict]) -> str:
        """Generate aggregate markdown report."""
        passed = sum(1 for r in results if r.get("passed"))
        failed = len(results) - passed

        lines = [
            "# Sailly v4 Caller-Bot Aggregate Report",
            "",
            f"## Summary",
            f"- **Total Scenarios**: {len(results)}",
            f"- **Passed**: {passed}",
            f"- **Failed**: {failed}",
            f"- **Pass Rate**: {100 * passed // len(results)}%",
            "",
            "## Thresholds",
            "- **Internal Alpha**: smoke 10/10, false_commits=0, legacy_hits=0",
            "- **Supervised Beta**: core ≥90%, false_commits=0, false_success=0, readback ≥95%, end_call ≥95%",
            "- **Production**: full ≥95%, critical safety 100%, messy ≥90%, legacy_hits=0, dup_tools=0, commit_without_confirmation=0",
            "",
            "## Results by Scenario",
        ]

        for result in results:
            scenario_id = result.get("scenario_id", "unknown")
            status = "PASS" if result.get("passed") else "FAIL"
            turn_count = result.get("turn_count", 0)
            error = result.get("error", "")
            lines.append(
                f"- [{status}] {scenario_id} (turns={turn_count}) {f'[{error}]' if error else ''}"
            )

        return "\n".join(lines)

    @staticmethod
    def generate_aggregate_json(results: list[dict]) -> dict:
        """Generate aggregate JSON report."""
        return {
            "total": len(results),
            "passed": sum(1 for r in results if r.get("passed")),
            "failed": sum(1 for r in results if not r.get("passed")),
            "pass_rate": sum(1 for r in results if r.get("passed")) / len(results) if results else 0,
            "results": [
                {
                    "scenario_id": r.get("scenario_id"),
                    "call_sid": r.get("call_sid"),
                    "passed": r.get("passed"),
                    "turn_count": r.get("turn_count"),
                    "error": r.get("error"),
                    "tools_fired": r.get("tools_fired", []),
                    "latencies_ms": r.get("latencies_ms", []),
                    "signals": r.get("signals", {}),
                }
                for r in results
            ],
        }
