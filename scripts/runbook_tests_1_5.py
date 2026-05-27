#!/usr/bin/env python3
"""Runbook tests 1-5 against /ws/demo_text (headless brain path)."""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import time
import uuid

import websockets

WS_URL = os.environ.get(
    "SAILLY_WS_URL", "ws://127.0.0.1:8080/ws/headless?tenant=doboo"
)
TURN_GAP_S = 0.4
PER_TURN_TIMEOUT_S = 60.0


async def _recv_json(ws, timeout_s: float) -> dict:
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout_s)
    if isinstance(raw, bytes):
        return {"type": "_binary", "size": len(raw)}
    return json.loads(raw)


async def _drain_until_bot(ws, deadline: float, tools_acc: list[str]) -> dict | None:
    while time.monotonic() < deadline:
        remaining = max(0.1, deadline - time.monotonic())
        msg = await _recv_json(ws, remaining)
        mtype = msg.get("type")
        if mtype == "bot_text":
            tools_acc.extend(msg.get("tools_fired") or [])
            return msg
        if mtype == "tool_event":
            name = msg.get("name", "")
            if name:
                tools_acc.append(name)
        if mtype == "error":
            return msg
        if mtype == "session_end":
            return msg
    return None


async def run_session(name: str, turns: list[str], timeout_s: float = 120.0) -> dict:
    call_sid = None
    bot_lines: list[str] = []
    tools: list[str] = []
    errors: list[str] = []
    latencies: list[float] = []

    async with websockets.connect(WS_URL) as ws:
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline:
            msg = await _recv_json(ws, deadline - time.monotonic())
            if msg.get("type") == "session_init":
                call_sid = msg.get("call_sid")
                break
            if msg.get("type") == "bot_text":
                bot_lines.append(msg.get("text", ""))
                break
            if msg.get("type") == "error":
                errors.append(msg.get("message") or str(msg))
                break

        # Greeting turn (turn 0) if not already consumed
        if bot_lines and call_sid:
            pass
        elif call_sid:
            greet = await _drain_until_bot(
                ws, time.monotonic() + 15.0, tools
            )
            if greet and greet.get("type") == "bot_text":
                bot_lines.append(greet.get("text", ""))
            elif greet and greet.get("type") == "error":
                errors.append(greet.get("message", str(greet)))

        for user_text in turns:
            if errors:
                break
            t0 = time.monotonic()
            await ws.send(json.dumps({"type": "user_text", "text": user_text}))
            reply = await _drain_until_bot(
                ws, time.monotonic() + PER_TURN_TIMEOUT_S, tools
            )
            if not reply:
                errors.append(f"timeout waiting for bot after: {user_text[:40]!r}")
                break
            if reply.get("type") == "bot_text":
                bot_lines.append(reply.get("text", ""))
                latencies.append((time.monotonic() - t0) * 1000)
            elif reply.get("type") == "error":
                errors.append(reply.get("message", str(reply)))
                break
            await asyncio.sleep(TURN_GAP_S)

        try:
            await ws.send(json.dumps({"type": "end_session"}))
            await asyncio.wait_for(ws.recv(), timeout=5)
        except Exception:
            pass

    joined = "\n".join(bot_lines)
    phone_asks = len(re.findall(r"telefonnummer", joined, re.I))
    create_orders = sum(1 for t in tools if t == "create_order")
    farewell = bool(re.search(r"wiederhören|wiedersehen|aufgezeichnet|bestellung.*aufgenommen", joined, re.I))
    readback = bool(re.search(r"stimmt|zusammenfassung|euro|€|gesamt", joined, re.I))
    correction_ask = bool(re.search(r"was soll ich.*ändern|was möchten sie ändern", joined, re.I))

    return {
        "name": name,
        "call_sid": call_sid,
        "errors": errors,
        "bot_turns": len(bot_lines),
        "phone_prompt_count": phone_asks,
        "create_order_tools": create_orders,
        "farewell": farewell,
        "readback": readback,
        "correction_ask": correction_ask,
        "avg_turn_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "last_bot": bot_lines[-1][:200] if bot_lines else "",
        "snippet": joined[:1200],
    }


async def main() -> int:
    scenarios = [
        (
            "TEST1_smoke_order_confirm",
            [
                "Hallo, ich möchte ein Bibimbap bestellen.",
                "Zum Abholen bitte.",
                "Mein Name ist Müller.",
                "017612345678",
                "Ja, stimmt so.",
            ],
        ),
        (
            "TEST3_menu_price_readback",
            [
                "Ich hätte gerne ein Bibimbap.",
                "Abholung.",
                "Schmidt.",
                "01765551234",
                "Ja.",
            ],
        ),
        (
            "TEST4_phone_loop_no_phone",
            [
                "Ich möchte Bulgogi bestellen.",
                "Lieferung bitte.",
                "Friedrich-Ebert-Allee 69 Bonn.",
                "Mein Name ist Weber.",
                "Nein, das stimmt nicht.",
                "Okay.",
            ],
        ),
        (
            "TEST5_duplicate_after_commit",
            [
                "Ich möchte Kimchi bestellen.",
                "Abholung.",
                "Fischer.",
                "01761112233",
                "Ja, bitte aufnehmen.",
                "Noch ein Kimchi bitte.",
                "Ja.",
            ],
        ),
        (
            "TEST6_correction_flow",
            [
                "Bibimbap bitte.",
                "Abholung.",
                "Meyer.",
                "01769998877",
                "Nein.",
                "Zwei Bibimbap bitte.",
                "Ja.",
            ],
        ),
    ]

    results = []
    for name, turns in scenarios:
        print(f"\n=== Running {name} ===", flush=True)
        try:
            r = await run_session(name, turns)
        except Exception as exc:
            r = {"name": name, "errors": [str(exc)], "call_sid": None}
        results.append(r)
        print(json.dumps(r, ensure_ascii=False, indent=2), flush=True)

    # Pass/fail heuristics
    print("\n=== SUMMARY ===", flush=True)
    for r in results:
        name = r["name"]
        ok = not r.get("errors") and r.get("bot_turns", 0) > 0
        notes = []
        if name == "TEST4_phone_loop_no_phone" and r.get("phone_prompt_count", 0) > 1:
            ok = False
            notes.append(f"phone_asks={r['phone_prompt_count']}>1")
        if name == "TEST5_duplicate_after_commit" and r.get("create_order_tools", 0) > 1:
            ok = False
            notes.append(f"duplicate create_order tools={r['create_order_tools']}")
        if name == "TEST6_correction_flow" and not r.get("correction_ask"):
            notes.append("no correction prompt seen")
        status = "PASS" if ok and not notes else "CHECK"
        extra = f" ({'; '.join(notes)})" if notes else ""
        print(f"{status} {name} call_sid={r.get('call_sid')}{extra}")

    out_path = f"/tmp/runbook_results_{uuid.uuid4().hex[:8]}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
