-- Phase 0B: Layer observability columns for turn-level tracing (Sailly Debugger)
-- Idempotent: uses ALTER TABLE ... ADD COLUMN IF NOT EXISTS
-- Run after Phase 9 migration 0002

-- ── Layer 1: FSM node routing and forced tool decisions ───────────────────────────
-- layer1_decision = {"node": "PROMPT_PHONE", "forced_tools": ["send_sms"], "state_hash": "abc123", "validators_run": [...]}
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS layer1_decision JSONB;

-- ── Layer 2: Raw LLM output before policy rewrite ──────────────────────────────────
-- layer2_raw_output = first 500 chars of Gemini text response (for debugging)
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS layer2_raw_output TEXT;

-- ── Layer 3: Policy layer warnings and rewrites ──────────────────────────────────────
-- layer3_changes = {"text_changed": false, "tools_changed": false, "warnings": ["confidence_low"]}
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS layer3_changes JSONB;

-- ── Indexes for debugger queries ──────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_turn_metrics_layer1_decision
    ON google_turn_metrics USING GIN (layer1_decision);

CREATE INDEX IF NOT EXISTS idx_turn_metrics_layer3_changes
    ON google_turn_metrics USING GIN (layer3_changes);
