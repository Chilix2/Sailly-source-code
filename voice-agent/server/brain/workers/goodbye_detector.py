"""
goodbye_detector — Required worker for greeting/smalltalk profiles.

Detects explicit goodbye intent using regex fast-path.
Estimated latency: <1 ms (pure regex, no I/O).
"""
from __future__ import annotations

import re
import time

from server.brain.workers import Worker, WorkerContext, WorkerKind, WorkerOutput

_GOODBYE_RE = re.compile(
    r"\b(tschüss?|auf wiedersehen|auf wiederhören|bye|ciao|tschau|"
    r"das war.?s|das wär.?s|schönen (tag|abend|morgen|nachmittag)|"
    r"noch einen schönen|gespräch beendet|gespräch ist vorbei)\b",
    re.I,
)


class GoodbyeDetector(Worker):
    name = "goodbye_detector"
    kind = WorkerKind.REQUIRED
    estimated_latency_ms = 1
    timeout_ms = 50

    async def run(self, ctx: WorkerContext) -> WorkerOutput:
        t0 = time.monotonic()
        is_goodbye = bool(_GOODBYE_RE.search(ctx.user_text))
        latency_ms = int((time.monotonic() - t0) * 1000)
        return WorkerOutput(
            worker_name=self.name,
            success=True,
            data={"is_goodbye": is_goodbye},
            confidence=0.95 if is_goodbye else 1.0,
            latency_ms=latency_ms,
        )


goodbye_detector = GoodbyeDetector()
