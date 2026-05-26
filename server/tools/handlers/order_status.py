"""
order_status — look up the current status of an existing order.

Phase 3 stub (PR-7 / FINDING-012): fail-clean placeholder.

Read-only tool — NOT in GATED_TOOLS_BASE (no slot validation gate
required for status enquiries). Also NOT in AUDITED_TOOLS (read-only
queries are not audit-worthy).

No legacy implementation exists in tools/executor.py. Future PRs
should:
  1. Add the schema to tools/definitions.py.
  2. Query the orders table and return structured status
     (e.g. {"status": "in_kitchen", "eta_minutes": 20}).
  3. Optionally add circuit-breaker wrapping for DB reads if latency
     matters (unlikely — same DB as create_order).
"""
from __future__ import annotations

import logging

from server.tools.common.context import ToolContext
from server.tools.common.error_codes import ErrorCode
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "order_status"


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args (expected from LLM):
      order_id_or_phone: str — order reference or phone number used to place order
    """
    identifier = args.get("order_id_or_phone")
    if not identifier:
        logger.warning(
            "[order_status] called without order_id_or_phone (call_sid=%s)",
            ctx.call_sid,
        )
        return ToolResult(
            ok=False,
            error="missing identifier (order_id_or_phone required)",
            error_code=ErrorCode.TOOL_VALIDATION_FAILED,
        )

    logger.warning(
        "[order_status] NOT IMPLEMENTED — returning warm-handoff result "
        "(call_sid=%s identifier=%r)",
        ctx.call_sid,
        identifier,
    )
    return ToolResult(
        ok=False,
        error="order_status not yet implemented",
        error_code=ErrorCode.TOOL_NOT_IMPLEMENTED,
        data={
            "caller_facing_message": (
                "Lassen Sie mich nachschauen — "
                "ich verbinde Sie kurz mit einem Mitarbeiter."
            ),
            "requires_human": True,
        },
    )
