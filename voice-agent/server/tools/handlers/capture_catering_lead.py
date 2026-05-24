"""
capture_catering_lead — record a group catering enquiry for human follow-up.

Per Phase 4 C4 decision (catering-warm-handoff): catering enquiries (>20
guests or special occasion) do NOT commit a reservation. Instead a lead row
is written to the catering_leads table so a sales rep can call back.

This handler is the only one of the six new handlers that implements DB I/O
directly rather than returning a fail-clean stub, because the DB write IS
the user-visible feature — without it, no lead is captured and the enquiry
is silently lost.

Schema: migrations/0004_catering_leads_table.sql
"""
from __future__ import annotations

import logging

from server.tools.common.context import ToolContext
from server.tools.common.error_codes import ErrorCode
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "capture_catering_lead"

_REQUIRED_FIELDS = ("phone", "name", "occasion_date", "guests")


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args (expected from LLM):
      phone:                 str  — caller contact number (E.164 format)
      name:                  str  — contact name
      occasion_date:         str  — event date (ISO date or natural language)
      guests:                int  — approximate guest count
      callback_availability: str  — preferred callback window (optional)
      notes:                 str  — any additional context (optional)
    """
    missing = [k for k in _REQUIRED_FIELDS if not args.get(k)]
    if missing:
        logger.warning(
            "[capture_catering_lead] missing required fields=%r (call_sid=%s)",
            missing,
            ctx.call_sid,
        )
        return ToolResult(
            ok=False,
            error=f"missing required fields: {missing}",
            error_code=ErrorCode.TOOL_VALIDATION_FAILED,
        )

    try:
        guests = int(args["guests"])
    except (TypeError, ValueError):
        return ToolResult(
            ok=False,
            error="guests must be an integer",
            error_code=ErrorCode.TOOL_VALIDATION_FAILED,
        )

    try:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO catering_leads
                    (call_sid, tenant_id, phone, name, occasion_date,
                     guests, callback_availability, notes, captured_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, now())
                """,
                ctx.call_sid,
                ctx.tenant_id,
                args["phone"],
                args["name"],
                args["occasion_date"],
                guests,
                args.get("callback_availability"),
                args.get("notes"),
            )
        logger.info(
            "[capture_catering_lead] lead captured call_sid=%s name=%r guests=%d",
            ctx.call_sid,
            args["name"],
            guests,
        )
        return ToolResult(
            ok=True,
            data={
                "lead_captured": True,
                "callback_window": args.get("callback_availability"),
                "caller_facing_message": (
                    "Vielen Dank, ein Mitarbeiter wird Sie zurückrufen."
                ),
            },
        )
    except Exception as exc:
        logger.exception(
            "[capture_catering_lead] DB write failed (call_sid=%s): %s",
            ctx.call_sid,
            exc,
        )
        return ToolResult(
            ok=False,
            error=str(exc),
            error_code=ErrorCode.TOOL_DEPENDENCY_ERROR,
        )


async def _get_pool():
    """Lazy-import DB pool — avoids circular imports at module load time."""
    try:
        from server.configs.db import get_pool  # type: ignore
        return await get_pool()
    except ImportError:
        raise RuntimeError("DB pool not available; set POSTGRES_DSN in environment")
