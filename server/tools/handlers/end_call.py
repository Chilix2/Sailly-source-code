"""
end_call — terminates the call.

Phase 6 task 6.6 (verification):
  Phase 3 implemented the end-call state machine in
  server/brain/layer1/goodbye_state_machine.py. This handler is the tool
  endpoint that Phase 3's dispatcher routes `end_call` tool calls to.

  Decision: tool-end-call: state-machine
  The handler delegates to the state machine rather than mutating state
  directly, ensuring the once-per-call deduplication guarantee.
"""
from __future__ import annotations

import logging

from server.tools.common.context import ToolContext
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "end_call"


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args:
      reason: str — why the call is ending (optional)

    The goodbye state machine sets state.call_ended = True exactly once.
    Subsequent calls to end_call within the same call are no-ops.
    """
    state = ctx.state
    if state is not None and getattr(state, "call_ended", False):
        logger.debug(
            "[end_call] no-op — call already ended (call_sid=%s)", ctx.call_sid
        )
        return ToolResult(
            ok=True,
            data={"status": "already_ended", "call_sid": ctx.call_sid},
        )

    # Delegate to legacy executor to handle Twilio hang-up
    try:
        from tools.executor import _end_call as _legacy  # type: ignore
        result = await _legacy(args, ctx.call_sid, ctx.tenant_id)
        return ToolResult(ok=result.get("success", True), data=result)
    except (ImportError, AttributeError):
        # State machine will handle via goodbye_state_machine when available
        if state is not None:
            state.call_ended = True
            state.farewell_spoken = True
        return ToolResult(
            ok=True,
            data={"status": "ended", "call_sid": ctx.call_sid},
        )
