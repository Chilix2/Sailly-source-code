"""
Layer 1 — Identifier lookup helpers for existing-transaction intents.

Used by MODIFY_ORDER, CANCEL_ORDER, ORDER_STATUS, MODIFY_RESERVATION,
CANCEL_RESERVATION to locate the right record before LLM talks to caller.

Phase 2: stubs only — fully wired in Phase 3 when the order lookup
API is available.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def find_order_by(
    phone: Optional[str] = None,
    name: Optional[str] = None,
    order_number: Optional[str] = None,
) -> Optional[dict]:
    """Return the most recent order matching the given identifiers.

    Phase 2 stub: always returns None (triggers human handoff path).
    Phase 3 will call the order management API.
    """
    logger.debug(
        f"find_order_by: phone={phone!r} name={name!r} order_number={order_number!r} "
        "(stub — returns None)"
    )
    return None


async def find_reservation_by(
    phone: Optional[str] = None,
    name: Optional[str] = None,
    date: Optional[str] = None,
) -> Optional[dict]:
    """Return the reservation matching the given identifiers.

    Phase 2 stub: always returns None (triggers human handoff path).
    Phase 3 will call the reservation management API.
    """
    logger.debug(
        f"find_reservation_by: phone={phone!r} name={name!r} date={date!r} "
        "(stub — returns None)"
    )
    return None
