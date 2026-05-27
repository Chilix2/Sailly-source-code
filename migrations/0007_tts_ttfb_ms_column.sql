-- Phase 9 A1: Add tts_ttfb_ms (time-to-first-byte from brain perspective)
-- This column captures the end-to-end latency from when STT completes (stt_done_at)
-- to when the first audio chunk is sent to the client (tts_first_byte_at).
-- Idempotent: uses ADD COLUMN IF NOT EXISTS

-- ── Time-to-first-audio (TTFB) from brain perspective ────────────────────────────
-- Calculated as: tts_first_byte_at - stt_done_at (in milliseconds)
-- Includes: LLM processing + TTS synthesis + network delay
-- This is the primary metric for perceived latency to the user
ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS tts_ttfb_ms INT;

-- ── Update llm_latency_ms label (optional; documented below) ──────────────────────
-- Note: llm_latency_ms in the existing schema is computed as:
--   time from stt_done to first TTS text sent (l2_done if no tools, tool_done if tools)
-- This captures "brain processing time" (LLM only, no TTS synthesis)
-- 
-- tts_ttfb_ms captures end-to-end "perceived latency":
--   time from stt_done to first audio byte (TTFB)
-- 
-- The breakdown is:
--   tts_ttfb_ms ≈ llm_latency_ms + tts_first_byte_ms
--   where tts_first_byte_ms = time from l2_done (or tool_done) to first audio

-- ── Indexes for common queries ────────────────────────────────────────────────
-- Already created by migration 0002, but repeated for safety
CREATE INDEX IF NOT EXISTS idx_turn_metrics_tts_ttfb_ms
    ON google_turn_metrics (tts_ttfb_ms)
    WHERE tts_ttfb_ms IS NOT NULL;
