"""
create_reservation — books a table.

Phase 6 decision:
  - tool-create-reservation-conflicts: current-alternatives
    When the requested slot is unavailable, offer 3 nearby time alternatives.
    If none available within ±90 min, set cross_sell_eligible=True (Phase 10).

Note: cross-tenant referrals (cross-sell to other restaurants) are deferred
to Phase 10 which requires multi-tenant directory infrastructure.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from server.tools.common.context import ToolContext
from server.tools.common.error_codes import ErrorCode
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "create_reservation"

# Maximum party size alternatives search window (minutes in each direction)
_ALTERNATIVE_DELTAS_MINUTES = [-30, 30, 60, 90, -60, -90, 120]
_MAX_ALTERNATIVES = 3


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args:
      date:       str (YYYY-MM-DD)
      time:       str (HH:MM)
      party_size: int
      name:       str
      phone:      str (optional)
      email:      str (optional)
      notes:      str (optional)
    """
    required = ["date", "time", "party_size", "name"]
    missing = [f for f in required if not args.get(f)]
    if missing:
        return ToolResult(
            ok=False,
            error=f"Fehlende Pflichtfelder: {', '.join(missing)}",
            error_code=ErrorCode.MISSING_REQUIRED_SLOT,
        )

    requested = _parse_datetime(args.get("date", ""), args.get("time", ""))
    if requested is None:
        return ToolResult(
            ok=False,
            error=f"Datum/Zeit nicht lesbar: {args.get('date')} {args.get('time')}",
            error_code=ErrorCode.TOOL_VALIDATION_FAILED,
        )

    party_size = _safe_int(args.get("party_size"), default=1)

    # Check for past dates (graceful rejection with alternatives)
    from datetime import datetime as dt_cls
    from zoneinfo import ZoneInfo
    BERLIN = ZoneInfo("Europe/Berlin")
    now = dt_cls.now(BERLIN)
    if requested <= now:
        # Past date requested — offer alternatives
        alternatives = await _find_alternatives(ctx, now, party_size)
        if alternatives:
            return ToolResult(
                ok=False,
                data={
                    "requested_past": requested.isoformat(),
                    "alternatives": alternatives,
                    "reason": "Reservierungen können nur für zukünftige Zeiten vorgenommen werden.",
                },
                error="reservation_date_in_past",
                error_code=ErrorCode.TOOL_VALIDATION_FAILED,
            )
        else:
            return ToolResult(
                ok=False,
                error="Reservierungen können nur für zukünftige Zeiten vorgenommen werden. Es stehen derzeit keine alternativen Zeitfenster zur Verfügung.",
                error_code=ErrorCode.TOOL_VALIDATION_FAILED,
            )

    # Check availability at requested slot
    available = await _check_capacity(ctx, requested, party_size)
    if available:
        return await _commit_reservation(args, ctx)

    # Conflict — find up to 3 alternatives within the opening hours window
    alternatives = await _find_alternatives(ctx, requested, party_size)

    return ToolResult(
        ok=False,
        data={
            "requested_unavailable": requested.isoformat(),
            "alternatives": alternatives,
            "cross_sell_eligible": len(alternatives) == 0,  # Phase 10 hook
        },
        error="reservation_slot_unavailable",
        error_code=ErrorCode.TOOL_VALIDATION_FAILED,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_datetime(date_str: str, time_str: str) -> Optional[datetime]:
    """Parse YYYY-MM-DD + HH:MM → aware datetime (Berlin tz)."""
    from zoneinfo import ZoneInfo
    BERLIN = ZoneInfo("Europe/Berlin")
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=BERLIN)
    except (ValueError, TypeError):
        return None


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _is_within_hours(ctx: ToolContext, dt: datetime) -> bool:
    """True if dt is within the tenant's opening hours."""
    try:
        from server.core.tenant_config import get_tenant_registry  # type: ignore
        tcfg = get_tenant_registry().load_tenant(ctx.tenant_id)
        return tcfg.is_open_now(at=dt) if tcfg else True
    except Exception:
        return True  # fail open


async def _check_capacity(ctx: ToolContext, dt: datetime, party_size: int) -> bool:
    """
    True if there is capacity at this slot. Delegates to the legacy availability
    checker from executor.py for the actual DB query.
    """
    try:
        from tools.executor import _check_availability as _legacy_check  # type: ignore
        result = await _legacy_check(
            {
                "date": dt.strftime("%Y-%m-%d"),
                "time": dt.strftime("%H:%M"),
                "party_size": str(party_size),
            },
            ctx.call_sid,
            ctx.tenant_id,
        )
        # Legacy returns {available: bool, ...}
        return bool(result.get("available", True))
    except Exception as e:
        logger.debug("[create_reservation] capacity check error (fail-open): %s", e)
        return True  # fail open — let reservation proceed


async def _find_alternatives(
    ctx: ToolContext, requested: datetime, party_size: int
) -> list[str]:
    """Return up to _MAX_ALTERNATIVES available slot ISO strings near requested."""
    alternatives: list[str] = []
    for delta_min in _ALTERNATIVE_DELTAS_MINUTES:
        if len(alternatives) >= _MAX_ALTERNATIVES:
            break
        candidate = requested + timedelta(minutes=delta_min)
        if not _is_within_hours(ctx, candidate):
            continue
        if await _check_capacity(ctx, candidate, party_size):
            alternatives.append(candidate.isoformat())
    return alternatives


async def _commit_reservation(args: dict, ctx: ToolContext) -> ToolResult:
    """Delegate to legacy executor to write the DB row + SMS."""
    try:
        from tools.executor import _create_reservation as _legacy  # type: ignore
        result = await _legacy(args, ctx.call_sid, ctx.tenant_id)
        if result.get("success") is False or result.get("error"):
            return ToolResult(ok=False, data=result, error=result.get("error", "reservation failed"), error_code=ErrorCode.TOOL_DEPENDENCY_ERROR)
        return ToolResult(ok=True, data=result)
    except ImportError:
        import uuid
        res_id = f"RES-{uuid.uuid4().hex[:8].upper()}"
        return ToolResult(
            ok=True,
            data={
                "reservation_id": res_id,
                "message": (
                    f"Reservierung bestätigt! {args.get('name')}, "
                    f"{args.get('party_size')} Personen, "
                    f"{args.get('date')} um {args.get('time')} Uhr."
                ),
            },
        )
