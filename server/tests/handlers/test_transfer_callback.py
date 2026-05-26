"""
PR-8 Part B tests — DB-backed callback queue (FINDING-015).

Verifies that _schedule_callback writes to the `callback_queue` Postgres table
rather than an in-memory list, and handles DB failures cleanly.

Run with:
  cd /home/charles2/sailly-browser-demo
  source venv/bin/activate
  python -m pytest server/tests/handlers/test_transfer_callback.py -v
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.tools.common.errors import ToolResult


def _make_ctx(call_sid: str = "CA_test", tenant_id: str = "t1") -> MagicMock:
    state = MagicMock()
    # Provide a phone via shared_slots
    phone_slot = MagicMock()
    phone_slot.value = "+4917912345678"
    state.shared_slots = {"phone": phone_slot}
    state.recent_responses = []

    ctx = MagicMock()
    ctx.call_sid = call_sid
    ctx.tenant_id = tenant_id
    ctx.state = state
    return ctx


class _AsyncCtxMgr:
    def __init__(self, obj):
        self._obj = obj

    async def __aenter__(self):
        return self._obj

    async def __aexit__(self, *args):
        pass


def _make_pool(row_id: int = 42, side_effect=None) -> MagicMock:
    conn = AsyncMock()
    if side_effect:
        conn.fetchval = AsyncMock(side_effect=side_effect)
    else:
        conn.fetchval = AsyncMock(return_value=row_id)
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_AsyncCtxMgr(conn))
    return pool, conn


class TestScheduleCallback:

    @pytest.mark.asyncio
    async def test_successful_db_insert(self):
        """Happy path: insert to callback_queue and return ok=True with callback_id."""
        from server.tools.handlers.transfer_to_human import _schedule_callback
        ctx = _make_ctx()
        payload = {"transfer_reason": "caller_requested"}
        pool, conn = _make_pool(row_id=99)

        with patch(
            "server.tools.handlers.transfer_to_human._get_db_pool",
            AsyncMock(return_value=pool),
        ):
            result = await _schedule_callback(payload, ctx)

        assert isinstance(result, ToolResult)
        assert result.ok is True
        assert result.data["callback_scheduled"] is True
        assert result.data["callback_id"] == 99
        assert "scheduled_for" in result.data
        assert "Mitarbeiter" in result.data.get("caller_facing_message", "")

        # Confirm DB was called with correct args
        conn.fetchval.assert_awaited_once()
        pos = conn.fetchval.await_args.args
        assert pos[1] == ctx.call_sid   # $1
        assert pos[2] == ctx.tenant_id  # $2
        assert pos[3] == "+4917912345678"  # $3 phone

    @pytest.mark.asyncio
    async def test_db_failure_returns_error_result(self):
        """DB write failure → ok=False with ERR_CALLBACK_DB_FAILED, no exception raised."""
        from server.tools.handlers.transfer_to_human import _schedule_callback
        ctx = _make_ctx()
        payload = {"transfer_reason": "technical"}
        pool, _ = _make_pool(side_effect=RuntimeError("connection refused"))

        with patch(
            "server.tools.handlers.transfer_to_human._get_db_pool",
            AsyncMock(return_value=pool),
        ):
            result = await _schedule_callback(payload, ctx)

        assert result.ok is False
        assert result.error_code == "ERR_CALLBACK_DB_FAILED"
        assert result.data.get("callback_scheduled") is False

    @pytest.mark.asyncio
    async def test_no_phone_returns_error_without_db_call(self):
        """If no phone available, return ERR_CALLBACK_NO_PHONE without touching DB."""
        from server.tools.handlers.transfer_to_human import _schedule_callback

        # Configure all phone-bearing attributes to None explicitly so
        # _extract_phone() returns None (MagicMock would return a truthy object
        # for any attribute by default).
        state = MagicMock()
        state.shared_slots = {}         # no phone/messaging_phone slot
        state.caller_phone = None       # no caller_phone attribute
        state.caller_id_phone = None    # no caller_id_phone attribute
        ctx = _make_ctx()
        ctx.state = state
        payload = {}
        pool, conn = _make_pool()

        with patch(
            "server.tools.handlers.transfer_to_human._get_db_pool",
            AsyncMock(return_value=pool),
        ):
            result = await _schedule_callback(payload, ctx)

        assert result.ok is False
        assert result.error_code == "ERR_CALLBACK_NO_PHONE"
        conn.fetchval.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_transfer_failed_flag_set(self):
        """callback result must always set transfer_failed=True."""
        from server.tools.handlers.transfer_to_human import _schedule_callback
        ctx = _make_ctx()
        pool, _ = _make_pool(row_id=1)

        with patch(
            "server.tools.handlers.transfer_to_human._get_db_pool",
            AsyncMock(return_value=pool),
        ):
            result = await _schedule_callback({"transfer_reason": "after_hours"}, ctx)

        assert result.data.get("transfer_failed") is True


class TestNoInMemoryQueue:

    def test_callback_queue_removed(self):
        """FINDING-015: _CALLBACK_QUEUE must not exist on the module."""
        import server.tools.handlers.transfer_to_human as t
        assert not hasattr(t, "_CALLBACK_QUEUE"), (
            "_CALLBACK_QUEUE still exists; remove it (FINDING-015)"
        )

    def test_get_pending_callbacks_removed(self):
        """FINDING-015: get_pending_callbacks() must not exist (query DB instead)."""
        import server.tools.handlers.transfer_to_human as t
        assert not hasattr(t, "get_pending_callbacks"), (
            "get_pending_callbacks still exists; callers should query callback_queue table"
        )

    def test_get_db_pool_helper_exists(self):
        """Replacement for the in-memory queue."""
        from server.tools.handlers.transfer_to_human import _get_db_pool
        assert callable(_get_db_pool)
