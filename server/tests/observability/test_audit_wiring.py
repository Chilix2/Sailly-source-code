"""
PR-3 tests — write_audit_entry() wiring verification (FINDING-004).

Tests are structured at three levels:
  1. audit.py module unit tests (AUDITED_TOOLS shape, write_audit_entry no-op for
     non-audited tools, exception safety).
  2. execute_tool integration tests (mock the DB pool; verify audit is called /
     not called for audited vs. non-audited tools).
  3. Regression guard (wiring stays in executor.py source).

We mock the DB pool at the asyncpg level so no live DB is needed for CI.

Run with:
  cd /home/charles2/sailly-browser-demo
  source venv/bin/activate
  python -m pytest server/tests/observability/test_audit_wiring.py -v
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_AUDITED_TOOLS = frozenset({
    "create_order",
    "create_reservation",
    "modify_order",
    "cancel_order",
    "transfer_to_human",
})


def _mock_pool():
    """Return a mock asyncpg connection pool that swallows all queries."""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None)
    pool = AsyncMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(__aenter__=AsyncMock(return_value=conn),
                               __aexit__=AsyncMock(return_value=False))
    )
    return pool, conn


# ---------------------------------------------------------------------------
# 1. audit.py module — unit tests
# ---------------------------------------------------------------------------

def test_audited_tools_list_matches_phase8_plan():
    """Catch accidental removal from AUDITED_TOOLS."""
    from server.brain.observability.audit import AUDITED_TOOLS
    assert EXPECTED_AUDITED_TOOLS <= set(AUDITED_TOOLS), (
        f"Missing tools: {EXPECTED_AUDITED_TOOLS - set(AUDITED_TOOLS)}"
    )


@pytest.mark.asyncio
async def test_write_audit_entry_noop_for_non_audited_tool():
    """Non-audited tools are silently ignored; no DB call made."""
    pool, conn = _mock_pool()
    with patch("server.brain.observability.audit._get_pool", return_value=pool):
        from server.brain.observability.audit import write_audit_entry
        await write_audit_entry(
            call_sid="demo-test",
            tenant_id="doboo",
            tool_name="get_menu",   # NOT audited
            args={},
            result={},
            success=True,
        )
    conn.execute.assert_not_called()


@pytest.mark.asyncio
async def test_write_audit_entry_inserts_row_for_audited_tool():
    """Audited tool writes exactly one row to bot_tool_audit_log."""
    pool, conn = _mock_pool()
    with patch("server.brain.observability.audit._get_pool", return_value=pool):
        from server.brain.observability.audit import write_audit_entry
        await write_audit_entry(
            call_sid="demo-abc",
            tenant_id="doboo",
            tool_name="create_order",
            args={"items": [{"name": "Bibimbap", "quantity": 1}]},
            result={"order_id": "ORD-001", "success": True},
            success=True,
        )
    conn.execute.assert_called_once()
    call_sql = conn.execute.call_args[0][0]
    assert "bot_tool_audit_log" in call_sql, "Expected INSERT into bot_tool_audit_log"


@pytest.mark.asyncio
async def test_write_audit_entry_does_not_raise_on_db_error():
    """DB failures must NOT propagate — write_audit_entry must be fire-and-forget safe."""
    pool = AsyncMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(side_effect=Exception("connection refused")),
            __aexit__=AsyncMock(return_value=False),
        )
    )
    with patch("server.brain.observability.audit._get_pool", return_value=pool):
        from server.brain.observability.audit import write_audit_entry
        # Must not raise — exception must be swallowed and logged
        await write_audit_entry(
            call_sid="demo-x",
            tenant_id="doboo",
            tool_name="create_order",
            args={},
            result={},
            success=False,
        )


@pytest.mark.asyncio
async def test_write_audit_entry_records_failure_correctly():
    """success=False must be passed through to the DB INSERT."""
    pool, conn = _mock_pool()
    with patch("server.brain.observability.audit._get_pool", return_value=pool):
        from server.brain.observability.audit import write_audit_entry
        await write_audit_entry(
            call_sid="demo-fail",
            tenant_id="doboo",
            tool_name="transfer_to_human",
            args={"reason": "test"},
            result={"error": "transfer_failed"},
            success=False,
        )
    # conn.execute(SQL, call_sid, tenant_id, tool_name, args_json, result_json, success)
    # → positional[0]=SQL, [1]=call_sid, [2]=tenant_id, [3]=tool_name,
    #   [4]=args_json, [5]=result_json, [6]=success
    positional = conn.execute.call_args.args
    assert positional[6] is False, f"Expected success=False at index 6, got {positional[6]!r}"


# ---------------------------------------------------------------------------
# 2. execute_tool — integration tests with mocked audit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_tool_writes_audit_on_success_phase6_path():
    """Phase 6 handler path: create_order success → audit written.

    The GUARDIAN pre-commit gate is mocked to (True, None, []) so the Phase 6
    handler bridge is reached regardless of args completeness.
    """
    from server.tools.common.errors import ToolResult

    mock_handler = AsyncMock(return_value=ToolResult(ok=True, data={"order_id": "X"}))

    with patch("server.brain.observability.audit.write_audit_entry",
               new_callable=AsyncMock) as mock_audit, \
         patch("tools.executor._guardian_pre_commit_check",
               return_value=(True, None, [])), \
         patch("server.tools.handlers.ALL_HANDLERS",
               {"create_order": mock_handler}):
        from tools.executor import execute_tool
        result = await execute_tool(
            tool_name="create_order",
            args={"items": []},
            call_sid="demo-test",
            tenant_id="doboo",
        )

    mock_audit.assert_called_once()
    kw = mock_audit.call_args.kwargs
    assert kw["tool_name"] == "create_order"
    assert kw["success"] is True
    assert kw["call_sid"] == "demo-test"


@pytest.mark.asyncio
async def test_execute_tool_writes_audit_on_failure_phase6_path():
    """Phase 6 handler path: create_order failure → audit written with success=False."""
    from server.tools.common.errors import ToolResult

    mock_handler = AsyncMock(return_value=ToolResult(ok=False, error="slot_missing"))

    with patch("server.brain.observability.audit.write_audit_entry",
               new_callable=AsyncMock) as mock_audit, \
         patch("tools.executor._guardian_pre_commit_check",
               return_value=(True, None, [])), \
         patch("server.tools.handlers.ALL_HANDLERS",
               {"create_order": mock_handler}):
        from tools.executor import execute_tool
        await execute_tool(
            tool_name="create_order",
            args={},
            call_sid="demo-fail",
            tenant_id="doboo",
        )

    mock_audit.assert_called_once()
    kw = mock_audit.call_args.kwargs
    assert kw["success"] is False
    assert "error" in kw["result"]


@pytest.mark.asyncio
async def test_execute_tool_no_audit_for_non_audited_tool():
    """get_menu is not in AUDITED_TOOLS — no audit row should be written."""
    from server.tools.common.errors import ToolResult

    mock_handler = AsyncMock(return_value=ToolResult(ok=True, data={"menu": []}))

    with patch("server.brain.observability.audit.write_audit_entry",
               new_callable=AsyncMock) as mock_audit, \
         patch("tools.executor._guardian_pre_commit_check",
               return_value=(True, None, [])), \
         patch("server.tools.handlers.ALL_HANDLERS",
               {"get_menu": mock_handler}):
        from tools.executor import execute_tool
        await execute_tool(
            tool_name="get_menu",
            args={},
            call_sid="demo-test",
            tenant_id="doboo",
        )

    mock_audit.assert_not_called()


@pytest.mark.asyncio
async def test_execute_tool_returns_result_even_when_audit_fails():
    """Audit write failure must not affect the tool return value."""
    from server.tools.common.errors import ToolResult

    mock_handler = AsyncMock(return_value=ToolResult(ok=True, data={"order_id": "Y"}))

    with patch("server.brain.observability.audit.write_audit_entry",
               new_callable=AsyncMock, side_effect=Exception("DB down")), \
         patch("tools.executor._guardian_pre_commit_check",
               return_value=(True, None, [])), \
         patch("server.tools.handlers.ALL_HANDLERS",
               {"create_order": mock_handler}):
        from tools.executor import execute_tool
        result = await execute_tool(
            tool_name="create_order",
            args={},
            call_sid="demo-test",
            tenant_id="doboo",
        )

    # Tool result must still be returned despite audit failure
    assert result is not None
    # Phase 6 result contains the ToolResult.to_legacy_dict() output
    assert result.get("success") is True or "order_id" in result


# ---------------------------------------------------------------------------
# 3. Regression guard — wiring in executor.py source
# ---------------------------------------------------------------------------

def test_audit_wiring_present_in_executor():
    """Verify write_audit_entry is imported and called in tools/executor.py."""
    import os
    executor_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "tools", "executor.py"
    )
    src = open(os.path.abspath(executor_path), encoding="utf-8").read()
    assert "write_audit_entry" in src, "write_audit_entry not found in tools/executor.py"
    assert "AUDITED_TOOLS" in src, "AUDITED_TOOLS not referenced in tools/executor.py"


def test_audit_table_name_is_bot_tool_audit_log():
    """Verify audit.py targets bot_tool_audit_log, not the CRM audit_log."""
    import server.brain.observability.audit as audit_mod
    src = open(audit_mod.__file__, encoding="utf-8").read()
    assert "bot_tool_audit_log" in src, "Expected table name bot_tool_audit_log in audit.py"
    # The CRM table should not be the target
    assert "INSERT INTO audit_log" not in src, (
        "audit.py still targeting old 'audit_log' table — should use 'bot_tool_audit_log'"
    )
