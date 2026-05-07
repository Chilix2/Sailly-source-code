"""
confirmation_parser — Required worker for multi-step flows (reservation, order finalize).

Classifies user utterance as confirm / deny / unclear using regex.
~80% of cases handled by regex; ambiguous cases return UNCLEAR.
Estimated latency: <1 ms.
"""
from __future__ import annotations

import re
import time
from typing import Literal

from server.brain.workers import Worker, WorkerContext, WorkerKind, WorkerOutput

_CONFIRM_RE = re.compile(
    r"^[\s,]*(ja\b|genau\b|richtig\b|stimmt\b|korrekt\b|"
    r"okay\b|ok\b|alles klar\b|super\b|prima\b|"
    r"das stimmt\b|ja,?\s*bitte\b|passt\b|gut\b|"
    r"bitte\b|machen\b|so ist es\b)",
    re.I,
)
_DENY_RE = re.compile(
    r"^[\s,]*(nein\b|ne\b|nö\b|nicht\b|falsch\b|"
    r"das stimmt nicht\b|das ist falsch\b|"
    r"nein,?\s*danke\b|lieber nicht\b|stopp\b|"
    r"warte mal\b|moment\b)",
    re.I,
)


ConfirmResult = Literal["confirm", "deny", "unclear"]


class ConfirmationParser(Worker):
    name = "confirmation_parser"
    kind = WorkerKind.REQUIRED
    estimated_latency_ms = 1
    timeout_ms = 50

    async def run(self, ctx: WorkerContext) -> WorkerOutput:
        t0 = time.monotonic()
        text = ctx.user_text.strip()
        result: ConfirmResult = "unclear"
        confidence = 0.5

        if _CONFIRM_RE.match(text):
            result = "confirm"
            confidence = 0.92
        elif _DENY_RE.match(text):
            result = "deny"
            confidence = 0.90

        # Longer text usually contains more nuance — lower confidence
        if len(text) > 60:
            confidence *= 0.85

        latency_ms = int((time.monotonic() - t0) * 1000)
        return WorkerOutput(
            worker_name=self.name,
            success=True,
            data={"result": result, "raw_text": text},
            confidence=confidence,
            latency_ms=latency_ms,
        )


confirmation_parser = ConfirmationParser()
