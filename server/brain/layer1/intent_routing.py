"""
Layer 1 — Intent → ConversationNode routing table.

Maps each IntentKind to the canonical conversation node name
that handles it. Used by the orchestrator to switch nodes on
first capture of an intent.

Philosophy: routing is code (not LLM). The LLM talks freely
WITHIN a node; the orchestrator decides BETWEEN nodes.
"""
from __future__ import annotations

from typing import Dict

from server.brain.captured_intents import IntentKind

# Maps IntentKind → conversation node name (key in ALL_NODES)
ROUTING: Dict[IntentKind, str] = {
    # Commerce — new transactions
    IntentKind.TAKEAWAY: "ordering",
    IntentKind.DELIVERY: "ordering",
    IntentKind.BULK_ORDER: "ordering",
    IntentKind.RESERVATION: "reservation",
    IntentKind.PRE_ORDER: "pre_order",

    # Commerce — existing transactions
    IntentKind.MODIFY_ORDER: "modify_order",
    IntentKind.CANCEL_ORDER: "cancel_order",
    IntentKind.ORDER_STATUS: "order_status",
    IntentKind.MODIFY_RESERVATION: "modify_reservation",
    IntentKind.CANCEL_RESERVATION: "cancel_reservation",

    # Service
    IntentKind.COMPLAINT: "complaint",
    IntentKind.PAYMENT_ISSUE: "payment_issue",
    IntentKind.LOST_AND_FOUND: "lost_and_found",
    IntentKind.DIETARY_INQUIRY: "dietary_inquiry",
    IntentKind.GROUP_CATERING: "group_catering",

    # Information
    IntentKind.FAQ: "faq",
}


def route_intent(kind: IntentKind) -> str:
    """Return the node name for a given IntentKind.

    Returns "escalation" if no mapping found (safe fallback).
    """
    return ROUTING.get(kind, "escalation")
