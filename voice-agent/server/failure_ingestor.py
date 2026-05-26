"""
FailureIngestor — central service for capturing and recording failures from validation and production.

Automatically feeds failures into the Known Issues system and generates daily failure reports.
Can be called from:
  - Validation loops (light_validation_loop.py, fix_validation_loop.py)
  - Production code (brain_service.py, future integration)

Usage:
    from server.failure_ingestor import FailureIngestor
    ingestor = FailureIngestor()
    
    # After a scenario fails:
    ingestor.ingest_failure({
        "scenario_id": "B1.2_neutral",
        "call_sid": "demo-abc123",
        "composite_score": 45.0,
        "tools_expected": ["get_menu", "verify_address"],
        "achtung_flags": [{"flag": "Achtung Sailly: DATUM_FALSCH"}],
        "failure_reasons": ["Wrong date confirmed", "Address validation loop"],
        "source": "validation",  # or "production"
    })
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class FailureIngestor:
    """Central service for capturing and recording failures."""

    def __init__(self):
        try:
            from server.validation.known_issues_advisor import KnownIssuesAdvisor
            self.advisor = KnownIssuesAdvisor()
        except ImportError as e:
            logger.warning(f"Could not import KnownIssuesAdvisor: {e}")
            self.advisor = None

        self.output_dir = Path("/tmp/daily_failures")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def ingest_failure(self, metrics: Dict[str, Any]) -> Optional[str]:
        """
        Record a failure from any source (validation or production).

        Args:
            metrics: Dictionary containing scenario/call failure data
                - scenario_id: str (e.g., "B1.2_neutral")
                - call_sid: str (call identifier)
                - composite_score: float (0-100)
                - tools_expected: list[str]
                - tools_called: list[str] (optional)
                - achtung_flags: list[dict] (optional)
                - failure_reasons: list[str] (optional)
                - source: str ("validation" or "production")

        Returns:
            issue_id: str if failure was successfully recorded, None otherwise
        """
        if metrics.get("passed", True):
            # Not a failure, skip
            return None

        try:
            failure_data = {
                "scenario_id": metrics.get("scenario_id", "unknown"),
                "call_sid": metrics.get("call_sid", ""),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "composite_score": metrics.get("composite_score", metrics.get("composite", 0)),
                "tools_expected": metrics.get("tools_expected", []),
                "tools_called": metrics.get("tools_called", []),
                "achtung_flags": metrics.get("achtung_flags", []),
                "failure_reasons": metrics.get("failure_reasons", []),
                "source": metrics.get("source", "production"),
            }

            # Record into known issues database
            issue_id = None
            if self.advisor:
                issue_id = self.advisor.record_failed_call(failure_data)
                logger.info(
                    f"Failure ingested: {failure_data['scenario_id']} | "
                    f"Score: {failure_data['composite_score']} | "
                    f"Issue: {issue_id}"
                )
            else:
                logger.warning("Advisor unavailable, skipping issue recording")

            # Also save to daily report
            self._save_to_daily_report(failure_data, issue_id)

            return issue_id

        except Exception as e:
            logger.error(f"Failed to ingest failure: {e}", exc_info=True)
            return None

    def _save_to_daily_report(self, failure_data: Dict[str, Any], issue_id: Optional[str]) -> None:
        """Append failure to the daily report file."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        file_path = self.output_dir / f"failures_{today}.json"

        try:
            # Read existing data or start fresh
            if file_path.exists():
                data = json.loads(file_path.read_text(encoding="utf-8"))
            else:
                data = []

            # Append this failure with issue reference
            entry = {**failure_data, "matched_issue_id": issue_id}
            data.append(entry)

            # Write back atomically (simple write, not production-grade)
            file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        except Exception as e:
            logger.warning(f"Could not save daily failure report: {e}")
