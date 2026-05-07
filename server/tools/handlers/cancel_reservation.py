"""
cancel_reservation — cancel an existing table reservation.

Phase 3 stub (PR-7 / FINDING-012): fail-clean placeholder.

No legacy implementation exists in tools/executor.py. Cancellation
policies (lead time, deposit forfeiture) are tenant-specific and
should be driven by tenant_cfg in a future implementation.

Future PRs should:
  1. Add the schema to tools/definitions.py.
  2. Implement: UPDATE reservations SET status='cancelled' WHERE ...
     + optional SMS / email confirmation.
  3. Enforce cancellation window from tenant_cfg
     (e.g. "free cancellation up to 24h before booking").
"""
from __future__ import annotations

import logging

from server.tools.common.context import ToolContext
from server.tools.common.error_codes import ErrorCode
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "cancel_reservation"


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args (expected from LLM):
      reservation_id_or_phone: str — reservation reference or booking phone
      reason:                  str — cancellation reason (optional, for records)
    """
    identifier = args.get("reservation_id_or_phone")
    if not identifier:
        logger.warning(
            "[cancel_reservation] called without reservation_id_or_phone "
            "(call_sid=%s)",
            ctx.call_sid,
        )
        return ToolResult(
            ok=False,
            error="missing identifier (reservation_id_or_phone required)",
            error_code=ErrorCode.TOOL_VALIDATION_FAILED,
        )

    logger.warning(
        "[cancel_reservation] NOT IMPLEMENTED — returning warm-handoff result "
        "(call_sid=%s identifier=%r reason=%r)",
        ctx.call_sid,
        identifier,
        args.get("reason"),
    )
    return ToolResult(
        ok=False,
        error="cancel_reservation not yet implemented",
        error_code=ErrorCode.TOOL_NOT_IMPLEMENTED,
        data={
            "caller_facing_message": (
                "Diese Funktion wird gerade vorbereitet. "
                "Ich verbinde Sie mit einem Mitarbeiter."
            ),
            "requires_human": True,
        },
    )
