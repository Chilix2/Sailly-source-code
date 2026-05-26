"""Build markdown call reports and JSON bundles from database records for LLM analysis."""

import json
import logging
from typing import Any, Dict, Optional

from server.database import get_pool

logger = logging.getLogger(__name__)


async def fetch_call_report_bundle(call_sid: str) -> Dict[str, Any]:
    """
    Fetch all call data from DB and return a structured JSON-serializable bundle.

    Returns:
        dict with keys:
            found (bool), call_sid, call (metadata), transcripts, turn_metrics, tool_calls
    """
    pool = await get_pool()
    def _row_to_dict(row) -> Dict[str, Any]:
        return {k: (str(v) if not isinstance(v, (str, int, float, bool, type(None), list, dict)) else v)
                for k, v in dict(row).items()}

    async with pool.acquire() as conn:
        call = await conn.fetchrow(
            "SELECT * FROM google_calls WHERE call_sid = $1",
            call_sid,
        )
        if not call:
            turn_metrics = await conn.fetch(
                "SELECT * FROM google_turn_metrics WHERE call_sid = $1 ORDER BY turn_number",
                call_sid,
            )
            if not turn_metrics:
                logger.warning("[report] Call not found: %s", call_sid)
                return {"found": False, "call_sid": call_sid}
            logger.warning("[report] Call row missing but turn metrics exist: %s", call_sid)
            latencies = [
                m["total_latency_ms"] for m in turn_metrics
                if m.get("total_latency_ms") is not None
            ]
            sorted_lat = sorted(latencies)
            p50 = sorted_lat[len(sorted_lat) // 2] if sorted_lat else None
            p95 = sorted_lat[int(len(sorted_lat) * 0.95)] if sorted_lat else None
            metrics_dicts = [_row_to_dict(r) for r in turn_metrics]
            transcripts = []
            for metric in metrics_dicts:
                turn_number = metric.get("turn_number")
                if metric.get("user_text"):
                    transcripts.append({
                        "call_sid": call_sid,
                        "role": "user",
                        "content": metric.get("user_text"),
                        "turn_number": turn_number,
                    })
                if metric.get("bot_text"):
                    transcripts.append({
                        "call_sid": call_sid,
                        "role": "assistant",
                        "content": metric.get("bot_text"),
                        "turn_number": turn_number,
                    })
            return {
                "found": True,
                "orphan_metrics_only": True,
                "call_sid": call_sid,
                "call": {
                    "call_sid": call_sid,
                    "tenant_id": metrics_dicts[0].get("tenant_id") if metrics_dicts else None,
                    "outcome": "orphan_metrics_only",
                },
                "transcripts": transcripts,
                "turn_metrics": metrics_dicts,
                "tool_calls": [],
                "summary": {
                    "total_turns": len(transcripts),
                    "total_tool_calls": 0,
                    "latency_p50_ms": p50,
                    "latency_p95_ms": p95,
                    "outcome": "orphan_metrics_only",
                    "quality_score": None,
                    "duration_seconds": None,
                },
            }

        transcripts = await conn.fetch(
            "SELECT * FROM google_transcripts WHERE call_sid = $1 ORDER BY turn_number",
            call_sid,
        )
        turn_metrics = await conn.fetch(
            "SELECT * FROM google_turn_metrics WHERE call_sid = $1 ORDER BY turn_number",
            call_sid,
        )
        tool_calls = await conn.fetch(
            "SELECT * FROM google_tool_calls WHERE call_sid = $1 ORDER BY turn_number",
            call_sid,
        )

    call_dict = _row_to_dict(call)

    latencies = [
        m["total_latency_ms"] for m in turn_metrics
        if m.get("total_latency_ms") is not None
    ]
    sorted_lat = sorted(latencies)
    p50 = sorted_lat[len(sorted_lat) // 2] if sorted_lat else None
    p95 = sorted_lat[int(len(sorted_lat) * 0.95)] if sorted_lat else None

    return {
        "found": True,
        "call_sid": call_sid,
        "call": call_dict,
        "transcripts": [_row_to_dict(r) for r in transcripts],
        "turn_metrics": [_row_to_dict(r) for r in turn_metrics],
        "tool_calls": [_row_to_dict(r) for r in tool_calls],
        "summary": {
            "total_turns": len(transcripts),
            "total_tool_calls": len(tool_calls),
            "latency_p50_ms": p50,
            "latency_p95_ms": p95,
            "outcome": call_dict.get("outcome"),
            "quality_score": call_dict.get("quality_score"),
            "duration_seconds": call_dict.get("duration_seconds"),
        },
    }


async def build_call_report_markdown(
    call_sid: str,
    include_journal: bool = False,
    journal_lines: int = 200,
) -> str:
    """
    Fetch call data from DB and build a markdown report with turn-by-turn metrics.

    Args:
        call_sid: The call session ID (e.g., 'demo-xyz')
        include_journal: If True, attempt to append filtered journalctl excerpt.
        journal_lines: Max journal lines to scan (only used when include_journal=True).

    Returns:
        Markdown-formatted call report with transcripts and metrics.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        call = await conn.fetchrow(
            "SELECT * FROM google_calls WHERE call_sid = $1",
            call_sid,
        )
        if not call:
            turn_metrics = await conn.fetch(
                "SELECT * FROM google_turn_metrics WHERE call_sid = $1 ORDER BY turn_number",
                call_sid,
            )
            if turn_metrics:
                lines = [
                    f"# Call Report: {call_sid}",
                    "\nCall row is missing, but orphan turn metrics were found.",
                    "\n## Conversation Flow\n",
                ]
                for metric in turn_metrics:
                    turn_num = metric["turn_number"]
                    if metric.get("user_text"):
                        lines.append(f"### Turn {turn_num}: USER")
                        lines.append(f"**Message**: {metric['user_text']}\n")
                    if metric.get("bot_text"):
                        lines.append(f"### Turn {turn_num}: ASSISTANT")
                        lines.append(f"**Message**: {metric['bot_text']}\n")
                    if metric.get("total_latency_ms"):
                        lines.append("**Metrics:**")
                        lines.append(f"- Latency: {metric['total_latency_ms']}ms")
                    if metric.get("tools_called"):
                        lines.append(f"- Tools: {metric['tools_called']}")
                    lines.append("")
                lines.append("\n## Summary\n")
                lines.append(f"- **Orphan Metrics Only**: true")
                lines.append(f"- **Metric Turns**: {len(turn_metrics)}")
                return "\n".join(lines)
            logger.warning("[report] Call not found: %s", call_sid)
            return f"# Call Report: {call_sid}\n\nCall data not found in database.\n"

        transcripts = await conn.fetch(
            "SELECT * FROM google_transcripts WHERE call_sid = $1 ORDER BY turn_number",
            call_sid,
        )
        tool_calls = await conn.fetch(
            "SELECT * FROM google_tool_calls WHERE call_sid = $1 ORDER BY turn_number",
            call_sid,
        )
        turn_metrics = await conn.fetch(
            "SELECT * FROM google_turn_metrics WHERE call_sid = $1 ORDER BY turn_number",
            call_sid,
        )

    lines = [
        f"# Call Report: {call_sid}",
        f"\n**Date**: {call.get('created_at', 'N/A')}",
        f"**Started**: {call.get('started_at', 'N/A')}",
        f"**Ended**: {call.get('ended_at', 'N/A')}",
        f"**Duration**: {call.get('duration_seconds', 0)}s",
        f"**Outcome**: {call.get('outcome', 'N/A')}",
        f"**Disposition**: {call.get('call_disposition', 'N/A')}",
        f"**Overall Score**: {call.get('quality_score', 'N/A')}/10",
        f"**Tenant**: {call.get('tenant_id', 'N/A')}",
        "\n## Conversation Flow\n",
    ]

    metrics_by_turn = {m["turn_number"]: m for m in turn_metrics}
    tools_by_turn = {t["turn_number"]: t for t in tool_calls}

    for transcript in transcripts:
        turn_num = transcript["turn_number"]
        role = transcript["role"]
        content = transcript["content"]

        lines.append(f"### Turn {turn_num}: {role.upper()}")
        lines.append(f"**Message**: {content}\n")

        if turn_num in metrics_by_turn:
            m = metrics_by_turn[turn_num]
            lines.append("**Metrics**:")
            if m.get("total_latency_ms"):
                lines.append(f"- Total Latency: {m['total_latency_ms']}ms")
            if m.get("llm_latency_ms"):
                lines.append(f"- Brain Processing: {m['llm_latency_ms']}ms (STT final → TTS text)")
            if m.get("tts_ttfb_ms"):
                lines.append(f"- TTS TTFB: {m['tts_ttfb_ms']}ms (STT final → first audio)")
            if m.get("stt_confidence"):
                lines.append(f"- STT Confidence: {m['stt_confidence']:.2f}")
            if m.get("intent"):
                lines.append(f"- Intent: {m['intent']} ({m.get('turn_type', '')})")
            if m.get("tools_called"):
                lines.append(f"- Tools: {m['tools_called']}")
            lines.append("")

        if turn_num in tools_by_turn:
            t = tools_by_turn[turn_num]
            lines.append(f"**Tool Call**: `{t.get('tool_name', 'unknown')}`")
            lines.append(f"- Arguments: {t.get('arguments', '{}')}  ")
            lines.append(f"- Success: {t.get('success', 'unknown')}\n")

    lines.append("\n## Summary\n")
    lines.append(f"- **Total Turns**: {len(transcripts)}")
    lines.append(f"- **Tool Calls**: {len(tool_calls)}")
    if turn_metrics:
        latencies = [m["total_latency_ms"] or 0 for m in turn_metrics if m.get("total_latency_ms")]
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            lines.append(f"- **Avg Latency**: {avg_latency:.0f}ms")
            lines.append(f"- **p95 Latency**: {p95_latency}ms")
    
    lines.append("\n## Latency Breakdown\n")
    lines.append("- **Brain Processing** (`llm_latency_ms`): Time from STT final to first TTS text generated by LLM")
    lines.append("- **TTS TTFB** (`tts_ttfb_ms`): End-to-end time from STT final to first audio byte sent to client")
    lines.append("  - Includes: LLM processing + TTS synthesis + network delay")
    lines.append("  - Perceived latency by user ≈ TTS TTFB")
    lines.append("- **TTS Synthesis** = TTS TTFB - Brain Processing (synthesis + network)")


    if include_journal:
        lines.append("\n## Journal Excerpt\n")
        try:
            import subprocess
            result = subprocess.run(
                ["journalctl", "-u", "sailly-browser-demo.service",
                 "--since", str(call.get("started_at", "")),
                 "--until", str(call.get("ended_at", "")),
                 "--no-pager", "-n", str(journal_lines)],
                capture_output=True, text=True, timeout=10,
            )
            if result.stdout:
                lines.append("```")
                lines.append(result.stdout[:4000])
                lines.append("```")
            else:
                lines.append("_(No journal entries found)_")
        except Exception as e:
            lines.append(f"_(Journal fetch failed: {e})_")

    return "\n".join(lines)
