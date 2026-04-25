"""
Response variation rotator — per-language pools per var-language-scope.

Per var-rotator-vs-llm: keep-rotator — deterministic post-LLM phrase swap.
Per var-pool-size: pool-4-5 — 4-5 variations per topic.
Per var-jaccard: threshold-055 — swap when Jaccard similarity >= 0.55.
Per var-topic-coverage: keep-4 — delivery_time, opening_hours, ask_for_order, anything_else.
Per var-timing: keep-order — vary BEFORE appending to history (enforced by callers).
Per var-language-scope: per-language-pools — structure: {lang: {topic: [phrasings...]}}.
  "de" is fully populated. Other languages have empty scaffolding for Phase 10 multi-tenant.

vary() is the new Phase 7 API; apply_response_variations() (old flat-pool API) is kept for
backward compatibility with callers that don't yet pass a lang parameter.
"""
from __future__ import annotations

import random
from collections import defaultdict
from typing import Callable

# -- Per-language variation pools ---------------------------------------------

VARIATION_POOLS: dict[str, dict[str, list[str]]] = {
    "de": {
        "delivery_time": [
            "Die Lieferzeit betraegt etwa 30-60 Minuten.",
            "Wir sind in 30 bis 60 Minuten bei Ihnen.",
            "Rechnen Sie mit 30 bis 60 Minuten Lieferzeit.",
            "Etwa eine halbe bis eine Stunde, je nach Auslastung.",
            "30-60 Minuten — ich melde mich, falls es laenger dauert.",
        ],
        "opening_hours": [
            "Wir haben Dienstag bis Sonntag von elf bis zweiundzwanzig Uhr geoeffnet.",
            "Geoeffnet ist von Dienstag bis Sonntag, jeweils elf bis zweiundzwanzig Uhr.",
            "Dienstag bis Sonntag, elf bis zweiundzwanzig Uhr — Montag ist Ruhetag.",
            "Ausser montags haben wir taeglich von elf bis zweiundzwanzig Uhr geoeffnet.",
        ],
        "ask_for_order": [
            "Was darf ich Ihnen heute aufnehmen?",
            "Was moechten Sie bestellen?",
            "Sagen Sie mir, was Sie heute geniessen moechten.",
            "Was kann ich fuer Sie aufschreiben?",
        ],
        "anything_else": [
            "Sonst noch etwas?",
            "Darf es noch etwas sein?",
            "Moechten Sie noch etwas hinzufuegen?",
            "Kann ich noch etwas fuer Sie tun?",
        ],
    },
    # Empty scaffolding — Phase 10 (multi-tenant) populates as needed
    "en": {
        "delivery_time": [],
        "opening_hours": [],
        "ask_for_order": [],
        "anything_else": [],
    },
    "fr": {
        "delivery_time": [],
        "opening_hours": [],
        "ask_for_order": [],
        "anything_else": [],
    },
}

# Backward-compat flat pool (German only) — used by legacy VariationRotator and
# apply_response_variations() callers that predate the per-language structure.
_LEGACY_POOLS: dict[str, list[str]] = VARIATION_POOLS["de"]

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "delivery_time": ["lieferzeit", "lieferung", "minuten", "zustellung"],
    "opening_hours": ["oeffnungszeiten", "geoeffnet", "ruhetag", "zeiten"],
    "ask_for_order": ["bestellen", "gericht", "bestellung", "notieren"],
    "anything_else": ["sonst noch", "noch etwas", "andere frage"],
}


# -- Jaccard helpers ----------------------------------------------------------

def _jaccard_words(a: str, b: str) -> float:
    sa, sb = set(a.lower().split()), set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# -- Phase 7 API: vary() with per-language pools ------------------------------

def vary(text: str, lang: str, recent_bot: list[str]) -> str:
    """
    Per var-jaccard: threshold-055 + var-pool-size: pool-4-5.

    If text matches (by Jaccard >= 0.55 or substring) a phrase in any pool,
    and that topic appears in recent_bot, swap it for a less-recently-used phrase.

    If the pool for the requested language is empty (scaffolding), the text
    passes through unchanged — ready for Phase 10 multi-tenant population.

    Per var-timing: keep-order — callers MUST call vary() before appending
    the bot response to history.
    """
    lang_pools = VARIATION_POOLS.get(lang, {})

    for topic, phrasings in lang_pools.items():
        if not phrasings:
            continue  # empty scaffolding for non-de languages

        # Check if text matches this pool
        lower = text.lower()
        matched = any(
            p.lower() in lower or _jaccard_words(text, p) >= 0.55
            for p in phrasings
        )
        if not matched:
            continue

        # Was this topic recently used?
        recently_used = {
            p for p in phrasings
            if any(_jaccard_words(p, r) >= 0.55 for r in recent_bot)
        }
        if not recently_used:
            continue  # not a repetition — leave text as is

        text_lower = text.lower().strip()
        unused = [
            p for p in phrasings
            if p not in recently_used
            and p.lower().strip() != text_lower
            and _jaccard_words(p, text) < 0.90  # exclude near-identical phrases
        ]
        if unused:
            return unused[0]

    return text


# -- Legacy API (backward compat) --------------------------------------------

class VariationRotator:
    def __init__(self) -> None:
        self._used: dict[str, list[int]] = defaultdict(list)

    def get(self, topic: str) -> str:
        pool = _LEGACY_POOLS.get(topic)
        if not pool:
            return ""
        used = self._used[topic]
        available = [i for i in range(len(pool)) if i not in used]
        if not available:
            self._used[topic] = []
            available = list(range(len(pool)))
        idx = random.choice(available)
        used.append(idx)
        return pool[idx]


def topic_recently_used(topic: str, recent_responses: list[str]) -> bool:
    kws = TOPIC_KEYWORDS.get(topic, [])
    if not kws:
        return False
    for resp in recent_responses[-4:]:
        low = resp.lower()
        if any(kw in low for kw in kws):
            return True
    return False


def apply_response_variations(
    bot_response: str,
    recent_responses: list[str],
    rotator: VariationRotator,
    near_match: Callable[[str, str], float] = _jaccard_words,
) -> str:
    """Swap repeated pool phrases for alternates when the topic appeared recently.

    Legacy flat-pool API — prefer vary() for new callers.
    """
    if not bot_response.strip():
        return bot_response
    out = bot_response
    lower = out.lower()

    for topic, pool in _LEGACY_POOLS.items():
        if not topic_recently_used(topic, recent_responses):
            continue
        for phrase in pool:
            pl = phrase.lower()
            if pl in lower or near_match(out, phrase) > 0.55:
                fresh = rotator.get(topic)
                if fresh and fresh != phrase:
                    idx = out.lower().find(pl)
                    if idx >= 0:
                        out = out[:idx] + fresh + out[idx + len(phrase):]
                    else:
                        out = out.replace(phrase, fresh, 1)
                    lower = out.lower()
                break
    return out
