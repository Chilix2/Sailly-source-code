"""
SSML pronunciation hints per tts-pronunciation: ssml-phonetic.

Dish names get IPA hints to prevent common TTS mangling:
  language-specific names are wrapped with phoneme SSML.

Hints are tenant-specific and live in tenant YAML under tts.pronunciations.
This runs only when the voice is a Gemini voice — Gemini supports <phoneme>
SSML; Neural2 / Chirp3 voices typically do not (see tts_client.GEMINI_VOICES).

Usage:
    text = apply_pronunciation_hints(raw_text, tenant_cfg, voice)
    # then pass text to the TTS backend
"""
from __future__ import annotations

import re

from server.brain.tts.tts_client import GEMINI_VOICES


def apply_pronunciation_hints(text: str, tenant_cfg: dict, voice: str) -> str:
    """
    Wrap menu item names with <phoneme> SSML tags using IPA from tenant YAML.

    Only applied when voice is a known Gemini voice.
    The phoneme map is read from tenant_cfg["tts"]["pronunciations"].
    Word-boundary matching is case-insensitive so "Bibimbaps" also matches.

    Example:
        "ein Gericht bitte"
        → 'ein <phoneme alphabet="ipa" ph="gəri:xt">Gericht</phoneme> bitte'
    """
    if voice not in GEMINI_VOICES:
        return text

    pron_map: dict[str, str] = tenant_cfg.get("tts", {}).get("pronunciations", {})
    if not pron_map:
        return text

    for word, ipa in pron_map.items():
        pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
        replacement = f'<phoneme alphabet="ipa" ph="{ipa}">{word}</phoneme>'
        text = pattern.sub(replacement, text)

    return text
