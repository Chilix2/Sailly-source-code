"""
Bot-output profanity filter per decision bot-filter (8.S5).

Filters BOT OUTPUT only. Caller input is NOT filtered — callers may use
heated language in complaints, and filtering that would break extraction.

The word list is conservative: only words that would be clearly unacceptable
in a professional restaurant context and could never appear in a legitimate
bot response. This avoids false-positives on dish descriptions, complaints
about food quality, etc.
"""
from __future__ import annotations

# Conservative German profanity list — only clear-cut offensive terms.
# Kept minimal to avoid false-positives on legitimate restaurant vocabulary.
_PROFANITY_DE: frozenset[str] = frozenset({
    "scheiß",
    "scheiße",
    "scheißen",
    "ficken",
    "wichser",
    "arschloch",
    "hurensohn",
    "fotze",
    "wichsen",
    "dreckssau",
    "mistkerl",
    "vollidiot",
    "du idiot",
    "sie idiot",
})

_SUBSTITUTION_DE = "Einen Moment bitte, ich formuliere das anders."


def contains_profanity(text: str) -> bool:
    lower = text.lower()
    return any(word in lower for word in _PROFANITY_DE)


def filter_bot_profanity(text: str) -> tuple[str, list]:
    """
    Replace bot output that contains profanity with a neutral placeholder.

    Returns (cleaned_text, warnings_list).
    The warnings_list contains dicts suitable for PolicyWarning construction.
    """
    from server.brain.layer3.policy import PolicyWarning  # local import avoids cycle

    if not contains_profanity(text):
        return text, []

    return _SUBSTITUTION_DE, [
        PolicyWarning(
            code="BOT_PROFANITY",
            detail="bot output contained profanity — replaced with neutral text",
            original=text[:120],
        )
    ]
