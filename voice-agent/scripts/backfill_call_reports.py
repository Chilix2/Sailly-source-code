#!/usr/bin/env python3
"""
Backfill call reports for all calls from a given date.

Generates both MD and JSON reports for each call and saves them to:
  call_reports/YYYY-MM-DD/HH/call_sid.md
  call_reports/YYYY-MM-DD/HH/call_sid.json

Usage:
  cd sailly-browser-demo
  set -a && source .env && set +a
  ./venv/bin/python scripts/backfill_call_reports.py --date 2026-04-28
  ./venv/bin/python scripts/backfill_call_reports.py --date 2026-04-27 --date 2026-04-28
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


async def backfill(date_str: str) -> None:
    from dotenv import load_dotenv
    from server.call_report.builder import fetch_call_report_bundle, build_call_report_markdown
    from server.database import get_pool

    load_dotenv(_ROOT / ".env")

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Query all calls from the given date
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        rows = await conn.fetch(
            """
            SELECT call_sid, started_at
            FROM google_calls
            WHERE DATE(started_at AT TIME ZONE 'UTC') = $1::date
            ORDER BY started_at ASC
            """,
            date_obj,
        )

    if not rows:
        print(f"No calls found for {date_str}")
        return

    print(f"Found {len(rows)} calls for {date_str}")

    for i, row in enumerate(rows, start=1):
        call_sid = row["call_sid"]
        try:
            print(f"[{i}/{len(rows)}] Generating reports for {call_sid}...", end=" ", flush=True)

            bundle = await fetch_call_report_bundle(call_sid)
            md_body = await build_call_report_markdown(call_sid, include_journal=False, journal_lines=200)

            # Determine folder from the call's started_at time
            started_at = row["started_at"]
            folder = Path("call_reports") / started_at.strftime("%Y-%m-%d") / started_at.strftime("%H")
            folder.mkdir(parents=True, exist_ok=True)

            # Write both formats
            md_file = folder / f"{call_sid}.md"
            json_file = folder / f"{call_sid}.json"

            md_file.write_text(md_body, encoding="utf-8")
            json_file.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")

            print(f"✓ saved to {folder}")

        except Exception as e:
            print(f"✗ error: {e}")

    print(f"\nBackfill complete for {date_str}")


def main() -> None:
    p = argparse.ArgumentParser(description="Backfill call reports from a given date.")
    p.add_argument(
        "--date",
        required=True,
        help="Date in YYYY-MM-DD format, e.g., 2026-04-28",
    )
    args = p.parse_args()

    # Validate date format
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print(f"Invalid date format: {args.date}. Use YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(backfill(args.date))


if __name__ == "__main__":
    main()
