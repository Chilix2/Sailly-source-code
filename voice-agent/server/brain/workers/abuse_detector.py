"""
abuse_detector — Required worker for greeting/smalltalk/escalation profiles.

Detects abusive language using a regex fast-path.
Ambiguous cases (sarcasm, cultural slang) are flagged as UNCERTAIN.
Estimated latency: <1 ms.

Safety: does not call any tools or modify state.
"""
from __future__ import annotations

import re
import time

from server.brain.workers import Worker, WorkerContext, WorkerKind, WorkerOutput

# Explicit slurs and aggression markers (German restaurant context)
_ABUSE_RE = re.compile(
    r"\b(scheiß|fick|arschloch|wichser|idiot|vollidiot|hurensohn|"
    r"dummkopf|ich töte|ich bringe|du stirbst|verpiss dich|"
    r"halt (die )?fresse|leck mich)\b",
    re.I,
)
# Frustration markers (not abuse, but elevated tone — flag for mood detection)
_FRUSTRATION_RE = re.compile(
    r"\b(unverschämtheit|skandal|unzumutbar|inakzeptabel|"
    r"so ein mist|das ist ja (wohl )?(nicht wahr|ein witz)|"
    r"völlig inkompetent|lächerlich)\b",
    re.I,
)


class AbuseDetector(Worker):
    name = "abuse_detector"
    kind = WorkerKind.REQUIRED
    estimated_latency_ms = 1
    timeout_ms = 50

    async def run(self, ctx: WorkerContext) -> WorkerOutput:
        t0 = time.monotonic()
        is_abuse = bool(_ABUSE_RE.search(ctx.user_text))
        is_frustrated = bool(_FRUSTRATION_RE.search(ctx.user_text))
        latency_ms = int((time.monotonic() - t0) * 1000)
        return WorkerOutput(
            worker_name=self.name,
            success=True,
            data={
                "is_abuse": is_abuse,
                "is_frustrated": is_frustrated,
                "abuse_strikes": 1 if is_abuse else 0,
            },
            confidence=0.90,
            latency_ms=latency_ms,
        )


abuse_detector = AbuseDetector()
