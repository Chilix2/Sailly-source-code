"""
faq — answer common questions about the restaurant.

Phase 6 decision:
  - tool-faq: static-with-llm-fallback
    1. Look up the question in the tenant's FAQ YAML (keyword scoring).
    2. If confidence >= 0.7 → return static answer (fast, deterministic).
    3. If no match → return {llm_fallback: True} so the main LLM answers
       using its grounded context (Phase 4 compact menu/facts).

configs/tenants/doboo.yaml must have a `faqs:` list:
  faqs:
    - keywords: ["öffnungszeiten", "geöffnet", "offen"]
      answer: "Wir haben dienstags bis sonntags von 12–15 Uhr und 17–22 Uhr geöffnet."
    - keywords: ["reservierung", "tisch buchen"]
      answer: "Reservierungen sind online, telefonisch oder per E-Mail möglich."
    - ...
"""
from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Optional

from server.tools.common.context import ToolContext
from server.tools.common.error_codes import ErrorCode
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "faq"

STATIC_MATCH_THRESHOLD = 0.7


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args:
      question: str — the caller's question (free text)
    """
    question = str(args.get("question") or "").strip().lower()
    if not question:
        return ToolResult(ok=False, error="Keine Frage angegeben", error_code=ErrorCode.MISSING_REQUIRED_SLOT)

    faqs = ctx.get_tenant_value("faqs", default=[]) or []

    # ── Static keyword match ──────────────────────────────────────────────────
    best_entry: Optional[dict] = None
    best_score = 0.0

    for entry in faqs:
        if not isinstance(entry, dict):
            continue
        keywords = entry.get("keywords") or []
        score = _match_score(question, keywords)
        if score > best_score:
            best_score = score
            best_entry = entry

    if best_entry and best_score >= STATIC_MATCH_THRESHOLD:
        logger.debug(
            "[faq] static match (score=%.2f) for question=%r", best_score, question[:80]
        )
        return ToolResult(
            ok=True,
            data={
                "answer": best_entry["answer"],
                "source": "static",
                "confidence": round(best_score, 3),
            },
        )

    # ── LLM fallback ──────────────────────────────────────────────────────────
    logger.debug(
        "[faq] no static match (best=%.2f) — LLM fallback for question=%r",
        best_score, question[:80],
    )
    return ToolResult(
        ok=True,
        data={
            "answer": None,
            "source": "llm_fallback",
            "llm_fallback": True,
        },
    )


def _match_score(question: str, keywords: list) -> float:
    """
    Score question against a keyword list.

    Returns max of:
      - Direct substring match: 0.9
      - SequenceMatcher ratio against each keyword
    """
    if not keywords:
        return 0.0
    best = 0.0
    for kw in keywords:
        kw_lower = str(kw).lower()
        if kw_lower in question:
            best = max(best, 0.9)
        else:
            ratio = SequenceMatcher(None, question, kw_lower).ratio()
            best = max(best, ratio)
    return best
