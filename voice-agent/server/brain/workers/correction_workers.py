"""
correction_workers.py — Phase 6.2: correction detection and slot delta computation.

Workers:
    correction_detector           — identifies what is being corrected
    previous_turn_reference_resolver — which slot from the previous turn is corrected
    state_delta_builder           — computes the minimal state change

None of these call commit tools.
"""
from __future__ import annotations

import re
import time
from typing import Optional

from server.brain.workers import Worker, WorkerContext, WorkerKind, WorkerOutput

_CORRECTION_RE = re.compile(
    r"\b(ich wollte (eigentlich|lieber|stattdessen)|"
    r"eigentlich (wollte|meinte|habe ich|ist es)|"
    r"ich meinte|korrektur:|nicht .{1,20}sondern|"
    r"entschuldigung,? ich meinte|doch lieber|nein,? (es sind|ich brauche)|"
    r"warte,? (ich meinte|das war falsch)|das stimmt nicht)\b",
    re.I,
)

_SLOT_KEYWORDS: dict[str, list[str]] = {
    "party_size":       ["personen", "leute", "gäste", "anzahl"],
    "reservation_date": ["datum", "tag", "heute", "morgen", "montag", "dienstag",
                         "mittwoch", "donnerstag", "freitag", "samstag", "sonntag"],
    "reservation_time": ["uhr", "halb", "uhrzeit", "um "],
    "customer_name":    ["name", "heiße", "bin ich", "ich bin"],
    "phone_number":     ["nummer", "telefon", "handy"],
}


def _detect_corrected_slot(text: str) -> Optional[str]:
    lower = text.lower()
    for slot, keywords in _SLOT_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return slot
    return None


class CorrectionDetector(Worker):
    name = "correction_detector"
    kind = WorkerKind.REQUIRED
    estimated_latency_ms = 1
    timeout_ms = 50

    async def run(self, ctx: WorkerContext) -> WorkerOutput:
        t0 = time.monotonic()
        is_correction = bool(_CORRECTION_RE.search(ctx.user_text))
        corrected_slot = _detect_corrected_slot(ctx.user_text) if is_correction else None
        return WorkerOutput(
            worker_name=self.name,
            success=True,
            data={
                "is_correction": is_correction,
                "corrected_slot": corrected_slot,
            },
            confidence=0.85 if is_correction else 1.0,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )


class PreviousTurnReferenceResolver(Worker):
    name = "previous_turn_reference_resolver"
    kind = WorkerKind.REQUIRED
    estimated_latency_ms = 1
    timeout_ms = 50

    async def run(self, ctx: WorkerContext) -> WorkerOutput:
        t0 = time.monotonic()
        corrected_slot = _detect_corrected_slot(ctx.user_text)
        return WorkerOutput(
            worker_name=self.name,
            success=True,
            data={"corrected_slot": corrected_slot},
            confidence=0.80,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )


class StateDeltaBuilder(Worker):
    name = "state_delta_builder"
    kind = WorkerKind.REQUIRED
    estimated_latency_ms = 1
    timeout_ms = 50

    async def run(self, ctx: WorkerContext) -> WorkerOutput:
        t0 = time.monotonic()
        # Identify what new value is being provided after the correction
        corrected_slot = _detect_corrected_slot(ctx.user_text)
        delta: dict = {}
        if corrected_slot:
            delta["corrected_slot"] = corrected_slot
            delta["correction_text"] = ctx.user_text
        return WorkerOutput(
            worker_name=self.name,
            success=True,
            data={"state_delta": delta},
            confidence=0.75,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )


correction_detector = CorrectionDetector()
previous_turn_reference_resolver = PreviousTurnReferenceResolver()
state_delta_builder = StateDeltaBuilder()
