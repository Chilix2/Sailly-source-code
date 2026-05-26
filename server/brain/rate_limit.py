"""
Per-caller rate limiting per decision per-caller-rate (9.X5).

Limits each phone number to LIMIT calls per WINDOW_SECONDS (sliding window).
Restaurant managers and known internal numbers can be added to the override
list in configs/rate_limit_overrides.txt to bypass the limit entirely.

Usage (in Twilio webhook handler):

    from server.brain.rate_limit import check_rate_limit, rate_limit_response_xml
    from_number = form_data.get("From", "")
    if not check_rate_limit(from_number):
        return Response(content=rate_limit_response_xml(), media_type="application/xml")
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from pathlib import Path

logger = logging.getLogger(__name__)

WINDOW_SECONDS: int = 3600
LIMIT: int          = 3

OVERRIDE_FILE = Path("configs/rate_limit_overrides.txt")

_OVERRIDE_PHONES: set[str] = set()
_call_history: dict[str, deque] = defaultdict(deque)
_overrides_loaded = False


def load_overrides() -> None:
    global _overrides_loaded
    _OVERRIDE_PHONES.clear()
    try:
        if OVERRIDE_FILE.exists():
            for line in OVERRIDE_FILE.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    _OVERRIDE_PHONES.add(line)
            logger.info("rate_limit_overrides_loaded", extra={"count": len(_OVERRIDE_PHONES)})
    except Exception as exc:
        logger.warning("rate_limit: could not load override file: %s", exc)
    _overrides_loaded = True


def check_rate_limit(phone: str) -> bool:
    if not _overrides_loaded:
        load_overrides()

    if not phone:
        return True

    if phone in _OVERRIDE_PHONES:
        return True

    now = time.time()
    history = _call_history[phone]

    while history and history[0] < now - WINDOW_SECONDS:
        history.popleft()

    if len(history) >= LIMIT:
        logger.warning("rate_limit_rejected", extra={"phone_tail": phone[-4:], "calls_in_window": len(history)})
        return False

    history.append(now)
    return True


def add_override(phone: str) -> None:
    _OVERRIDE_PHONES.add(phone)


def get_window_count(phone: str) -> int:
    now = time.time()
    history = _call_history[phone]
    while history and history[0] < now - WINDOW_SECONDS:
        history.popleft()
    return len(history)


def rate_limit_response_xml() -> str:
    return (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<Response>"
        "<Say language='de-DE'>"
        "Sie haben in der letzten Stunde bereits mehrere Anrufe getaetigt. "
        "Bitte rufen Sie in einer Stunde erneut an, "
        "oder hinterlassen Sie uns eine Nachricht."
        "</Say>"
        "<Hangup/>"
        "</Response>"
    )
