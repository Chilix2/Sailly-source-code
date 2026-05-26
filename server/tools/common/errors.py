"""
Tool result contract — Phase 6.

All handlers return a ToolResult. The executor bridge converts it to the
legacy dict format that executor.py callers expect.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolResult:
    """
    Canonical return type for every Phase 6 tool handler.

    ok=True  → data carries the success payload.
    ok=False → error carries a short machine-readable reason string;
               data may carry additional context (e.g. requires_human, alternatives).

    Phase 9 B1: `error_code` carries a structured ERR_* code from
    server.tools.common.error_codes.ErrorCode on failure paths.  The
    dispatcher collects codes across all tool calls and writes them to
    google_turn_metrics.error_codes for dashboard queries.
    """
    ok: bool
    data: dict = field(default_factory=dict)
    error: Optional[str] = None
    error_code: Optional[str] = None   # Phase 9 B1 — ERR_* taxonomy code

    def to_legacy_dict(self) -> dict:
        """Convert to the dict format executor.py callers expect.

        On failure, injects ``_error_code`` so the turn processor can collect
        ERR_* codes for google_turn_metrics.error_codes (Phase 9 B1).
        """
        if self.ok:
            return {"success": True, **self.data}
        base = {"success": False, "error": self.error, **self.data}
        if self.error_code:
            base["_error_code"] = self.error_code
        return base
