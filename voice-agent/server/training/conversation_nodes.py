"""
Conversation nodes for Sailly.

Pattern from Pipecat Flows / StateFlow, implemented for Google ADK:
- Each node = focused prompt (3-8 lines) + complete tools list + transition rules
- Transitions are deterministic (code decides) not LLM-decided
- The LLM talks freely WITHIN a node — code handles BETWEEN nodes
- A4: Every node declares EVERY tool that check_forced_commits might inject
  so the first-pass node.tools filter never silently drops a forced tool.

Category A (data-retrieval, LLM-driven with guardrails):
  check_availability, faq, get_date_info, get_menu, get_weather

Category B (state-transition, code-driven ONLY — never LLM-decided):
  ai_greeting, create_order, create_reservation, end_call, request_callback,
  send_sms, technical_issues_callback, transfer_to_human, transfer_to_tier2,
  verify_address

All tools from scenarios are covered across nodes:
  check_availability, create_order, create_reservation, end_call,
  faq, get_date_info, get_menu, get_weather, request_callback, send_sms,
  technical_issues_callback, transfer_to_human, transfer_to_tier2,
  verify_address, update_state
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict

_SIE_RULE = "\nWICHTIG: Verwende IMMER die Höflichkeitsform 'Sie'. Niemals 'du' oder 'dir'."


@dataclass
class ConversationNode:
    """A single conversation state with its own prompt and tools."""
    name: str
    prompt: str
    tools: List[str]
    prerequisites: Dict[str, str] = field(default_factory=dict)


GREETING = ConversationNode(
    name="greeting",
    prompt=(
        "Du bist Sailly, die KI-Rezeptionistin vom Restaurant DOBOO in Bonn (koreanische Küche).\n"
        "Beim ersten Kontakt: kurz vorstellen und 1–2 konkrete Beispiele nennen, wobei du helfen kannst "
        "(z. B. Öffnungszeiten, Adresse, Menü, Bestellung, Reservierung), dann fragen womit du helfen kannst. "
        "Maximal drei kurze Sätze. Sieze den Kunden.\n"
        "Adresse: Friedrich-Ebert-Allee 69, 53113 Bonn.\n"
        "Öffnungszeiten: Di-So 12:00-14:30 und 17:30-22:00, Montag Ruhetag.\n"
        "Keine Emotionsmarker wie (warm) oder (lächelnd).\n"
        "Erster Turn immer: [TOOL:ai_greeting]"
        + _SIE_RULE
    ),
    # A4: Added get_date_info, check_availability, verify_address for forced commits
    tools=["ai_greeting", "faq", "end_call", "get_weather",
           "get_date_info", "check_availability", "verify_address"],
)

MENU_BROWSE = ConversationNode(
    name="menu_browse",
    prompt=(
        "Du bist Sailly vom Restaurant DOBOO. Der Kunde fragt nach dem Menü.\n"
        "Bestellbar: Bibimbap, Bulgogi, Kimchi Jjigae, Tteokbokki, Japchae, Mandu, "
        "Tofu Jjigae, Tofu Bibimbap, Mochi-Eis.\n"
        "Rufe [TOOL:get_menu] auf falls noch nicht geschehen.\n"
        "Beantworte die Frage und frage ob der Kunde bestellen möchte. Maximal 2 Sätze."
        + _SIE_RULE
    ),
    # A4: Added get_date_info, end_call for forced commits
    tools=["ai_greeting", "get_menu", "faq", "get_date_info", "end_call"],
    prerequisites={"menu_fetched": "get_menu"},
)

ORDERING = ConversationNode(
    name="ordering",
    prompt=(
        "Du bist Sailly vom Restaurant DOBOO. Der Kunde möchte bestellen.\n"
        "Bestellbar: Bibimbap, Bulgogi, Kimchi Jjigae, Tteokbokki, Japchae, Mandu, "
        "Tofu Jjigae, Tofu Bibimbap, Mochi-Eis.\n"
        "Erfrage: Gericht (nur von der Karte!) und Telefonnummer.\n"
        "Nicht auf der Karte? Höflich ablehnen, 2 Alternativen nennen.\n"
        "Wenn Gericht bekannt: Bestellung aufnehmen → [TOOL:create_order] → [TOOL:send_sms].\n"
        "Lieferzeit: ca. 30-60 Minuten. Maximal 2 Sätze."
        + _SIE_RULE
    ),
    # A4: Added get_date_info, check_availability, end_call for forced commits
    tools=["ai_greeting", "create_order", "send_sms", "get_menu",
           "verify_address", "get_date_info", "check_availability", "end_call"],
    prerequisites={"menu_fetched": "get_menu"},
)

RESERVATION = ConversationNode(
    name="reservation",
    prompt=(
        "Du bist Sailly vom Restaurant DOBOO. Der Kunde möchte reservieren.\n"
        "Erfrage: Datum, Uhrzeit, Personenzahl, Name.\n"
        "ZUERST [TOOL:check_availability] aufrufen, DANN Zusammenfassung geben.\n"
        "Sobald alle Daten vorliegen → [TOOL:create_reservation] (keine explizite Bestätigung nötig).\n"
        "Öffnungszeiten: Di-So 12:00-14:30 und 17:30-22:00. Montag Ruhetag.\n"
        "Mehr als 20 Personen → Bitte um Kontaktaufnahme per E-Mail.\n"
        "Maximal 2 Sätze."
        + _SIE_RULE
    ),
    # A4: Added verify_address, send_sms, end_call for forced commits
    tools=["check_availability", "create_reservation", "get_date_info",
           "get_weather", "verify_address", "send_sms", "end_call"],
)

ESCALATION = ConversationNode(
    name="escalation",
    prompt=(
        "Du bist Sailly vom Restaurant DOBOO. Der Kunde hat ein Problem.\n"
        "Technisch ('App kaputt', 'Fehler'): → [TOOL:technical_issues_callback].\n"
        "Beleidigung/Drohung: Einmal → [TOOL:transfer_to_tier2].\n"
        "Catering/Gruppen >20 Personen: → [TOOL:transfer_to_human].\n"
        "Rückrufwunsch: → [TOOL:request_callback].\n"
        "Bei Frustration: Empathie zeigen, Lösung anbieten. KEIN Transfer.\n"
        "Maximal 2 Sätze.\n"
        "ABSOLUT PFLICHT: Antworte NUR auf Deutsch. Niemals Englisch.\n"
        "Format: [TOOL:name] für alle Werkzeuge — kein anderes Format.\n"
        "Nach 2 Turns ohne Lösung: immer [TOOL:transfer_to_tier2] setzen."
        + _SIE_RULE
    ),
    # A4: Added request_callback, end_call
    tools=["technical_issues_callback", "transfer_to_tier2",
           "transfer_to_human", "request_callback", "end_call"],
)

FAQ = ConversationNode(
    name="faq",
    prompt=(
        "Du bist Sailly vom Restaurant DOBOO.\n"
        "Adresse: Friedrich-Ebert-Allee 69, 53113 Bonn (Eingang Adalbert-Stifter-Straße).\n"
        "Öffnungszeiten: Mo-Do 11:30-21:30, Fr 11:30-14:00 & 18:00-21:30, Sa 18:00-21:30, So geschlossen.\n"
        "Lieferzeit: ca. 30-60 Minuten.\n"
        "Beantworte kurz und frage ob du noch helfen kannst. Maximal 2 Sätze."
        + _SIE_RULE
    ),
    # A4: Added check_availability, create_order, send_sms, request_callback
    tools=["ai_greeting", "faq", "end_call", "get_weather",
           "get_date_info", "verify_address", "check_availability",
           "create_order", "send_sms", "request_callback"],
)

GOODBYE = ConversationNode(
    name="goodbye",
    prompt=(
        "Du bist Sailly vom Restaurant DOBOO.\n"
        "'Vielen Dank für Ihren Anruf bei DOBOO! Auf Wiedersehen.'\n"
        "Rufe [TOOL:end_call] auf."
        + _SIE_RULE
    ),
    # A4: Added send_sms for post-order/reservation confirmation SMS
    tools=["end_call", "send_sms"],
)

ALL_NODES: Dict[str, ConversationNode] = {
    "greeting": GREETING,
    "menu_browse": MENU_BROWSE,
    "ordering": ORDERING,
    "reservation": RESERVATION,
    "escalation": ESCALATION,
    "faq": FAQ,
    "goodbye": GOODBYE,
}
