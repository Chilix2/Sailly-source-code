"""
OrderSlots — canonical slot form for a single call.

This is the authoritative "what do we know" object. Every user utterance
is extracted into slot fragments by SlotExtractor, which are merged here.
The dialog prompt reads from this; node_manager's forced commits still
read from ConversationState; both are kept in sync.

Design principles:
- Never overwrite a filled slot without explicit user correction
- Track confidence per slot (high/medium/low)
- Track source turn for debugging and corrections detection
- Partial values are valid (street without number → partial)

DEPRECATION: OrderSlots will be fully migrated to CapturedIntent over
phases 2-3. Phase 1 marks all public methods with deprecation warnings
to track usage. Do not add new code using OrderSlots; use CapturedIntent instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Literal, Optional
import warnings
import logging
from functools import wraps
import inspect

logger = logging.getLogger(__name__)

_WARNED_CALLERS = set()  # Track which callers we've warned (once per unique location)


def _deprecated_orderslots(fn):
    """Decorator that emits a deprecation warning for OrderSlots methods.
    
    Warns once per unique caller location (e.g., "file.py:123").
    Also emits a structured log entry for dashboarding.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Get the caller's location
        frame = inspect.currentframe().f_back
        caller_key = f"{frame.f_code.co_filename}:{frame.f_lineno}"
        
        # Warn only once per unique caller
        if caller_key not in _WARNED_CALLERS:
            _WARNED_CALLERS.add(caller_key)
            warnings.warn(
                f"OrderSlots.{fn.__name__} is deprecated; migrate to CapturedIntent. "
                f"Called from {caller_key}",
                DeprecationWarning,
                stacklevel=2,
            )
            # Structured log for dashboarding
            logger.warning(
                "deprecated_orderslots_call",
                extra={
                    "method": fn.__name__,
                    "caller": caller_key,
                    "phase": "1",
                }
            )
        
        return fn(*args, **kwargs)
    
    return wrapper


class SlotStatus(str, Enum):
    MISSING = "missing"
    PARTIAL = "partial"      # has value but incomplete (street w/o number)
    FILLED = "filled"
    CONFIRMED = "confirmed"  # user explicitly confirmed ("ja, genau")


@dataclass
class SlotValue:
    """One slot with value, confidence, and provenance."""
    value: Optional[str] = None
    status: SlotStatus = SlotStatus.MISSING
    confidence: Literal["high", "medium", "low"] = "low"
    source_turn: Optional[int] = None
    raw_mentions: List[str] = field(default_factory=list)

    def is_usable(self) -> bool:
        return self.status in (SlotStatus.FILLED, SlotStatus.CONFIRMED)

    def needs_ask(self) -> bool:
        return self.status == SlotStatus.MISSING

    def needs_clarify(self) -> bool:
        return self.status == SlotStatus.PARTIAL


@dataclass
class OrderSlots:
    """Canonical slot form — persists for the whole call."""

    # Customer
    name:           SlotValue = field(default_factory=SlotValue)
    phone:          SlotValue = field(default_factory=SlotValue)

    # Order
    delivery_type:  SlotValue = field(default_factory=SlotValue)  # "delivery" | "pickup"
    items:          SlotValue = field(default_factory=SlotValue)  # comma-joined string

    # Delivery address (only required when delivery_type == "delivery")
    address_street: SlotValue = field(default_factory=SlotValue)
    address_number: SlotValue = field(default_factory=SlotValue)
    address_city:   SlotValue = field(default_factory=SlotValue)

    # Reservation fields
    party_size:        SlotValue = field(default_factory=SlotValue)
    reservation_date:  SlotValue = field(default_factory=SlotValue)
    reservation_time:  SlotValue = field(default_factory=SlotValue)

    # High-level intent: "order" | "reservation" | "faq" | None
    intent: Optional[str] = None

    # ------------------------------------------------------------------
    # Required-slot logic
    # ------------------------------------------------------------------

    @_deprecated_orderslots
    def required_for_order(self) -> List[str]:
        """Slot names that must be filled before create_order can fire.
        
        Order reflects DISH-FIRST checkout flow (tenant requirement):
        1. items (dishes to order)
        2. delivery_type (delivery vs pickup)
        3. address (if delivery)
        4. phone (contact number)
        5. name (full name, last in checkout)
        """
        req = ["items", "delivery_type"]
        if self.delivery_type.value == "delivery":
            req += ["address_street", "address_number"]
        req += ["phone", "name"]
        return req

    @_deprecated_orderslots
    def required_for_reservation(self) -> List[str]:
        return ["name", "party_size", "reservation_date", "reservation_time"]

    @_deprecated_orderslots
    def missing_required(self) -> List[str]:
        """Return required slot names that are not yet usable."""
        if self.intent == "reservation":
            required = self.required_for_reservation()
        else:
            required = self.required_for_order()
        return [name for name in required if not getattr(self, name).is_usable()]

    @_deprecated_orderslots
    def next_slot_to_ask(self) -> Optional[str]:
        """The single next slot to ask about, or None if all filled."""
        missing = self.missing_required()
        return missing[0] if missing else None

    @_deprecated_orderslots
    def has_readback_content(self, bot_response: str) -> bool:
        """True if the bot response contains a phone number, address, or
        ordered item that was extracted from the caller — indicating that
        this is a verification/readback turn requiring slower pacing."""
        if not bot_response:
            return False
        lower = bot_response.lower()
        if self.phone.is_usable() and self.phone.value and self.phone.value in lower:
            return True
        if self.address_street.is_usable() and self.address_street.value and \
                self.address_street.value.lower() in lower:
            return True
        if self.items.is_usable() and self.items.value:
            if any(
                item.strip().lower() in lower
                for item in self.items.value.split(",")
                if item.strip()
            ):
                return True
        return False

    # ------------------------------------------------------------------
    # Prompt-ready summaries (German)
    # ------------------------------------------------------------------

    @_deprecated_orderslots
    def known_summary_de(self) -> str:
        lines = []
        if self.name.is_usable():
            lines.append(f"- Name: {self.name.value}")
        if self.delivery_type.is_usable():
            dt = "Lieferung" if self.delivery_type.value == "delivery" else "Abholung"
            lines.append(f"- Art: {dt}")
        if self.items.is_usable():
            lines.append(f"- Bestellung: {self.items.value}")
        if self.address_street.value:  # show even if PARTIAL (partial street is informative)
            addr = self.address_street.value
            if self.address_number.is_usable():
                addr += f" {self.address_number.value}"
            if self.address_city.is_usable():
                addr += f", {self.address_city.value}"
            lines.append(f"- Adresse: {addr}")
        if self.phone.is_usable():
            lines.append(f"- Telefon: {self.phone.value}")
        elif self.phone.status == SlotStatus.PARTIAL and self.phone.value:
            lines.append(f"- Telefon (unbestätigt): {self.phone.value}")
        if self.party_size.is_usable():
            lines.append(f"- Personen: {self.party_size.value}")
        if self.reservation_date.is_usable():
            lines.append(f"- Datum: {self.reservation_date.value}")
        if self.reservation_time.is_usable():
            lines.append(f"- Uhrzeit: {self.reservation_time.value}")
        return "\n".join(lines) if lines else "(noch keine Daten erfasst)"

    @_deprecated_orderslots
    def missing_summary_de(self) -> str:
        missing = self.missing_required()
        if not missing:
            return "(alle Pflichtdaten vorhanden)"
        mapping = {
            "name":             "Name",
            "phone":            "Telefonnummer",
            "delivery_type":    "Lieferung oder Abholung?",
            "items":            "Bestellung",
            "address_street":   "Straße",
            "address_number":   "Hausnummer",
            "address_city":     "Ort",
            "party_size":       "Personenzahl",
            "reservation_date": "Datum",
            "reservation_time": "Uhrzeit",
        }
        return "\n".join(f"- {mapping.get(s, s)}" for s in missing)

    @_deprecated_orderslots
    def is_phone_from_caller_id(self) -> bool:
        """True when phone slot was seeded from Twilio caller-ID (not spoken)."""
        return (
            self.phone.status == SlotStatus.PARTIAL
            and bool(self.phone.raw_mentions)
            and self.phone.raw_mentions[0].startswith("caller_id:")
        )

    # ------------------------------------------------------------------
    # Merge extraction results
    # ------------------------------------------------------------------

    @_deprecated_orderslots
    def merge_extraction(self, extraction: dict, turn_idx: int) -> List[str]:
        """
        Merge a SlotExtractor result into current slots.
        Returns list of slot names that were newly filled/updated.

        Rules:
        - Never overwrite CONFIRMED slots (unless correction=True)
        - Don't overwrite FILLED slots with lower-confidence data
        - Partial values stored with PARTIAL status
        """
        newly_filled: List[str] = []

        for slot_name, slot_data in extraction.items():
            if slot_name == "intent":
                if slot_data and not self.intent:
                    self.intent = str(slot_data)
                continue

            if not hasattr(self, slot_name):
                continue

            current: SlotValue = getattr(self, slot_name)

            new_value = (
                slot_data.get("value") if isinstance(slot_data, dict) else slot_data
            )
            if not new_value:
                continue

            new_conf: str = (
                slot_data.get("confidence", "medium")
                if isinstance(slot_data, dict)
                else "medium"
            )
            is_correction: bool = (
                slot_data.get("correction", False)
                if isinstance(slot_data, dict)
                else False
            )
            is_partial: bool = (
                slot_data.get("partial", False)
                if isinstance(slot_data, dict)
                else False
            )

            # Never overwrite CONFIRMED without explicit correction
            if current.status == SlotStatus.CONFIRMED and not is_correction:
                continue

            # Don't downgrade a FILLED slot with lower-confidence new data
            if current.is_usable() and not is_correction and _conf_lt(new_conf, current.confidence):
                continue

            current.value = str(new_value).strip()
            current.status = SlotStatus.PARTIAL if is_partial else SlotStatus.FILLED
            current.confidence = new_conf
            current.source_turn = turn_idx
            current.raw_mentions.append(str(new_value).strip())

            if current.status == SlotStatus.FILLED:
                newly_filled.append(slot_name)

        return newly_filled

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    @_deprecated_orderslots
    def to_dict(self) -> dict:
        result = {}
        for k, v in self.__dict__.items():
            if isinstance(v, SlotValue):
                d = asdict(v)
                d["status"] = v.status.value
                result[k] = d
            else:
                result[k] = v
        return result

    @_deprecated_orderslots
    @classmethod
    def from_dict(cls, data: dict) -> "OrderSlots":
        slots = cls()
        for k, v in data.items():
            if k == "intent":
                slots.intent = v
            elif isinstance(v, dict) and "status" in v:
                setattr(slots, k, SlotValue(
                    value=v.get("value"),
                    status=SlotStatus(v.get("status", "missing")),
                    confidence=v.get("confidence", "low"),
                    source_turn=v.get("source_turn"),
                    raw_mentions=v.get("raw_mentions", []),
                ))
        return slots


def _conf_lt(a: str, b: str) -> bool:
    order = {"low": 0, "medium": 1, "high": 2}
    return order.get(a, 0) < order.get(b, 0)
