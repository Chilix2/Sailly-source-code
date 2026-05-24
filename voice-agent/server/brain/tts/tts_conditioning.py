"""
TTS conditioning per Phase 7 decisions.

Per tts-speed-baseline: rate-15  — DOBOO baseline 1.5×.
Per tts-rate-clamp: clamp-75-200 — final rate clamped to 0.75–2.0 range.
Per tts-moods: moods-on          — caller mood applies a rate_mul on top of situation.

compute_speaking_rate() is the single source of truth for the final speaking rate.
All callers (tts_client.py, brain_service.py, tests) should use this function.

Relationship to server/brain/tts_conditioning.py (the original file):
  That file remains the live production path imported by brain_service.py. This
  module adds the tenant-YAML-driven baseline and exports compute_speaking_rate()
  as the clean Phase 7 API. Phase 8 migration will consolidate the two files.
"""
from __future__ import annotations

GLOBAL_SPEED_MULTIPLIER_DEFAULT: float = 1.5
RATE_CLAMP_MIN: float = 0.75
RATE_CLAMP_MAX: float = 2.00


def compute_speaking_rate(
    situation: str,
    mood: str,
    tenant_cfg: dict,
) -> float:
    """
    Final rate = baseline × situation_rate × mood_rate_mul, clamped to [0.75, 2.0].

    Per VoiceTier.{PERSONA, SITUATION, CALLER_MIRROR} from Phase 1 vocab:
      - baseline  → tenant YAML tts.speed_multiplier (default 1.5×)
      - situation → SITUATION_STYLES[situation]["rate"]
      - mood      → CALLER_MIRRORS[mood]["rate_mul"]

    Verified test cases (baseline 1.5):
      GREETING_FIRST + NEUTRAL  → 1.5 × 1.05 × 1.0  = 1.575
      INFO_READBACK  + CONFUSED → 1.5 × 0.88 × 0.88 = 1.162  (rounds to 1.16)
      URGENT_CLEAR   + IMPATIENT→ 1.5 × 1.05 × 1.05 = 1.654  (under 2.0 cap)
    """
    from server.brain.tts.situation_styles import SITUATION_STYLES
    from server.brain.tts.caller_mirrors import CALLER_MIRRORS

    baseline: float = tenant_cfg.get("tts", {}).get(
        "speed_multiplier", GLOBAL_SPEED_MULTIPLIER_DEFAULT
    )
    sit_rate: float = SITUATION_STYLES.get(situation, {}).get("rate", 1.0)
    mood_mul: float = CALLER_MIRRORS.get(mood, {}).get("rate_mul", 1.0)

    final = baseline * sit_rate * mood_mul
    return max(RATE_CLAMP_MIN, min(RATE_CLAMP_MAX, final))
