"""
Core types for the node graph.

Node     — immutable data describing a conversation state (prompt + tool whitelist).
NodeId   — canonical string-valued enum; values match the old node name strings so
           check_forced_commits conditions like `node_name == "ordering"` continue to work.
NodePrerequisite — a single prerequisite that must be satisfied before the node runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from server.brain.conversation_state import ConversationState


class NodeId(str, Enum):
    GREETING = "greeting"
    CONFIRMATION = "confirmation"          # multi-intent readback gate
    ERROR_RECOVERY = "error_recovery"      # tool failure recovery
    GOODBYE = "goodbye"
    MENU_BROWSE = "menu_browse"
    FAQ = "faq"
    DIETARY_INQUIRY_NODE = "dietary_inquiry"
    ORDERING = "ordering"
    RESERVATION = "reservation"
    PRE_ORDER_CONFIRM = "pre_order"        # after-hours scheduled order (maps to old "pre_order" name)
    ORDER_LOOKUP = "order_lookup"          # anchor capture before modify/cancel/status
    MODIFY_ORDER_NODE = "modify_order"
    CANCEL_ORDER_NODE = "cancel_order"
    ORDER_STATUS_NODE = "order_status"
    MODIFY_RESERVATION_NODE = "modify_reservation"
    CANCEL_RESERVATION_NODE = "cancel_reservation"
    COMPLAINT_NODE = "complaint"
    PAYMENT_ISSUE_NODE = "payment_issue"
    LOST_AND_FOUND_NODE = "lost_and_found"
    GROUP_CATERING_NODE = "group_catering"
    ESCALATION = "escalation"


@dataclass(frozen=True)
class NodePrerequisite:
    """
    A prerequisite tool that must run before the node's LLM prompt.

    state_check(state) returns True when the prerequisite has NOT yet been
    satisfied — i.e., the tool should fire this turn.
    """
    tool_name: str
    state_check: Callable  # (ConversationState) -> bool


# Common prerequisites shared by multiple nodes
MENU_FETCHED_PREREQ = NodePrerequisite(
    tool_name="get_menu",
    state_check=lambda s: not getattr(s, "menu_fetched", False),
)


@dataclass(frozen=True)
class Node:
    """
    Immutable descriptor of a single conversation state.

    prompt  — injected verbatim into MemoryManager; supports {tenant_name} etc.
    tools   — frozenset; only these tools are available in this node.
    prerequisites — tuple of NodePrerequisite; checked at start of each turn.
    description   — human-readable summary for docs/debugging.
    """
    id: NodeId
    prompt: str
    tools: frozenset
    prerequisites: tuple = field(default_factory=tuple)
    description: str = ""

    @property
    def name(self) -> str:
        """Backward-compat accessor — equals id.value (the old ConversationNode.name)."""
        return self.id.value

    def validate(self) -> None:
        lines = [ln for ln in self.prompt.strip().splitlines() if ln.strip()]
        if len(lines) < 3:
            raise ValueError(
                f"Node {self.id}: prompt must have >= 3 non-empty lines, got {len(lines)}"
            )
        # Upper bound (12 lines) is aspirational; not enforced hard during migration
        if not self.tools:
            raise ValueError(f"Node {self.id}: tool whitelist must not be empty")
