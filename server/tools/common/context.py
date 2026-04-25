"""
ToolContext — per-call context passed to every Phase 6 handler.

Encapsulates the call_sid, tenant configuration, and live ConversationState
so handlers don't need to import globals or call load-functions themselves.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

BERLIN_TZ = ZoneInfo("Europe/Berlin")


@dataclass
class ToolContext:
    """
    Read-only context for tool handlers.

    Built by the executor bridge before dispatching each tool call.
    Handlers should treat all fields as read-only — mutations go through
    state directly when necessary.
    """
    call_sid: str
    tenant_id: str
    tenant_cfg: dict  # raw tenant YAML as dict
    state: Any        # ConversationState — typed as Any to avoid circular import

    def now(self) -> datetime:
        """Current time in Berlin timezone."""
        return datetime.now(BERLIN_TZ)

    def get_tenant_value(self, *keys: str, default: Any = None) -> Any:
        """Safely traverse nested tenant_cfg by dot-path keys."""
        node = self.tenant_cfg
        for key in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(key, default)
        return node
