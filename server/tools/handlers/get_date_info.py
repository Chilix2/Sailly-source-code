"""
get_date_info — resolve relative dates and optionally check availability.

Phase 6 decision:
  - tool-check-availability: extend-get-date-info
    Instead of a separate check_availability tool, extend get_date_info
    to include capacity queries when check_capacity=True and party_size given.
"""
from __future__ import annotations

import logging

from server.tools.common.context import ToolContext
from server.tools.common.error_codes import ErrorCode
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "get_date_info"


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args:
      date:           str — relative ("heute", "nächsten Freitag") or YYYY-MM-DD
      check_capacity: bool — if True, also return available time slots
      party_size:     int — required when check_capacity=True
    """
    check_capacity = bool(args.get("check_capacity", False))
    party_size_raw = args.get("party_size")
    party_size = int(party_size_raw) if party_size_raw else None

    # ── Date resolution (delegate to legacy executor) ─────────────────────────
    try:
        from tools.executor import _get_date_info as _legacy  # type: ignore
        date_result = await _legacy(args, ctx.call_sid, ctx.tenant_id)
    except ImportError:
        from datetime import datetime, date
        today = date.today()
        date_result = {
            "date": today.isoformat(),
            "weekday": today.strftime("%A"),
            "relative": "heute",
            "message": f"{today.strftime('%d.%m.%Y')}",
        }

    if date_result.get("error"):
        return ToolResult(ok=False, data=date_result, error=date_result["error"], error_code=ErrorCode.TOOL_VALIDATION_FAILED)

    if not check_capacity or not party_size:
        return ToolResult(ok=True, data=date_result)

    # ── Availability check ────────────────────────────────────────────────────
    try:
        from tools.executor import _check_availability as _legacy_avail  # type: ignore
        avail_result = await _legacy_avail(
            {
                "date": date_result.get("date", ""),
                "party_size": str(party_size),
            },
            ctx.call_sid,
            ctx.tenant_id,
        )
        date_result["available_slots"] = avail_result.get("available_slots") or avail_result
        date_result["capacity_checked"] = True
    except Exception as e:
        logger.debug("[get_date_info] capacity check failed (non-fatal): %s", e)
        date_result["available_slots"] = None
        date_result["capacity_check_error"] = str(e)[:100]

    return ToolResult(ok=True, data=date_result)
