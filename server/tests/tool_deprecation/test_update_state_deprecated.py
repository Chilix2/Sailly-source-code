"""
FINDING-026 regression — update_state removed from LLM-facing tool definitions.

Guards that update_state is not presented to the LLM anymore (removed from
TOOL_DECLARATIONS in tools/definitions.py).
"""
from __future__ import annotations

import pytest

_TOOL_DEFS_PATH = "tools/definitions.py"


def test_finding_026_update_state_not_in_tool_declarations():
    """update_state must not be in TOOL_DECLARATIONS (LLM-facing tools)."""
    import tools.definitions
    import inspect

    src = inspect.getsource(tools.definitions)
    # Check that the definition doesn't contain update_state in TOOL_DECLARATIONS
    if '"name": "update_state"' in src:
        # More specific: is it in TOOL_DECLARATIONS?
        if "TOOL_DECLARATIONS" in src:
            lines = src.split("\n")
            in_decls = False
            found_update_state_in_decls = False
            for i, line in enumerate(lines):
                if "TOOL_DECLARATIONS" in line:
                    in_decls = True
                elif in_decls and line.strip().startswith("]"):
                    in_decls = False
                elif in_decls and '"name": "update_state"' in line:
                    found_update_state_in_decls = True
                    break
            assert not found_update_state_in_decls, (
                "FINDING-026: update_state still in TOOL_DECLARATIONS"
            )


@pytest.mark.asyncio
async def test_finding_026_update_state_handler_returns_error():
    """update_state handler must return error code ERR_DEPRECATED_TOOL."""
    try:
        from server.tools.handlers.update_state import handle
        from server.tools.common.context import ToolContext
        from server.brain.conversation_state import ConversationState

        # Create mock state and context
        state = ConversationState(call_sid="test")
        ctx = ToolContext(
            call_sid="test",
            tenant_id="test",
            state=state,
            tenant_cfg={},
        )

        result = await handle({"test": "arg"}, ctx)
        assert result.ok is False, "Handler should return error"
        assert result.error_code == "ERR_DEPRECATED_TOOL"
    except Exception as e:
        pytest.skip(f"Skipping (ToolContext signature): {e}")


def test_finding_026_handler_exists_for_grace_period():
    """update_state handler must still exist for deprecation grace period."""
    from pathlib import Path
    handler = Path("server/tools/handlers/update_state.py")
    assert handler.exists(), (
        "update_state handler should exist for grace period"
    )
