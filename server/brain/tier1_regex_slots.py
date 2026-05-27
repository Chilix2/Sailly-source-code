"""Tier-1 German regex slot fills for latency-sensitive order turns."""
from __future__ import annotations

import re
from dataclasses import dataclass

_PHONE_RE = re.compile(r"(?:\+?\d[\d\s()/.-]{6,}\d)")
_QTY_RE = re.compile(
    r"\b(?:ich\s+)?(?:nehme|möchte|moechte|haette|hätte|bestelle|bestellen)\s+"
    r"(\d{1,2}|ein|eine|einen|zwei|drei|vier|fünf|fuenf)\s*(?:mal|x|×)?\b",
    re.I,
)
_ADDR_RE = re.compile(
    r"\b((?:[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\-]+(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\-]+){0,3}\s+"
    r"(?:straße|strasse|weg|allee|platz|gasse|ring|damm|ufer)"
    r"|[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\-]*(?:straße|strasse|weg|allee|platz|gasse|ring|damm|ufer))"
    r"\s+\d{1,4}[a-zA-Z]?(?:\s*,?\s*(?:in\s+)?[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\- ]{2,30})?)\b",
    re.I,
)
_QTY_WORDS = {"ein": 1, "eine": 1, "einen": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "fuenf": 5}


@dataclass
class Tier1Slots:
    phone_number: str | None = None
    delivery_address: str | None = None
    order_quantity: int | None = None


def extract_tier1_slots(text: str) -> Tier1Slots:
    slots = Tier1Slots()
    phone_match = _PHONE_RE.search(text or "")
    if phone_match:
        digits = re.sub(r"\D+", "", phone_match.group(0))
        if len(digits) >= 7:
            slots.phone_number = digits

    addr_match = _ADDR_RE.search(text or "")
    if addr_match and re.search(r"\d", addr_match.group(1)):
        address = " ".join(addr_match.group(1).split())
        address = re.sub(r"^(?:bitte\s+)?(?:nach|an)\s+", "", address, flags=re.I)
        address = re.sub(r"\s+(?:liefern|geliefert|bringen)$", "", address, flags=re.I)
        slots.delivery_address = address

    qty_match = _QTY_RE.search(text or "")
    if qty_match:
        raw = qty_match.group(1).lower()
        slots.order_quantity = _QTY_WORDS.get(raw, int(raw) if raw.isdigit() else None)
    return slots


def apply_tier1_slots(state, text: str) -> dict:
    """Apply cheap high-confidence slots before LLM extraction."""
    slots = extract_tier1_slots(text)
    applied: dict[str, object] = {}
    if slots.phone_number and not getattr(state, "phone_number", None):
        state.phone_number = slots.phone_number
        state.phone_extracted = True
        applied["phone_number"] = slots.phone_number
    if slots.delivery_address and not getattr(state, "delivery_address", None):
        state.delivery_address = slots.delivery_address
        state.delivery_address_mentioned = True
        state.delivery_intended = True
        applied["delivery_address"] = slots.delivery_address
    if slots.order_quantity and slots.order_quantity > 0:
        state.order_quantity = slots.order_quantity
        applied["order_quantity"] = slots.order_quantity
    return applied
