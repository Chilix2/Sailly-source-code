-- Phase 8: append-only audit trail per decision postgres-audit-table (8.S8)
-- Run once against the production database. Idempotent (CREATE TABLE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT now(),
    call_sid    TEXT        NOT NULL,
    tenant_id   TEXT        NOT NULL,
    tool_name   TEXT        NOT NULL,
    args        JSONB       NOT NULL,
    result      JSONB       NOT NULL,
    success     BOOLEAN     NOT NULL
);

-- Fast lookup by call for dispute resolution
CREATE INDEX IF NOT EXISTS idx_audit_call_sid  ON audit_log (call_sid);
-- Fast time-range queries for dashboards and retention cleanup
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log (timestamp DESC);
-- Per-tenant rollup (Phase 9 dashboards)
CREATE INDEX IF NOT EXISTS idx_audit_tenant    ON audit_log (tenant_id, timestamp DESC);

-- Append-only enforcement: application role may INSERT but not UPDATE or DELETE.
-- Run as superuser; adjust role name to match your Cloud SQL setup.
-- REVOKE UPDATE, DELETE ON audit_log FROM sailly_app;
-- GRANT INSERT, SELECT ON audit_log TO sailly_app;
-- GRANT USAGE, SELECT ON SEQUENCE audit_log_id_seq TO sailly_app;
