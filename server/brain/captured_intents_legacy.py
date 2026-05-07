"""
CapturedIntent — per-intent slot storage for multi-intent calls.

After extract_multi() returns >= 2 intents, parse_multi_intent_extraction()
converts the raw JSON into a list of CapturedIntent objects sorted by priority
(takeaway/delivery first, reservation last).  The list is stored on
ConversationState.captured_intents and ConversationState.current_intent_idx
tracks which intent the bot is currently reading back and confirming.

Lifecycle of a CapturedIntent:
    captured  → bot reads slots back to caller
    confirmed → caller says "ja" → tool fires
    completed → tool response received, advance to next intent
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

INTENT_PRIORITY: List[str] = [
    "takeaway",    # happening now, most urgent
    "delivery",    # happening now
    "bulk_order",  # scheduled, mid-urgency
    "reservation", # scheduled, least urgent
    "faq",
]

INTENT_LABELS_DE: Dict[str, str] = {
    "takeaway":    "Abholung",
    "delivery":    "Lieferung",
    "bulk_order":  "Sammelbestellung",
    "reservation": "Reservierung",
    "faq":         "Frage",
}


@dataclass
class CapturedIntent:
    type: str                                    # takeaway | delivery | bulk_order | reservation
    slots: dict                                  # all extracted data for this intent (raw from extractor)
    confidence: str = "high"                     # "high" | "low"
    status: str = "captured"                     # captured | confirmed | completed
    missing_slots: List[str] = field(default_factory=list)
    tool_result: Optional[dict] = None

    @property
    def label_de(self) -> str:
        return INTENT_LABELS_DE.get(self.type, self.type)

    def items_summary(self) -> str:
        """Return a compact German string of items for read-back."""
        items = self.slots.get("items", [])
        if not items:
            return ""
        parts = []
        for item in items:
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

    def readback_slots_de(self) -> str:
        """Return a bullet list of known slot values for prompt injection."""
        lines = []
        s = self.slots
        if s.get("party_size"):
            lines.append(f"- Personen: {s['party_size']}")
        offset = s.get("pickup_offset_minutes")
        if offset:
            lines.append(f"- Abholzeit: in {offset} Minuten")
        if s.get("date"):
            lines.append(f"- Datum: {s['date']}")
        if s.get("time"):
            lines.append(f"- Uhrzeit: {s['time']}")
        if s.get("occasion"):
            lines.append(f"- Anlass: {s['occasion']}")
        reqs = s.get("special_requests", [])
        if reqs:
            lines.append(f"- Sonderwünsche: {', '.join(reqs)}")
        items = self.items_summary()
        if items:
            lines.append(f"- Artikel: {items}")
        return "\n".join(lines) if lines else "(keine Details erfasst)"


def sort_intents_by_priority(intents: List[CapturedIntent]) -> List[CapturedIntent]:
    return sorted(
        intents,
        key=lambda i: INTENT_PRIORITY.index(i.type) if i.type in INTENT_PRIORITY else len(INTENT_PRIORITY)
    )


def parse_multi_intent_extraction(raw: dict) -> List[CapturedIntent]:
    """
    Convert extract_multi() raw JSON into sorted CapturedIntent list.
    Returns [] if fewer than 2 intents found (caller should use normal OrderSlots path).
    """
    intents_raw = raw.get("intents", [])
    if not isinstance(intents_raw, list) or len(intents_raw) < 2:
        return []

    type_map = {
        "order": "takeaway", "takeaway": "takeaway", "pickup": "takeaway",
        "abholung": "takeaway", "delivery": "delivery", "lieferung": "delivery",
        "bulk": "bulk_order", "bulk_order": "bulk_order",
        "sammelbestellung": "bulk_order", "reservation": "reservation",
        "reservierung": "reservation", "faq": "faq",
    }

    intents: List[CapturedIntent] = []
    for intent_raw in intents_raw:
        if not isinstance(intent_raw, dict):
            continue
        raw_type = intent_raw.get("type", "")
        canonical = type_map.get(raw_type.lower(), raw_type)
        if not canonical:
            continue
        intents.append(CapturedIntent(
            type=canonical,
            slots=intent_raw,
            confidence=intent_raw.get("confidence", "high"),
        ))

    return sort_intents_by_priority(intents)
