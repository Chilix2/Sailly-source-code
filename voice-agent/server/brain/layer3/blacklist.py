"""
Hallucination blacklist per decision expand-while-grounding (8.H10 + 8.H1).

GLOBAL_BLACKLIST covers things no restaurant tenant would ever offer via the bot.
Per-tenant extensions live in tenant YAML under hallucination_blacklist[].

get_blacklist_for_tenant() merges both sets. The result is cached; TTL is
short (60 s) so YAML changes propagate without restart.

Usage (from policy.py):
    text, removed = strip_blacklisted(text, tenant_id)
"""
from __future__ import annotations

import re
import time

_CACHE: dict[str, tuple[float, set[str]]] = {}
_CACHE_TTL_S = 60.0

# Items DOBOO and no similar restaurant could plausibly offer via an AI phone bot.
# Extend with new hallucinations discovered in production (expand-while-grounding).
GLOBAL_BLACKLIST: frozenset[str] = frozenset({
    "kundenkonto",
    "kundenkonten",
    "bonuspunkte",
    "treueprogramm",
    "treuepunkte",
    "treuekarte",
    "loyaltyprogramm",
    "loyaltypoints",
    "rabattcode",
    "gutscheincode",
    "mitgliedschaft",
    "online-konto",
    "online konto",
    "kassensystem",
    "guthabenkonto",
    "guthaben",
    "punkte sammeln",
    "kreditkarte akzeptieren",
})


def get_blacklist_for_tenant(tenant_id: str) -> set[str]:
    """
    Return merged blacklist (global + per-tenant) with 60 s cache.
    Falls back to GLOBAL_BLACKLIST if tenant config cannot be loaded.
    """
    now = time.monotonic()
    cached = _CACHE.get(tenant_id)
    if cached and (now - cached[0]) < _CACHE_TTL_S:
        return cached[1]

    try:
        from server.core.tenant_config import get_tenant_config
        cfg = get_tenant_config(tenant_id)
        tenant_extra: list[str] = cfg.get("hallucination_blacklist", [])
        merged: set[str] = set(GLOBAL_BLACKLIST) | {t.lower() for t in tenant_extra}
    except Exception:
        merged = set(GLOBAL_BLACKLIST)

    _CACHE[tenant_id] = (now, merged)
    return merged


def _split_sentences(text: str) -> list[str]:
    """German-aware sentence splitter shared across blacklist and price checks."""
    return re.split(r"(?<=[.!?])\s+", text.strip())


def strip_blacklisted(
    text: str,
    tenant_id: str,
) -> tuple[str, list[str]]:
    """
    Remove any sentence that contains a blacklisted term.

    Returns:
        (cleaned_text, list_of_removed_terms)
    """
    blacklist = get_blacklist_for_tenant(tenant_id)
    sentences = _split_sentences(text)
    kept: list[str] = []
    removed_terms: list[str] = []

    for sentence in sentences:
        lower = sentence.lower()
        hit = next((t for t in blacklist if t in lower), None)
        if hit:
            removed_terms.append(hit)
        else:
            kept.append(sentence)

    cleaned = " ".join(kept).strip() or "Wie kann ich Ihnen weiterhelfen?"
    return cleaned, removed_terms
