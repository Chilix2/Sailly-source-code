"""
Slim NodeManager — Layer 1 node selection using CapturedIntent state.

This module provides a clean, ~150-line NodeManager that uses the typed
NodeId→Node registry and the CapturedIntent model.  It replaces the
keyword-based giant in server/brain/node_manager.py for node selection;
check_forced_commits stays on the legacy class (Stream 2).

Public API:
    NodeManager.select_node(state, user_text) -> Node
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from server.brain.layer1.nodes import REGISTRY, NodeId
from server.brain.layer1.nodes.base import Node

if TYPE_CHECKING:
    from server.brain.conversation_state import ConversationState

# ── IntentKind → NodeId authoritative mapping ─────────────────────────────────
# Imported lazily inside _pick_node_id to avoid circular imports at module load.
def _intent_kind_to_node_id_map():
    from server.brain.captured_intents import IntentKind
    return {
        IntentKind.TAKEAWAY:              NodeId.ORDERING,
        IntentKind.DELIVERY:              NodeId.ORDERING,
        IntentKind.BULK_ORDER:            NodeId.ORDERING,
        IntentKind.PRE_ORDER:             NodeId.PRE_ORDER_CONFIRM,
        IntentKind.RESERVATION:           NodeId.RESERVATION,
        IntentKind.MODIFY_ORDER:          NodeId.MODIFY_ORDER_NODE,
        IntentKind.CANCEL_ORDER:          NodeId.CANCEL_ORDER_NODE,
        IntentKind.ORDER_STATUS:          NodeId.ORDER_STATUS_NODE,
        IntentKind.MODIFY_RESERVATION:    NodeId.MODIFY_RESERVATION_NODE,
        IntentKind.CANCEL_RESERVATION:    NodeId.CANCEL_RESERVATION_NODE,
        IntentKind.COMPLAINT:             NodeId.COMPLAINT_NODE,
        IntentKind.PAYMENT_ISSUE:         NodeId.PAYMENT_ISSUE_NODE,
        IntentKind.LOST_AND_FOUND:        NodeId.LOST_AND_FOUND_NODE,
        IntentKind.GROUP_CATERING:        NodeId.GROUP_CATERING_NODE,
        IntentKind.DIETARY_INQUIRY:       NodeId.DIETARY_INQUIRY_NODE,
        IntentKind.FAQ:                   NodeId.FAQ,
    }


# Intent kinds that require an anchor identifier before proceeding
_ANCHOR_REQUIRED_FOR: frozenset = frozenset()  # populated lazily

def _anchor_required_kinds():
    from server.brain.captured_intents import IntentKind
    return frozenset({
        IntentKind.MODIFY_ORDER,
        IntentKind.CANCEL_ORDER,
        IntentKind.ORDER_STATUS,
        IntentKind.MODIFY_RESERVATION,
        IntentKind.CANCEL_RESERVATION,
    })


class NodeManager:
    """
    Slim node selector.  Knows nothing about keywords, tool names, or
    check_forced_commits — those stay on the legacy NodeManager.
    """

    def select_node(self, state: "ConversationState", user_text: str) -> Node:
        """Return the Node appropriate for the current conversation state."""
        node_id = self._pick_node_id(state)
        return REGISTRY[node_id]

    # ── Confirmation response handler (Phase 4 C1) ────────────────────────────

    def handle_confirmation_response(self, state: "ConversationState") -> str:
        """
        Read the confirmation_response slot written by the CONFIRMATION node and
        perform one of three state transitions.

        Returns a string describing the action taken (for logging/tracing).
        """
        last_extraction = getattr(state, "last_extraction", {}) or {}
        response = last_extraction.get("confirmation_response", "")

        if not response:
            return "no_confirmation_response_yet"

        try:
            from server.brain.captured_intents import IntentStatus, transition_intent
        except ImportError:
            return "import_error"

        ci = getattr(state, "captured_intents", []) or []

        if response == "confirm_all":
            # All intents confirmed — mark them CONFIRMED and proceed from idx 0
            for intent in ci:
                if intent.status == IntentStatus.CAPTURED:
                    try:
                        transition_intent(intent, IntentStatus.CONFIRMED)
                    except Exception:
                        intent.status = IntentStatus.CONFIRMED
            state.current_intent_idx = 0
            # Clear the slot so we don't loop
            if hasattr(state, "last_extraction") and isinstance(state.last_extraction, dict):
                state.last_extraction.pop("confirmation_response", None)
            return "confirm_all"

        elif response == "restart_all":
            # Caller wants to restart — clear all intents and go to greeting
            state.captured_intents = []
            state.current_intent_idx = None
            if hasattr(state, "last_extraction") and isinstance(state.last_extraction, dict):
                state.last_extraction.pop("confirmation_response", None)
            return "restart_all"

        elif response == "correct_specific":
            # Caller wants to correct one item — stay in CONFIRMATION and
            # rely on the extractor next turn to overwrite the specific slot.
            # Clear the slot so we prompt again.
            if hasattr(state, "last_extraction") and isinstance(state.last_extraction, dict):
                state.last_extraction.pop("confirmation_response", None)
            return "correct_specific"

        return f"unknown_response:{response}"

    # ── Private helpers ────────────────────────────────────────────────────────

    def _pick_node_id(self, state: "ConversationState") -> NodeId:
        # End-of-call fast path
        if getattr(state, "call_ended", False):
            return NodeId.GOODBYE

        ci = getattr(state, "captured_intents", None) or []
        idx = getattr(state, "current_intent_idx", None)

        # No intents captured via the v4 path → check legacy intent flags before
        # falling back to greeting, so the legacy reservation/order path transitions
        # out of greeting correctly.
        if not ci or idx is None:
            if getattr(state, "reservation_intent", False) and not getattr(state, "reservation_created", False):
                return NodeId.RESERVATION
            if getattr(state, "order_intent", False) and not getattr(state, "order_created", False):
                return NodeId.ORDERING
            return NodeId.GREETING

        try:
            from server.brain.captured_intents import sort_by_priority, IntentStatus
        except ImportError:
            return NodeId.GREETING

        sorted_intents = sort_by_priority(ci)
        if idx >= len(sorted_intents):
            return NodeId.GREETING

        current = sorted_intents[idx]

        # Multi-intent readback gate: confirm all intents before acting
        if len(ci) > 1 and current.status == IntentStatus.CAPTURED:
            return NodeId.CONFIRMATION

        # Anchor lookup: existing-transaction ops need an identifier first
        anchor_kinds = _anchor_required_kinds()
        if current.kind in anchor_kinds:
            anchor_slot = (
                "order_identifier"
                if "order" in current.kind.value
                else "reservation_identifier"
            )
            slots = getattr(current, "slots", {}) or {}
            if slots.get(anchor_slot) is None:
                return NodeId.ORDER_LOOKUP

        # Primary routing table
        mapping = _intent_kind_to_node_id_map()
        return mapping.get(current.kind, NodeId.GREETING)
