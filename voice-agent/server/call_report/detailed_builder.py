"""Build comprehensive call analysis reports matching Sailly call analysis template."""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from server.database import get_pool

logger = logging.getLogger(__name__)


async def build_detailed_call_report(call_sid: str) -> str:
    """
    Build comprehensive call analysis report with all metrics, flags, and per-turn breakdown.
    
    Matches format:
    - Call Overview
    - Aggregate health
    - Caller-flag insights
    - Per-turn breakdown
    - Timeline table
    - Transcripts
    - Tool calls
    - Session blob excerpt
    - Auto-generated observations
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Fetch call metadata
        call = await conn.fetchrow(
            "SELECT * FROM google_calls WHERE call_sid = $1",
            call_sid
        )
        if not call:
            return f"# Call Report: {call_sid}\n\nCall data not found.\n"

        # Fetch transcripts, metrics, tool calls
        transcripts = await conn.fetch(
            "SELECT * FROM google_transcripts WHERE call_sid = $1 ORDER BY turn_number",
            call_sid
        )
        metrics = await conn.fetch(
            "SELECT * FROM google_turn_metrics WHERE call_sid = $1 ORDER BY turn_number",
            call_sid
        )
        tool_calls = await conn.fetch(
            "SELECT * FROM google_tool_calls WHERE call_sid = $1 ORDER BY turn_number",
            call_sid
        )
        session_blob = call.get('session_data', {})

    # Build report sections
    lines = []

    # ─────────────────────────────────────────────────────────────────
    # 1. CALL OVERVIEW
    # ─────────────────────────────────────────────────────────────────
    lines.extend([
        f"# Sailly — Full Call Analysis Report",
        f"## Call ID: `{call_sid}`",
        f"_Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC | Source: Postgres (`google_*`) + runtime env snapshot",
        "",
        "---",
        "",
        "## 1. Call Overview",
        "",
        "| Parameter | Value |",
        "|-----------|-------|",
        f"| **Call SID** | `{call_sid}` |",
        f"| **Caller / channel** | `{call.get('from_number', 'unknown')}` |",
        f"| **Started** | {call.get('started_at', 'N/A')} |",
        f"| **Ended** | {call.get('ended_at', 'N/A')} |",
        f"| **Duration** | **{call.get('duration_seconds', 0)} seconds ({call.get('duration_seconds', 0)//60}:{call.get('duration_seconds', 0)%60:02d} min)** |",
        f"| **Total DB turns** | {len(transcripts)} |",
        f"| **Outcome / reason** | `{call.get('outcome', 'unknown')}` |",
        f"| **Quality score** | {call.get('quality_score', 'N/A')} / 10 |",
        f"| **Was escalated** | {call.get('was_escalated', False)} |",
        f"| **Tenant** | `{call.get('tenant', 'unknown')}` |",
        "",
    ])

    # ─────────────────────────────────────────────────────────────────
    # 2. AGGREGATE HEALTH
    # ─────────────────────────────────────────────────────────────────
    latencies = [m.get('total_latency_ms', 0) for m in metrics if m.get('total_latency_ms')]
    p50_latency = sorted(latencies)[len(latencies)//2] if latencies else None
    p95_latency = sorted(latencies)[int(len(latencies)*0.95)] if latencies else None
    max_latency = max(latencies) if latencies else None

    loop_count = len([m for m in metrics if m.get('loop_detected')])
    barge_in_count = len([m for m in metrics if m.get('barge_in_succeeded')])

    lines.extend([
        "## 2. Aggregate health (from `google_turn_metrics`)",
        "",
        "| Check | Value | Notes |",
        "|-------|-------|-------|",
        f"| Latency p50 / p95 / max (total) | {p50_latency} / {p95_latency} / {max_latency} ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |",
        f"| Loop incidents | {loop_count} | `loop_detected_in_stream` |",
        f"| Barge-in successes | {barge_in_count} | `barge_in_succeeded` |",
        "",
    ])

    # ─────────────────────────────────────────────────────────────────
    # 3. CALLER FLAGS
    # ─────────────────────────────────────────────────────────────────
    achtung_flags = _extract_achtung_flags(transcripts)
    lines.extend([
        "## 3. Caller-flag insights (`Achtung Sailly: …` / `Attention Sailly: …`)",
        "",
        "_Test harness, caller-bot, or human reviewer: phrases like **Achtung Sailly:** mark what Sailly did **wrong**._",
        "",
    ])
    
    if achtung_flags:
        for i, flag in enumerate(achtung_flags, 1):
            lines.extend([
                f"### Flag #{i} (turn {flag['turn_num']})",
                "",
                f"**What the caller says went wrong:**",
                f"> {flag['error_type']}",
                "",
                f"**Excerpt:** {flag['excerpt'][:200]}...",
                "",
            ])
    else:
        lines.append("_(No caller flags detected)_\n")

    # ─────────────────────────────────────────────────────────────────
    # 4. PER-TURN BREAKDOWN
    # ─────────────────────────────────────────────────────────────────
    metrics_by_turn = {m['turn_number']: m for m in metrics}
    lines.append("## 4. Per-turn breakdown (DB)\n")

    for transcript in transcripts:
        turn_num = transcript['turn_number']
        role = transcript['role']
        content = transcript['content']
        metric = metrics_by_turn.get(turn_num, {})

        lines.extend([
            f"### Turn {turn_num}",
            "",
            "```",
            f"stt_latency_ms:    {metric.get('stt_latency_ms', 'None')}",
            f"llm_latency_ms:    {metric.get('llm_latency_ms', 'None')} {'✅' if metric.get('llm_latency_ms', 0) < 3000 else '⚠️'}",
            f"tts_latency_ms:    {metric.get('tts_latency_ms', 'None')}",
            f"total_latency_ms:  {metric.get('total_latency_ms', 'None')} {'✅' if metric.get('total_latency_ms', 0) < 3000 else '⚠️'}",
            f"tools_called:      {metric.get('tools_called', [])}",
            f"loop:              detected={metric.get('loop_detected')} reason={metric.get('loop_reason', None)}",
            "```",
            "",
            f"**{role.upper()}**: {content}",
            "",
        ])

    # ─────────────────────────────────────────────────────────────────
    # 5. TIMELINE TABLE
    # ─────────────────────────────────────────────────────────────────
    lines.extend([
        "## 5. Timeline table (compact)",
        "",
        "| Turn | total_ms | llm_ms | tools | flags |",
        "|------|----------|--------|-------|-------|",
    ])

    for turn_num, metric in sorted(metrics_by_turn.items()):
        tools = ', '.join(metric.get('tools_called', [])[:2])  # First 2 tools
        flags_str = "⚠️ Loop" if metric.get('loop_detected') else ""
        lines.append(
            f"| {turn_num} | {metric.get('total_latency_ms', 'N/A')} | "
            f"{metric.get('llm_latency_ms', 'N/A')} | {tools} | {flags_str} |"
        )

    lines.append("")

    # ─────────────────────────────────────────────────────────────────
    # 6. TRANSCRIPTS
    # ─────────────────────────────────────────────────────────────────
    lines.extend([
        "## 6. Transcripts (`google_transcripts`)",
        "",
    ])

    for transcript in transcripts:
        lines.append(f"- **{transcript['role']}** (turn {transcript['turn_number']}): {transcript['content'][:100]}...")

    lines.append("")

    # ─────────────────────────────────────────────────────────────────
    # 7. TOOL CALLS
    # ─────────────────────────────────────────────────────────────────
    lines.extend([
        "## 7. Tool calls (`google_tool_calls`)",
        "",
    ])

    for tool in tool_calls:
        lines.append(f"- `{tool.get('tool_name', 'unknown')}` @ turn {tool.get('turn_number', 'None')} — "
                    f"success={tool.get('success', 'unknown')} — {tool.get('arguments', '(empty)')}")

    lines.append("")

    # ─────────────────────────────────────────────────────────────────
    # 8. SESSION BLOB EXCERPT
    # ─────────────────────────────────────────────────────────────────
    lines.extend([
        "## 8. Session blob excerpt (`google_calls.session_data`)",
        "",
        "```json",
        json.dumps(session_blob, indent=2)[:1000],  # First 1000 chars
        "```",
        "",
    ])

    # ─────────────────────────────────────────────────────────────────
    # 9. AUTO-GENERATED OBSERVATIONS
    # ─────────────────────────────────────────────────────────────────
    lines.extend([
        "## 9. Auto-generated observations",
        "",
        f"- **Caller-reported issues** (`Achtung Sailly`): {len(achtung_flags)} marker(s) found — see **§3**",
        f"- **Overall quality**: {call.get('quality_score', 'N/A')}/10",
        "",
        "_Report end._",
    ])

    return "\n".join(lines)


def _extract_achtung_flags(transcripts: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extract and parse Achtung Sailly flags from transcripts."""
    flags = []
    for transcript in transcripts:
        content = transcript.get('content', '')
        if '[Achtung Sailly:' in content or '[Attention Sailly:' in content:
            # Extract everything after the marker
            start = content.find('[Achtung Sailly:') if '[Achtung Sailly:' in content else content.find('[Attention Sailly:')
            if start != -1:
                end = content.find(']', start)
                if end != -1:
                    error_msg = content[start:end+1]
                    flags.append({
                        'turn_num': transcript.get('turn_number'),
                        'error_type': error_msg.split('—')[1].strip() if '—' in error_msg else error_msg,
                        'excerpt': content[:150]
                    })
    return flags
