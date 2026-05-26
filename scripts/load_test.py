#!/usr/bin/env python3
"""
load_test.py — parallel WebSocket browser-demo load harness.

Fires N concurrent /ws/demo connections that send silence frames for a
duration and count how many complete cleanly.  Used to validate concurrent
call capacity before switching live-traffic ramps up.

This is intentionally simple — not a replacement for k6.  Just a quick
"does the server survive 50 simultaneous sessions?" smoke test.

Usage:
    python scripts/load_test.py --url ws://localhost:8080/ws/demo \
        --concurrency 25 --duration 30

Exit code is 0 if >=95% of sessions completed without errors, 1 otherwise.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time

try:
    import websockets
except ImportError:
    print("ERROR: pip install websockets", file=sys.stderr)
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger("load_test")


async def _single_session(session_id: int, url: str, duration: float) -> bool:
    try:
        async with websockets.connect(url, ping_interval=20) as ws:
            # Handshake — the browser demo expects a consent payload.
            await ws.send(
                json.dumps(
                    {
                        "type": "hello",
                        "tenant_id": "doboo",
                        "voice": "Kore",
                        "consent_given": True,
                        "load_test_session": session_id,
                    }
                )
            )
            # Feed silence audio for the duration.
            end = time.monotonic() + duration
            silence_20ms = b"\x00" * (16000 * 2 // 50)  # PCM16 @16kHz, 20ms
            sent = 0
            while time.monotonic() < end:
                await ws.send(silence_20ms)
                sent += 1
                await asyncio.sleep(0.02)
            log.info(f"session {session_id} ok ({sent} audio frames sent)")
            return True
    except Exception as exc:
        log.warning(f"session {session_id} failed: {type(exc).__name__}: {exc}")
        return False


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="ws://localhost:8080/ws/demo")
    parser.add_argument("--concurrency", type=int, default=25)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--pass-rate", type=float, default=0.95)
    args = parser.parse_args()

    log.info(
        f"Starting load test: url={args.url} "
        f"concurrency={args.concurrency} duration={args.duration}s"
    )
    t0 = time.monotonic()
    tasks = [
        _single_session(i, args.url, args.duration)
        for i in range(args.concurrency)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    elapsed = time.monotonic() - t0
    ok = sum(1 for r in results if r is True)
    total = len(results)
    rate = ok / total if total else 0.0
    log.info(
        f"Done in {elapsed:.1f}s — {ok}/{total} sessions OK ({rate*100:.1f}%)"
    )
    return 0 if rate >= args.pass_rate else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
