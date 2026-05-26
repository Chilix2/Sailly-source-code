"""
Finalized 6 caller mood mirrors per Phase 7 Task 7.7.

Each entry is a plain dict with:
  rate_mul      — multiplied with situation rate (before baseline).
  prompt_add    — German prompt fragment appended to style_instruction (empty for NEUTRAL).
  skip_chitchat — if True, Layer 2 prompt assembly drops optional chit-chat phrases.
                  Per skip-small-talk decision for IMPATIENT mood.

The skip_chitchat flag is consumed by server/brain/layer2/system_prompt.py:
  build_system_prompt(..., voice_mood=pkg.voice_mood) calls
  _apply_skip_chitchat() to remove filler openers like "Sehr gerne!" / "Natürlich!".

Per tts-moods: moods-on — all 6 moods are available per tenant configuration.
"""
from __future__ import annotations

CALLER_MIRRORS: dict[str, dict] = {
    "NEUTRAL": {
        "rate_mul": 1.0,
        "prompt_add": "",
        "skip_chitchat": False,
    },
    "FRUSTRATED": {
        "rate_mul": 0.92,
        "prompt_add": "Senke die Stimme leicht, sprich verständnisvoll und ruhig.",
        "skip_chitchat": False,
    },
    "IMPATIENT": {
        "rate_mul": 1.05,
        "prompt_add": "Knackig und zielgerichtet — keine Smalltalk-Phrasen.",
        "skip_chitchat": True,  # per skip-small-talk decision
    },
    "CONFUSED": {
        "rate_mul": 0.88,
        "prompt_add": "Sprich langsamer, deutlicher, mit kurzen Pausen.",
        "skip_chitchat": False,
    },
    "RELAXED": {
        "rate_mul": 1.0,
        "prompt_add": "Leichter Gesprächston, locker.",
        "skip_chitchat": False,
    },
    "ELDERLY": {
        "rate_mul": 0.85,
        "prompt_add": "Deutliche Aussprache, ruhiges Tempo, keine Eile.",
        "skip_chitchat": False,
    },
}

# Convenience sets for validation
ALL_MOODS: frozenset[str] = frozenset(CALLER_MIRRORS)

# Filler phrases that IMPATIENT skip_chitchat removes from bot responses.
# Layer 2 prompt assembly calls strip_chitchat() when skip_chitchat is True.
_CHITCHAT_OPENERS: tuple[str, ...] = (
    "Sehr gerne!", "Sehr gerne,", "Sehr gerne —",
    "Natürlich!", "Natürlich,", "Natürlich —",
    "Selbstverständlich!", "Selbstverständlich,",
    "Mit Vergnügen!", "Aber gerne!",
    "Klar doch!", "Klar,",
    "Oh,", "Oh ja,",
)


def strip_chitchat(text: str) -> str:
    """
    Remove common chit-chat opener phrases from the beginning of a bot response.

    Called by Layer 2 system_prompt assembly when voice_mood == "IMPATIENT"
    and the caller_mirror's skip_chitchat flag is True.

    Only strips from the start of the string; mid-sentence filler is preserved
    because removing it would produce grammatically broken German.
    """
    stripped = text.lstrip()
    for phrase in _CHITCHAT_OPENERS:
        if stripped.startswith(phrase):
            stripped = stripped[len(phrase):].lstrip(" ,—–")
            # Capitalize the remaining text if we stripped the opener
            if stripped and stripped[0].islower():
                stripped = stripped[0].upper() + stripped[1:]
            return stripped
    return text
