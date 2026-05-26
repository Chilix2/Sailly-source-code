"""
cancel_order — cancel an existing takeaway / delivery order.

Phase 3 stub (PR-7 / FINDING-012): fail-clean placeholder.

No legacy implementation exists in tools/executor.py. Cancellation
has order-timing constraints (e.g. cannot cancel after the kitchen
accepts) that need to be implemented with a proper state machine in a
future PR.

Also listed in AUDITED_TOOLS (server/brain/observability/audit.py) —
audit writes are already handled by the dispatcher's _execute_allowed
loop, so this handler doesn't need to call write_audit_entry directly.
"""
from __future__ import annotations

import logging

from server.tools.common.context import ToolContext
from server.tools.common.error_codes import ErrorCode
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "cancel_order"


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args (expected from LLM):
      order_id_or_phone: str — order reference or phone used to place order
      reason:            str — cancellation reason (optional, for audit)
    """
    identifier = args.get("order_id_or_phone")
    if not identifier:
        logger.warning(
            "[cancel_order] called without order_id_or_phone (call_sid=%s)",
            ctx.call_sid,
        )
        return ToolResult(
            ok=False,
            error="missing identifier (order_id_or_phone required)",
            error_code=ErrorCode.TOOL_VALIDATION_FAILED,
        )

    logger.warning(
        "[cancel_order] NOT IMPLEMENTED — returning warm-handoff result "
        "(call_sid=%s identifier=%r reason=%r)",
        ctx.call_sid,
        identifier,
        args.get("reason"),
    )
    return ToolResult(
        ok=False,
        error="cancel_order not yet implemented",
        error_code=ErrorCode.TOOL_NOT_IMPLEMENTED,
        data={
            "caller_facing_message": (
                "Diese Funktion wird gerade vorbereitet. "
                "Ich verbinde Sie mit einem Mitarbeiter."
            ),
            "requires_human": True,
        },
    )
