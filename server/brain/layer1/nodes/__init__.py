"""
Node registry — single source of truth for all conversation nodes.

Import from here:
    from server.brain.layer1.nodes import REGISTRY, NodeId

All 21 nodes are validated at import time; a bad node definition crashes startup,
which is the intended behaviour (fail fast, not at runtime).
"""

from typing import Dict

from server.brain.layer1.nodes.base import Node, NodeId, NodePrerequisite, MENU_FETCHED_PREREQ  # noqa: F401

# --- individual node imports ---
from server.brain.layer1.nodes.greeting import GREETING
from server.brain.layer1.nodes.confirmation import CONFIRMATION
from server.brain.layer1.nodes.error_recovery import ERROR_RECOVERY
from server.brain.layer1.nodes.goodbye import GOODBYE
from server.brain.layer1.nodes.menu_browse import MENU_BROWSE
from server.brain.layer1.nodes.faq import FAQ
from server.brain.layer1.nodes.dietary_inquiry import DIETARY_INQUIRY
from server.brain.layer1.nodes.ordering import ORDERING
from server.brain.layer1.nodes.reservation import RESERVATION
from server.brain.layer1.nodes.pre_order_confirm import PRE_ORDER_CONFIRM
from server.brain.layer1.nodes.order_lookup import ORDER_LOOKUP
from server.brain.layer1.nodes.modify_order import MODIFY_ORDER
from server.brain.layer1.nodes.cancel_order import CANCEL_ORDER
from server.brain.layer1.nodes.order_status import ORDER_STATUS
from server.brain.layer1.nodes.modify_reservation import MODIFY_RESERVATION
from server.brain.layer1.nodes.cancel_reservation import CANCEL_RESERVATION
from server.brain.layer1.nodes.complaint import COMPLAINT
from server.brain.layer1.nodes.payment_issue import PAYMENT_ISSUE
from server.brain.layer1.nodes.lost_and_found import LOST_AND_FOUND
from server.brain.layer1.nodes.group_catering import GROUP_CATERING
from server.brain.layer1.nodes.escalation import ESCALATION

REGISTRY: Dict[NodeId, Node] = {
    NodeId.GREETING: GREETING,
    NodeId.CONFIRMATION: CONFIRMATION,
    NodeId.ERROR_RECOVERY: ERROR_RECOVERY,
    NodeId.GOODBYE: GOODBYE,
    NodeId.MENU_BROWSE: MENU_BROWSE,
    NodeId.FAQ: FAQ,
    NodeId.DIETARY_INQUIRY_NODE: DIETARY_INQUIRY,
    NodeId.ORDERING: ORDERING,
    NodeId.RESERVATION: RESERVATION,
    NodeId.PRE_ORDER_CONFIRM: PRE_ORDER_CONFIRM,
    NodeId.ORDER_LOOKUP: ORDER_LOOKUP,
    NodeId.MODIFY_ORDER_NODE: MODIFY_ORDER,
    NodeId.CANCEL_ORDER_NODE: CANCEL_ORDER,
    NodeId.ORDER_STATUS_NODE: ORDER_STATUS,
    NodeId.MODIFY_RESERVATION_NODE: MODIFY_RESERVATION,
    NodeId.CANCEL_RESERVATION_NODE: CANCEL_RESERVATION,
    NodeId.COMPLAINT_NODE: COMPLAINT,
    NodeId.PAYMENT_ISSUE_NODE: PAYMENT_ISSUE,
    NodeId.LOST_AND_FOUND_NODE: LOST_AND_FOUND,
    NodeId.GROUP_CATERING_NODE: GROUP_CATERING,
    NodeId.ESCALATION: ESCALATION,
}

# --- import-time validation ---
_seen_values: set = set()
for _node_id, _node in REGISTRY.items():
    assert _node_id.value not in _seen_values, (
        f"Duplicate NodeId value: {_node_id.value!r}"
    )
    _seen_values.add(_node_id.value)
    _node.validate()

assert len(REGISTRY) == 21, (
    f"REGISTRY must have exactly 21 nodes, got {len(REGISTRY)}"
)

del _seen_values, _node_id, _node
