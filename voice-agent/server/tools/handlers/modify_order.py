"""
modify_order — change items, channel, or pickup time on an existing order.

Phase 3 stub (PR-7 / FINDING-012): fail-clean placeholder.

No legacy implementation exists in tools/executor.py and the tool is not
in tools/definitions.py. This handler exists so the dispatcher finds a
Phase-3-shaped handler rather than falling through to the broken legacy
path when the LLM emits this tool call.

Future PRs should:
  1. Add the schema to tools/definitions.py.
  2. Implement the DB write (UPDATE orders SET ... WHERE ...) with
     idempotency key and circuit-breaker wrapping.
  3. Add modify_order to GATED_TOOLS_BASE in tools/dispatcher.py
     (order_id_or_phone must be verified before mutation).
"""
from __future__ import annotations

import logging

from server.tools.common.context import ToolContext
from server.tools.common.error_codes import ErrorCode
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "modify_order"


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args (expected from LLM):
      order_id_or_phone: str — order reference or phone used to place order
      items:             list[{dish, quantity}] — new item list (optional)
      channel:           "takeaway" | "delivery" (optional)
      pickup_time:       str (optional)
    """
    identifier = args.get("order_id_or_phone")
    if not identifier:
        logger.warning(
            "[modify_order] called without order_id_or_phone (call_sid=%s)",
            ctx.call_sid,
        )
        return ToolResult(
            ok=False,
            error="missing identifier (order_id_or_phone required)",
            error_code=ErrorCode.TOOL_VALIDATION_FAILED,
        )

    logger.warning(
        "[modify_order] NOT IMPLEMENTED — returning warm-handoff result "
        "(call_sid=%s identifier=%r)",
        ctx.call_sid,
        identifier,
    )
    return ToolResult(
        ok=False,
        error="modify_order not yet implemented",
        error_code=ErrorCode.TOOL_NOT_IMPLEMENTED,
        data={
            "caller_facing_message": (
                "Diese Funktion wird gerade vorbereitet. "
                "Ich verbinde Sie mit einem Mitarbeiter."
            ),
            "requires_human": True,
        },
    )
