"""Latency baseline — replayable over `google_turn_metrics` + `google_calls`.

Pulls the last N calls from Postgres and prints the p50/p95/p99 breakdown used
in ``LATENCY_TEST.md``. Re-run after any latency-related change to verify the
fix actually moved the needle.

Usage::

    DATABASE_URL='postgresql://postgres:sailly2026@localhost:5432/sailly' \
        PYTHONPATH=. python tests/latency_baseline.py           # last 30 calls
    PYTHONPATH=. python tests/latency_baseline.py --limit 100   # last 100 calls

Columns printed
----------------
- Per-call summary (turn count, p50/p95 per call)
- Overall p50/p90/p95/p99/max for total, LLM, STT, TTS stages
- Latency-by-tool-count bucket (0, 1, 2, 3, 4+ tools per turn)
- Slowest 10 turns (for outlier hunting — these point straight at retry storms)

The numbers in ``LATENCY_TEST.md`` were produced by running this script on
2026-04-21 against 30 calls / 249 turn-metric rows. Reproducing the same
numbers requires a snapshot of that DB; on a live DB the rolling window
obviously moves.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Iterable, List, Optional


def _pct(xs: List[int], p: float) -> Optional[int]:
    if not xs:
        return None
    xs = sorted(xs)
    i = min(len(xs) - 1, int(len(xs) * p))
    return xs[i]


def _stats(name: str, xs: List[int]) -> None:
    if not xs:
        print(f"  {name:20s} no data")
        return
    xs = sorted(xs)
    n = len(xs)
    print(
        f"  {name:20s} n={n:<4d} "
        f"min={xs[0]:>5d} p50={_pct(xs, 0.50):>5d} "
        f"p90={_pct(xs, 0.90):>5d} p95={_pct(xs, 0.95):>5d} "
        f"p99={_pct(xs, 0.99):>5d} max={xs[-1]:>6d} "
        f"mean={sum(xs)//n:>5d}"
    )


def _as_list(v: Any) -> List[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


async def _run(limit: int) -> int:
    # Defer import — the script should still parse without asyncpg installed.
    from server.database import get_pool  # type: ignore

    pool = await get_pool()
    async with pool.acquire() as conn:
        call_rows = await conn.fetch(
            """
            SELECT call_sid, started_at, duration_seconds, total_turns,
                   avg_latency_ms, p95_latency_ms
            FROM google_calls
            ORDER BY started_at DESC
            LIMIT $1
            """,
            limit,
        )
        if not call_rows:
            print("No calls found in google_calls — is DATABASE_URL pointing at the right DB?")
            return 1

        sids = [r["call_sid"] for r in call_rows]
        print(f"=== last {len(call_rows)} calls ===")
        for r in call_rows:
            print(
                f"{r['call_sid'][:28]:28s} "
                f"turns={(r['total_turns'] or 0):>3} "
                f"dur={(r['duration_seconds'] or 0):>4d}s "
                f"avg={(r['avg_latency_ms'] or 0):>5d}ms "
                f"p95={(r['p95_latency_ms'] or 0):>5d}ms"
            )

        tm_rows = await conn.fetch(
            """
            SELECT call_sid, turn_number,
                   stt_latency_ms, llm_latency_ms, tts_latency_ms, total_latency_ms,
                   tools_called, node_name,
                   length(bot_text)  AS bot_len,
                   length(user_text) AS user_len,
                   substring(bot_text,  1, 80) AS bot80,
                   substring(user_text, 1, 60) AS user60
            FROM google_turn_metrics
            WHERE call_sid = ANY($1::text[])
            ORDER BY call_sid, turn_number
            """,
            sids,
        )
        print(f"\n=== {len(tm_rows)} turn metrics ===")

    total = [r["total_latency_ms"] for r in tm_rows if r["total_latency_ms"]]
    llm = [r["llm_latency_ms"] for r in tm_rows if r["llm_latency_ms"]]
    stt = [r["stt_latency_ms"] for r in tm_rows if r["stt_latency_ms"]]
    tts = [r["tts_latency_ms"] for r in tm_rows if r["tts_latency_ms"]]

    _stats("total_latency_ms", total)
    _stats("llm_latency_ms", llm)
    _stats("stt_latency_ms", stt)
    _stats("tts_latency_ms", tts)

    # Tools/turn bucket analysis
    print("\n=== latency by tool-count ===")
    buckets: dict[int, List[int]] = {}
    for r in tm_rows:
        if not r["total_latency_ms"]:
            continue
        n = len(_as_list(r["tools_called"]))
        buckets.setdefault(n, []).append(r["total_latency_ms"])
    for n in sorted(buckets):
        xs = buckets[n]
        xs_sorted = sorted(xs)
        print(
            f"  n_tools={n:<2d}  count={len(xs):>3d}  "
            f"p50={_pct(xs_sorted, 0.50):>5d}ms  "
            f"p95={_pct(xs_sorted, 0.95):>5d}ms  "
            f"mean={sum(xs)//len(xs):>5d}ms"
        )

    # Bot text length (output token proxy)
    bot_lens = [r["bot_len"] for r in tm_rows if r["bot_len"]]
    if bot_lens:
        bot_lens.sort()
        print(
            f"\n  bot_text chars: p50={_pct(bot_lens, 0.50)} "
            f"p95={_pct(bot_lens, 0.95)} max={bot_lens[-1]}"
        )

    # Slowest turns — these are the outlier hunters
    slow = sorted(
        (r for r in tm_rows if r["total_latency_ms"]),
        key=lambda r: r["total_latency_ms"],
        reverse=True,
    )[:10]
    print("\n=== slowest 10 turns ===")
    for r in slow:
        tools = _as_list(r["tools_called"])
        print(
            f"{r['call_sid'][:28]:28s} T{r['turn_number']:>2d} "
            f"{r['total_latency_ms']:>5d}ms "
            f"bot_len={r['bot_len'] or 0:>3d} "
            f"tools={tools} "
            f"user={r['user60']!r}"
        )

    # Sanity thresholds — flag regressions in CI
    total_sorted = sorted(total)
    p50 = _pct(total_sorted, 0.50) or 0
    p95 = _pct(total_sorted, 0.95) or 0
    p99 = _pct(total_sorted, 0.99) or 0

    print("\n=== thresholds (see LATENCY_TEST.md target = 800ms p50 / 1800ms p95) ===")
    print(f"  p50={p50}ms  p95={p95}ms  p99={p99}ms")
    if p50 > 1500:
        print(f"  ⚠ p50 over 1500ms — LLM streaming (L1) likely not shipped")
    if p99 > 10_000:
        print(f"  ⚠ p99 over 10s — retry storm (L2) likely still active")

    return 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--limit", type=int, default=30, help="number of recent calls")
    args = parser.parse_args(list(argv) if argv is not None else None)

    # Friendly message if DATABASE_URL is missing.
    if not os.getenv("DATABASE_URL"):
        print(
            "DATABASE_URL not set. Example:\n"
            "  DATABASE_URL='postgresql://postgres:<pw>@localhost:5432/sailly' "
            "PYTHONPATH=. python tests/latency_baseline.py",
            file=sys.stderr,
        )
        return 2

    return asyncio.run(_run(args.limit))


if __name__ == "__main__":
    sys.exit(main())
