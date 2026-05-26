"""
Verify vary-first-then-append ordering per var-timing: keep-order.

If we append first and then vary, the rotator sees the un-varied text in
recent_bot and can incorrectly trigger a swap on the NEXT turn (the just-
appended phrase immediately matches the pool and is flagged as "recently used",
causing unnecessary rotation at the start of the next response).

These tests are regression guards — they verify the invariant without changing
production code.  No mocks needed; vary() is pure.
"""
from __future__ import annotations

import pytest

from server.brain.response_variations import vary, VARIATION_POOLS


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _de_pool(topic: str) -> list[str]:
    return VARIATION_POOLS["de"][topic]


# ---------------------------------------------------------------------------
# Core ordering invariant
# ---------------------------------------------------------------------------

def test_vary_before_append_rotates_correctly():
    """
    Ordering: vary THEN append.

    When the recent_bot list contains a delivery_time phrasing from a prior
    turn, vary() swaps the raw LLM response for a fresh phrasing.  The fresh
    phrasing (not the raw one) is what gets appended to history.
    """
    pool = _de_pool("delivery_time")
    prior_phrasing = pool[1]  # "Wir sind in 30 bis 60 Minuten bei Ihnen."
    raw_response = pool[0]    # "Die Lieferzeit betraegt etwa 30-60 Minuten."

    recent_bot = [prior_phrasing]

    # Step 1: vary
    varied = vary(raw_response, lang="de", recent_bot=recent_bot)
    assert varied != raw_response, "rotator should have picked an alternate phrase"
    assert varied in pool, "rotated phrase must come from the pool"

    # Step 2: append the varied result (not the raw response)
    recent_bot.append(varied)

    assert varied in recent_bot
    assert raw_response not in recent_bot, (
        "only the varied text should be in history, not the un-varied LLM output"
    )


def test_wrong_order_append_then_vary_causes_stale_signal():
    """
    Ordering: append THEN vary (incorrect order).

    This test demonstrates WHY the correct order matters: if we append the
    raw response first, the rotator immediately sees it in recent_bot and
    treats it as 'recently used', which means the next turn will again want
    to rotate it — defeating deduplication.
    """
    pool = _de_pool("delivery_time")
    prior_phrasing = pool[1]
    raw_response = pool[0]

    recent_bot = [prior_phrasing]

    # Step 1 (wrong): append FIRST
    recent_bot.append(raw_response)

    # Step 2 (wrong): vary AFTER — the raw response is already in recent_bot
    # so vary() sees the just-appended phrase as 'recently used' and rotates
    # it away, even though we just said it.  This is the stale-signal bug.
    varied_after_append = vary(raw_response, lang="de", recent_bot=recent_bot)

    # The varied phrase is different — confirming the rotation fired
    # immediately after appending (spurious rotation).
    # We assert this here as documentation of the bug, not as desired behavior.
    assert varied_after_append != raw_response, (
        "rotator fired again right after appending — this is the stale-signal "
        "bug that vary-first-then-append prevents"
    )


# ---------------------------------------------------------------------------
# Language scaffolding
# ---------------------------------------------------------------------------

def test_empty_language_pool_passes_through():
    """
    Hypothetical 'en' tenant — empty pools mean vary() returns text unchanged.
    """
    raw = "Delivery takes 30-60 minutes."
    recent = ["We deliver in 30 to 60 minutes."]

    result = vary(raw, lang="en", recent_bot=recent)
    assert result == raw, "empty pool should not alter the text"


def test_unknown_language_passes_through():
    """Unknown language code → no pools found → text unchanged."""
    raw = "Bitte warten Sie einen Moment."
    result = vary(raw, lang="zz", recent_bot=["Bitte warten Sie."])
    assert result == raw


# ---------------------------------------------------------------------------
# German pool: no repetition → no swap
# ---------------------------------------------------------------------------

def test_no_swap_when_topic_not_recently_used():
    """
    If the topic hasn't appeared in recent_bot, vary() leaves the text as-is
    even when the text matches a pool phrase.
    """
    pool = _de_pool("delivery_time")
    text = pool[0]
    # recent_bot contains only opening_hours content — no delivery_time
    recent_bot = ["Wir haben Dienstag bis Sonntag von elf bis zweiundzwanzig Uhr geoeffnet."]

    result = vary(text, lang="de", recent_bot=recent_bot)
    assert result == text, "no swap when the topic is not recently used"


# ---------------------------------------------------------------------------
# Pool size guard
# ---------------------------------------------------------------------------

def test_all_de_pools_have_at_least_4_entries():
    """Per var-pool-size: pool-4-5 — every populated pool must have >= 4 phrases."""
    for topic, phrasings in VARIATION_POOLS["de"].items():
        assert len(phrasings) >= 4, (
            f"Pool 'de.{topic}' has only {len(phrasings)} phrases; "
            f"minimum is 4 per var-pool-size: pool-4-5"
        )


# ---------------------------------------------------------------------------
# Situation + mood coverage guard
# ---------------------------------------------------------------------------

def test_all_situation_keys_have_tag_and_rate():
    """All 15 SITUATION_STYLES entries must have 'tag', 'rate', 'prompt_add'."""
    from server.brain.tts.situation_styles import SITUATION_STYLES, ALL_SITUATIONS

    assert len(ALL_SITUATIONS) == 15, (
        f"Expected 15 situations, got {len(ALL_SITUATIONS)}: {ALL_SITUATIONS}"
    )
    for key, style in SITUATION_STYLES.items():
        assert "tag" in style, f"SITUATION_STYLES[{key!r}] missing 'tag'"
        assert "rate" in style, f"SITUATION_STYLES[{key!r}] missing 'rate'"
        assert "prompt_add" in style, f"SITUATION_STYLES[{key!r}] missing 'prompt_add'"
        assert 0.75 <= style["rate"] <= 2.0, (
            f"SITUATION_STYLES[{key!r}]['rate'] = {style['rate']} out of clamp range"
        )


def test_all_mood_keys_have_rate_mul_and_skip_chitchat():
    """All 6 CALLER_MIRRORS entries must have 'rate_mul' and 'skip_chitchat'."""
    from server.brain.tts.caller_mirrors import CALLER_MIRRORS, ALL_MOODS

    assert len(ALL_MOODS) == 6, (
        f"Expected 6 moods, got {len(ALL_MOODS)}: {ALL_MOODS}"
    )
    for key, mirror in CALLER_MIRRORS.items():
        assert "rate_mul" in mirror, f"CALLER_MIRRORS[{key!r}] missing 'rate_mul'"
        assert "skip_chitchat" in mirror, f"CALLER_MIRRORS[{key!r}] missing 'skip_chitchat'"

    # IMPATIENT is the only mood with skip_chitchat=True
    assert CALLER_MIRRORS["IMPATIENT"]["skip_chitchat"] is True
    for key, mirror in CALLER_MIRRORS.items():
        if key != "IMPATIENT":
            assert mirror["skip_chitchat"] is False, (
                f"Only IMPATIENT should have skip_chitchat=True; got True for {key!r}"
            )


# ---------------------------------------------------------------------------
# Rate computation
# ---------------------------------------------------------------------------

def test_compute_speaking_rate_baseline_times_situation_mood():
    """Phase 7 rate math: baseline x sit_rate x mood_mul, clamped 0.75-2.0."""
    from server.brain.tts.tts_conditioning import (
        compute_speaking_rate,
        RATE_CLAMP_MIN,
        RATE_CLAMP_MAX,
    )

    tenant_cfg = {"tts": {"speed_multiplier": 1.5}}

    # GREETING_FIRST (1.05) + NEUTRAL (1.0) = 1.5 * 1.05 * 1.0 = 1.575
    r = compute_speaking_rate("GREETING_FIRST", "NEUTRAL", tenant_cfg)
    assert abs(r - 1.575) < 0.001, f"Expected ~1.575, got {r}"

    # INFO_READBACK (0.88) + CONFUSED (0.88) = 1.5 * 0.88 * 0.88 = 1.1616
    r = compute_speaking_rate("INFO_READBACK", "CONFUSED", tenant_cfg)
    assert abs(r - 1.1616) < 0.001, f"Expected ~1.1616, got {r}"

    # URGENT_CLEAR (1.05) + IMPATIENT (1.05) = 1.5 * 1.05 * 1.05 = 1.65375 < 2.0
    r = compute_speaking_rate("URGENT_CLEAR", "IMPATIENT", tenant_cfg)
    assert abs(r - 1.65375) < 0.001 and r <= RATE_CLAMP_MAX, (
        f"Expected ~1.654, got {r}"
    )

    # Edge: stacked multipliers should clamp at 2.0
    high_cfg = {"tts": {"speed_multiplier": 2.0}}
    r_clamped = compute_speaking_rate("URGENT_CLEAR", "IMPATIENT", high_cfg)
    assert r_clamped == RATE_CLAMP_MAX, f"Expected clamped to {RATE_CLAMP_MAX}, got {r_clamped}"

    # Edge: very low multiplier should clamp at 0.75
    low_cfg = {"tts": {"speed_multiplier": 0.5}}
    r_low = compute_speaking_rate("FAREWELL_WARM", "ELDERLY", low_cfg)
    assert r_low == RATE_CLAMP_MIN, f"Expected clamped to {RATE_CLAMP_MIN}, got {r_low}"


# ---------------------------------------------------------------------------
# Pronunciation hints
# ---------------------------------------------------------------------------

def test_pronunciation_hints_injected_for_gemini_voice():
    """SSML phoneme tags are added for Gemini voices."""
    from server.brain.tts.pronunciation import apply_pronunciation_hints

    tenant_cfg = {
        "tts": {
            "pronunciations": {"Bibimbap": "bibimbap", "Bulgogi": "bulɡoɡi"}
        }
    }
    text = "ein Bibimbap und ein Bulgogi bitte"
    result = apply_pronunciation_hints(text, tenant_cfg, voice="Kore")
    assert '<phoneme alphabet="ipa" ph="bibimbap">Bibimbap</phoneme>' in result
    assert '<phoneme alphabet="ipa" ph="bulɡoɡi">Bulgogi</phoneme>' in result


def test_pronunciation_hints_stripped_for_non_gemini_voice():
    """No SSML injection for voices outside GEMINI_VOICES."""
    from server.brain.tts.pronunciation import apply_pronunciation_hints

    tenant_cfg = {"tts": {"pronunciations": {"Bibimbap": "bibimbap"}}}
    text = "ein Bibimbap bitte"
    result = apply_pronunciation_hints(text, tenant_cfg, voice="neural2-de-DE-A")
    assert result == text, "non-Gemini voice should return text unchanged"


# ---------------------------------------------------------------------------
# Emotion tag injection
# ---------------------------------------------------------------------------

def test_emotion_tag_injected_for_gemini_voice():
    from server.brain.tts.tts_client import prepare_text_for_tts

    result = prepare_text_for_tts("Hallo!", "GREETING_FIRST", voice="Kore")
    assert result.startswith("[warm]"), f"Expected [warm] tag, got: {result!r}"


def test_emotion_tag_stripped_for_non_gemini_voice():
    from server.brain.tts.tts_client import prepare_text_for_tts

    result = prepare_text_for_tts("[warm] Hallo!", "GREETING_FIRST", voice="neural2-de-DE-A")
    assert not result.startswith("["), f"Expected tags stripped, got: {result!r}"


# ---------------------------------------------------------------------------
# skip_chitchat stripping
# ---------------------------------------------------------------------------

def test_strip_chitchat_removes_opener():
    from server.brain.tts.caller_mirrors import strip_chitchat

    assert strip_chitchat("Sehr gerne! Ich nehme Ihre Bestellung auf.") == \
        "Ich nehme Ihre Bestellung auf."
    assert strip_chitchat("Natürlich! Das ist kein Problem.") == \
        "Das ist kein Problem."
    assert strip_chitchat("Klar, ich verbinde Sie.") == "Ich verbinde Sie."


def test_strip_chitchat_leaves_non_filler_unchanged():
    from server.brain.tts.caller_mirrors import strip_chitchat

    text = "Ich verbinde Sie jetzt."
    assert strip_chitchat(text) == text
