"""Order flow finite-state compatibility layer.

The current pipeline still persists legacy ``end_call_stage`` strings. This
module centralizes the mapping so follow-up shrink work can move branch logic
behind typed states without changing stored call state in one release.
"""
from __future__ import annotations

from enum import Enum


class OrderFSM(str, Enum):
    IDLE = "idle"
    PRE_COMMIT_READBACK = "pre_commit_readback"
    ORDER_READBACK = "order_pre_commit_readback"
    PHONE_READBACK = "phone_readback_pending"
    CORRECTION_PENDING = "correction_pending"
    CONFIRMED = "confirmed"


_ALIASES = {
    "readback_pending": OrderFSM.PRE_COMMIT_READBACK,
    "order_readback_pending": OrderFSM.ORDER_READBACK,
}


def order_stage(value: str | OrderFSM | None) -> OrderFSM:
    """Normalize legacy ``end_call_stage`` values to the six-state FSM."""
    if isinstance(value, OrderFSM):
        return value
    if not value:
        return OrderFSM.IDLE
    text = str(value)
    if text in _ALIASES:
        return _ALIASES[text]
    try:
        return OrderFSM(text)
    except ValueError:
        return OrderFSM.IDLE


def order_stage_value(value: str | OrderFSM | None) -> str:
    """Return the legacy string value for persistence/backwards compatibility."""
    return order_stage(value).value


READBACK_STAGES = {
    OrderFSM.PRE_COMMIT_READBACK,
    OrderFSM.ORDER_READBACK,
    OrderFSM.PHONE_READBACK,
}
