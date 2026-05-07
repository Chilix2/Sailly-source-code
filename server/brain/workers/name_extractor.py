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
    # "für Müller bitte" / "für Familie Müller"
    re.compile(
        r"\bfür\s+(?:familie\s+)?([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)\s*(bitte|danke|,|$)",
        re.I,
    ),
    # "Name: Müller" / "Name ist Müller"
    re.compile(
        r"\bname[:\s]+(?:ist\s+)?([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)",
        re.I,
    ),
]

# Common German first names to validate extracted strings
_COMMON_PREFIXES = {
    "herr", "frau", "dr", "prof", "ich", "mein", "der", "die", "das",
    "ein", "eine", "beim", "bei", "vom", "von", "am", "im",
}


def _clean_name(raw: str) -> Optional[str]:
    """Basic sanity check on extracted name."""
    parts = raw.strip().split()
    if not parts:
        return None
    # Reject single-word extractions that are common words
    if len(parts) == 1 and parts[0].lower() in _COMMON_PREFIXES:
        return None
    return " ".join(p.capitalize() for p in parts)


class NameExtractor(Worker):
    name = "name_extractor"
    kind = WorkerKind.OPTIONAL
    estimated_latency_ms = 1
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
