-- Phase 2: ExecutionSpan trace — flat per-span table (Langfuse-style observations).
-- One row per operation within a turn. Scalar columns are indexed for cross-call
-- aggregation ("which layer/operation/tool breaks most"); variable payload lives
-- in JSONB. Adjacency via parent_span_id (hierarchy is shallow — no ltree needed).
-- Idempotent: CREATE ... IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS google_turn_spans (
    id            BIGSERIAL PRIMARY KEY,
    call_sid      TEXT        NOT NULL,
    turn_number   INTEGER     NOT NULL,
    tenant_id     TEXT,
    span_id       TEXT        NOT NULL,
    parent_span_id TEXT,
    layer         SMALLINT    NOT NULL,           -- 1 Orchestrator / 2 LLM / 3 Policy
    operation     TEXT        NOT NULL,           -- classify|prereq|chat|commit_gate|policy|execute_tool
    name          TEXT,
    status        TEXT        NOT NULL DEFAULT 'ok', -- ok|error|blocked
    t_start_ms    DOUBLE PRECISION,
    t_end_ms      DOUBLE PRECISION,
    latency_ms    DOUBLE PRECISION,
    ttft_ms       DOUBLE PRECISION,
    model         TEXT,
    tokens_in     INTEGER,
    tokens_out    INTEGER,
    finish_reason TEXT,
    io            JSONB       NOT NULL DEFAULT '{}',
    build_sha     TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One physical row per (call, turn, span); re-persist replaces cleanly.
CREATE UNIQUE INDEX IF NOT EXISTS uq_turn_spans_call_turn_span
    ON google_turn_spans (call_sid, turn_number, span_id);

-- Cross-call aggregation: "which operation/layer/status breaks most".
CREATE INDEX IF NOT EXISTS idx_turn_spans_op_status
    ON google_turn_spans (operation, status);
CREATE INDEX IF NOT EXISTS idx_turn_spans_layer
    ON google_turn_spans (layer);
CREATE INDEX IF NOT EXISTS idx_turn_spans_call
    ON google_turn_spans (call_sid, turn_number);
CREATE INDEX IF NOT EXISTS idx_turn_spans_tenant
    ON google_turn_spans (tenant_id);
