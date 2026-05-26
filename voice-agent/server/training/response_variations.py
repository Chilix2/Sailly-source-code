"""Rotate German phrasing to reduce Jaccard repetition in training."""

from __future__ import annotations

import random
from collections import defaultdict
from typing import Callable

VARIATION_POOLS: dict[str, list[str]] = {
    "delivery_time": [
        "Die Lieferzeit beträgt ca. 30–60 Minuten.",
        "Sie können mit ungefähr 30 bis 60 Minuten rechnen.",
        "Unsere Lieferung dauert in der Regel eine halbe bis eine Stunde.",
        "Erfahrungsgemäß ist Ihre Bestellung in 30–60 Minuten bei Ihnen.",
        "Die Zustellung dauert etwa 30 bis 60 Minuten — je nach Auslastung.",
    ],
    "opening_hours": [
        "Wir haben Dienstag bis Sonntag geöffnet, von 12:00–14:30 und 17:30–22:00 Uhr.",
        "Unsere Öffnungszeiten sind Di–So, mittags 12–14:30 Uhr und abends 17:30–22 Uhr.",
        "Sie erreichen uns Dienstag bis Sonntag — mittags ab 12 und abends ab 17:30 Uhr.",
        "Montag ist Ruhetag. Sonst sind wir mittags und abends für Sie da.",
    ],
    "ask_for_order": [
        "Welches Gericht darf ich für Sie notieren?",
        "Was möchten Sie bestellen?",
        "Haben Sie sich schon für ein Gericht entschieden?",
        "Darf ich Ihre Bestellung aufnehmen?",
        "Was darf es sein?",
    ],
    "anything_else": [
        "Kann ich sonst noch etwas für Sie tun?",
        "Haben Sie noch eine Frage?",
        "Darf ich Ihnen mit etwas anderem helfen?",
        "Gibt es noch etwas, das ich für Sie klären kann?",
    ],
}

TOPIC_KEYWORDS: dict[str, list[str]] = {
    "delivery_time": ["lieferzeit", "lieferung", "minuten", "zustellung"],
    "opening_hours": ["öffnungszeiten", "oeffnungszeiten", "geöffnet", "geoeffnet", "ruhetag"],
    "ask_for_order": ["bestellen", "gericht", "bestellung", "notieren"],
    "anything_else": ["sonst noch", "noch etwas", "andere frage"],
}


def _jaccard_words(a: str, b: str) -> float:
    sa, sb = set(a.lower().split()), set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


class VariationRotator:
    def __init__(self) -> None:
        self._used: dict[str, list[int]] = defaultdict(list)

    def get(self, topic: str) -> str:
        pool = VARIATION_POOLS.get(topic)
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
    """Swap repeated pool phrases for alternates when the topic already appeared recently."""
    if not bot_response.strip():
        return bot_response
    out = bot_response
    lower = out.lower()

    for topic, pool in VARIATION_POOLS.items():
        if not topic_recently_used(topic, recent_responses):
            continue
        for phrase in pool:
            pl = phrase.lower()
            if pl in lower or near_match(out, phrase) > 0.55:
                fresh = rotator.get(topic)
                if fresh and fresh != phrase:
                    # Replace first occurrence (case-insensitive safe for German umlauts)
                    idx = out.lower().find(pl)
                    if idx >= 0:
                        out = out[:idx] + fresh + out[idx + len(phrase) :]
                    else:
                        out = out.replace(phrase, fresh, 1)
                    lower = out.lower()
                break
    return out
