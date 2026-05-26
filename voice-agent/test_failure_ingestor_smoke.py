#!/usr/bin/env python3
"""
Smoke test for FailureIngestor integration.
Verifies that failures are correctly ingested and recorded.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "/home/charles2/sailly-browser-demo")

from server.failure_ingestor import FailureIngestor
from server.validation.known_issues_advisor import KnownIssuesAdvisor


def test_failure_ingestor():
    """Test basic FailureIngestor functionality."""
    print("\n" + "="*70)
    print("SMOKE TEST: FailureIngestor")
    print("="*70)

    # Initialize
    ingestor = FailureIngestor()
    print("✓ FailureIngestor initialized")

    # Test 1: Ingest a sample failure
    test_failure = {
        "scenario_id": "B1.2_neutral",
        "call_sid": "demo-test-123",
        "composite_score": 45.0,
        "tools_expected": ["get_menu", "verify_address"],
        "tools_called": ["get_menu"],
        "achtung_flags": [
            {"flag": "Achtung Sailly: DATUM_FALSCH"},
            {"flag": "Achtung Sailly: BOT_LOOP"},
        ],
        "failure_reasons": ["Wrong date confirmed", "Address validation loop"],
        "passed": False,
        "source": "validation",
    }

    issue_id = ingestor.ingest_failure(test_failure)
    print(f"✓ Failure ingested, issue_id: {issue_id}")

    # Test 2: Verify auto-detected issue was created
    advisor = KnownIssuesAdvisor()
    auto_issues = [i for i in advisor._issues if i.get("category") == "auto_detected"]
    print(f"✓ Auto-detected issues in database: {len(auto_issues)}")

    if auto_issues:
        latest = auto_issues[-1]
        print(f"  Latest auto-detected issue:")
        print(f"    ID: {latest['id']}")
        print(f"    Title: {latest['title']}")
        print(f"    Flags: {latest['achtung_flags']}")
        print(f"    Root cause: {latest['root_cause']}")

    # Test 3: Verify daily report was created
    today = datetime.utcnow().strftime("%Y-%m-%d")
    daily_report_path = Path(f"/tmp/daily_failures/failures_{today}.json")
    if daily_report_path.exists():
        data = json.loads(daily_report_path.read_text())
        print(f"✓ Daily report created: {daily_report_path}")
        print(f"  Entries: {len(data)}")
        if data:
            latest_entry = data[-1]
            print(f"  Latest entry:")
            print(f"    Scenario: {latest_entry['scenario_id']}")
            print(f"    Score: {latest_entry['composite_score']}")
            print(f"    Issue: {latest_entry['matched_issue_id']}")
    else:
        print(f"✗ Daily report not found: {daily_report_path}")
        return False

    # Test 4: Test passed=True scenario (should skip ingestion)
    passed_scenario = {
        **test_failure,
        "passed": True,
        "scenario_id": "B1.2_elderly",
    }
    result = ingestor.ingest_failure(passed_scenario)
    if result is None:
        print("✓ Passed scenario correctly skipped")
    else:
        print(f"✗ Passed scenario should have been skipped, got {result}")
        return False

    print("\n" + "="*70)
    print("SMOKE TEST PASSED")
    print("="*70 + "\n")
    return True


if __name__ == "__main__":
    try:
        success = test_failure_ingestor()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ SMOKE TEST FAILED: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
