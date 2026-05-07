"""
reservation_workers.py — Phase 6.1 reservation slot extraction workers.

Workers:
    date_parser        — parses German date expressions to ISO date
    time_parser        — parses German time expressions to HH:MM
    party_size_parser  — extracts integer guest count
    availability_checker — calls check_availability tool (PARALLEL_SAFE)
    schema_validator   — verifies all required reservation slots are present

None of these workers call commit tools (create_reservation, send_sms).
"""
from __future__ import annotations

import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from server.brain.workers import Worker, WorkerContext, WorkerKind, WorkerOutput

# ── Date parser ──────────────────────────────────────────────────────────────────

_TODAY_RE = re.compile(r"\bheute\b", re.I)
_TOMORROW_RE = re.compile(r"\bmorgen\b", re.I)
_AFTER_TOMORROW_RE = re.compile(r"\bübermorgen\b", re.I)
_DAY_NAMES_DE: dict[str, int] = {
    "montag": 0, "dienstag": 1, "mittwoch": 2, "donnerstag": 3,
    "freitag": 4, "samstag": 5, "sonntag": 6,
}
_DAY_NAME_RE = re.compile(
    r"\b(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)\b", re.I
)
_DATE_NUMERIC_RE = re.compile(r"\b(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?\b")
_MONTH_NAMES_DE: dict[str, int] = {
    "januar": 1, "februar": 2, "märz": 3, "april": 4,
    "mai": 5, "juni": 6, "juli": 7, "august": 8,
    "september": 9, "oktober": 10, "november": 11, "dezember": 12,
}
_MONTH_NAME_RE = re.compile(
    r"\b(\d{1,2})\.\s*(januar|februar|märz|april|mai|juni|juli|august|"
    r"september|oktober|november|dezember)\b",
    re.I,
)


def _parse_date(text: str) -> Optional[str]:
    today = date.today()
    if _TODAY_RE.search(text):
        return today.isoformat()
    if _AFTER_TOMORROW_RE.search(text):
        return (today + timedelta(days=2)).isoformat()
    if _TOMORROW_RE.search(text):
        return (today + timedelta(days=1)).isoformat()
    m = _DAY_NAME_RE.search(text)
    if m:
        target_dow = _DAY_NAMES_DE[m.group(1).lower()]
        days_ahead = (target_dow - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7  # next week if same day
        return (today + timedelta(days=days_ahead)).isoformat()
    m = _MONTH_NAME_RE.search(text)
    if m:
        day = int(m.group(1))
        month = _MONTH_NAMES_DE[m.group(2).lower()]
        year = today.year
        try:
            d = date(year, month, day)
            if d < today:
                d = date(year + 1, month, day)
            return d.isoformat()
        except ValueError:
            pass
    m = _DATE_NUMERIC_RE.search(text)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        year = today.year
        if m.group(3):
            y = int(m.group(3))
            year = y if y > 100 else 2000 + y
        try:
            d = date(year, month, day)
            if d < today:
                d = date(year + 1, month, day)
            return d.isoformat()
        except ValueError:
            pass
    return None


class DateParser(Worker):
    name = "date_parser"
    kind = WorkerKind.REQUIRED
    estimated_latency_ms = 1
    timeout_ms = 50

    async def run(self, ctx: WorkerContext) -> WorkerOutput:
        t0 = time.monotonic()
        parsed = _parse_date(ctx.user_text)
        # Prefer already-known date from state if user didn't mention one
        if parsed is None and ctx.reservation_date:
            parsed = ctx.reservation_date
            confidence = 0.95  # carried over from state
        else:
            confidence = 0.85 if parsed else 0.0
        return WorkerOutput(
            worker_name=self.name,
            success=True,
            data={"reservation_date": parsed},
            confidence=confidence,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )


# ── Time parser ──────────────────────────────────────────────────────────────────

_TIME_EXPLICIT_RE = re.compile(
    r"\b(\d{1,2})[:\.](\d{2})\s*(uhr)?\b", re.I
)
_TIME_OCLOCK_RE = re.compile(
    r"\b(\d{1,2})\s*uhr\b", re.I
)
_TIME_GERMAN_RE = re.compile(
    r"\b(halb)\s*(\d{1,2})\b", re.I
)
_WORD_TO_HOUR: dict[str, int] = {
    "eins": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6,
    "sieben": 7, "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12,
    "dreizehn": 13, "vierzehn": 14, "fünfzehn": 15, "sechzehn": 16,
    "siebzehn": 17, "achtzehn": 18, "neunzehn": 19, "zwanzig": 20,
}


def _is_time_valid_for_today(time_str: str, reservation_date: Optional[str] = None) -> bool:
    """Check if reservation time is not in the past (restaurant timezone: Europe/Berlin = CEST).
    
    Args:
        time_str: Time in HH:MM format (e.g., "19:00")
        reservation_date: ISO date string (e.g., "2026-04-30"); if None, assumed today
    
    Returns:
        True if time is valid (not in past), False if time is in the past
    """
    try:
        # Restaurant is in Bonn, Germany → Europe/Berlin timezone (CEST = UTC+2 in summer)
        import zoneinfo
        tz_berlin = zoneinfo.ZoneInfo("Europe/Berlin")
        now_berlin = datetime.now(tz_berlin)
        
        # Parse reservation date
        if reservation_date is None:
            res_date = now_berlin.date()
        else:
            res_date = date.fromisoformat(reservation_date)
        
        # If reservation is for today, check if time has passed
        if res_date == now_berlin.date():
            h, m = int(time_str.split(":")[0]), int(time_str.split(":")[1])
            res_time = datetime(now_berlin.year, now_berlin.month, now_berlin.day, h, m, tzinfo=tz_berlin)
            # Allow 5-minute buffer for booking confirmation
            return res_time > now_berlin + timedelta(minutes=5)
        
        # If reservation is future date, it's always valid
        return True
    except Exception:
        # If parsing fails, assume valid (don't block the user)
        return True


def _parse_time(text: str) -> Optional[str]:
    m = _TIME_EXPLICIT_RE.search(text)
    if m:
        h, mn = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mn <= 59:
            return f"{h:02d}:{mn:02d}"
    m = _TIME_GERMAN_RE.search(text)
    if m:
        # "halb acht" = 07:30
        h = int(m.group(2))
        return f"{h - 1:02d}:30"
    m = _TIME_OCLOCK_RE.search(text)
    if m:
        h = int(m.group(1))
        if h <= 9:
            h += 12  # evening context for restaurants
        return f"{h:02d}:00"
    # Try written-out numbers ("neunzehn Uhr")
    for word, h in _WORD_TO_HOUR.items():
        if re.search(rf"\b{word}\s*(uhr)?\b", text, re.I):
            if h <= 9:
                h += 12
            return f"{h:02d}:00"
    return None


class TimeParser(Worker):
    name = "time_parser"
    kind = WorkerKind.REQUIRED
    estimated_latency_ms = 1
    timeout_ms = 50

    async def run(self, ctx: WorkerContext) -> WorkerOutput:
        t0 = time.monotonic()
        parsed = _parse_time(ctx.user_text)
        
        # Check if time is valid (not in the past) if reserving for today
        is_valid = True
        if parsed is not None and ctx.reservation_date:
            is_valid = _is_time_valid_for_today(parsed, ctx.reservation_date)
        
        if parsed is None and ctx.reservation_time:
            parsed = ctx.reservation_time
            confidence = 0.95
        else:
            confidence = 0.85 if parsed else 0.0
        
        # If time is in the past, mark it invalid by returning None + low confidence
        if parsed is not None and not is_valid:
            parsed = None
            confidence = 0.0  # Signal that this time is invalid
        
        return WorkerOutput(
            worker_name=self.name,
            success=True,
            data={"reservation_time": parsed},
            confidence=confidence,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )


# ── Party size parser ────────────────────────────────────────────────────────────

_PARTY_DIGIT_RE = re.compile(
    r"\b(\d{1,2})\s*(person(?:en)?|pers\.?|leute|gäste|gaeste|persone?n?)\b",
    re.I,
)
_PARTY_WORD_MAP = {
    "ein": 1, "eine": 1, "zwei": 2, "drei": 3, "vier": 4,
    "fünf": 5, "fuenf": 5, "sechs": 6, "sieben": 7, "acht": 8,
    "neun": 9, "zehn": 10,
}
_PARTY_WORD_RE = re.compile(
    r"\b(ein(?:e)?|zwei|drei|vier|fünf|fuenf|sechs|sieben|acht|neun|zehn)"
    r"\s+(?:person(?:en)?|pers\.?|leute|gäste|gaeste)\b",
    re.I,
)
_FUR_N_RE = re.compile(
    r"\b(?:für|zu)\s+(\d+)\b", re.I
)


def _parse_party_size(text: str) -> Optional[int]:
    m = _PARTY_DIGIT_RE.search(text)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 50:
            return n
    m = _PARTY_WORD_RE.search(text)
    if m:
        word = m.group(1).lower()
        # Normalise umlauts
        word = word.replace("ü", "u").replace("ö", "o").replace("ä", "a")
        n = _PARTY_WORD_MAP.get(word, 0)
        if 1 <= n <= 10:
            return n
    m = _FUR_N_RE.search(text)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 50:
            return n
    return None


class PartySizeParser(Worker):
    name = "party_size_parser"
    kind = WorkerKind.REQUIRED
    estimated_latency_ms = 1
    timeout_ms = 50

    async def run(self, ctx: WorkerContext) -> WorkerOutput:
        t0 = time.monotonic()
        parsed = _parse_party_size(ctx.user_text)
        if parsed is None and ctx.party_size:
            parsed = ctx.party_size
            confidence = 0.95
        else:
            confidence = 0.90 if parsed else 0.0
        return WorkerOutput(
            worker_name=self.name,
            success=True,
            data={"party_size": parsed},
            confidence=confidence,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )


# ── Schema validator ─────────────────────────────────────────────────────────────

_RESERVATION_REQUIRED = ["party_size", "reservation_date", "reservation_time"]


class ReservationSchemaValidator(Worker):
    name = "schema_validator"
    kind = WorkerKind.REQUIRED
    estimated_latency_ms = 1
    timeout_ms = 50

    async def run(self, ctx: WorkerContext) -> WorkerOutput:
        t0 = time.monotonic()
        # Check state fields
        filled = {
            "party_size": ctx.party_size,
            "reservation_date": ctx.reservation_date,
            "reservation_time": ctx.reservation_time,
            "customer_name": ctx.customer_name,
        }
        missing = [k for k in _RESERVATION_REQUIRED if not filled.get(k)]
        return WorkerOutput(
            worker_name=self.name,
            success=True,
            data={
                "schema_valid": len(missing) == 0,
                "missing_slots": missing,
                "filled_slots": {k: v for k, v in filled.items() if v},
            },
            confidence=1.0,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )


# ── Singletons ───────────────────────────────────────────────────────────────────

date_parser = DateParser()
time_parser = TimeParser()
party_size_parser = PartySizeParser()
schema_validator = ReservationSchemaValidator()
