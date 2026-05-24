"""
conversation_nodes.py — compatibility shim (Phase 3 Stream 1)

The canonical node definitions now live in server/brain/layer1/nodes/.
This module re-exports everything that existing callers depend on so that no
import changes are required outside of node_manager.py.

Retained exports:
  ConversationNode    — alias for the new Node dataclass
  ALL_NODES           — Dict[str, Node] keyed by NodeId.value strings
  GREETING, ORDERING, RESERVATION, … — individual node constants
  build_nodes()       — kept for tenant parameterisation (tenant=None → ALL_NODES copy)

The shared prompt constants (_PERSONA, _SIE_RULE, …) are now canonical in
server/brain/layer1/nodes/_prompts.py; they are re-exported here for any code
that still does `from conversation_nodes import _PERSONA`.
"""

from __future__ import annotations

from typing import Dict, Optional

# ── Registry ──────────────────────────────────────────────────────────────────
from server.brain.layer1.nodes import REGISTRY, NodeId  # noqa: F401
from server.brain.layer1.nodes.base import Node, NodePrerequisite  # noqa: F401

# ── Backward-compat type alias ────────────────────────────────────────────────
# Old code that does `node: ConversationNode` continues to work.
ConversationNode = Node

# ── Individual node constants ─────────────────────────────────────────────────
GREETING = REGISTRY[NodeId.GREETING]
CONFIRMATION = REGISTRY[NodeId.CONFIRMATION]
ERROR_RECOVERY = REGISTRY[NodeId.ERROR_RECOVERY]
GOODBYE = REGISTRY[NodeId.GOODBYE]
MENU_BROWSE = REGISTRY[NodeId.MENU_BROWSE]
FAQ = REGISTRY[NodeId.FAQ]
DIETARY_INQUIRY = REGISTRY[NodeId.DIETARY_INQUIRY_NODE]
ORDERING = REGISTRY[NodeId.ORDERING]
RESERVATION = REGISTRY[NodeId.RESERVATION]
PRE_ORDER = REGISTRY[NodeId.PRE_ORDER_CONFIRM]
ORDER_LOOKUP = REGISTRY[NodeId.ORDER_LOOKUP]
MODIFY_ORDER = REGISTRY[NodeId.MODIFY_ORDER_NODE]
CANCEL_ORDER = REGISTRY[NodeId.CANCEL_ORDER_NODE]
ORDER_STATUS = REGISTRY[NodeId.ORDER_STATUS_NODE]
MODIFY_RESERVATION = REGISTRY[NodeId.MODIFY_RESERVATION_NODE]
CANCEL_RESERVATION = REGISTRY[NodeId.CANCEL_RESERVATION_NODE]
COMPLAINT = REGISTRY[NodeId.COMPLAINT_NODE]
PAYMENT_ISSUE = REGISTRY[NodeId.PAYMENT_ISSUE_NODE]
LOST_AND_FOUND = REGISTRY[NodeId.LOST_AND_FOUND_NODE]
GROUP_CATERING = REGISTRY[NodeId.GROUP_CATERING_NODE]
ESCALATION = REGISTRY[NodeId.ESCALATION]

# ── ALL_NODES dict (keyed by NodeId.value strings for backward compat) ────────
ALL_NODES: Dict[str, Node] = {
    node_id.value: node for node_id, node in REGISTRY.items()
}

# ── Shared prompt constants (re-exported from _prompts) ───────────────────────
from server.brain.layer1.nodes._prompts import (  # noqa: E402, F401
    PERSONA as _PERSONA,
    SIE_RULE as _SIE_RULE,
    NO_GREETING_RULE as _NO_GREETING_RULE,
    PLAIN_TEXT_RULE as _PLAIN_TEXT_RULE,
    WORD_CAP_RULE as _WORD_CAP_RULE,
    OFF_TOPIC_RULE as _OFF_TOPIC_RULE,
    CONFIRM_DATA_RULE as _CONFIRM_DATA_RULE,
)

# ── build_nodes() ─────────────────────────────────────────────────────────────

def build_nodes(tenant=None) -> Dict[str, Node]:
    """
    Return a dict of conversation nodes parameterised by tenant configuration.

    When tenant is None → returns a copy of ALL_NODES (the DOBOO defaults).
    When tenant is provided → builds tenant-specific node instances.

    NOTE: The tenant-specific path still uses inline ConversationNode instances
    for now; it will be migrated to the registry in a future PR.
    """
    if tenant is None:
        return dict(ALL_NODES)

    # ── Tenant-parameterised builds (legacy path, kept verbatim) ────────────
    from dataclasses import dataclass, field as dc_field
    from typing import List

    @dataclass
    class _LegacyNode:
        """Thin stand-in that provides the same interface as Node for tenant builds."""
        name: str
        prompt: str
        tools: List[str]
        prerequisites: dict = dc_field(default_factory=dict)

        # Provide the interface Node exposes so NodeManager.select_node works
        @property
        def id(self):
            from server.brain.layer1.nodes.base import NodeId
            try:
                return NodeId(self.name)
            except ValueError:
                return self.name

    agent_name = tenant.agent_name
    business_name = tenant.practice.name
    city = tenant.city
    address = tenant.practice.location
    hours_formatted = (
        tenant.hours_formatted
        or (tenant.practice.hours if tenant.practice.hours else "Mo–Do 11:30–21:30, Fr 11:30–14:00 & 18:00–21:30, Sa 18:00–21:30, So geschlossen")
    )
    items_str = (
        ", ".join(tenant.items) if tenant.items
        else "Bibimbap, Bulgogi, Kimchi Jjigae, Tteokbokki, Japchae, Mandu, Tofu Jjigae, Tofu Bibimbap, Mochi-Eis"
    )
    industry = (
        ", ".join(tenant.practice.specializations)
        if tenant.practice.specializations
        else "koreanische Küche"
    )
    formality_rule = tenant.formality_rule

    base_tools_greeting = [
        "ai_greeting", "faq", "check_availability", "end_call",
        "get_weather", "get_date_info", "get_directions", "get_nearby_parking",
        "verify_address", "create_reservation", "send_sms",
        "create_order", "get_menu", "transfer_to_tier2", "technical_issues_callback",
        "request_callback", "transfer_to_human", "get_restaurant_info",
    ]
    base_tools_menu = [
        "ai_greeting", "get_menu", "faq", "get_date_info", "end_call",
        "check_availability", "verify_address", "create_order", "create_reservation",
        "send_sms", "get_weather", "get_directions", "get_nearby_parking",
        "transfer_to_tier2", "technical_issues_callback",
        "request_callback", "transfer_to_human", "get_restaurant_info",
    ]
    base_tools_ordering = [
        "ai_greeting", "create_order", "send_sms", "get_menu", "verify_address",
        "get_date_info", "check_availability", "end_call",
        "create_reservation", "faq", "get_weather", "get_directions", "get_nearby_parking",
        "transfer_to_tier2", "technical_issues_callback",
        "request_callback", "transfer_to_human", "get_restaurant_info",
    ]
    base_tools_reservation = [
        "ai_greeting", "check_availability", "create_reservation", "get_date_info",
        "get_weather", "get_directions", "get_nearby_parking",
        "verify_address", "send_sms", "faq", "end_call", "create_order",
        "get_menu", "transfer_to_tier2", "technical_issues_callback",
        "request_callback", "transfer_to_human", "get_restaurant_info",
    ]
    base_tools_escalation = [
        "technical_issues_callback", "transfer_to_tier2",
        "transfer_to_human", "request_callback", "end_call",
        "create_order", "create_reservation",
        "get_menu", "get_date_info", "check_availability",
        "get_weather", "get_directions", "get_nearby_parking",
        "faq", "send_sms", "ai_greeting", "get_restaurant_info",
    ]
    base_tools_faq = [
        "ai_greeting", "faq", "end_call", "get_weather", "get_menu",
        "get_date_info", "get_directions", "get_nearby_parking", "check_availability",
        "create_order", "send_sms", "request_callback", "create_reservation",
        "transfer_to_tier2", "technical_issues_callback", "transfer_to_human", "get_restaurant_info",
    ]
    base_tools_goodbye = [
        "end_call", "send_sms", "create_order", "create_reservation",
        "ai_greeting", "get_menu", "verify_address", "faq", "get_date_info",
        "check_availability", "get_weather", "get_directions", "get_nearby_parking",
        "transfer_to_tier2", "technical_issues_callback",
        "request_callback", "transfer_to_human", "get_restaurant_info",
    ]

    greeting = _LegacyNode(
        name="greeting",
        prompt=(
            _PERSONA
            + f"Du bist {agent_name}, die KI-Assistentin vom {business_name} in {city} ({industry}).\n"
            f"Die automatische Begrüßung wurde bereits abgespielt. Beantworte direkt die Frage des Anrufers. Maximal 1 Satz.\n"
            f"Adresse: {address}.\n"
            f"Öffnungszeiten: {hours_formatted}.\n"
            f"Keine Emotionsmarker wie (warm) oder (lächelnd).\n"
            f"Erster Turn immer: [TOOL:ai_greeting]"
            + _NO_GREETING_RULE
            + formality_rule
            + _PLAIN_TEXT_RULE
            + _WORD_CAP_RULE
            + _OFF_TOPIC_RULE
        ),
        tools=base_tools_greeting,
    )

    menu_browse = _LegacyNode(
        name="menu_browse",
        prompt=(
            _PERSONA
            + f"WICHTIG: Du hast den Anrufer BEREITS begrüßt. "
            f"BEGINNE DEINE ANTWORT NICHT MIT EINER BEGRÜSSUNG. "
            f"Verboten: 'Guten Tag', 'Hallo', 'Herzlich willkommen', 'Willkommen', 'Schön dass Sie anrufen', 'Ich bin {agent_name}'. "
            f"Antworte sofort und direkt auf die Aussage oder Frage des Anrufers.\n"
            f"Du bist {agent_name} vom {business_name}. Der Kunde fragt nach dem Menü.\n"
            f"Bestellbar: {items_str}.\n"
            f"Rufe [TOOL:get_menu] auf falls noch nicht geschehen.\n"
            f"Beantworte die Frage und frage ob der Kunde bestellen möchte."
            + formality_rule
            + _PLAIN_TEXT_RULE
            + _WORD_CAP_RULE
            + _OFF_TOPIC_RULE
        ),
        tools=base_tools_menu,
        prerequisites={"menu_fetched": "get_menu"},
    )

    ordering = _LegacyNode(
        name="ordering",
        prompt=(
            _PERSONA
            + f"Du bist {agent_name} vom {business_name}. Der Kunde möchte bestellen.\n"
            f"Bestellbar: {items_str}.\n"
            + formality_rule
            + _PLAIN_TEXT_RULE
            + _WORD_CAP_RULE
            + _OFF_TOPIC_RULE
            + _CONFIRM_DATA_RULE
        ),
        tools=base_tools_ordering,
    )

    reservation = _LegacyNode(
        name="reservation",
        prompt=(
            _PERSONA
            + f"Du bist {agent_name} vom {business_name}. Der Kunde möchte reservieren.\n"
            f"Erfrage nacheinander (nicht alles auf einmal): 1) Datum 2) Uhrzeit 3) Personenzahl 4) Name.\n"
            f"Prüfe Verfügbarkeit mit [TOOL:check_availability] sobald Datum+Uhrzeit bekannt.\n"
            f"Sobald alle 4 Angaben vorliegen: [TOOL:create_reservation] aufrufen.\n"
            f"Öffnungszeiten: {hours_formatted}.\n"
            + formality_rule
            + _PLAIN_TEXT_RULE
            + _WORD_CAP_RULE
            + _OFF_TOPIC_RULE
            + _CONFIRM_DATA_RULE
        ),
        tools=base_tools_reservation,
    )

    escalation = _LegacyNode(
        name="escalation",
        prompt=(
            _PERSONA
            + f"Du bist {agent_name} vom {business_name}. Der Kunde hat ein Problem.\n"
            f"Technisch: → [TOOL:technical_issues_callback].\n"
            f"Beleidigung: → [TOOL:transfer_to_tier2].\n"
            f"Catering/Gruppen >20: → [TOOL:transfer_to_human].\n"
            f"Rückruf: → [TOOL:request_callback].\n"
            + formality_rule
            + _PLAIN_TEXT_RULE
            + _WORD_CAP_RULE
        ),
        tools=base_tools_escalation,
        prerequisites={"menu_fetched": "get_menu"},
    )

    faq = _LegacyNode(
        name="faq",
        prompt=(
            _PERSONA
            + f"Du bist {agent_name} vom {business_name}.\n"
            f"Adresse: {address}.\n"
            f"Öffnungszeiten: {hours_formatted}.\n"
            f"Lieferzeit: ca. 30-60 Minuten.\n"
            f"Beantworte kurz und frage ob du noch helfen kannst."
            + formality_rule
            + _PLAIN_TEXT_RULE
            + _WORD_CAP_RULE
            + _OFF_TOPIC_RULE
        ),
        tools=base_tools_faq,
    )

    goodbye = _LegacyNode(
        name="goodbye",
        prompt=(
            _PERSONA
            + f"Du bist {agent_name} vom {business_name}.\n"
            f"'Vielen Dank für Ihren Anruf bei {business_name}! Auf Wiedersehen.'\n"
            f"Rufe [TOOL:end_call] auf."
            + formality_rule
            + _PLAIN_TEXT_RULE
            + _WORD_CAP_RULE
        ),
        tools=base_tools_goodbye,
    )

    return {
        "greeting": greeting,
        "menu_browse": menu_browse,
        "ordering": ordering,
        "reservation": reservation,
        "escalation": escalation,
        "faq": faq,
        "goodbye": goodbye,
    }
