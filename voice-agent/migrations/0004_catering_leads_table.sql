-- Migration 0004: catering_leads table
-- Created: PR-7 / FINDING-012 (capture_catering_lead handler — Phase 4 C4)
--
-- Per Phase 4 C4 decision (catering-warm-handoff): catering enquiries for
-- groups > 20 persons or special occasions do NOT commit a reservation.
-- Instead a lead row is written here so a sales rep can call back.
--
-- The application user (sailly) has INSERT + SELECT only. UPDATE/DELETE
-- are reserved for the CRM/admin role to set follow_up_status.
--
-- Apply with:
--   psql $POSTGRES_DSN -f migrations/0004_catering_leads_table.sql

CREATE TABLE IF NOT EXISTS catering_leads (
    id                   BIGSERIAL PRIMARY KEY,
    call_sid             TEXT        NOT NULL,
    tenant_id            TEXT        NOT NULL,
    phone                TEXT        NOT NULL,
    name                 TEXT        NOT NULL,
    occasion_date        TEXT,                        -- natural language or ISO date
    guests               INT,
    callback_availability TEXT,                       -- e.g. "Mo-Fr 9-17 Uhr"
    notes                TEXT,
    captured_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    follow_up_status     TEXT        NOT NULL DEFAULT 'pending'
                             CHECK (follow_up_status IN ('pending', 'contacted', 'booked', 'lost'))
);

CREATE INDEX IF NOT EXISTS idx_catering_leads_status_captured
    ON catering_leads (follow_up_status, captured_at DESC);

CREATE INDEX IF NOT EXISTS idx_catering_leads_tenant_captured
    ON catering_leads (tenant_id, captured_at DESC);

COMMENT ON TABLE catering_leads IS
    'Catering enquiry leads captured by the voice bot (Phase 4 C4). '
    'Append-only from the application; CRM updates follow_up_status.';
