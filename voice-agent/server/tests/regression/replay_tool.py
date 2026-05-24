"""
Production replay tool — ingest google_turn_metrics into JSONL scenarios.

Reads completed calls from the production postgres database and converts
them into harness-compatible JSONL scenario files. This lets you:

  1. Find calls that expose specific bugs (e.g. tool not fired, forbidden phrase)
  2. Turn them into regression tests that prevent regressions

Usage:
    # List recent production calls
    python -m server.tests.regression.replay_tool list

    # Convert a specific call to JSONL
    python -m server.tests.regression.replay_tool convert CALL_SID

    # Convert last N calls and save to scenarios/
    python -m server.tests.regression.replay_tool batch --limit 20

    # Filter by tool that was (or wasn't) fired
    python -m server.tests.regression.replay_tool batch --tool create_order --limit 10

Options:
    --dsn         Postgres DSN (default: $SAILLY_PG_DSN or postgresql://...)
    --output-dir  Where to write JSONL files (default: scenarios/ next to this file)
    --dry-run     Print but don't write files
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import pathlib
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sailly.replay")

DEFAULT_PG_DSN = os.environ.get(
    "SAILLY_PG_DSN",
    "postgresql://sailly:sailly@localhost:5432/sailly",
)

SCENARIOS_DIR = pathlib.Path(__file__).parent / "scenarios"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _connect(dsn: str):
    try:
        import asyncpg
        return await asyncpg.connect(dsn)
    except ImportError:
        raise RuntimeError("asyncpg not installed — run: pip install asyncpg")


async def list_recent_calls(dsn: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Return summary of recent production calls."""
    conn = await _connect(dsn)
    try:
        rows = await conn.fetch(
            """
            SELECT
                call_sid,
                MIN(created_at) AS call_start,
                MAX(created_at) AS call_end,
                COUNT(*) AS turn_count,
                ARRAY_AGG(DISTINCT jsonb_array_elements_text(
                    CASE WHEN jsonb_typeof(tools_called::jsonb) = 'array'
                         THEN tools_called::jsonb ELSE '[]'::jsonb END
                )) AS all_tools
            FROM google_turn_metrics
            WHERE call_sid IS NOT NULL
            GROUP BY call_sid
            ORDER BY MAX(created_at) DESC
            LIMIT $1
            """,
            limit,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def fetch_call_turns(dsn: str, call_sid: str) -> List[Dict[str, Any]]:
    """Return all turns for a call, ordered by turn_number."""
    conn = await _connect(dsn)
    try:
        rows = await conn.fetch(
            """
            SELECT
                turn_number,
                user_utterance,
                llm_response,
                tools_called,
                latency_ms,
                created_at
            FROM google_turn_metrics
            WHERE call_sid = $1
            ORDER BY turn_number ASC
            """,
            call_sid,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# JSONL conversion
# ---------------------------------------------------------------------------

def _sanitize_name(call_sid: str) -> str:
    """Turn a call_sid into a filename-safe scenario name."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", call_sid)[:40]


def turns_to_jsonl(
    call_sid: str,
    turns: List[Dict[str, Any]],
    description: str = "",
) -> str:
    """Convert a list of DB turns into a JSONL scenario string."""
    lines: List[str] = []

    # Extract all tools fired across all turns
    all_tools: List[str] = []
    for t in turns:
        tools_raw = t.get("tools_called") or "[]"
        if isinstance(tools_raw, str):
            try:
                tools_raw = json.loads(tools_raw)
            except json.JSONDecodeError:
                tools_raw = []
        if isinstance(tools_raw, list):
            all_tools.extend(tools_raw)

    call_start = turns[0].get("created_at") if turns else None
    ts = call_start.strftime("%Y-%m-%d") if isinstance(call_start, datetime) else "unknown"

    meta = {
        "meta": {
            "name": f"replay_{_sanitize_name(call_sid)}",
            "description": description or f"Replayed from production call {call_sid} ({ts})",
            "source_call_sid": call_sid,
            "turn_count": len(turns),
            "all_tools_fired": all_tools,
            "recorded_at": ts,
        }
    }
    lines.append(json.dumps(meta))

    for turn in turns:
        utterance = (turn.get("user_utterance") or "").strip()
        if utterance:
            lines.append(json.dumps({"role": "user", "text": utterance}))

        # Inline assertions based on what actually happened
        tools_raw = turn.get("tools_called") or "[]"
        if isinstance(tools_raw, str):
            try:
                tools_raw = json.loads(tools_raw)
            except json.JSONDecodeError:
                tools_raw = []
        for tool in (tools_raw if isinstance(tools_raw, list) else []):
            lines.append(json.dumps({
                "role": "assert",
                "type": "tool",
                "name": tool,
                "at_end": True,
            }))

    # Universal forbidden phrases
    for phrase in [
        "technisches problem", "technischer fehler", "[tool:", "bekannte daten"
    ]:
        lines.append(json.dumps({
            "role": "assert",
            "type": "forbid",
            "text": phrase,
        }))

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

async def cmd_list(args) -> None:
    calls = await list_recent_calls(args.dsn, limit=args.limit)
    if not calls:
        print("No calls found.")
        return
    print(f"{'call_sid':<30} {'turns':>5} {'start':<20} {'tools'}")
    print("-" * 90)
    for c in calls:
        start = str(c.get("call_start") or "")[:19]
        tools = ", ".join(c.get("all_tools") or [])[:40]
        print(f"{c['call_sid']:<30} {c['turn_count']:>5} {start:<20} {tools}")


async def cmd_convert(args) -> None:
    turns = await fetch_call_turns(args.dsn, args.call_sid)
    if not turns:
        print(f"No turns found for call_sid={args.call_sid!r}")
        sys.exit(1)
    jsonl_text = turns_to_jsonl(args.call_sid, turns)
    if args.dry_run:
        print(jsonl_text)
    else:
        out_dir = pathlib.Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        fname = out_dir / f"replay_{_sanitize_name(args.call_sid)}.jsonl"
        fname.write_text(jsonl_text)
        print(f"Written: {fname}")


async def cmd_batch(args) -> None:
    conn = await _connect(args.dsn)
    try:
        query = """
            SELECT call_sid, COUNT(*) as turn_count
            FROM google_turn_metrics
            WHERE call_sid IS NOT NULL
        """
        if args.tool:
            query += f"""
                AND EXISTS (
                    SELECT 1 FROM google_turn_metrics t2
                    WHERE t2.call_sid = google_turn_metrics.call_sid
                    AND t2.tools_called::text LIKE '%{args.tool}%'
                )
            """
        query += " GROUP BY call_sid ORDER BY MAX(created_at) DESC LIMIT $1"
        rows = await conn.fetch(query, args.limit)
    finally:
        await conn.close()

    if not rows:
        print("No matching calls.")
        return

    print(f"Converting {len(rows)} calls...")
    out_dir = pathlib.Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for row in rows:
        call_sid = row["call_sid"]
        turns = await fetch_call_turns(args.dsn, call_sid)
        jsonl_text = turns_to_jsonl(call_sid, turns)
        if args.dry_run:
            print(f"\n# {call_sid}")
            print(jsonl_text[:300] + "..." if len(jsonl_text) > 300 else jsonl_text)
        else:
            fname = out_dir / f"replay_{_sanitize_name(call_sid)}.jsonl"
            fname.write_text(jsonl_text)
    if not args.dry_run:
        print(f"Written {len(rows)} JSONL files to {out_dir}")


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Sailly production replay tool")
    parser.add_argument("--dsn", default=DEFAULT_PG_DSN)
    parser.add_argument("--output-dir", default=str(SCENARIOS_DIR / "replays"))
    parser.add_argument("--dry-run", action="store_true")

    sub = parser.add_subparsers(dest="command")

    sub_list = sub.add_parser("list", help="List recent production calls")
    sub_list.add_argument("--limit", type=int, default=50)

    sub_convert = sub.add_parser("convert", help="Convert one call to JSONL")
    sub_convert.add_argument("call_sid", help="The call SID to convert")

    sub_batch = sub.add_parser("batch", help="Batch convert recent calls")
    sub_batch.add_argument("--limit", type=int, default=20)
    sub_batch.add_argument("--tool", default=None,
                           help="Filter to calls where this tool fired")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if args.command == "list":
        await cmd_list(args)
    elif args.command == "convert":
        await cmd_convert(args)
    elif args.command == "batch":
        await cmd_batch(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(_main())
