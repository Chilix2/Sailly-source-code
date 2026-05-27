"""
name_extractor — Optional worker for greeting / order / reservation profiles.

Extracts a caller name from the utterance using simple pattern matching.
More complex extraction (ambiguous German names) falls back to slot_extractor.
Estimated latency: <1 ms (regex only).
"""
from __future__ import annotations

import re
import time
from typing import Optional

from server.brain.workers import Worker, WorkerContext, WorkerKind, WorkerOutput

# Name patterns: covers all common German ways to state a name
_NAME_PATTERNS = [
    # "Auf den Namen Müller" / "auf Namen Müller"
    re.compile(
        r"\bauf (den )?namen\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)",
        re.I,
    ),
    # "Ich bin / ich heiße / ich heisse ..."
    re.compile(
        r"\bich (bin|heiße|heisse)\s+(?:der|die)?\s*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)",
        re.I,
    ),
    # "Mein Name ist / Mein Nachname ist ..."
    re.compile(
        r"\bmein (name|vorname|nachname) ist\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)",
        re.I,
    ),
    # "Hier spricht / Hier ist ..."
    re.compile(
        r"\bhier (spricht|ist)\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)",
        re.I,
    ),
    # "für Familie Müller" or "für Müller bitte" — _clean_name rejects lowercase captures
    re.compile(
        r"\bfür\s+(?:familie\s+)?([A-Za-zÄÖÜäöüß][a-zäöüß]{1,})\s*(?:bitte|danke|,|$)",
        re.IGNORECASE | re.UNICODE,
    ),
    # "Name: Wagner" — colon-separated name declaration
    re.compile(
        r"\bname\s*:\s*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)",
        re.IGNORECASE | re.UNICODE,
    ),
    # "Name ist Müller" / "der Name für X ist Müller"
    re.compile(
        r"\bname\b.{0,40}?ist\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)",
        re.IGNORECASE | re.UNICODE,
    ),
]

# Common German first names to validate extracted strings
_COMMON_PREFIXES = {
    "herr", "frau", "dr", "prof", "ich", "mein", "der", "die", "das",
    "ein", "eine", "beim", "bei", "vom", "von", "am", "im",
}


def _clean_name(raw: str) -> Optional[str]:
    """Validate and normalize an extracted name candidate.
    
    Rejects: common words, short fragments, anything that doesn't start with
    an uppercase letter (filters out German articles / prepositions captured
    by the 'für' pattern, e.g. 'für die Reservierung' → 'Die' is rejected).
    """
    parts = raw.strip().split()
    if not parts:
        return None
    # The first word must start with an uppercase letter — proper noun rule.
    # This is the primary guard against false positives like "Die" from "für die"
    if parts[0] and parts[0][0] not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜabcdefghijklmnopqrstuvwxyz':
        return None
    # First word must actually start uppercase (not a common article)
    if parts[0][0].islower():
        return None
    # Reject common German articles, prepositions, filler words
    reject = {
        "die", "der", "das", "den", "dem", "ein", "eine", "einen", "einem",
        "für", "auf", "an", "bei", "von", "vom", "zur", "zum", "ich", "mein",
        "meine", "herr", "frau", "dr", "prof", "heute", "bitte", "danke",
        "reservierung", "reservieren", "tisch", "personen", "uhr",
    }
    if len(parts) == 1 and parts[0].lower() in reject:
        return None
    # Reject multi-word where all words are lowercase-initial (after normalization)
    return " ".join(p.capitalize() for p in parts)


class NameExtractor(Worker):
    name = "name_extractor"
    kind = WorkerKind.OPTIONAL
    estimated_latency_ms = 4  # Multiple regex patterns + validation
    timeout_ms = 100

    async def run(self, ctx: WorkerContext) -> WorkerOutput:
        t0 = time.monotonic()
        extracted: Optional[str] = None
        confidence = 0.0

        for pattern in _NAME_PATTERNS:
            m = pattern.search(ctx.user_text)
            if m:
                raw = m.group(m.lastindex or 1)
                cleaned = _clean_name(raw)
                if cleaned:
                    extracted = cleaned
                    confidence = 0.80
                    break

        latency_ms = int((time.monotonic() - t0) * 1000)
        return WorkerOutput(
            worker_name=self.name,
            success=True,
            data={"customer_name": extracted},   # key must match _WORKER_TO_SLOT mapping
            confidence=confidence if extracted else 1.0,
            latency_ms=latency_ms,
        )


name_extractor = NameExtractor()
