#!/usr/bin/env python3
"""
Generate a full call analysis markdown report (same structure as demo-*-analysis.md).

Caller-flag phrases (**Achtung Sailly:** / **Attention Sailly:**) in user transcripts are
detected automatically — they annotate what Sailly did wrong when metrics alone are insufficient.

Usage:
  cd sailly-browser-demo
  set -a && source .env && set +a
  ./venv/bin/python scripts/generate_call_report.py demo-11e8600aee44
  ./venv/bin/python scripts/generate_call_report.py demo-11e8600aee44 -o /tmp/report.md
  ./venv/bin/python scripts/generate_call_report.py demo-11e8600aee44 --json -o /tmp/bundle.json
  ./venv/bin/python scripts/generate_call_report.py demo-11e8600aee44 --journal
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Repo root: parent of scripts/
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    p = argparse.ArgumentParser(description="Build Sailly call analysis report from Postgres.")
    p.add_argument("call_sid", help="Call id, e.g. demo-11e8600aee44")
    p.add_argument("-o", "--output", help="Write to file (stdout if omitted for markdown)")
    p.add_argument("--json", action="store_true", help="Emit JSON bundle instead of markdown")
    p.add_argument(
        "--journal",
        action="store_true",
        help="Append filtered journalctl excerpt (requires journalctl on host)",
    )
    p.add_argument("--journal-lines", type=int, default=200, help="Max journal lines to scan")
    args = p.parse_args()

    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")

    async def _run():
        if args.json:
            from server.call_report.builder import fetch_call_report_bundle

            bundle = await fetch_call_report_bundle(args.call_sid)
            text = json.dumps(bundle, indent=2, default=str)
        else:
            from server.call_report.builder import build_call_report_markdown

            text = await build_call_report_markdown(
                args.call_sid,
                include_journal=args.journal,
                journal_lines=args.journal_lines,
            )
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
            print(f"Wrote {args.output} ({len(text)} bytes)", file=sys.stderr)
        else:
            print(text)

    asyncio.run(_run())


if __name__ == "__main__":
    main()
