"""
PR-7 tests — six new handler stubs smoke + contract tests (FINDING-012).

Tests are structured at three levels:
  1. Import smoke: each handler can be imported and exposes handle().
  2. Contract tests: each stub returns ToolResult with expected fields on
     both happy-path (correct args) and sad-path (missing identifier).
  3. Registration guard: ALL_HANDLERS in __init__.py contains all expected keys.
  4. capture_catering_lead DB write test with a mock pool.

No live DB or external services required.

Run with:
  cd /home/charles2/sailly-browser-demo
  source venv/bin/activate
  python -m pytest server/tests/handlers/test_new_handlers_smoke.py -v
"""
from __future__ import annotations

import asyncio
from importlib import import_module
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.tools.common.errors import ToolResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ctx(call_sid: str = "CA_test", tenant_id: str = "t1") -> MagicMock:
    ctx = MagicMock()
    ctx.call_sid = call_sid
    ctx.tenant_id = tenant_id
    ctx.state = MagicMock()
    return ctx


_CTX = _make_ctx()

_STUB_HANDLER_NAMES = [
    "modify_order",
    "cancel_order",
    "order_status",
    "modify_reservation",
    "cancel_reservation",
]


# ---------------------------------------------------------------------------
# 1. Import smoke — all six handlers
# ---------------------------------------------------------------------------

class TestHandlerImports:

    @pytest.mark.parametrize("handler_name", [
        *_STUB_HANDLER_NAMES,
        "capture_catering_lead",
    ])
    def test_handler_module_importable(self, handler_name):
        mod = import_module(f"server.tools.handlers.{handler_name}")
        assert mod is not None

    @pytest.mark.parametrize("handler_name", [
        *_STUB_HANDLER_NAMES,
        "capture_catering_lead",
    ])
    def test_handler_has_callable_handle(self, handler_name):
        mod = import_module(f"server.tools.handlers.{handler_name}")
        assert hasattr(mod, "handle")
        assert callable(mod.handle)

    @pytest.mark.parametrize("handler_name", [
        *_STUB_HANDLER_NAMES,
        "capture_catering_lead",
    ])
    def test_handler_has_tool_name_constant(self, handler_name):
        mod = import_module(f"server.tools.handlers.{handler_name}")
        assert hasattr(mod, "TOOL_NAME")
        assert mod.TOOL_NAME == handler_name


# ---------------------------------------------------------------------------
# 2. Stub handler contract tests (modify_order, cancel_order, order_status,
#    modify_reservation, cancel_reservation)
# ---------------------------------------------------------------------------

class TestStubHandlersMissingIdentifier:
    """All stubs must reject calls missing the primary identifier."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("handler_name,identifier_key", [
        ("modify_order", "order_id_or_phone"),
        ("cancel_order", "order_id_or_phone"),
        ("order_status", "order_id_or_phone"),
        ("modify_reservation", "reservation_id_or_phone"),
        ("cancel_reservation", "reservation_id_or_phone"),
    ])
    async def test_missing_identifier_returns_validation_error(
        self, handler_name, identifier_key
    ):
        mod = import_module(f"server.tools.handlers.{handler_name}")
        result = await mod.handle({}, _CTX)
        assert isinstance(result, ToolResult)
        assert result.ok is False
        assert result.error_code == "ERR_TOOL_VALIDATION_FAILED"
        assert "missing" in (result.error or "").lower()


class TestStubHandlersWithIdentifier:
    """Stubs with a valid identifier must return a fail-clean NOT_IMPLEMENTED result."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("handler_name,args", [
        ("modify_order",        {"order_id_or_phone": "+4917912345678"}),
        ("cancel_order",        {"order_id_or_phone": "+4917912345678", "reason": "changed mind"}),
        ("order_status",        {"order_id_or_phone": "ORD-ABCD1234"}),
        ("modify_reservation",  {"reservation_id_or_phone": "+4917912345678", "party_size": 4}),
        ("cancel_reservation",  {"reservation_id_or_phone": "+4917912345678"}),
    ])
    async def test_returns_toolresult(self, handler_name, args):
        mod = import_module(f"server.tools.handlers.{handler_name}")
        result = await mod.handle(args, _CTX)
        assert isinstance(result, ToolResult)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("handler_name,args", [
        ("modify_order",        {"order_id_or_phone": "+4917912345678"}),
        ("cancel_order",        {"order_id_or_phone": "+4917912345678"}),
        ("order_status",        {"order_id_or_phone": "ORD-ABCD1234"}),
        ("modify_reservation",  {"reservation_id_or_phone": "+4917912345678"}),
        ("cancel_reservation",  {"reservation_id_or_phone": "+4917912345678"}),
    ])
    async def test_returns_not_implemented_error_code(self, handler_name, args):
        mod = import_module(f"server.tools.handlers.{handler_name}")
        result = await mod.handle(args, _CTX)
        assert result.ok is False
        assert result.error_code == "ERR_NOT_IMPLEMENTED"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("handler_name,args", [
        ("modify_order",        {"order_id_or_phone": "+4917912345678"}),
        ("cancel_order",        {"order_id_or_phone": "+4917912345678"}),
        ("modify_reservation",  {"reservation_id_or_phone": "+4917912345678"}),
        ("cancel_reservation",  {"reservation_id_or_phone": "+4917912345678"}),
    ])
    async def test_warm_handoff_stubs_set_requires_human(self, handler_name, args):
        """State-mutating stubs must signal requires_human so the LLM can route."""
        mod = import_module(f"server.tools.handlers.{handler_name}")
        result = await mod.handle(args, _CTX)
        assert result.data.get("requires_human") is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize("handler_name,args", [
        ("modify_order",        {"order_id_or_phone": "+4917912345678"}),
        ("cancel_order",        {"order_id_or_phone": "+4917912345678"}),
        ("order_status",        {"order_id_or_phone": "ORD-ABCD1234"}),
        ("modify_reservation",  {"reservation_id_or_phone": "+4917912345678"}),
        ("cancel_reservation",  {"reservation_id_or_phone": "+4917912345678"}),
    ])
    async def test_caller_facing_message_present(self, handler_name, args):
        """Every stub must include a German caller_facing_message for the LLM."""
        mod = import_module(f"server.tools.handlers.{handler_name}")
        result = await mod.handle(args, _CTX)
        msg = result.data.get("caller_facing_message", "")
        assert msg, f"{handler_name}: caller_facing_message must not be empty"


# ---------------------------------------------------------------------------
# 3. capture_catering_lead — validation + DB write
# ---------------------------------------------------------------------------

class TestCaptureCateringLead:

    _VALID_ARGS = {
        "phone": "+491793456789",
        "name": "Schmidt",
        "occasion_date": "2026-06-15",
        "guests": 25,
        "callback_availability": "Mo-Fr 9-17",
        "notes": "Jubilaeumsdinner",
    }

    @pytest.mark.asyncio
    async def test_missing_required_field_returns_error(self):
        from server.tools.handlers.capture_catering_lead import handle
        for field in ("phone", "name", "occasion_date", "guests"):
            incomplete = {k: v for k, v in self._VALID_ARGS.items() if k != field}
            result = await handle(incomplete, _CTX)
            assert result.ok is False, f"should fail when {field!r} missing"
            assert result.error_code == "ERR_TOOL_VALIDATION_FAILED"
            assert "missing" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_invalid_guests_type_returns_error(self):
        from server.tools.handlers.capture_catering_lead import handle
        args = {**self._VALID_ARGS, "guests": "twenty-five"}
        result = await handle(args, _CTX)
        assert result.ok is False
        assert result.error_code == "ERR_TOOL_VALIDATION_FAILED"

    @pytest.mark.asyncio
    async def test_successful_db_write(self):
        """DB path: mock pool so no live DB required."""
        from server.tools.handlers.capture_catering_lead import handle

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(
            return_value=_async_context_manager(mock_conn)
        )

        with patch(
            "server.tools.handlers.capture_catering_lead._get_pool",
            AsyncMock(return_value=mock_pool),
        ):
            result = await handle(self._VALID_ARGS, _CTX)

        assert result.ok is True
        assert result.data["lead_captured"] is True
        assert result.data["callback_window"] == "Mo-Fr 9-17"
        assert "Mitarbeiter" in result.data.get("caller_facing_message", "")

        # Confirm DB was called with correct positional args
        mock_conn.execute.assert_awaited_once()
        call_args = mock_conn.execute.await_args
        pos = call_args.args
        assert pos[1] == _CTX.call_sid   # $1
        assert pos[2] == _CTX.tenant_id  # $2
        assert pos[3] == "+491793456789" # $3 phone
        assert pos[4] == "Schmidt"        # $4 name
        assert pos[5] == "2026-06-15"    # $5 occasion_date
        assert pos[6] == 25              # $6 guests (cast to int)

    @pytest.mark.asyncio
    async def test_db_failure_returns_dependency_error(self):
        from server.tools.handlers.capture_catering_lead import handle

        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=RuntimeError("connection refused"))
        mock_pool = MagicMock()
        mock_pool.acquire = MagicMock(
            return_value=_async_context_manager(mock_conn)
        )

        with patch(
            "server.tools.handlers.capture_catering_lead._get_pool",
            AsyncMock(return_value=mock_pool),
        ):
            result = await handle(self._VALID_ARGS, _CTX)

        assert result.ok is False
        assert result.error_code == "ERR_TOOL_DEPENDENCY_ERROR"


# ---------------------------------------------------------------------------
# 4. Registration guard
# ---------------------------------------------------------------------------

class TestAllHandlersRegistration:

    def test_all_six_new_handlers_in_all_handlers(self):
        from server.tools.handlers import ALL_HANDLERS
        new_handlers = {
            "modify_order", "cancel_order", "order_status",
            "modify_reservation", "cancel_reservation", "capture_catering_lead",
        }
        assert new_handlers.issubset(set(ALL_HANDLERS.keys())), (
            f"Missing from ALL_HANDLERS: {new_handlers - set(ALL_HANDLERS.keys())}"
        )

    def test_existing_handlers_still_present(self):
        """Regression: PR-7 must not accidentally remove existing entries."""
        from server.tools.handlers import ALL_HANDLERS
        existing = {
            "create_order", "create_reservation", "verify_address", "send_sms",
            "transfer_to_human", "get_menu", "get_date_info", "faq", "end_call",
        }
        assert existing.issubset(set(ALL_HANDLERS.keys()))

    def test_all_handlers_are_callable(self):
        from server.tools.handlers import ALL_HANDLERS
        for name, fn in ALL_HANDLERS.items():
            assert callable(fn), f"ALL_HANDLERS[{name!r}] is not callable"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

class _async_context_manager:
    """Minimal async context manager wrapper for mock objects."""

    def __init__(self, obj):
        self._obj = obj

    async def __aenter__(self):
        return self._obj

    async def __aexit__(self, *args):
        pass
