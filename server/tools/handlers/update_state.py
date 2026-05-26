"""
DEPRECATED — update_state tool.

Phase 6 decision:
  - tool-update-state: deprecate
    This tool was a generic state-modification escape hatch. Phase 3's
    structured writeback (state.tool_results) replaced it.

Handler logs every call as deprecated and returns a permissive response
so existing flows don't break. Removal target: Phase 8.

After 2 weeks of zero deprecation warnings in production logs,
delete this file and remove "update_state" from executor.py's handler dict.
"""
from __future__ import annotations

import logging

from server.tools.common.context import ToolContext
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "update_state"


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    logger.warning(
        "deprecated_update_state_call",
        extra={
            "args_keys": list(args.keys()),
            "call_sid": ctx.call_sid,
            "tenant_id": ctx.tenant_id,
        },
    )
    # Return error to indicate deprecation per FINDING-026
    return ToolResult(
        ok=False,
        error="update_state is deprecated (removed from LLM tool definitions)",
        error_code="ERR_DEPRECATED_TOOL",
        data={},
    )
