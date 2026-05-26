CREATE TABLE IF NOT EXISTS google_call_reports (
    id BIGSERIAL PRIMARY KEY,
    call_sid TEXT NOT NULL UNIQUE REFERENCES google_calls(call_sid) ON DELETE CASCADE,
    json_path TEXT,
    md_path TEXT,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    found BOOLEAN NOT NULL DEFAULT FALSE,
    transcript_count INTEGER NOT NULL DEFAULT 0,
    turn_metric_count INTEGER NOT NULL DEFAULT 0,
    tool_call_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_google_call_reports_generated_at
    ON google_call_reports(generated_at DESC);
