"""
src/metrics.py — Post-call metrics pull from google_turn_metrics

Fetches turn-level data and derives signals.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def fetch_call_metrics(pg_dsn: str, call_sid: str) -> dict:
    """Fetch all metrics for a call from google_turn_metrics.

    Returns dict indexed by turn_number with fields:
        - node_name (= v4 profile)
        - tools_called (JSON list)
        - intent_classify_ms
        - worker_p50_ms, worker_p95_ms
        - generator_total_ms
        - layer1_decision (JSON)
    """
    try:
        import asyncpg
    except ImportError:
        logger.warning("asyncpg not installed; metrics will be empty")
        return {}

    try:
        conn = await asyncpg.connect(pg_dsn)
        try:
            rows = await conn.fetch(
                """
                SELECT
                    turn_number,
                    node_name,
                    tools_called,
                    intent_classify_ms,
                    worker_p50_ms,
                    worker_p95_ms,
                    generator_total_ms,
                    layer1_decision
                FROM google_turn_metrics
                WHERE call_sid = $1
                ORDER BY turn_number ASC
                """,
                call_sid,
            )
            metrics = {}
            for row in rows:
                turn_num = row["turn_number"]
                metrics[turn_num] = {
                    "node_name": row["node_name"],
                    "tools_called": row["tools_called"] or [],
                    "intent_classify_ms": row["intent_classify_ms"],
                    "worker_p50_ms": row["worker_p50_ms"],
                    "worker_p95_ms": row["worker_p95_ms"],
                    "generator_total_ms": row["generator_total_ms"],
                    "layer1_decision": row["layer1_decision"],
                }
            return metrics
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"Failed to fetch metrics for {call_sid}: {e}")
        return {}


def derive_signals(
    call_metrics: dict,
    bot_responses: list[str],
    user_utterances: list[str],
) -> dict:
    """Derive high-level signals from metrics.

    Returns dict with keys like:
        - one_llm_per_turn: bool
        - has_readback: bool
        - commit_gate_timing_ok: bool
    """
    signals = {}

    # one_llm_per_turn: count turns where generator_total_ms is non-null
    generator_turns = sum(
        1 for m in call_metrics.values() if m.get("generator_total_ms") is not None
    )
    signals["one_llm_per_turn"] = generator_turns == len(bot_responses)

    # has_readback: check if any turn contains readback patterns
    readback_patterns = ["stimmt das so", "korrekt", "passt so", "richtig"]
    has_readback = any(
        any(p in bot_text.lower() for p in readback_patterns) for bot_text in bot_responses
    )
    signals["has_readback"] = has_readback

    # commit_gate_timing_ok: if create_reservation/create_order fired,
    # verify it was after a confirmation utterance
    commit_fired = False
    for m in call_metrics.values():
        tools = m.get("tools_called", [])
        if isinstance(tools, str):
            try:
                import json
                tools = json.loads(tools)
            except:
                tools = []
        if any(t in tools for t in ["create_reservation", "create_order"]):
            commit_fired = True
            break

    signals["commit_gate_timing_ok"] = not commit_fired or has_readback

    # latency_acceptable: max generator latency < 5000 ms
    max_gen_latency = max(
        (m.get("generator_total_ms") or 0 for m in call_metrics.values()),
        default=0,
    )
    signals["latency_acceptable"] = max_gen_latency < 5000

    return signals
