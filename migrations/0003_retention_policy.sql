-- Phase 9 A5: 90-day retention per decision retain-90.
-- Transcripts (google_turn_metrics) → 90 days, then purged.
-- Aggregates (google_calls) → retained forever.
-- Compliance (audit_log)    → retained forever.
--
-- pg_cron variant (preferred if available):
--   SELECT cron.schedule(
--       'cleanup-old-transcripts',
--       '0 3 * * *',          -- 03:00 UTC daily
--       $$SELECT cleanup_old_transcripts()$$
--   );
--
-- If pg_cron is unavailable, use scripts/cron/cleanup_old_transcripts.sh
-- scheduled via systemd timer (see systemd/sailly-cleanup.timer).

-- ── Cleanup function ─────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION cleanup_old_transcripts()
RETURNS TABLE(deleted_turn_rows BIGINT) AS $$
DECLARE
    _n BIGINT;
BEGIN
    -- Delete turn-level transcript data older than 90 days.
    -- PII in user_text/bot_text/slot_state_json is removed with the row.
    -- Aggregates in google_calls and audit_log are intentionally NOT touched.
    DELETE FROM google_turn_metrics
    WHERE ts < now() - interval '90 days';

    GET DIAGNOSTICS _n = ROW_COUNT;
    RETURN QUERY SELECT _n;
END;
$$ LANGUAGE plpgsql;

-- ── Verify the function works (dry-run in a transaction that is rolled back) ──
-- Run this manually to test before scheduling:
--   BEGIN;
--   SELECT cleanup_old_transcripts();
--   ROLLBACK;
