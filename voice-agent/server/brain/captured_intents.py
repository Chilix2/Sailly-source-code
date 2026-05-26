"""
CapturedIntent — the sole state model for what the bot has heard.

One call contains a list of CapturedIntents. Each intent moves through
an explicit finite state machine: captured → confirmed → completed.

Per Phase 2 decisions:
  - confidence-everywhere: every slot carries confidence (ported from OrderSlots)
  - distinct-confirm-required: FILLED and CONFIRMED are distinct statuses
  - urgency-current: INTENT_PRIORITY stays (takeaway > delivery > bulk > reservation > faq)
  - explicit-fsm: a single transition function; nothing else mutates status

Backward compatibility:
  - .type property aliases .kind.value (for existing callers in adk_turn_processor.py)
  - sort_intents_by_priority() aliases sort_by_priority()
  - parse_multi_intent_extraction() kept as a thin wrapper
  - INTENT_LABELS_DE dict preserved
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class IntentKind(str, Enum):
    # Commerce — new transactions
    TAKEAWAY = "takeaway"
    DELIVERY = "delivery"
    BULK_ORDER = "bulk_order"
    RESERVATION = "reservation"
    PRE_ORDER = "pre_order"                    # after-hours scheduled takeaway/delivery

    # Commerce — existing transaction
    MODIFY_ORDER = "modify_order"              # "add a Bibimbap to my order"
    CANCEL_ORDER = "cancel_order"              # "cancel the order I just placed"
    ORDER_STATUS = "order_status"              # "where's my delivery?"
    MODIFY_RESERVATION = "modify_reservation"  # "change from 7pm to 8pm"
    CANCEL_RESERVATION = "cancel_reservation"  # "cancel our Friday booking"

    # Service
    COMPLAINT = "complaint"                    # distinct from generic escalation
    PAYMENT_ISSUE = "payment_issue"            # PayPal/card problem
    LOST_AND_FOUND = "lost_and_found"          # left a jacket at the restaurant
    DIETARY_INQUIRY = "dietary_inquiry"        # gluten-free? vegan?
    GROUP_CATERING = "group_catering"          # >30 quantity — requires human handling

    # Information
    FAQ = "faq"


# Urgency ordering — caller's time-sensitivity determines processing order
# (per decision urgency-current, extended for all 16 intent kinds)
INTENT_PRIORITY: Dict[IntentKind, int] = {
    # Now-urgent
    IntentKind.PAYMENT_ISSUE: 0,
    IntentKind.ORDER_STATUS: 1,
    IntentKind.COMPLAINT: 2,
    IntentKind.LOST_AND_FOUND: 3,

    # Today commerce
    IntentKind.TAKEAWAY: 10,
    IntentKind.DELIVERY: 11,
    IntentKind.CANCEL_ORDER: 12,
    IntentKind.MODIFY_ORDER: 13,

    # Scheduled commerce
    IntentKind.PRE_ORDER: 20,
    IntentKind.BULK_ORDER: 21,
    IntentKind.GROUP_CATERING: 22,
    IntentKind.CANCEL_RESERVATION: 23,
    IntentKind.MODIFY_RESERVATION: 24,
    IntentKind.RESERVATION: 25,

    # Information
    IntentKind.DIETARY_INQUIRY: 30,
    IntentKind.FAQ: 31,
}

# German labels for prompt injection
INTENT_LABELS_DE: Dict[str, str] = {
    "takeaway":            "Abholung",
    "delivery":            "Lieferung",
    "bulk_order":          "Sammelbestellung",
    "reservation":         "Reservierung",
    "pre_order":           "Vorbestellung",
    "modify_order":        "Bestellungsänderung",
    "cancel_order":        "Bestellstornierung",
    "order_status":        "Bestellstatus",
    "modify_reservation":  "Reservierungsänderung",
    "cancel_reservation":  "Reservierungsstornierung",
    "complaint":           "Beschwerde",
    "payment_issue":       "Zahlungsproblem",
    "lost_and_found":      "Fundsachen",
    "dietary_inquiry":     "Ernährungsfrage",
    "group_catering":      "Gruppenbestellung",
    "faq":                 "Frage",
}


class IntentStatus(str, Enum):
    CAPTURED = "captured"    # heard but not yet confirmed by caller
    CONFIRMED = "confirmed"  # caller said "ja, genau" — safe to commit
    COMPLETED = "completed"  # tool has fired successfully
    FAILED = "failed"        # tool fired and errored
    CANCELLED = "cancelled"  # caller rescinded mid-flow


class SlotStatus(str, Enum):
    MISSING = "missing"
    PARTIAL = "partial"
    FILLED = "filled"        # heard but not explicitly confirmed
    CONFIRMED = "confirmed"  # caller said yes — required before commit


class SlotConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SlotValue:
    """A single slot with confidence and status."""
    name: str
    value: Optional[str] = None
    status: SlotStatus = SlotStatus.MISSING
    confidence: SlotConfidence = SlotConfidence.MEDIUM
    source_turn: int = -1
    from_caller_id: bool = False


@dataclass
class CapturedIntent:
    """One intent the caller expressed during this call."""
    kind: IntentKind
    status: IntentStatus = IntentStatus.CAPTURED
    slots: Dict[str, SlotValue] = field(default_factory=dict)
    created_turn: int = 0
    tool_result: Optional[dict] = None

    # ------------------------------------------------------------------
    # Backward-compatibility shims (for existing callers using .type)
    # ------------------------------------------------------------------

    @property
    def type(self) -> str:
        """Alias for kind.value — preserved for callers in adk_turn_processor.py."""
        return self.kind.value

    # ------------------------------------------------------------------
    # Business logic
    # ------------------------------------------------------------------

    def get_slot(self, name: str) -> Optional[SlotValue]:
        return self.slots.get(name)

    def is_committable(self) -> bool:
        """True iff every required slot is CONFIRMED."""
        required = REQUIRED_SLOTS.get(self.kind, set())
        return all(
            self.slots.get(s, SlotValue(name=s)).status == SlotStatus.CONFIRMED
            for s in required
        )

    @property
    def label_de(self) -> str:
        return INTENT_LABELS_DE.get(self.kind.value, self.kind.value)

    def items_summary(self) -> str:
        """Return a compact German string of items for read-back.
        
        Supports both new SlotValue-based slots and legacy raw-dict slots.
        """
        # New path: items slot contains a SlotValue
        items_slot = self.slots.get("items")
        if isinstance(items_slot, SlotValue):
            raw = items_slot.value
        elif isinstance(items_slot, (list, dict)):
            raw = items_slot
        else:
            raw = None

        if not raw:
            return ""

        if isinstance(raw, list):
            parts = []
            for item in raw:
                if isinstance(item, dict):
                    qty = item.get("quantity")
                    name = item.get("name", "")
                    if qty and qty != 1:
                        parts.append(f"{qty}x {name}")
                    elif name:
                        parts.append(name)
                elif isinstance(item, str):
                    parts.append(item)
            return ", ".join(parts)

        # PR-16a: guard against the slot value being the string "[]" (a stringified
        # empty list from JSON parsing or SlotExtractor output). str([]) == "[]" is
        # truthy, which previously caused readback_slots_de() to emit "Artikel: []"
        # verbatim into TTS output. Return "" for empty-list string representations.
        raw_str = str(raw)
        if raw_str in ("[]", "{}", "None", "null", ""):
            return ""
        return raw_str

    def readback_slots_de(self) -> str:
        """Return a bullet list of known slot values for prompt injection."""
        lines = []

        def _val(name: str):
            sv = self.slots.get(name)
            if isinstance(sv, SlotValue):
                return sv.value
            return sv  # legacy: raw value

        if _val("party_size"):
            lines.append(f"- Personen: {_val('party_size')}")
        offset = _val("pickup_offset_minutes")
        if offset:
            lines.append(f"- Abholzeit: in {offset} Minuten")
        if _val("date"):
            lines.append(f"- Datum: {_val('date')}")
        if _val("time"):
            lines.append(f"- Uhrzeit: {_val('time')}")
        if _val("occasion"):
            lines.append(f"- Anlass: {_val('occasion')}")
        reqs = _val("special_requests")
        # PR-16a: guard against stringified empty list "[]" from JSON round-trips.
        # "[]" is truthy in Python so the naive `if reqs:` check passes, causing
        # "- Sonderwünsche: []" to appear verbatim in TTS output.
        if reqs and str(reqs) not in ("[]", "{}", "None", "null", ""):
            if isinstance(reqs, list):
                joined = ", ".join(str(r) for r in reqs if r)
                if joined:
                    lines.append(f"- Sonderwünsche: {joined}")
            else:
                lines.append(f"- Sonderwünsche: {reqs}")
        items = self.items_summary()
        if items:
            lines.append(f"- Artikel: {items}")
        return "\n".join(lines) if lines else "(keine Details erfasst)"


# ---------------------------------------------------------------------------
# Required slots per intent kind
# ---------------------------------------------------------------------------

REQUIRED_SLOTS: Dict[IntentKind, set] = {
    # New commerce
    IntentKind.TAKEAWAY: {"items", "pickup_time", "phone", "name"},
    IntentKind.DELIVERY: {"items", "address", "phone", "name"},
    IntentKind.PRE_ORDER: {"items", "pickup_time", "phone", "name", "channel"},
    IntentKind.BULK_ORDER: {"items", "pickup_time", "phone", "name", "party_size"},
    IntentKind.RESERVATION: {"date", "time", "party_size", "name", "phone"},

    # Existing-transaction ops
    IntentKind.MODIFY_ORDER: {"order_identifier", "modification"},
    IntentKind.CANCEL_ORDER: {"order_identifier"},
    IntentKind.ORDER_STATUS: {"order_identifier"},
    IntentKind.MODIFY_RESERVATION: {"reservation_identifier", "modification"},
    IntentKind.CANCEL_RESERVATION: {"reservation_identifier"},

    # Service
    IntentKind.COMPLAINT: {"complaint_type", "description"},
    IntentKind.PAYMENT_ISSUE: {"issue_type", "order_identifier"},
    IntentKind.LOST_AND_FOUND: {"item_description", "visit_date", "phone"},
    IntentKind.GROUP_CATERING: {
        "phone", "name",
        "catering_callback_availability",  # Phase 4 C4: when to call back
        "event_date", "party_size",        # optional but captured when provided
    },

    # Information
    IntentKind.DIETARY_INQUIRY: {"dietary_restriction"},
    IntentKind.FAQ: set(),
}


# ---------------------------------------------------------------------------
# Intent FSM — the ONLY function allowed to mutate IntentStatus
# ---------------------------------------------------------------------------

ALLOWED_TRANSITIONS: Dict[IntentStatus, set] = {
    IntentStatus.CAPTURED:   {IntentStatus.CONFIRMED, IntentStatus.CANCELLED},
    IntentStatus.CONFIRMED:  {IntentStatus.COMPLETED, IntentStatus.FAILED, IntentStatus.CANCELLED},
    IntentStatus.COMPLETED:  set(),   # terminal
    IntentStatus.FAILED:     {IntentStatus.CONFIRMED},  # retry path
    IntentStatus.CANCELLED:  set(),   # terminal
}


class InvalidTransitionError(Exception):
    pass


def transition_intent(
    intent: CapturedIntent,
    new_status: IntentStatus,
    reason: str,
    tool_result: Optional[dict] = None,
) -> CapturedIntent:
    """The sole function that mutates IntentStatus. Every other caller is wrong.

    Raises InvalidTransitionError on illegal transitions.
    """
    if new_status not in ALLOWED_TRANSITIONS[intent.status]:
        raise InvalidTransitionError(
            f"Cannot transition {intent.kind.value} from {intent.status.value} "
            f"to {new_status.value} (reason: {reason})"
        )
    intent.status = new_status
    if tool_result is not None:
        intent.tool_result = tool_result
    logger.info(
        "intent_transition",
        extra={
            "kind": intent.kind.value,
            "from_status": intent.status.value,
            "to_status": new_status.value,
            "reason": reason,
        },
    )
    return intent


# ---------------------------------------------------------------------------
# Sort / priority helpers
# ---------------------------------------------------------------------------

def sort_by_priority(intents: List[CapturedIntent]) -> List[CapturedIntent]:
    """Sort by urgency (PAYMENT_ISSUE first, FAQ last). Stable sort."""
    return sorted(intents, key=lambda i: INTENT_PRIORITY.get(i.kind, 99))


def sort_intents_by_priority(intents: List[CapturedIntent]) -> List[CapturedIntent]:
    """Backward-compatible alias for sort_by_priority()."""
    return sort_by_priority(intents)


# ---------------------------------------------------------------------------
# Legacy parse helper (used by adk_turn_processor.py)
# ---------------------------------------------------------------------------

def parse_multi_intent_extraction(raw: dict) -> List[CapturedIntent]:
    """Convert extract_multi() raw JSON into sorted CapturedIntent list.

    Preserved for backward compatibility. New code should call
    slot_extractor.parse_extraction_to_intents() directly.

    Returns [] if fewer than 2 intents found.
    """
    intents_raw = raw.get("intents", [])
    if not isinstance(intents_raw, list) or len(intents_raw) < 2:
        return []

    # Legacy type-string normalisation map
    _KIND_MAP: Dict[str, str] = {
        "order": "takeaway", "takeaway": "takeaway", "pickup": "takeaway",
        "abholung": "takeaway", "delivery": "delivery", "lieferung": "delivery",
        "bulk": "bulk_order", "bulk_order": "bulk_order",
        "sammelbestellung": "bulk_order", "reservation": "reservation",
        "reservierung": "reservation", "pre_order": "pre_order",
        "vorbestellung": "pre_order", "faq": "faq",
    }

    intents: List[CapturedIntent] = []
    for intent_raw in intents_raw:
        if not isinstance(intent_raw, dict):
            continue
        raw_type = intent_raw.get("type", intent_raw.get("kind", ""))
        canonical_str = _KIND_MAP.get(raw_type.lower(), raw_type.lower())
        try:
            kind = IntentKind(canonical_str)
        except ValueError:
            logger.warning(f"parse_multi_intent_extraction: unknown kind {canonical_str!r}, skipping")
            continue

        # Build slots: legacy path keeps raw dict values for now
        # (fully typed in Task A4 slot_extractor refactor)
        raw_slots = {
            k: SlotValue(name=k, value=str(v) if v is not None else None,
                         status=SlotStatus.FILLED if v else SlotStatus.MISSING,
                         confidence=SlotConfidence.MEDIUM)
            for k, v in intent_raw.items()
            if k not in ("type", "kind", "confidence", "status")
        }

        intents.append(CapturedIntent(
            kind=kind,
            status=IntentStatus.CAPTURED,
            slots=raw_slots,
        ))

    return sort_by_priority(intents)
