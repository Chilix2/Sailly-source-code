#!/usr/bin/env python3
"""
Per-minute cron job to generate call reports for newly detected calls.

Tracks the last processed timestamp in /tmp/call_report_last_run.txt and queries for calls
created after that timestamp. Generates both MD and JSON reports for each new call.

Usage:
  # Run manually:
  cd sailly-browser-demo
  set -a && source .env && set +a
  ./venv/bin/python scripts/cron/generate_new_call_reports.py

  # Or add to crontab:
  * * * * * cd /home/charles2/sailly-browser-demo && set -a && source .env && set +a && ./venv/bin/python scripts/cron/generate_new_call_reports.py >> /tmp/call-report-cron.log 2>&1
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


LAST_RUN_FILE = Path("/tmp/call_report_last_run.txt")


def get_last_run_time() -> datetime:
    """Read the last run timestamp from disk, or return a default."""
    if LAST_RUN_FILE.exists():
        try:
            ts_str = LAST_RUN_FILE.read_text().strip()
            return datetime.fromisoformat(ts_str)
        except Exception as e:
            print(f"[WARN] Failed to read last run time: {e}", file=sys.stderr)
    # Default: 1 hour ago (to catch any backlog)
    return datetime.now(timezone.utc).replace(hour=max(0, datetime.now(timezone.utc).hour - 1))


def save_last_run_time(ts: datetime) -> None:
    """Write the current timestamp to disk."""
    try:
        LAST_RUN_FILE.write_text(ts.isoformat(), encoding="utf-8")
    except Exception as e:
        print(f"[WARN] Failed to save last run time: {e}", file=sys.stderr)


async def generate_new_reports() -> None:
    from dotenv import load_dotenv
    from server.call_report.builder import fetch_call_report_bundle, build_call_report_markdown
    from server.database import get_pool

    load_dotenv(_ROOT / ".env")

    last_run = get_last_run_time()
    print(f"[{datetime.now(timezone.utc).isoformat()}] Checking for calls since {last_run.isoformat()}")

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Query all calls created after last run timestamp
        rows = await conn.fetch(
            """
            SELECT call_sid, started_at
            FROM google_calls
            WHERE started_at > $1
            ORDER BY started_at ASC
            """,
            last_run,
        )

    if not rows:
        print(f"No new calls since {last_run.isoformat()}")
        return

    print(f"Found {len(rows)} new calls")

    for i, row in enumerate(rows, start=1):
        call_sid = row["call_sid"]
        try:
            print(f"  [{i}/{len(rows)}] {call_sid}...", end=" ", flush=True)

            bundle = await fetch_call_report_bundle(call_sid)
            md_body = await build_call_report_markdown(call_sid, include_journal=False, journal_lines=200)

            # Determine folder from the call's started_at time
            started_at = row["started_at"]
            folder = Path("call_reports") / started_at.strftime("%Y-%m-%d") / started_at.strftime("%H")
            folder.mkdir(parents=True, exist_ok=True)
            # Ensure group-write so any cron user can update the folder
            try:
                folder.chmod(0o2775)
                folder.parent.chmod(0o2775)
            except PermissionError:
                pass

            # Write both formats
            md_file = folder / f"{call_sid}.md"
            json_file = folder / f"{call_sid}.json"

            md_file.write_text(md_body, encoding="utf-8")
            json_file.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")

            print(f"✓ {folder.name}/")

        except Exception as e:
            print(f"✗ {e}")

    # Update last run timestamp to now
    now = datetime.now(timezone.utc)
    save_last_run_time(now)
    print(f"Updated last run time to {now.isoformat()}")


def main() -> None:
    asyncio.run(generate_new_reports())


if __name__ == "__main__":
    main()
