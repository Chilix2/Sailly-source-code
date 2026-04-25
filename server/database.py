"""
PostgreSQL persistence — writes call data to google_calls and related tables.
Uses asyncpg for async DB access.
"""

import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

import asyncpg
from loguru import logger


def _default_serializer(obj):
    """Handle Decimal and datetime types for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

BERLIN_TZ = ZoneInfo("Europe/Berlin")

_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres@localhost:5432/sailly")
        _pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)
        logger.info(f"Database pool created: {db_url.split('@')[1] if '@' in db_url else db_url}")
    return _pool


async def persist_call(session_data: dict, analytics_data: dict, audio_urls: dict | None = None) -> Optional[int]:
    """Write a completed call to google_calls and related tables. Returns the call ID.
    
    Args:
        session_data: Call session information
        analytics_data: Post-call analytics results
        audio_urls: Optional dict with 'caller_audio' and/or 'bot_audio' keys (GCS paths)
    """
    pool = await get_pool()
    call_sid = session_data.get("call_sid", "")
    if not call_sid:
        return None

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                duration = session_data.get("duration_secs", 0)
                cost = analytics_data.get("cost", {})
                quality = analytics_data.get("quality", {})
                summary = analytics_data.get("summary", {})
                sentiment_data = analytics_data.get("sentiment", {})
                audio_urls = audio_urls or {}

                call_id = await conn.fetchval("""
                    INSERT INTO google_calls (
                        call_sid, caller_number, started_at, ended_at,
                        duration_seconds, quality_score, outcome, sentiment,
                        language, was_escalated, total_cost_tokens, total_cost_telephony,
                        avg_latency_ms, session_data, analytics_data,
                        recording_consent_at, emergency_detected, emergency_keyword,
                        insurance_data_collected, caller_audio_url, agent_audio_url
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                              $16, $17, $18, $19, $20, $21)
                    ON CONFLICT (call_sid) DO UPDATE SET
                        ended_at = EXCLUDED.ended_at,
                        duration_seconds = EXCLUDED.duration_seconds,
                        quality_score = EXCLUDED.quality_score,
                        outcome = EXCLUDED.outcome,
                        sentiment = EXCLUDED.sentiment,
                        session_data = EXCLUDED.session_data,
                        analytics_data = EXCLUDED.analytics_data,
                        recording_consent_at = EXCLUDED.recording_consent_at,
                        emergency_detected = EXCLUDED.emergency_detected,
                        emergency_keyword = EXCLUDED.emergency_keyword,
                        insurance_data_collected = EXCLUDED.insurance_data_collected,
                        caller_audio_url = EXCLUDED.caller_audio_url,
                        agent_audio_url = EXCLUDED.agent_audio_url
                    RETURNING id
                """,
                    call_sid,
                    session_data.get("from_number", ""),
                    _parse_ts(session_data.get("started_at")),
                    _parse_ts(session_data.get("ended_at")),
                    round(duration) if duration else 0,
                    quality.get("score", 0) / 10.0,
                    summary.get("intent", "unknown") if not session_data.get("transcripts") else summary.get("intent", "completed"),
                    sentiment_data.get("overall", "neutral"),
                    "de",
                    any(tc.get("tool") == "transfer_to_human" for tc in session_data.get("tool_calls", [])),
                    cost.get("gemini_cost_usd", 0),
                    cost.get("twilio_cost_usd", 0),
                    # avg_latency_ms — calculated from real turn metrics when available
                    (lambda metrics: round(sum(m.get("total_latency_ms", 0) for m in metrics) / len(metrics)) if metrics else 0)(
                        [m for m in session_data.get("turn_metrics", []) if m.get("total_latency_ms")]
                    ),
                    json.dumps(session_data, ensure_ascii=False),
                    json.dumps(analytics_data, ensure_ascii=False),
                    # Compliance columns
                    _parse_ts(session_data.get("recording_consent_at")),
                    bool(session_data.get("emergency_detected", False)),
                    # First emergency keyword hit (if any)
                    (session_data.get("emergency_events") or [{}])[0].get("keyword") if session_data.get("emergency_detected") else None,
                    bool(session_data.get("insurance_data_collected", False)),
                    # Audio URLs from GCS uploads
                    audio_urls.get("caller_audio"),
                    audio_urls.get("bot_audio"),
                )

                # Persist tool calls
                for i, tc in enumerate(session_data.get("tool_calls", [])):
                    await conn.execute("""
                        INSERT INTO google_tool_calls (
                            call_id, call_sid, tool_name, arguments, result_summary,
                            duration_ms, turn_number, called_at, success, error_message
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """,
                        call_id, call_sid, tc.get("tool", ""),
                        json.dumps(tc.get("args", {}), ensure_ascii=False),
                        tc.get("result_summary", "")[:500],
                        tc.get("duration_ms", 0),
                        i + 1,
                        _parse_ts(tc.get("timestamp")),
                        tc.get("success", True),
                        tc.get("error_message"),
                    )

                # Persist transcripts
                for i, tr in enumerate(session_data.get("transcripts", [])):
                    await conn.execute("""
                        INSERT INTO google_transcripts (
                            call_id, call_sid, role, content, turn_number, timestamp
                        ) VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                        call_id, call_sid, tr.get("role", ""),
                        tr.get("text", ""),
                        i + 1,
                        _parse_ts(tr.get("timestamp")),
                    )

                # Persist quality evaluation
                if quality:
                    await conn.execute("""
                        INSERT INTO google_quality_evaluations (
                            call_id, call_sid, score, issues,
                            tool_usage_score, greeting_score, problem_resolution_score
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                        call_id, call_sid,
                        quality.get("score", 0) / 10.0,
                        json.dumps(quality.get("issues", []), ensure_ascii=False),
                        quality.get("tools_used", 0) * 1.0,
                        5.0,
                        8.0 if quality.get("score", 0) > 50 else 4.0,
                    )

                logger.info(
                    f"Persisted call {call_sid} to Postgres (id={call_id}, "
                    f"tools={len(session_data.get('tool_calls', []))}, "
                    f"transcripts={len(session_data.get('transcripts', []))})"
                )

        # Persist turn metrics outside the main transaction (non-critical)
        turn_metrics = session_data.get("turn_metrics", [])
        if turn_metrics and call_id:
            await persist_turn_metrics(call_id, call_sid, turn_metrics)

        return call_id

    except Exception as e:
        logger.exception(f"Failed to persist call {call_sid}: {e}")
        return None


def _to_dict(record) -> dict:
    """Convert asyncpg Record to JSON-safe dict."""
    d = dict(record)
    for k, v in d.items():
        if isinstance(v, Decimal):
            d[k] = float(v)
        elif isinstance(v, datetime):
            d[k] = v.isoformat()
        elif isinstance(v, UUID):
            d[k] = str(v)
    return d


def _parse_ts(ts_str: Optional[str]) -> Optional[datetime]:
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str)
    except (ValueError, TypeError):
        return datetime.now(BERLIN_TZ)


async def get_overview_stats() -> dict:
    """Get dashboard overview metrics."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        today = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                ROUND(AVG(duration_seconds)) as avg_duration,
                ROUND(AVG(quality_score::numeric), 1) as avg_quality,
                SUM(total_cost_tokens + total_cost_telephony) as total_cost,
                COUNT(CASE WHEN was_escalated THEN 1 END) as escalated,
                ROUND(AVG(avg_latency_ms)) as avg_latency
            FROM google_calls
            WHERE DATE(started_at) = CURRENT_DATE
        """)

        last_week = await conn.fetchrow("""
            SELECT COUNT(*) as total
            FROM google_calls
            WHERE DATE(started_at) = CURRENT_DATE - INTERVAL '7 days'
        """)

        volume_7d = await conn.fetch("""
            SELECT DATE(started_at)::text as date, COUNT(*) as count
            FROM google_calls
            WHERE started_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(started_at)
            ORDER BY DATE(started_at)
        """)

        quality_7d = await conn.fetch("""
            SELECT DATE(started_at)::text as date, ROUND(AVG(quality_score::numeric), 1) as score
            FROM google_calls
            WHERE started_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(started_at)
            ORDER BY DATE(started_at)
        """)

        recent = await conn.fetch("""
            SELECT id, call_sid, caller_number, started_at, duration_seconds,
                   quality_score, outcome
            FROM google_calls
            WHERE ended_at IS NOT NULL
            ORDER BY started_at DESC
            LIMIT 5
        """)

        avg_dur = int(today["avg_duration"] or 0)
        total_today = int(today["total"] or 0)
        total_last_week = int(last_week["total"] or 0)
        return {
            "totalCallsToday": total_today,
            "activeNow": 0,
            "avgDurationToday": f"{avg_dur // 60}m {avg_dur % 60}s",
            "qualityScoreToday": float(today["avg_quality"] or 0),
            "costToday": float(today["total_cost"] or 0),
            "resolutionRate": 85,
            "avgLatency": int(today["avg_latency"] or 0),
            "escalatedToday": int(today["escalated"] or 0),
            "deltaCallsVsLastWeek": total_today - total_last_week,
            "deltaQualityVsLastWeek": 0,
            "callVolume7Days": [_to_dict(r) for r in volume_7d],
            "qualityTrend7Days": [_to_dict(r) for r in quality_7d],
            "recentCalls": [_to_dict(r) for r in recent],
            "alerts": [],
        }


async def get_calls_list(limit: int = 50, offset: int = 0, search: str = "") -> dict:
    """Get paginated list of calls."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        where = "1=1"
        params = []
        if search:
            where = "(caller_number ILIKE $1 OR call_sid ILIKE $1)"
            params.append(f"%{search}%")

        count = await conn.fetchval(
            f"SELECT COUNT(*) FROM google_calls WHERE {where}", *params
        )

        idx = len(params) + 1
        rows = await conn.fetch(f"""
            SELECT
                gc.id, gc.call_sid, gc.caller_number, gc.started_at,
                gc.duration_seconds, gc.quality_score, gc.outcome,
                gc.total_cost_tokens + gc.total_cost_telephony as total_cost,
                gc.was_escalated, gc.caller_audio_url, gc.agent_audio_url,
                (SELECT COUNT(*) FROM google_tool_calls WHERE call_id = gc.id) as tool_count
            FROM google_calls gc
            WHERE {where}
            ORDER BY gc.started_at DESC
            LIMIT ${idx} OFFSET ${idx + 1}
        """, *params, limit, offset)

        return {
            "calls": [_to_dict(r) for r in rows],
            "total": count,
            "limit": limit,
            "offset": offset,
        }


async def get_call_detail(call_id: int) -> Optional[dict]:
    """Get full details for a single call.
    
    Returns a flat CallData object matching page.tsx expectations:
    {
        call_sid, call_id, started_at, ended_at, duration_seconds, quality_score, outcome,
        transcript, tool_calls, quality_evaluation, analytics_data, total_cost, ...
    }
    """
    import json
    pool = await get_pool()
    async with pool.acquire() as conn:
        call = await conn.fetchrow("SELECT * FROM google_calls WHERE id = $1", call_id)
        if not call:
            return None

        call_dict = _to_dict(call)
        
        transcript = await conn.fetch(
            "SELECT * FROM google_transcripts WHERE call_id = $1 ORDER BY turn_number", call_id
        )
        tools = await conn.fetch(
            "SELECT * FROM google_tool_calls WHERE call_id = $1 ORDER BY turn_number", call_id
        )
        quality = await conn.fetchrow(
            "SELECT * FROM google_quality_evaluations WHERE call_id = $1", call_id
        )

        # Flatten response to match page.tsx CallData shape
        return {
            **call_dict,
            "transcript": [_to_dict(r) for r in transcript],
            "tool_calls": [
                {
                    "tool_name": _to_dict(r).get("tool_name", ""),
                    "input_data": _to_dict(r).get("arguments", "{}"),
                    "result": _to_dict(r).get("result_summary", ""),
                    "created_at": _to_dict(r).get("called_at", ""),
                }
                for r in tools
            ],
            "quality_evaluation": _to_dict(quality) if quality else None,
            "analytics_data": json.loads(call_dict.get("analytics_data") or "null"),
            "total_cost": float(call_dict.get("total_cost_tokens", 0)) + float(call_dict.get("total_cost_telephony", 0)),
        }




async def ensure_turn_metrics_table():
    """Create the google_turn_metrics table if it doesn't exist."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS google_turn_metrics (
                id SERIAL PRIMARY KEY,
                call_id UUID REFERENCES google_calls(id) ON DELETE CASCADE,
                call_sid TEXT NOT NULL,
                tenant_id TEXT,
                turn_number INTEGER NOT NULL,
                user_text TEXT,
                bot_text TEXT,
                vad_start_ms BIGINT,
                vad_stop_ms BIGINT,
                stt_latency_ms INTEGER,
                llm_latency_ms INTEGER,
                tts_latency_ms INTEGER,
                total_latency_ms INTEGER,
                tools_called JSONB DEFAULT '[]',
                node_name TEXT,
                stage1_clean_text TEXT,
                stage2_clean_text TEXT,
                stage3_text TEXT,
                has_markdown BOOLEAN DEFAULT FALSE,
                has_greeting BOOLEAN DEFAULT FALSE,
                stt_confidence REAL,
                build_sha TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        # Additive migrations for pre-existing deployments.
        for _col_ddl in (
            "ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS tenant_id TEXT",
            "ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS stt_confidence REAL",
            "ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS build_sha TEXT",
            # Sprint C: eager validation breakdown per turn
            "ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS validation_breakdown JSONB DEFAULT '{}'",
            # Adaptive TTS conditioning: situation style and caller mood per turn
            "ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS tts_situation TEXT",
            "ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS tts_mood TEXT",
            # Phase 1: per-layer observability columns (la-layer-observability)
            "ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS layer1_decision JSONB",
            "ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS layer2_raw_output TEXT",
            "ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS layer3_changes JSONB",
        ):
            try:
                await conn.execute(_col_ddl)
            except Exception as _mig_err:
                logger.warning(f"[DB] migration '{_col_ddl}' failed: {_mig_err}")
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_turn_metrics_call_sid
            ON google_turn_metrics(call_sid)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_turn_metrics_call_id
            ON google_turn_metrics(call_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_turn_metrics_tenant_id
            ON google_turn_metrics(tenant_id)
        """)
    logger.info("google_turn_metrics table ensured")


async def ensure_turn_evaluations_table():
    """Create the turn_evaluations table if it doesn't exist."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS turn_evaluations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                call_sid VARCHAR(255) NOT NULL,
                turn_number INT NOT NULL,
                scenario_matched VARCHAR(100),
                scenario_confidence REAL,
                expected_tools JSONB,
                actual_tools JSONB,
                trajectory_match VARCHAR(20),
                stage_status JSONB,
                failure_patterns JSONB,
                turn_verdict VARCHAR(20),
                verdict_reason TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(call_sid, turn_number),
                FOREIGN KEY (call_sid) REFERENCES google_calls(call_sid)
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_turn_eval_call
            ON turn_evaluations(call_sid, turn_number)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_turn_eval_verdict
            ON turn_evaluations(turn_verdict)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_turn_eval_patterns
            ON turn_evaluations USING GIN (failure_patterns)
        """)
    logger.info("turn_evaluations table ensured")


async def ensure_guardian_blocks_table():
    """Create the guardian_blocks table if it doesn't exist (G3.1 — GUARDIAN pre-commit gate)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS guardian_blocks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                call_sid VARCHAR(255) NOT NULL,
                turn_number INT NOT NULL,
                tool_name VARCHAR(100) NOT NULL,
                reason TEXT NOT NULL,
                args JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_guardian_blocks_call
            ON guardian_blocks(call_sid, turn_number)
        """)
    logger.info("guardian_blocks table ensured")


async def persist_guardian_block(call_sid: str, turn_number: int, tool_name: str, reason: str, args: dict) -> None:
    """Write a GUARDIAN block event to guardian_blocks. Fire-and-forget — never raises."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO guardian_blocks (call_sid, turn_number, tool_name, reason, args)
                VALUES ($1, $2, $3, $4, $5)
                """,
                call_sid,
                turn_number,
                tool_name,
                reason,
                json.dumps(args, default=_default_serializer),
            )
        logger.info(f"[GUARDIAN] block recorded: {tool_name} blocked at turn {turn_number} for {call_sid}")
    except Exception as e:
        logger.debug(f"[GUARDIAN] persist_guardian_block failed (non-fatal): {e}")


async def persist_turn_metrics(call_id: int, call_sid: str, metrics: list[dict]) -> None:
    """Write per-turn metrics to google_turn_metrics. Called after persist_call.
    
    Writes all columns from the Sprint 0 observability expansion:
      - LLM config (tokens, max_output, temperature)
      - Slot state + diff + counts + missing-required
      - ValidationRegistry fired/completed/pending/cancellations
      - Raw utterance-in-prompt flag + prompt snapshot
      - Intent flags + node + multi-intent flag
      - Mood confidence + signals matched
      - Barge-in attempted/succeeded/latency
      - Loop detection signals
      - Subsystems fired tracker
    """
    if not metrics:
        return
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            for m in metrics:
                await conn.execute("""
                    INSERT INTO google_turn_metrics (
                        call_id, call_sid, turn_number, user_text, bot_text,
                        vad_start_ms, vad_stop_ms, stt_latency_ms, llm_latency_ms,
                        tts_latency_ms, total_latency_ms, tools_called, node_name,
                        stage1_clean_text, stage2_clean_text, stage3_text,
                        has_markdown, has_greeting, validation_breakdown,
                        tts_situation, tts_mood, stt_confidence,
                        -- Sprint 0 expansion begins
                        prompt_tokens_in, prompt_tokens_out, max_output_tokens_config,
                        temperature_config, top_p_config,
                        slot_state_json, slot_state_diff,
                        slots_filled_count, slots_confirmed_count, slots_missing_required,
                        validations_fired_this_turn, validations_completed_this_turn,
                        validations_pending_end_of_turn, validation_cancellations,
                        raw_utterance_in_prompt, prompt_snapshot_head,
                        intent_flags_active, node_active, prompt_had_multiple_intents,
                        mood_confidence, mood_signals_matched,
                        barge_in_attempted, barge_in_succeeded, barge_in_latency_ms,
                        loop_detected_in_stream, loop_reason,
                        stream_aborted_at_sentence, cross_turn_similarity_max,
                        subsystems_fired, tts_rate_pct
                    ) VALUES (
                        $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,
                        $19,$20,$21,$22,
                        $23,$24,$25,$26,$27,
                        $28,$29,$30,$31,$32,
                        $33,$34,$35,$36,
                        $37,$38,
                        $39,$40,$41,
                        $42,$43,
                        $44,$45,$46,
                        $47,$48,$49,$50,
                        $51,$52
                    )
                    ON CONFLICT DO NOTHING
                """,
                    call_id, call_sid,
                    m.get("turn_number", 0),
                    m.get("user_text", ""),
                    m.get("bot_text", ""),
                    m.get("vad_start_ms"),
                    m.get("vad_stop_ms"),
                    m.get("stt_latency_ms"),
                    m.get("llm_latency_ms"),
                    m.get("tts_latency_ms"),
                    m.get("total_latency_ms"),
                    json.dumps(m.get("tools_called", []), ensure_ascii=False),
                    m.get("node_name"),
                    m.get("stage1_clean_text"),
                    m.get("stage2_clean_text"),
                    m.get("stage3_text"),
                    bool(m.get("has_markdown", False)),
                    bool(m.get("has_greeting", False)),
                    json.dumps(m.get("validation_breakdown", {}), ensure_ascii=False),
                    m.get("tts_situation"),
                    m.get("tts_mood"),
                    m.get("stt_confidence"),
                    # Sprint 0 expansion payload
                    m.get("prompt_tokens_in"),
                    m.get("prompt_tokens_out"),
                    m.get("max_output_tokens_config"),
                    m.get("temperature_config"),
                    m.get("top_p_config"),
                    json.dumps(m.get("slot_state_json"), ensure_ascii=False) if m.get("slot_state_json") is not None else None,
                    json.dumps(m.get("slot_state_diff"), ensure_ascii=False) if m.get("slot_state_diff") is not None else None,
                    m.get("slots_filled_count"),
                    m.get("slots_confirmed_count"),
                    json.dumps(m.get("slots_missing_required"), ensure_ascii=False) if m.get("slots_missing_required") is not None else None,
                    json.dumps(m.get("validations_fired_this_turn"), ensure_ascii=False) if m.get("validations_fired_this_turn") is not None else None,
                    json.dumps(m.get("validations_completed_this_turn"), ensure_ascii=False) if m.get("validations_completed_this_turn") is not None else None,
                    json.dumps(m.get("validations_pending_end_of_turn"), ensure_ascii=False) if m.get("validations_pending_end_of_turn") is not None else None,
                    m.get("validation_cancellations"),
                    m.get("raw_utterance_in_prompt"),
                    m.get("prompt_snapshot_head"),
                    json.dumps(m.get("intent_flags_active"), ensure_ascii=False) if m.get("intent_flags_active") is not None else None,
                    m.get("node_active"),
                    m.get("prompt_had_multiple_intents"),
                    m.get("mood_confidence"),
                    json.dumps(m.get("mood_signals_matched"), ensure_ascii=False) if m.get("mood_signals_matched") is not None else None,
                    m.get("barge_in_attempted"),
                    m.get("barge_in_succeeded"),
                    m.get("barge_in_latency_ms"),
                    m.get("loop_detected_in_stream"),
                    m.get("loop_reason"),
                    m.get("stream_aborted_at_sentence"),
                    m.get("cross_turn_similarity_max"),
                    json.dumps(m.get("subsystems_fired"), ensure_ascii=False) if m.get("subsystems_fired") is not None else None,
                    m.get("tts_rate_pct"),
                )
        logger.debug(f"Persisted {len(metrics)} turn metrics for {call_sid}")
    except Exception as e:
        logger.warning(f"Failed to persist turn metrics for {call_sid}: {e}")


async def persist_call_aggregates(call_sid: str) -> None:
    """Sprint 0.4 call-end aggregation hook + Sprint 3.4 cost tracking.

    Reads google_turn_metrics rows for a call and writes derived percentiles,
    subsystem-health aggregates, and estimated cost_cents back to google_calls.
    Non-fatal on error.
    """
    pool = await get_pool()
    try:
        async with pool.acquire() as conn:
            aggregates = await conn.fetchrow("""
                SELECT
                    ROUND(AVG(total_latency_ms))::INT AS avg_latency_ms,
                    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY total_latency_ms))::INT AS p50_latency_ms,
                    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_ms))::INT AS p95_latency_ms,
                    MAX(total_latency_ms) AS max_latency_ms,
                    COALESCE(SUM(total_latency_ms), 0) AS total_dead_air_ms,
                    COUNT(*) FILTER (
                        WHERE subsystems_fired->>'slot_extractor' = 'completed'
                    )::FLOAT
                        / NULLIF(COUNT(*), 0) AS slot_extractor_success_rate,
                    COUNT(*) FILTER (
                        WHERE subsystems_fired->>'validation_registry' = 'fired'
                    )::INT AS validation_registry_invocations,
                    COUNT(*) FILTER (WHERE loop_detected_in_stream)::INT AS loop_incidents,
                    -- Sprint 3.4: token + char totals for cost estimation
                    COALESCE(SUM(prompt_tokens_in), 0)::INT AS tokens_in_total,
                    COALESCE(SUM(prompt_tokens_out), 0)::INT AS tokens_out_total,
                    COALESCE(SUM(LENGTH(bot_text)), 0)::INT AS tts_chars_total
                FROM google_turn_metrics
                WHERE call_sid = $1
            """, call_sid)
            if not aggregates:
                return

            # Sprint 3.4: cost estimation in cents.
            # Rates (2026 pricing, USD):
            #   Deepgram Nova-3: $0.0043/min
            #   Gemini 2.5 Flash input:  $0.075 per 1M tokens
            #   Gemini 2.5 Flash output: $0.30  per 1M tokens
            #   Gemini 2.5 Flash TTS: ~$30 per 1M chars
            #   Twilio voice EU: ~$0.85/min (rough)
            # We approximate STT/Twilio from duration_seconds fetched below.
            duration_row = await conn.fetchrow(
                "SELECT duration_seconds FROM google_calls WHERE call_sid = $1",
                call_sid,
            )
            duration_s = float((duration_row or {}).get("duration_seconds") or 0)
            stt_cents = (duration_s / 60.0) * 0.43  # $0.0043/min → 0.43¢
            llm_in_cents = (aggregates["tokens_in_total"] / 1_000_000.0) * 7.5
            llm_out_cents = (aggregates["tokens_out_total"] / 1_000_000.0) * 30.0
            tts_cents = (aggregates["tts_chars_total"] / 1_000_000.0) * 3000.0
            twilio_cents = (duration_s / 60.0) * 85.0
            cost_cents = round(
                stt_cents + llm_in_cents + llm_out_cents + tts_cents + twilio_cents,
                4,
            )

            await conn.execute("""
                UPDATE google_calls SET
                    avg_latency_ms = COALESCE($2, avg_latency_ms),
                    p50_latency_ms = COALESCE($3, p50_latency_ms),
                    p95_latency_ms = COALESCE($4, p95_latency_ms),
                    max_latency_ms = COALESCE($5, max_latency_ms),
                    total_dead_air_ms = COALESCE($6, total_dead_air_ms),
                    slot_extractor_success_rate = COALESCE($7, slot_extractor_success_rate),
                    validation_registry_invocations = COALESCE($8, validation_registry_invocations),
                    loop_incidents = COALESCE($9, loop_incidents),
                    cost_cents = COALESCE($10, cost_cents)
                WHERE call_sid = $1
            """,
                call_sid,
                aggregates["avg_latency_ms"],
                aggregates["p50_latency_ms"],
                aggregates["p95_latency_ms"],
                aggregates["max_latency_ms"],
                int(aggregates["total_dead_air_ms"]) if aggregates["total_dead_air_ms"] is not None else None,
                aggregates["slot_extractor_success_rate"],
                aggregates["validation_registry_invocations"],
                aggregates["loop_incidents"],
                cost_cents,
            )
    except Exception as e:
        logger.warning(f"Failed to persist call aggregates for {call_sid}: {e}")


async def get_calls_with_latency(limit: int = 50, offset: int = 0) -> dict:
    """Get calls list with per-turn latency aggregates for Call Analysis tab.

    Field names are aligned with the Next.js CallSummary interface:
      avg_latency_ms, p95_latency_ms, issues_count, turn_count
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM google_calls")
        rows = await conn.fetch("""
            SELECT
                gc.id, gc.call_sid, gc.caller_number, gc.started_at, gc.ended_at,
                gc.duration_seconds, gc.quality_score, gc.outcome, gc.was_escalated,
                COALESCE(
                    (SELECT COUNT(*) FROM google_turn_metrics WHERE call_sid = gc.call_sid),
                    0
                ) as turn_count,
                COALESCE(
                    (SELECT ROUND(AVG(total_latency_ms)) FROM google_turn_metrics WHERE call_sid = gc.call_sid),
                    gc.avg_latency_ms
                ) as avg_latency_ms,
                COALESCE(
                    (SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_ms)
                     FROM google_turn_metrics WHERE call_sid = gc.call_sid AND total_latency_ms IS NOT NULL),
                    0
                )::bigint as p95_latency_ms,
                (
                    COALESCE(
                        (SELECT COUNT(*) FROM google_turn_metrics WHERE call_sid = gc.call_sid AND has_greeting = TRUE),
                        0
                    ) +
                    COALESCE(
                        (SELECT COUNT(*) FROM google_turn_metrics WHERE call_sid = gc.call_sid AND has_markdown = TRUE),
                        0
                    )
                ) as issues_count
            FROM google_calls gc
            ORDER BY gc.started_at DESC
            LIMIT $1 OFFSET $2
        """, limit, offset)

        return {
            "calls": [_to_dict(r) for r in rows],
            "total": count,
            "limit": limit,
            "offset": offset,
        }


async def get_turn_metrics(call_sid: str) -> list[dict]:
    """Get all per-turn metrics for a single call, ordered by turn number.

    Adds `tools_fired` alias for `tools_called` to match the Next.js TurnMetric interface.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM google_turn_metrics
            WHERE call_sid = $1
            ORDER BY turn_number
        """, call_sid)
        results = []
        for r in rows:
            d = _to_dict(r)
            # Parse tools_called JSON string into list and alias as tools_fired for the UI
            tc = d.get("tools_called", "[]")
            if isinstance(tc, str):
                import json as _json
                try:
                    tc = _json.loads(tc)
                except Exception:
                    tc = []
            d["tools_fired"] = tc if isinstance(tc, list) else []
            results.append(d)
        return results


async def get_latency_stats() -> dict:
    """Aggregate latency percentiles across all calls for the dashboard summary."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_turns,
                COUNT(DISTINCT call_sid) as total_calls,
                ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY total_latency_ms)) as p50_total_ms,
                ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_ms)) as p95_total_ms,
                ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_latency_ms)) as p99_total_ms,
                ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY stt_latency_ms)) as p50_stt_ms,
                ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY stt_latency_ms)) as p95_stt_ms,
                ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY llm_latency_ms)) as p50_llm_ms,
                ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY llm_latency_ms)) as p95_llm_ms,
                ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY tts_latency_ms)) as p50_tts_ms,
                ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY tts_latency_ms)) as p95_tts_ms,
                SUM(CASE WHEN has_markdown THEN 1 ELSE 0 END) as markdown_issues,
                SUM(CASE WHEN has_greeting THEN 1 ELSE 0 END) as greeting_issues
            FROM google_turn_metrics
            WHERE total_latency_ms IS NOT NULL
        """)
        return _to_dict(row) if row else {}


async def get_turn_context(call_sid: str, turn_number: int) -> Optional[dict]:
    """Get stored context for a specific turn, shaped for the Next.js ReplayResult interface.

    Returns: { turn_number, original_output, replayed_output, context_preview, diagnostic_stages, tools }
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                tm.*,
                gc.session_data,
                gc.analytics_data
            FROM google_turn_metrics tm
            JOIN google_calls gc ON gc.call_sid = tm.call_sid
            WHERE tm.call_sid = $1 AND tm.turn_number = $2
        """, call_sid, turn_number)
        if not row:
            return None
        d = _to_dict(row)
        import json as _json
        session = d.pop("session_data", None) or "{}"
        analytics = d.pop("analytics_data", None) or "{}"
        if isinstance(session, str):
            try:
                session = _json.loads(session)
            except Exception:
                session = {}
        
        # Get tools for this turn
        tools = await conn.fetch("""
            SELECT tool_name, arguments, result_summary, duration_ms, success, error_message
            FROM google_tool_calls
            WHERE call_sid = $1 AND turn_number = $2
        """, call_sid, turn_number)
        
        ctx_parts = []
        if d.get("user_text"):
            ctx_parts.append(f"User: {d['user_text']}")
        if d.get("node_name"):
            ctx_parts.append(f"Node: {d['node_name']}")
        
        return {
            "turn_number": d.get("turn_number", turn_number),
            "original_output": d.get("bot_text", ""),
            "replayed_output": None,
            "context_preview": " | ".join(ctx_parts) if ctx_parts else str(d.get("user_text", "")),
            "note": "live replay requires Phase 2 architectural changes",
            "diagnostic_stages": {
                "stage1_clean_text": d.get("stage1_clean_text"),
                "stage2_clean_text": d.get("stage2_clean_text"),
                "stage3_text": d.get("stage3_text"),
            },
            "tools": [
                {
                    "tool_name": t["tool_name"],
                    "arguments": t["arguments"] if isinstance(t["arguments"], dict) else {},
                    "result_summary": t["result_summary"],
                    "duration_ms": t["duration_ms"],
                    "success": t["success"],
                    "error_message": t["error_message"],
                }
                for t in tools
            ],
            "latencies": {
                "stt_ms": d.get("stt_latency_ms"),
                "llm_ms": d.get("llm_latency_ms"),
                "tts_ms": d.get("tts_latency_ms"),
                "total_ms": d.get("total_latency_ms"),
            },
        }


async def ensure_whatsapp_contacts_table():
    """Create the whatsapp_contacts table if it doesn't exist."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_contacts (
                id SERIAL PRIMARY KEY,
                phone_number TEXT UNIQUE NOT NULL,
                opted_in_at TIMESTAMPTZ DEFAULT NOW(),
                source TEXT DEFAULT 'wa_link',
                last_message_at TIMESTAMPTZ
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_wa_contacts_phone
            ON whatsapp_contacts(phone_number)
        """)
    logger.info("whatsapp_contacts table ensured")


async def is_whatsapp_opted_in(phone: str) -> bool:
    """Check if a phone number has opted in for WhatsApp messaging."""
    if not phone:
        return False
    normalized = phone.lstrip("+")
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchval(
            "SELECT 1 FROM whatsapp_contacts WHERE phone_number = $1 OR phone_number = $2",
            phone, normalized,
        )
        return row is not None


async def register_whatsapp_optin(phone: str, source: str = "wa_link"):
    """Register a phone number as opted in for WhatsApp. Idempotent."""
    if not phone:
        return
    normalized = "+" + phone.lstrip("+")
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO whatsapp_contacts (phone_number, source, last_message_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (phone_number) DO UPDATE SET last_message_at = NOW()
        """, normalized, source)
    logger.info(f"WhatsApp opt-in registered: {normalized} (source={source})")


async def get_analytics() -> dict:
    """Get aggregated analytics data."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        volume = await conn.fetch("""
            SELECT DATE(started_at)::text as date, COUNT(*) as count
            FROM google_calls
            WHERE started_at >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE(started_at) ORDER BY DATE(started_at)
        """)

        quality_dist = await conn.fetch("""
            SELECT
                CASE
                    WHEN quality_score >= 9 THEN '9-10'
                    WHEN quality_score >= 8 THEN '8-9'
                    WHEN quality_score >= 7 THEN '7-8'
                    WHEN quality_score >= 6 THEN '6-7'
                    ELSE '<6'
                END as range,
                COUNT(*) as count
            FROM google_calls WHERE quality_score IS NOT NULL
            GROUP BY range ORDER BY range DESC
        """)

        outcomes = await conn.fetch("""
            SELECT outcome, COUNT(*) as count, ROUND(AVG(quality_score::numeric), 1) as avg_quality
            FROM google_calls WHERE outcome IS NOT NULL
            GROUP BY outcome
        """)

        cost = await conn.fetchrow("""
            SELECT
                SUM(total_cost_tokens) as tokens_cost,
                SUM(total_cost_telephony) as telephony_cost,
                SUM(total_cost_tokens + total_cost_telephony) as total_cost
            FROM google_calls
            WHERE started_at >= CURRENT_DATE - INTERVAL '30 days'
        """)

        sentiments = await conn.fetch("""
            SELECT sentiment, COUNT(*) as count
            FROM google_calls WHERE sentiment IS NOT NULL
            GROUP BY sentiment
        """)

        return {
            "callVolume": [_to_dict(r) for r in volume],
            "qualityDistribution": [_to_dict(r) for r in quality_dist],
            "outcomes": [_to_dict(r) for r in outcomes],
            "latencyDistribution": [],
            "costBreakdown": _to_dict(cost) if cost else {},
            "languages": [{"language": "de", "count": await conn.fetchval("SELECT COUNT(*) FROM google_calls")}],
            "sentiments": [_to_dict(r) for r in sentiments],
        }
