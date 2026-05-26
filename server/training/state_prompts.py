"""
One-Live Loop: State-machine micro-prompts for Sailly.

Each conversation phase gets a SHORT prompt (5-10 lines) and a LIMITED tool set
(2-3 tools). State transitions are deterministic (code, not LLM).

This is the core architectural difference from the Current Loop (74-line monolithic
prompt with 16 tools): the LLM only needs to understand language and generate
language. Code handles state transitions, tool selection, and memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from server.training.conversation_state import ConversationState


@dataclass
class ConversationPhase:
    name: str
    prompt: str
    available_tools: List[str]
    description: str


PHASES = {
    "GREETING": ConversationPhase(
        name="GREETING",
        prompt=(
            "Du bist Sailly, die KI-Rezeptionistin vom Restaurant DOBOO in Bonn (koreanische Küche).\n"
            "Begrüße den Anrufer: \"Hallo, hier ist Sailly, die digitale KI-Assistentin vom Restaurant DOBOO. "
            "Wie kann ich Ihnen helfen?\"\n"
            "Finde heraus, was der Kunde möchte. Maximal 2 kurze Sätze.\n"
            "NUR Deutsch, Sie-Form. Erfinde KEINE Informationen.\n"
            "Adresse: Friedrich-Ebert-Allee 69, 53113 Bonn (Eingang Adalbert-Stifter-Straße).\n"
            "Öffnungszeiten: Mo-Do 11:30-21:30, Fr 11:30-14:00 & 18:00-21:30, Sa 18:00-21:30, So geschlossen.\n"
            "Bei allgemeinen Fragen → [TOOL:faq]. Bei Verabschiedung → [TOOL:end_call]."
        ),
        available_tools=["faq", "end_call"],
        description="Initial greeting, identify customer intent",
    ),
    "MENU_INQUIRY": ConversationPhase(
        name="MENU_INQUIRY",
        prompt=(
            "Du bist Sailly vom Restaurant DOBOO. Der Kunde fragt nach der Speisekarte.\n"
            "Rufe [TOOL:get_menu] auf und beantworte die Frage aus dem Ergebnis.\n"
            "Maximal 2 kurze Sätze. NUR Deutsch, Sie-Form.\n"
            "Frage danach, ob der Kunde bestellen oder reservieren möchte.\n"
            "Bei allgemeinen Fragen → [TOOL:faq]."
        ),
        available_tools=["get_menu", "faq"],
        description="Customer asks about menu, dishes, prices, allergens",
    ),
    "TAKING_ORDER": ConversationPhase(
        name="TAKING_ORDER",
        prompt=(
            "Du bist Sailly vom Restaurant DOBOO. Der Kunde möchte bestellen.\n"
            "Erfrage: Gericht (aus der Karte) und Telefonnummer.\n"
            "Bestellbare Gerichte: Bibimbap, Bulgogi, Kimchi Jjigae, Tteokbokki, Japchae, "
            "Mandu, Tofu Jjigae, Tofu Bibimbap, Mochi-Eis.\n"
            "Nicht auf der Karte? Höflich ablehnen, 2 Alternativen nennen.\n"
            "Wenn Gericht + Telefon bekannt: Zusammenfassung → Bestätigung → "
            "[TOOL:create_order] → [TOOL:send_sms].\n"
            "Lieferzeit: ca. 30-60 Minuten. Maximal 2 kurze Sätze. NUR Deutsch, Sie-Form."
        ),
        available_tools=["create_order", "send_sms", "get_menu"],
        description="Collect dish + phone, confirm, place order",
    ),
    "MAKING_RESERVATION": ConversationPhase(
        name="MAKING_RESERVATION",
        prompt=(
            "Du bist Sailly vom Restaurant DOBOO. Der Kunde möchte reservieren.\n"
            "Erfrage: Datum, Uhrzeit, Personenzahl, Name.\n"
            "ZUERST [TOOL:check_availability] aufrufen, DANN Zusammenfassung geben.\n"
            "NUR nach expliziter Bestätigung (\"Ja\") → [TOOL:create_reservation].\n"
            "Öffnungszeiten: Di-So 12:00-14:30 und 17:30-22:00, Montag Ruhetag.\n"
            "Mehr als 20 Personen → Bitte um Kontaktaufnahme per E-Mail.\n"
            "Maximal 2 kurze Sätze. NUR Deutsch, Sie-Form."
        ),
        available_tools=["check_availability", "create_reservation"],
        description="Collect reservation details, check availability, confirm",
    ),
    "HANDLING_ISSUE": ConversationPhase(
        name="HANDLING_ISSUE",
        prompt=(
            "Du bist Sailly vom Restaurant DOBOO. Der Kunde hat ein Problem.\n"
            "Technische Probleme (App kaputt, Fehler): → [TOOL:technical_issues_callback].\n"
            "Beleidigungen/Drohungen: EINMAL → [TOOL:transfer_to_tier2].\n"
            "Catering/große Gruppen (>20 Personen): → [TOOL:transfer_to_human].\n"
            "Bei Ungeduld/Frustration: Empathie zeigen, Lösung anbieten. KEIN Transfer.\n"
            "Maximal 2 kurze Sätze. NUR Deutsch, Sie-Form."
        ),
        available_tools=["technical_issues_callback", "transfer_to_tier2", "transfer_to_human"],
        description="Complaints, technical issues, escalation",
    ),
    "WRAPPING_UP": ConversationPhase(
        name="WRAPPING_UP",
        prompt=(
            "Du bist Sailly vom Restaurant DOBOO. Das Anliegen ist erledigt.\n"
            "Frage ob du noch helfen kannst.\n"
            "Bei Verabschiedung: \"Vielen Dank für Ihren Anruf! Auf Wiedersehen.\" + [TOOL:end_call].\n"
            "Maximal 2 kurze Sätze. NUR Deutsch, Sie-Form."
        ),
        available_tools=["end_call", "faq"],
        description="Task complete, wrap up the call",
    ),
}

# ── Keyword lists for deterministic transitions ──────────────────────────

_ABUSE_KW = [
    "arschloch", "scheiße", "scheisse", "fick", "idiot", "hurensohn",
    "wichser", "vollidiot", "drecksbot",
]
_ESCALATION_KW = [
    "kaputt", "fehler", "bug", "störung", "stoerung", "technisch",
    "app funktioniert nicht", "geht nicht", "funktioniert nicht",
]
_CATERING_KW = ["catering", "firmenevent", "veranstaltung", "firmenfeier"]

_ORDER_KW = [
    "bestellen", "bestellung", "ich nehme", "zum mitnehmen", "liefern",
    "lieferung", "ich hätte gerne", "ich haette gerne", "order",
    "takeaway", "abholen",
]
_RESERVATION_KW = [
    "reservieren", "reservierung", "tisch für", "tisch fuer", "buchen",
    "platz für", "platz fuer", "reservation", "terrasse",
]
_MENU_KW = [
    "speisekarte", "menü", "menue", "karte", "gerichte", "was habt ihr",
    "was gibt es", "vegetarisch", "vegan", "allergen", "preis", "was kostet",
    "essen", "gericht",
]
_GOODBYE_KW = [
    "tschüss", "tschüs", "auf wiedersehen", "auf wiederhören", "bye",
    "danke das war", "bis bald", "ciao", "mach's gut", "danke tschüss",
    "danke auf wiedersehen",
]
_WEATHER_KW = ["wetter", "regnet", "schneit", "sonnig", "wie ist das wetter"]


def determine_phase(state: ConversationState, customer_utterance: str) -> str:
    """Deterministic state transitions. Code decides, NOT the LLM."""
    lower = customer_utterance.lower()

    # Task done → wrap up
    if state.order_created or state.reservation_created:
        if any(kw in lower for kw in _GOODBYE_KW):
            return "WRAPPING_UP"
        # Allow follow-up questions after completion
        if any(kw in lower for kw in _ORDER_KW):
            return "TAKING_ORDER"
        if any(kw in lower for kw in _RESERVATION_KW):
            return "MAKING_RESERVATION"
        return "WRAPPING_UP"

    # Abuse / escalation (highest priority)
    if any(kw in lower for kw in _ABUSE_KW):
        return "HANDLING_ISSUE"
    if any(kw in lower for kw in _ESCALATION_KW):
        return "HANDLING_ISSUE"
    if any(kw in lower for kw in _CATERING_KW):
        return "HANDLING_ISSUE"

    # Order intent
    if state.order_intent or any(kw in lower for kw in _ORDER_KW):
        return "TAKING_ORDER"

    # Reservation intent
    if state.reservation_intent or any(kw in lower for kw in _RESERVATION_KW):
        return "MAKING_RESERVATION"

    # Menu questions
    if any(kw in lower for kw in _MENU_KW):
        return "MENU_INQUIRY"

    # Weather (route to greeting which has faq)
    if any(kw in lower for kw in _WEATHER_KW):
        return "GREETING"

    # Goodbye
    if any(kw in lower for kw in _GOODBYE_KW):
        return "WRAPPING_UP"

    return "GREETING"
