-- Phase 9 A1: Full per-turn observability schema (9.O1 + 9.O2 + 9.O3 + 9.O4)
-- Idempotent: uses ALTER TABLE ... ADD COLUMN IF NOT EXISTS
-- Run against production DB after Phase 8 migration.

-- ── Per-stage latency (per-stage decision 9.O2) ───────────────────────────────
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS stt_ms            INT;
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS extract_ms        INT;
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS l2_ms             INT;
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS tool_ms           INT;
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS tts_first_byte_ms INT;
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS total_ms          INT;

-- ── Token + cost (cost-dashboard decision 9.O3) ───────────────────────────────
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS prompt_tokens_in  INT;
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS prompt_tokens_out INT;
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS extract_tokens_in INT;
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS extract_tokens_out INT;
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS cost_eur          NUMERIC(10, 6);

-- ── Per-tool timing (per-tool-timing decision 9.O7) ──────────────────────────
-- Format: {"create_order": 245, "send_sms": 88}
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS tool_durations    JSONB;

-- ── STT + routing context ──────────────────────────────────────────────────────
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS stt_model         TEXT;
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS asr_confidence    NUMERIC(4, 3);
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS active_node       TEXT;

-- ── Error taxonomy (structured-codes decision 9.O4) ─────────────────────────
-- Array of ERR_* codes emitted this turn (e.g. {ERR_LLM_429, ERR_MAPS_TIMEOUT})
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS error_codes       TEXT[];

-- ── Indexes for dashboard queries ────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_turn_metrics_call_sid
    ON google_turn_metrics (call_sid);

CREATE INDEX IF NOT EXISTS idx_turn_metrics_tenant_time
    ON google_turn_metrics (tenant_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_turn_metrics_active_node
    ON google_turn_metrics (active_node);

CREATE INDEX IF NOT EXISTS idx_turn_metrics_error_codes
    ON google_turn_metrics USING GIN (error_codes);

-- ── Disposition column on google_calls (A2 disposition labeling) ─────────────
ALTER TABLE google_calls ADD COLUMN IF NOT EXISTS disposition TEXT;
ALTER TABLE google_calls ADD COLUMN IF NOT EXISTS call_cost_eur NUMERIC(10, 6);

-- ── Callback queue (B7 from Phase 8, surfaced in dashboard) ──────────────────
CREATE TABLE IF NOT EXISTS callback_queue (
    id           BIGSERIAL PRIMARY KEY,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    call_sid     TEXT        NOT NULL,
    tenant_id    TEXT        NOT NULL,
    phone        TEXT,
    name         TEXT,
    context_summary TEXT,
    scheduled_for TIMESTAMPTZ,
    status       TEXT NOT NULL DEFAULT 'pending'  -- pending | done | cancelled
);
CREATE INDEX IF NOT EXISTS idx_callback_status_sched
    ON callback_queue (status, scheduled_for ASC)
    WHERE status = 'pending';
