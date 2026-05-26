"""Session restore helpers shared by the live v4 turn processor.

The production reconnect path only needs ConversationState serialization. Keep
that helper separate from the retired ADK processor so importing v4 no longer
loads the legacy ADK stack.
"""

from __future__ import annotations

from server.brain.conversation_state import ConversationState


def conversation_state_from_dict(data: dict) -> ConversationState:
    """Deserialize ConversationState from a Redis-stored dict."""
    return ConversationState.from_dict(data or {})


def conversation_state_to_dict(state: ConversationState) -> dict:
    """Serialize ConversationState to a plain dict for Redis storage."""
    return state.to_dict()
