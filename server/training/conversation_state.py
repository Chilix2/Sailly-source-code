"""Tracks order/reservation intent across training conversation turns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, List

# Default dishes aligned with DOBOO menu (can be overridden per tenant)
KNOWN_DISHES = [
    "Bibimbap", "Bulgogi", "Kimchi Jjigae", "Tteokbokki", "Japchae", "Mandu",
    "Tofu Jjigae", "Tofu Bibimbap", "Mochi-Eis", "Mochi Eis",
]

# Global known items (for backward compatibility when not using tenant config)
_KNOWN_ITEMS: List[str] = list(KNOWN_DISHES)


def set_known_items(items: List[str]):
    """Called at startup to initialize known items from tenant config."""
    global _KNOWN_ITEMS
    _KNOWN_ITEMS = list(items) if items else list(KNOWN_DISHES)

ORDER_KEYWORDS = [
    "bestellen", "bestellung", "möchte bestellen", "moechte bestellen",
    "ich nehme", "zum mitnehmen", "liefern", "lieferung", "order",
    "ich hätte gerne", "ich haette gerne", "takeaway", "abholen",
    # Fix 3: Indirect order phrases for dual-intent scenarios
    "bestelle ich doch", "gleich was zu essen", "was zu essen",
    # Fix B: Delivery-related phrases
    "lieferung", "liefern", "delivery", "bestell", "essen bestellen",
    "zum mitnehmen", "abholen", "bring mir",
]

NEGATE_ORDER = [
    "nicht bestellen", "keine bestellung", "doch nicht", "stornieren",
    "abbrechen", "verzichten", "kein interesse",
    # Inquiry phrases: caller asks ABOUT a dish, not ordering it
    "wollte wissen, was", "wollte wissen was", "möchte wissen, was",
    "möchte wissen was", "wissen, was", "was ist das", "was sind das",
    "was bedeutet", "können sie erklären", "was genau ist",
]

RESERVATION_KEYWORDS = [
    "reservieren", "reservierung", "tisch für", "tisch fuer", "buchen",
    "platz für", "platz fuer", "reservation", "terrasse",
    "tisch", "plaetze", "plätze", "einen tisch", "freie plätze",
    "freie plaetze",
]

PHONE_PATTERN = re.compile(r"(\+?\d[\d\s\-/]{6,18}\d)")

# Keywords that trigger the delivery_address_mentioned flag (backward-compatible).
# Includes delivery intent words so forced order commits work even without explicit address text.
_ADDRESS_KW_STATE = [
    # Formal address vocabulary
    "adresse", "strasse", "straße", "hausnummer", "plz", "postleitzahl",
    "lieferadresse", "liefern an", "liefern nach", "lieferung an",
    "wohne in", "wohne auf", "meine adresse",
    "str.", "allee", "ring", "gasse", "markt",
    "hof", "graben", "damm", "ufer", "promenade",
    # Delivery intent words — also trigger the flag (backward compat with text validation)
    "lieferung", "geliefert", "liefern", "liefere", "zustellung",
    "delivery", "deliver", "delivered",
    "bring", "bringen", "gebracht",
    "mitnehmen", "zum mitnehmen", "takeaway", "take away",
    # Location mentions common in delivery scenarios
    "innenstadt", "altstadt", "stadtmitte", "zentrum",
    "bonn", "koeln", "köln", "berlin", "münchen", "muenchen",
    "hamburg", "düsseldorf", "duesseldorf", "frankfurt", "stuttgart",
    "dortmund", "essen", "leipzig", "dresden", "hannover",
]

# Subset of _ADDRESS_KW_STATE that indicates delivery INTENT specifically.
# Used to set delivery_intended flag separately from delivery_address_mentioned.
_DELIVERY_INTENT_KW = [
    "lieferung", "geliefert", "liefern", "liefere", "zustellung",
    "delivery", "deliver", "delivered",
    "bring", "bringen", "gebracht",
    "nach hause", "zu mir", "zu meiner",
]


@dataclass
class ConversationState:
    # 4-stack tracing fields (for observability and multi-tenant isolation)
    tenant_id: Optional[str] = None  # doboo, pizzeria_napoli, etc.
    call_id: Optional[str] = None    # unique call identifier for cross-component tracing
    user_id: Optional[str] = None    # customer/user identifier
    fsm_phase: Optional[str] = None  # current FSM phase (GREETING, INFO, ORDER, RESERVE, READBACK, COMMITTED)
    
    order_intent: bool = False
    selected_dish: Optional[str] = None
    phone_number: Optional[str] = None
    order_created: bool = False

    reservation_intent: bool = False
    party_size: Optional[int] = None
    reservation_date: Optional[str] = None
    reservation_time: Optional[str] = None
    reservation_created: bool = False

    menu_fetched: bool = False
    check_availability_called: bool = False
    get_date_info_called: bool = False
    verify_address_called: bool = False
    customer_confirmed: bool = False
    # Set when caller explicitly asks to have the menu sent (via SMS)
    sms_requested: bool = False

    # Set when caller explicitly mentions delivery intent (e.g. "Lieferung")
    delivery_intended: bool = False
    # Sticky flag — set once when an ACTUAL address is detected, never cleared
    delivery_address_mentioned: bool = False
    # Set once when get_weather is called
    get_weather_called: bool = False
    # Set once when ai_greeting is called (prevents double-call on node switch)
    ai_greeting_called: bool = False
    # Fix 1: One-shot flag to prevent transfer_to_tier2 from firing every turn
    transfer_to_tier2_called: bool = False
    # Fix D: Track escalation requests across turns
    escalation_requested: bool = False
    # Fix E: One-shot flag for request_callback
    request_callback_called: bool = False

    recent_responses: list[str] = field(default_factory=list)

    # Production fields — collected during live calls (not used in training scenarios)
    customer_name: Optional[str] = None
    delivery_address: Optional[str] = None
    
    # Training: known items list (dishes, services, etc.) from tenant config
    known_items: List[str] = field(default_factory=lambda: list(_KNOWN_ITEMS))

    def ready_for_order_commit(self) -> bool:
        # F1: intent + dish is necessary, but we also require that the delivery
        # type is resolved. For delivery orders, the caller must have provided
        # an address (delivery_address_mentioned=True) before create_order fires.
        # For takeaway/pickup (delivery_intended=False), no address is needed.
        # This prevents the bot from jumping to create_order without asking
        # "Lieferung oder Abholung?" and collecting the delivery address.
        delivery_resolved = (
            not self.delivery_intended          # takeaway — no address needed
            or self.delivery_address_mentioned  # delivery — address provided
        )
        return (
            self.order_intent
            and self.selected_dish is not None
            and delivery_resolved
            and not self.order_created
        )

    def ready_for_reservation_commit(self) -> bool:
        """Commit when all reservation data present. No explicit confirmation needed."""
        return (
            self.reservation_intent
            and self.party_size is not None
            and self.reservation_date is not None
            and self.reservation_time is not None
            and not self.reservation_created
        )

    def should_prompt_for_phone(self) -> bool:
        return (
            self.order_intent
            and self.selected_dish is not None
            and self.phone_number is None
            and not self.order_created
        )

    def to_dict(self) -> dict:
        """Serialize ConversationState to JSON-safe dict for Redis persistence."""
        return {
            # 4-stack tracing fields
            "tenant_id": self.tenant_id,
            "call_id": self.call_id,
            "user_id": self.user_id,
            "fsm_phase": self.fsm_phase,
            # Order fields
            "order_intent": self.order_intent,
            "selected_dish": self.selected_dish,
            "phone_number": self.phone_number,
            "order_created": self.order_created,
            # Reservation fields
            "reservation_intent": self.reservation_intent,
            "party_size": self.party_size,
            "reservation_date": self.reservation_date,
            "reservation_time": self.reservation_time,
            "reservation_created": self.reservation_created,
            # Tool call tracking
            "menu_fetched": self.menu_fetched,
            "check_availability_called": self.check_availability_called,
            "get_date_info_called": self.get_date_info_called,
            "verify_address_called": self.verify_address_called,
            "customer_confirmed": self.customer_confirmed,
            "delivery_intended": self.delivery_intended,
            "delivery_address_mentioned": self.delivery_address_mentioned,
            "get_weather_called": self.get_weather_called,
            "ai_greeting_called": self.ai_greeting_called,
            "transfer_to_tier2_called": self.transfer_to_tier2_called,
            "escalation_requested": self.escalation_requested,
            "request_callback_called": self.request_callback_called,
            "recent_responses": self.recent_responses,
            "customer_name": self.customer_name,
            "delivery_address": self.delivery_address,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ConversationState:
        """Reconstruct ConversationState from dict (e.g., from Redis)."""
        if not data:
            return cls()
        return cls(
            # 4-stack tracing fields
            tenant_id=data.get("tenant_id"),
            call_id=data.get("call_id"),
            user_id=data.get("user_id"),
            fsm_phase=data.get("fsm_phase"),
            # Order fields
            order_intent=data.get("order_intent", False),
            selected_dish=data.get("selected_dish"),
            phone_number=data.get("phone_number"),
            order_created=data.get("order_created", False),
            # Reservation fields
            reservation_intent=data.get("reservation_intent", False),
            party_size=data.get("party_size"),
            reservation_date=data.get("reservation_date"),
            reservation_time=data.get("reservation_time"),
            reservation_created=data.get("reservation_created", False),
            # Tool call tracking
            menu_fetched=data.get("menu_fetched", False),
            check_availability_called=data.get("check_availability_called", False),
            get_date_info_called=data.get("get_date_info_called", False),
            verify_address_called=data.get("verify_address_called", False),
            customer_confirmed=data.get("customer_confirmed", False),
            delivery_intended=data.get("delivery_intended", False),
            delivery_address_mentioned=data.get("delivery_address_mentioned", False),
            get_weather_called=data.get("get_weather_called", False),
            ai_greeting_called=data.get("ai_greeting_called", False),
            transfer_to_tier2_called=data.get("transfer_to_tier2_called", False),
            escalation_requested=data.get("escalation_requested", False),
            request_callback_called=data.get("request_callback_called", False),
            recent_responses=data.get("recent_responses", []),
            customer_name=data.get("customer_name"),
            delivery_address=data.get("delivery_address"),
        )


def _extract_dish(text: str, items: Optional[List[str]] = None) -> Optional[str]:
    # F9: Removed 5-char prefix match — it was causing hallucinations by
    # matching non-menu dish names. Exact substring match only.
    # Uses provided items list or falls back to global _KNOWN_ITEMS
    if items is None:
        items = _KNOWN_ITEMS
    
    lower = text.lower()
    for dish in items:
        if dish.lower() in lower:
            return dish
    # Safe first-word token match: "kimchi" → "Kimchi Jjigae", "tofu" → "Tofu Jjigae"
    # First-in-list wins — keeps "Tofu Jjigae" preferred over "Tofu Bibimbap".
    # Punctuation is stripped from tokens so "kimchi..." still matches "kimchi".
    # Only tokens >= 4 chars matched to prevent noise ("eis", etc.)
    first_words: dict[str, str] = {}
    for dish in items:
        fw = dish.lower().split()[0]
        if fw not in first_words:
            first_words[fw] = dish
    import re as _re
    for token in lower.split():
        clean = _re.sub(r"[^a-zäöüß]", "", token)
        if clean in first_words and len(clean) >= 4:
            return first_words[clean]
    return None


def _digits_only(s: str) -> str:
    return re.sub(r"\D", "", s)


# Shared hour-word lookup used both in update_state_from_utterance and externally
_HOUR_WORDS = {
    "zwölf": 12, "zwoelf": 12, "dreizehn": 13, "vierzehn": 14,
    "fünfzehn": 15, "fuenfzehn": 15, "sechzehn": 16, "siebzehn": 17,
    "achtzehn": 18, "neunzehn": 19, "zwanzig": 20, "einundzwanzig": 21,
    "eins": 13, "zwei": 14, "drei": 15, "vier": 16, "fünf": 17,
    "fuenf": 17, "sechs": 18, "sieben": 19, "acht": 20, "neun": 21,
    "zehn": 22, "elf": 23,
}


def update_state_from_utterance(state: ConversationState, utterance: str) -> None:
    lower = utterance.lower()

    if any(n in lower for n in NEGATE_ORDER):
        state.order_intent = False

    if any(kw in lower for kw in ORDER_KEYWORDS):
        state.order_intent = True

    if any(kw in lower for kw in RESERVATION_KEYWORDS):
        state.reservation_intent = True

    # Fix 2: Extract dish BEFORE checking order_intent
    # This allows dishes in customer utterances to be captured even on the first turn
    # before order_intent is explicitly set
    dish = _extract_dish(utterance)
    if dish:
        state.selected_dish = dish
        # Fix 2: Implicit order_intent from dish mention.
        # Only if not an inquiry (e.g. "was ist Kimchi?") and not a reservation.
        if not state.reservation_intent and not any(n in lower for n in NEGATE_ORDER):
            state.order_intent = True

    m = PHONE_PATTERN.search(utterance)
    if m:
        raw = m.group(1).strip()
        digits = _digits_only(raw)
        if len(digits) >= 8:
            state.phone_number = raw

    # Party size: "für vier", "4 personen", "zu dritt", "sechs leute"
    _WORD_NUMS = {
        "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "fuenf": 5,
        "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10,
        "zwölf": 12, "zwoelf": 12, "zwanzig": 20,
        "dritt": 3, "viert": 4, "fünft": 5, "sechst": 6,
    }
    pm = re.search(
        r"(?:für|fuer|zu)\s+(\d{1,2}|[a-zäöü]+)\s*(?:person|pers\.?|leute|gäste)?",
        lower,
    )
    if pm:
        val = pm.group(1)
        try:
            n = int(val)
        except ValueError:
            n = _WORD_NUMS.get(val, 0)
        if 1 <= n <= 50:
            state.party_size = n

    # Also catch "21 Personen" / "25 Leute" without a für/zu prefix
    if state.party_size is None:
        pm2 = re.search(
            r"\b(\d{1,2})\s+(?:person(?:en)?|pers\.?|leute|gäste|gaeste)\b",
            lower,
        )
        if pm2:
            try:
                n2 = int(pm2.group(1))
                if 1 <= n2 <= 50:
                    state.party_size = n2
            except ValueError:
                pass

    # Reservation date: "morgen", "Samstag", "am 15.", "nächsten Freitag"
    # F3: Check "übermorgen" and other extended phrases FIRST because "morgen"
    # is a substring of "übermorgen" — order matters here.
    _DAY_NAMES = [
        "montag", "dienstag", "mittwoch", "donnerstag",
        "freitag", "samstag", "sonntag",
        # English day names (accent scenarios may use mixed language)
        "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday",
    ]
    if not state.reservation_date:
        if "übermorgen" in lower or "uebermorgen" in lower:
            state.reservation_date = "Übermorgen"
        elif "wochenende" in lower:
            state.reservation_date = "Wochenende"
        elif "nächste woche" in lower or "naechste woche" in lower:
            state.reservation_date = "Nächste Woche"
        elif "übernächsten" in lower or "uebernächsten" in lower:
            state.reservation_date = "Übernächste Woche"
        elif any(d in lower for d in _DAY_NAMES):
            _EN_TO_DE = {
                "monday": "Montag", "tuesday": "Dienstag", "wednesday": "Mittwoch",
                "thursday": "Donnerstag", "friday": "Freitag", "saturday": "Samstag",
                "sunday": "Sonntag",
            }
            for d in _DAY_NAMES:
                if d in lower:
                    state.reservation_date = _EN_TO_DE.get(d, d.capitalize())
                    break
        elif "morgen" in lower:
            state.reservation_date = "Morgen"
        elif "heute" in lower:
            state.reservation_date = "Heute"
    dm = re.search(r"am\s+(\d{1,2})\.?\s*(\w+)?", lower)
    if dm:
        state.reservation_date = dm.group(0).strip()

    # Reservation time: "um 19 uhr", "19:30", "halb acht", "um acht"
    tm = re.search(r"(?:um\s+)?(\d{1,2})[:.:]?(\d{2})?\s*(?:uhr)", lower)
    if tm:
        h = int(tm.group(1))
        m_min = int(tm.group(2)) if tm.group(2) else 0
        if 10 <= h <= 23:
            state.reservation_time = f"{h:02d}:{m_min:02d}"
    tw = re.search(r"um\s+(\w+)", lower)
    if tw and not state.reservation_time:
        word = tw.group(1)
        h = _HOUR_WORDS.get(word)
        if h and 10 <= h <= 23:
            state.reservation_time = f"{h:02d}:00"
    if "halb acht" in lower:
        state.reservation_time = "19:30"
    elif "halb sieben" in lower:
        state.reservation_time = "18:30"
    elif "halb neun" in lower:
        state.reservation_time = "20:30"

    # F3: Extended time detection for informal time expressions
    if not state.reservation_time:
        if "abends" in lower or "am abend" in lower:
            state.reservation_time = "19:00"
        elif "mittags" in lower or "mittagessen" in lower or "am mittag" in lower:
            state.reservation_time = "12:00"
        elif "nachmittags" in lower or "am nachmittag" in lower:
            state.reservation_time = "15:00"
        elif "morgens" in lower or "zum frühstück" in lower:
            state.reservation_time = "10:00"
        else:
            # "gegen acht" / "gegen 20 Uhr" (approximate time)
            gm = re.search(r"gegen\s+(\d{1,2}|[a-zäöü]+)", lower)
            if gm:
                val = gm.group(1)
                try:
                    h = int(val)
                except ValueError:
                    h = _HOUR_WORDS.get(val, 0)
                if 10 <= h <= 23:
                    state.reservation_time = f"{h:02d}:00"

    # Delivery intent flag — caller mentioned they want delivery (not necessarily gave address)
    if not state.delivery_intended:
        if any(kw in lower for kw in _DELIVERY_INTENT_KW):
            state.delivery_intended = True

    # Delivery address detection — set once when any delivery keyword detected, never cleared.
    if not state.delivery_address_mentioned:
        if any(kw in lower for kw in _ADDRESS_KW_STATE):
            state.delivery_address_mentioned = True

    # Address text extraction — runs on every turn until delivery_address is captured.
    # Separate from delivery_address_mentioned so we catch addresses provided later.
    if not state.delivery_address:
        # Pattern 1: "Wordstr. 12" or "Word Str. 12, 10115 City" — German address formats
        # Allows optional space between street name and street type suffix.
        _addr_p1 = re.compile(
            r'\b([A-ZÄÖÜ][a-zäöüß\-]+'
            r'\s*'
            r'(?:str(?:aße?|\.?)|allee|ring|gasse|weg|platz|damm|berg|burg)'
            r'\.?\s*\d+[\w\-]*'
            r'(?:\s*,\s*[\d]{5}\s*[A-ZÄÖÜ][a-zäöüß\s]+)?)',
            re.IGNORECASE
        )
        # Pattern 2: "Adresse ist/: X" or "liefern an/nach X"
        _addr_p2 = re.compile(
            r'(?:adresse\s+ist|adresse\s*:|liefern\s+(?:an|nach|zu))\s+(.+?)(?:\s*[,.]|$)',
            re.IGNORECASE
        )
        m1 = _addr_p1.search(utterance)
        if m1:
            state.delivery_address = m1.group(0).strip()
        else:
            m2 = _addr_p2.search(utterance)
            if m2:
                state.delivery_address = m2.group(1).strip()

    # Implicit reservation intent: party_size >= 2 without food → reservation
    if (
        state.party_size is not None
        and state.party_size >= 2
        and not state.selected_dish
        and not state.order_intent
    ):
        state.reservation_intent = True

    # Fix C: implicit reservation intent from party_size + date/time together
    # (even party_size 1 is enough when combined with a date/time)
    # Handles cases where accent/sleepy caller gives date+party without
    # explicit "reservieren" keyword.
    if (
        not state.reservation_intent
        and state.party_size is not None
        and (state.reservation_date is not None or state.reservation_time is not None)
        and not state.order_intent
    ):
        state.reservation_intent = True

    # SMS/menu-send request detection
    _SMS_REQUEST_KW = [
        "schicken", "senden", "zuschicken", "per sms",
        "speisekarte schicken", "menü schicken", "menu schicken",
    ]
    if not state.sms_requested:
        if any(kw in lower for kw in _SMS_REQUEST_KW):
            state.sms_requested = True

    # Confirmation detection (sticky: once confirmed, stays confirmed until consumed)
    _CONFIRM_KW = [
        "ja", "bitte", "genau", "stimmt", "passt", "richtig",
        "machen sie", "buchen sie", "ok", "okay", "jawohl",
        "ja bitte", "ja genau", "ja gerne", "machen wir",
        "klingt gut", "perfekt", "einverstanden", "gerne",
    ]
    if any(kw in lower for kw in _CONFIRM_KW):
        state.customer_confirmed = True


def update_state_after_bot(state: ConversationState, bot_response: str) -> None:
    """
    Only set dish from bot response if the bot is EXPLICITLY CONFIRMING an order —
    never from suggestions or menu recommendations.

    Hallucination root cause: bot says "Ich empfehle Bibimbap" as a suggestion for
    a non-menu request → old code extracted Bibimbap → create_order fired for a
    dish the customer never chose.

    Fix: require confirmation language before extracting. Suggestions (empfehle,
    haben wir nicht, leider) are explicitly excluded.
    """
    if not state.order_intent or state.selected_dish:
        return
    lower = bot_response.lower()
    # Hard exclude: bot is suggesting an alternative or rejecting the request
    exclude_patterns = [
        "empfehle", "empfehlen", "leider", "haben wir nicht", "nicht auf der karte",
        "nicht im angebot", "können wir nicht", "alternativ", "stattdessen",
        "alternativlich", "vorschlag",
    ]
    if any(p in lower for p in exclude_patterns):
        return
    # Require confirmation language before extracting dish from bot.
    # Removed "ich habe" and "sie haben" — too broad: these match the forced-commit
    # template ("Ich habe Ihre Bestellung für X aufgenommen") and general statements,
    # causing a self-triggering loop: LLM text → dish extraction → premature create_order.
    confirm_patterns = [
        "bestellt", "aufgenommen", "notiert", "nehme ich auf", "ihre bestellung",
        "ich bestätige", "bestellung für",
    ]
    if not any(p in lower for p in confirm_patterns):
        return
    dish = _extract_dish(bot_response)
    if dish:
        state.selected_dish = dish
