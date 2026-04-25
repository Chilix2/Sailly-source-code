"""
modify_reservation — change party size, date, or time on an existing reservation.

Phase 3 stub (PR-7 / FINDING-012): fail-clean placeholder.

No legacy implementation exists in tools/executor.py. Reservation
modifications require availability re-checking (same as create_reservation),
which involves the check_availability→create_reservation flow.

Future PRs should:
  1. Add the schema to tools/definitions.py.
  2. Implement: availability re-check → UPDATE reservations → optional SMS
     confirmation.
  3. Decide whether to add to GATED_TOOLS_BASE (the identifier slot
     reservation_id_or_phone should be verified before mutation).
"""
from __future__ import annotations

import logging

from server.tools.common.context import ToolContext
from server.tools.common.error_codes import ErrorCode
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "modify_reservation"


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args (expected from LLM):
      reservation_id_or_phone: str — reservation reference or booking phone
      party_size:              int (optional)
      date:                    str (optional, ISO date or natural language)
      time:                    str (optional, HH:MM or natural language)
    """
    identifier = args.get("reservation_id_or_phone")
    if not identifier:
        logger.warning(
            "[modify_reservation] called without reservation_id_or_phone "
            "(call_sid=%s)",
            ctx.call_sid,
        )
        return ToolResult(
            ok=False,
            error="missing identifier (reservation_id_or_phone required)",
            error_code=ErrorCode.TOOL_VALIDATION_FAILED,
        )

    logger.warning(
        "[modify_reservation] NOT IMPLEMENTED — returning warm-handoff result "
        "(call_sid=%s identifier=%r)",
        ctx.call_sid,
        identifier,
    )
    return ToolResult(
        ok=False,
        error="modify_reservation not yet implemented",
        error_code=ErrorCode.TOOL_NOT_IMPLEMENTED,
        data={
            "caller_facing_message": (
                "Diese Funktion wird gerade vorbereitet. "
                "Ich verbinde Sie mit einem Mitarbeiter."
            ),
            "requires_human": True,
        },
    )
