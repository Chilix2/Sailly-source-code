"""
Layer 1 — after-hours business rules for the PRE_ORDER intent.

The restaurant's kitchen hours (Europe/Berlin time):
  Mon–Thu  11:30–21:30
  Fri      11:30–14:00  and  18:00–21:30
  Sat      18:00–21:30
  Sun      closed

Rules:
  - is_within_hours() → True when an order can be placed NOW
  - earliest_pre_order_time() → first valid kitchen-open moment from now
  - allowed_intents_now() → which IntentKinds can be committed right now
    (always includes FAQ, COMPLAINT, etc.; excludes TAKEAWAY/DELIVERY when closed)
"""
from __future__ import annotations

import datetime
from typing import List, Optional, Set

from server.brain.captured_intents import IntentKind

_TZ_BERLIN = datetime.timezone(datetime.timedelta(hours=2))  # CEST; adjust for CET in winter


def _berlin_now() -> datetime.datetime:
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
        return datetime.datetime.now(tz=ZoneInfo("Europe/Berlin"))
    except Exception:
        # Fallback: use UTC+2 (CEST), or UTC+1 (CET) for winter
        # In production this never triggers because the server is in Berlin.
        return datetime.datetime.now(tz=_TZ_BERLIN)


def _periods_for_weekday(weekday: int) -> List[tuple[datetime.time, datetime.time]]:
    """Return list of (open, close) datetime.time pairs for a given weekday.

    weekday: 0=Monday … 6=Sunday
    """
    t = datetime.time
    if weekday <= 3:  # Mon–Thu
        return [(t(11, 30), t(21, 30))]
    if weekday == 4:  # Fri
        return [(t(11, 30), t(14, 0)), (t(18, 0), t(21, 30))]
    if weekday == 5:  # Sat
        return [(t(18, 0), t(21, 30))]
    return []  # Sun: closed


def is_within_hours(now: Optional[datetime.datetime] = None) -> bool:
    """Return True iff the kitchen accepts orders right now."""
    if now is None:
        now = _berlin_now()
    periods = _periods_for_weekday(now.weekday())
    current = now.time()
    return any(open_ <= current < close_ for open_, close_ in periods)


def earliest_pre_order_time(
    now: Optional[datetime.datetime] = None,
    max_days_ahead: int = 7,
) -> Optional[datetime.datetime]:
    """Return the next kitchen-open moment from now.

    Returns None if the restaurant doesn't open within max_days_ahead days
    (shouldn't happen given the schedule above).
    """
    if now is None:
        now = _berlin_now()

    for day_offset in range(max_days_ahead * 2):  # extra buffer
        candidate_date = (now + datetime.timedelta(days=day_offset)).date()
        weekday = candidate_date.weekday()
        periods = _periods_for_weekday(weekday)
        for open_time, _ in periods:
            candidate_dt = datetime.datetime.combine(
                candidate_date, open_time, tzinfo=now.tzinfo
            )
            if candidate_dt > now:
                return candidate_dt

    return None  # shouldn't happen


# Intents that can NEVER be committed during after-hours
_BLOCKED_AFTER_HOURS: Set[IntentKind] = {
    IntentKind.TAKEAWAY,
    IntentKind.DELIVERY,
    IntentKind.BULK_ORDER,
}

# PRE_ORDER is allowed during and outside hours (it's explicitly for after-hours)
_ALWAYS_ALLOWED: Set[IntentKind] = {
    IntentKind.PRE_ORDER,
    IntentKind.FAQ,
    IntentKind.DIETARY_INQUIRY,
    IntentKind.COMPLAINT,
    IntentKind.PAYMENT_ISSUE,
    IntentKind.LOST_AND_FOUND,
    IntentKind.MODIFY_ORDER,
    IntentKind.CANCEL_ORDER,
    IntentKind.ORDER_STATUS,
    IntentKind.MODIFY_RESERVATION,
    IntentKind.CANCEL_RESERVATION,
    IntentKind.GROUP_CATERING,
}


def allowed_intents_now(now: Optional[datetime.datetime] = None) -> Set[IntentKind]:
    """Return the set of IntentKinds that can be committed right now.

    During kitchen hours: all intents are allowed.
    After kitchen hours: TAKEAWAY, DELIVERY, BULK_ORDER are blocked.
    PRE_ORDER, FAQ, service intents are always allowed.
    RESERVATION is allowed at all times (for future dates).
    """
    if now is None:
        now = _berlin_now()

    if is_within_hours(now):
        return set(IntentKind)  # everything allowed

    return _ALWAYS_ALLOWED | {IntentKind.RESERVATION}
