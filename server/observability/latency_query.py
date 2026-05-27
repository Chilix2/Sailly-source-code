"""
Latency verification query helper — inspect per-turn metrics for a given call.

Given a call_id, this module provides utilities to fetch and display:
- Turn number and role (user/assistant)
- Brain processing time (STT final to LLM text output)
- TTS TTFB (STT final to first audio byte — the key perceived latency metric)
- Total perceived latency from user's perspective
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from server.database import get_pool

logger = logging.getLogger(__name__)


async def query_call_latencies(call_sid: str) -> Dict[str, Any]:
    """
    Query latency metrics for a single call, showing per-turn breakdown.

    Returns a dict with:
        {
            "found": bool,
            "call_sid": call_sid,
            "total_turns": int,
            "turns": [
                {
                    "turn_number": int,
                    "role": "user" | "assistant",
                    "text_preview": str (first 60 chars),
                    "brain_processing_ms": int | None (llm_latency_ms),
                    "tts_ttfb_ms": int | None (time to first audio),
                    "total_perceived_latency_ms": int | None (tts_ttfb_ms if assistant, else null),
                    "notes": str (e.g. "Calculated from TurnTimings")
                }
            ],
            "summary": {
                "tts_ttfb_p50_ms": int | None,
                "tts_ttfb_p95_ms": int | None,
                "brain_processing_p50_ms": int | None,
                "tts_ttfb_missing_count": int,
                "total_assistant_turns": int,
            }
        }
    """
    pool = await get_pool()

    async with pool.acquire() as conn:
        # Fetch both transcripts and turn metrics
        transcripts = await conn.fetch(
            """
            SELECT turn_number, role, content
            FROM google_transcripts
            WHERE call_sid = $1
            ORDER BY turn_number
            """,
            call_sid,
        )
        
        turn_metrics = await conn.fetch(
            """
            SELECT 
                turn_number,
                llm_latency_ms,
                tts_ttfb_ms,
                stt_ms,
                extract_ms,
                l2_ms,
                tool_ms,
                tts_first_byte_ms,
                total_ms
            FROM google_turn_metrics
            WHERE call_sid = $1
            ORDER BY turn_number
            """,
            call_sid,
        )

    if not transcripts:
        logger.warning(f"[latency_query] Call not found: {call_sid}")
        return {
            "found": False,
            "call_sid": call_sid,
        }

    # Index metrics by turn_number for fast lookup
    metrics_by_turn = {m["turn_number"]: m for m in turn_metrics}

    # Build per-turn breakdown
    turns = []
    for transcript in transcripts:
        turn_num = transcript["turn_number"]
        role = transcript["role"]
        text = transcript["content"] or ""
        text_preview = text[:60] + ("..." if len(text) > 60 else "")

        metrics = metrics_by_turn.get(turn_num, {})

        # For assistant turns, perceived latency ≈ tts_ttfb_ms
        # (time from user final speech to bot first audio)
        perceived_latency = None
        if role == "assistant":
            perceived_latency = metrics.get("tts_ttfb_ms")

        turns.append({
            "turn_number": turn_num,
            "role": role,
            "text_preview": text_preview,
            "brain_processing_ms": metrics.get("llm_latency_ms"),
            "tts_ttfb_ms": metrics.get("tts_ttfb_ms"),
            "stt_ms": metrics.get("stt_ms"),
            "extract_ms": metrics.get("extract_ms"),
            "l2_ms": metrics.get("l2_ms"),
            "tool_ms": metrics.get("tool_ms"),
            "tts_first_byte_ms": metrics.get("tts_first_byte_ms"),
            "total_ms": metrics.get("total_ms"),
            "total_perceived_latency_ms": perceived_latency,
            "notes": "Calculated from TurnTimings" if metrics.get("tts_ttfb_ms") else "",
        })

    # Compute summary statistics
    tts_ttfb_values = [
        t["tts_ttfb_ms"] for t in turns
        if t["tts_ttfb_ms"] is not None
    ]
    brain_processing_values = [
        t["brain_processing_ms"] for t in turns
        if t["brain_processing_ms"] is not None
    ]

    tts_ttfb_p50 = None
    tts_ttfb_p95 = None
    if tts_ttfb_values:
        sorted_ttfb = sorted(tts_ttfb_values)
        tts_ttfb_p50 = sorted_ttfb[len(sorted_ttfb) // 2]
        tts_ttfb_p95 = sorted_ttfb[int(len(sorted_ttfb) * 0.95)] if len(sorted_ttfb) > 1 else sorted_ttfb[0]

    brain_p50 = None
    if brain_processing_values:
        sorted_brain = sorted(brain_processing_values)
        brain_p50 = sorted_brain[len(sorted_brain) // 2]

    assistant_turn_count = sum(1 for t in turns if t["role"] == "assistant")

    return {
        "found": True,
        "call_sid": call_sid,
        "total_turns": len(transcripts),
        "turns": turns,
        "summary": {
            "tts_ttfb_p50_ms": tts_ttfb_p50,
            "tts_ttfb_p95_ms": tts_ttfb_p95,
            "brain_processing_p50_ms": brain_p50,
            "tts_ttfb_missing_count": assistant_turn_count - len(tts_ttfb_values),
            "total_assistant_turns": assistant_turn_count,
        }
    }


async def query_call_latencies_markdown(call_sid: str) -> str:
    """
    Query latency metrics and format as markdown table.
    
    Returns a markdown string with per-turn breakdown, suitable for
    inclusion in reports or logging.
    """
    data = await query_call_latencies(call_sid)

    if not data.get("found"):
        return f"# Latency Report: {call_sid}\n\nCall not found.\n"

    lines = [
        f"# Latency Report: {call_sid}",
        "",
        "## Per-Turn Breakdown",
        "",
        "| Turn | Role | Brain (ms) | TTS TTFB (ms) | Perceived (ms) | Notes |",
        "|------|------|-----------|---------------|----------------|-------|",
    ]

    for turn in data["turns"]:
        brain = turn.get("brain_processing_ms") or "-"
        ttfb = turn.get("tts_ttfb_ms") or "-"
        perceived = turn.get("total_perceived_latency_ms") or "-"
        notes = turn.get("notes") or ""
        
        lines.append(
            f"| {turn['turn_number']} | {turn['role']} | {brain} | {ttfb} | {perceived} | {notes} |"
        )

    lines.extend([
        "",
        "## Summary Statistics",
        "",
        f"- **Total Turns**: {data['total_turns']}",
        f"- **Assistant Turns**: {data['summary']['total_assistant_turns']}",
        f"- **TTS TTFB p50**: {data['summary']['tts_ttfb_p50_ms']}ms",
        f"- **TTS TTFB p95**: {data['summary']['tts_ttfb_p95_ms']}ms",
        f"- **Brain Processing p50**: {data['summary']['brain_processing_p50_ms']}ms",
        f"- **Missing TTS TTFB Data**: {data['summary']['tts_ttfb_missing_count']} turns",
        "",
        "## Latency Definitions",
        "",
        "- **Brain Processing** = STT final → First LLM text output",
        "- **TTS TTFB** = STT final → First audio byte to client (perceived latency)",
        "- **Perceived Latency** = TTS TTFB (what user hears as response time)",
    ])

    return "\n".join(lines)
