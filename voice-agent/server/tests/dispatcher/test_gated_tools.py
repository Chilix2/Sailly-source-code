"""
PR-6 tests — GATED_TOOLS_BASE + required_slots_for_tool + dispatch_with_validation
gate behaviour (FINDING-011).

Tests are structured at three levels:
  1. required_slots_for_tool unit tests (pure function, no I/O).
  2. dispatch_with_validation integration tests using a mock registry and
     execute_fn. Covers blocked / allowed paths per gated tool.
  3. Regression guards (GATED_TOOLS_BASE shape stays stable).

No live DB or external services required.

Run with:
  cd /home/charles2/sailly-browser-demo
  source venv/bin/activate
  python -m pytest server/tests/dispatcher/test_gated_tools.py -v
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.brain.layer1.validation.registry import (
    ValidationContext,
    ValidationEntry,
    ValidationRegistry,
    ValidationResult,
    ValidationStatus,
)
from server.tools.dispatcher import (
    GATED_TOOLS_BASE,
    DispatchResult,
    dispatch_with_validation,
    required_slots_for_tool,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_registry(
    verified_paths: list[str] | None = None,
    failed_paths: list[str] | None = None,
) -> ValidationRegistry:
    """
    Build a ValidationRegistry pre-loaded with entries at the given statuses.
    Paths not in either list return UNVALIDATED (default for missing entries).
    """
    ctx = ValidationContext(
        tenant_id="t1",
        call_sid="CS_test",
        turn_idx=0,
        tenant_cfg={},
    )
    registry = ValidationRegistry(ctx)
    for path in (verified_paths or []):
        registry._entries[path] = ValidationEntry(
            slot_path=path,
            last_value="ok",
            result=ValidationResult(status=ValidationStatus.VERIFIED),
        )
    for path in (failed_paths or []):
        registry._entries[path] = ValidationEntry(
            slot_path=path,
            last_value="bad",
            result=ValidationResult(status=ValidationStatus.FAILED),
        )
    return registry


def _make_state(intent_idx: int = 0, *, call_sid: str = "CS_test") -> MagicMock:
    """Minimal ConversationState stand-in."""
    state = MagicMock()
    state.current_intent_idx = intent_idx
    state.call_sid = call_sid
    state.tenant_id = "t1"
    state._pending_validation_tasks = []
    return state


async def _noop_execute(tool_name: str, args: dict, call_sid: str, tenant_id: str,
                        conversation_state: Any) -> dict:
    return {"success": True, "tool": tool_name}


# ---------------------------------------------------------------------------
# 1. required_slots_for_tool — unit tests
# ---------------------------------------------------------------------------

class TestRequiredSlotsForTool:

    def test_create_order_takeaway_requires_phone_and_items(self):
        slots = required_slots_for_tool("create_order", {"channel": "takeaway"})
        assert slots == {"phone", "items"}

    def test_create_order_no_channel_requires_phone_and_items(self):
        """Absent channel key defaults to takeaway semantics — no address."""
        slots = required_slots_for_tool("create_order", {})
        assert slots == {"phone", "items"}

    def test_create_order_delivery_requires_address(self):
        slots = required_slots_for_tool("create_order", {"channel": "delivery"})
        assert slots == {"phone", "items", "address"}

    def test_create_reservation_required_slots(self):
        slots = required_slots_for_tool("create_reservation", {})
        assert slots == {"phone", "party_size", "name", "date", "time"}

    def test_verify_address_requires_address(self):
        slots = required_slots_for_tool("verify_address", {})
        assert slots == {"address"}

    def test_send_sms_requires_phone(self):
        slots = required_slots_for_tool("send_sms", {})
        assert slots == {"phone"}

    def test_get_menu_is_not_gated(self):
        """Read-only tools must return empty set — never gated."""
        assert required_slots_for_tool("get_menu", {}) == set()

    def test_faq_is_not_gated(self):
        assert required_slots_for_tool("faq", {}) == set()

    def test_get_date_info_is_not_gated(self):
        assert required_slots_for_tool("get_date_info", {}) == set()

    def test_transfer_to_human_is_not_gated(self):
        assert required_slots_for_tool("transfer_to_human", {}) == set()

    def test_returns_copy_not_reference(self):
        """Mutating the returned set must not affect GATED_TOOLS_BASE."""
        original = GATED_TOOLS_BASE["send_sms"].copy()
        slots = required_slots_for_tool("send_sms", {})
        slots.add("__injected__")
        assert GATED_TOOLS_BASE["send_sms"] == original


# ---------------------------------------------------------------------------
# 2. dispatch_with_validation — integration tests
# ---------------------------------------------------------------------------

class TestDispatchGateBlocking:

    @pytest.mark.asyncio
    async def test_create_order_blocked_phone_unverified(self):
        """Phone FILLED but not VERIFIED — create_order must be blocked."""
        registry = _make_registry(
            # "items" verified, phone absent (UNVALIDATED)
            verified_paths=["intent[0].items"],
        )
        state = _make_state()

        result = await dispatch_with_validation(
            [{"name": "create_order", "args": {"channel": "takeaway"}}],
            state,
            registry,
            _noop_execute,
        )

        assert len(result.blocked) == 1
        assert result.blocked[0]["name"] == "create_order"
        assert len(result.successes) == 0

    @pytest.mark.asyncio
    async def test_create_order_blocked_items_unverified(self):
        """Phone verified, items not — create_order must still be blocked."""
        registry = _make_registry(
            verified_paths=["intent[0].phone"],
        )
        state = _make_state()

        result = await dispatch_with_validation(
            [{"name": "create_order", "args": {"channel": "takeaway"}}],
            state,
            registry,
            _noop_execute,
        )

        assert len(result.blocked) == 1

    @pytest.mark.asyncio
    async def test_create_order_allowed_when_phone_and_items_verified(self):
        """All required takeaway slots VERIFIED — tool must pass through."""
        registry = _make_registry(
            verified_paths=["intent[0].phone", "intent[0].items"],
        )
        state = _make_state()

        result = await dispatch_with_validation(
            [{"name": "create_order", "args": {"channel": "takeaway"}}],
            state,
            registry,
            _noop_execute,
        )

        assert len(result.blocked) == 0
        assert len(result.successes) == 1

    @pytest.mark.asyncio
    async def test_create_order_delivery_blocked_when_address_failed(self):
        """Delivery order with failed address verification must be blocked."""
        registry = _make_registry(
            verified_paths=["intent[0].phone", "intent[0].items"],
            failed_paths=["intent[0].address"],
        )
        state = _make_state()

        result = await dispatch_with_validation(
            [{"name": "create_order", "args": {"channel": "delivery"}}],
            state,
            registry,
            _noop_execute,
        )

        assert len(result.blocked) == 1
        assert result.blocked[0]["name"] == "create_order"

    @pytest.mark.asyncio
    async def test_create_order_delivery_blocked_when_address_absent(self):
        """Delivery order where address slot was never validated — blocked."""
        registry = _make_registry(
            verified_paths=["intent[0].phone", "intent[0].items"],
            # address intentionally absent → UNVALIDATED
        )
        state = _make_state()

        result = await dispatch_with_validation(
            [{"name": "create_order", "args": {"channel": "delivery"}}],
            state,
            registry,
            _noop_execute,
        )

        assert len(result.blocked) == 1

    @pytest.mark.asyncio
    async def test_create_order_delivery_allowed_when_all_verified(self):
        """Delivery order with all three slots VERIFIED must pass through."""
        registry = _make_registry(
            verified_paths=[
                "intent[0].phone",
                "intent[0].items",
                "intent[0].address",
            ],
        )
        state = _make_state()

        result = await dispatch_with_validation(
            [{"name": "create_order", "args": {"channel": "delivery"}}],
            state,
            registry,
            _noop_execute,
        )

        assert len(result.blocked) == 0
        assert len(result.successes) == 1

    @pytest.mark.asyncio
    async def test_create_reservation_blocked_when_name_missing(self):
        """Reservation with phone/size/date/time but no name — blocked."""
        registry = _make_registry(
            verified_paths=[
                "intent[0].phone",
                "intent[0].party_size",
                "intent[0].date",
                "intent[0].time",
                # name intentionally absent
            ],
        )
        state = _make_state()

        result = await dispatch_with_validation(
            [{"name": "create_reservation", "args": {}}],
            state,
            registry,
            _noop_execute,
        )

        assert len(result.blocked) == 1

    @pytest.mark.asyncio
    async def test_create_reservation_allowed_when_all_verified(self):
        registry = _make_registry(
            verified_paths=[
                "intent[0].phone",
                "intent[0].party_size",
                "intent[0].name",
                "intent[0].date",
                "intent[0].time",
            ],
        )
        state = _make_state()

        result = await dispatch_with_validation(
            [{"name": "create_reservation", "args": {}}],
            state,
            registry,
            _noop_execute,
        )

        assert len(result.blocked) == 0
        assert len(result.successes) == 1

    @pytest.mark.asyncio
    async def test_send_sms_blocked_when_phone_unverified(self):
        registry = _make_registry()  # all UNVALIDATED
        state = _make_state()

        result = await dispatch_with_validation(
            [{"name": "send_sms", "args": {}}],
            state,
            registry,
            _noop_execute,
        )

        assert len(result.blocked) == 1

    @pytest.mark.asyncio
    async def test_send_sms_allowed_when_phone_verified(self):
        registry = _make_registry(verified_paths=["intent[0].phone"])
        state = _make_state()

        result = await dispatch_with_validation(
            [{"name": "send_sms", "args": {}}],
            state,
            registry,
            _noop_execute,
        )

        assert len(result.blocked) == 0
        assert len(result.successes) == 1

    @pytest.mark.asyncio
    async def test_verify_address_blocked_when_address_unverified(self):
        registry = _make_registry()  # address UNVALIDATED
        state = _make_state()

        result = await dispatch_with_validation(
            [{"name": "verify_address", "args": {}}],
            state,
            registry,
            _noop_execute,
        )

        assert len(result.blocked) == 1

    @pytest.mark.asyncio
    async def test_verify_address_allowed_when_address_verified(self):
        registry = _make_registry(verified_paths=["intent[0].address"])
        state = _make_state()

        result = await dispatch_with_validation(
            [{"name": "verify_address", "args": {}}],
            state,
            registry,
            _noop_execute,
        )

        assert len(result.blocked) == 0

    @pytest.mark.asyncio
    async def test_get_menu_always_allowed(self):
        """Read-only tool — never blocked regardless of registry state."""
        registry = _make_registry()  # all UNVALIDATED
        state = _make_state()

        result = await dispatch_with_validation(
            [{"name": "get_menu", "args": {}}],
            state,
            registry,
            _noop_execute,
        )

        assert len(result.blocked) == 0
        assert len(result.successes) == 1

    @pytest.mark.asyncio
    async def test_mixed_gated_and_readonly_in_one_call(self):
        """Read-only tools pass; gated tools with unvalidated slots block."""
        registry = _make_registry(
            verified_paths=["intent[0].phone"],
            # items not verified → create_order blocked
        )
        state = _make_state()

        result = await dispatch_with_validation(
            [
                {"name": "get_menu", "args": {}},
                {"name": "create_order", "args": {"channel": "takeaway"}},
            ],
            state,
            registry,
            _noop_execute,
        )

        assert len(result.blocked) == 1
        assert result.blocked[0]["name"] == "create_order"
        assert len(result.successes) == 1
        assert result.successes[0].name == "get_menu"

    @pytest.mark.asyncio
    async def test_blocked_result_contains_slot_statuses(self):
        """Blocked entry must carry statuses dict for observability / logging."""
        registry = _make_registry()
        state = _make_state()

        result = await dispatch_with_validation(
            [{"name": "send_sms", "args": {}}],
            state,
            registry,
            _noop_execute,
        )

        assert "statuses" in result.blocked[0]
        assert "intent[0].phone" in result.blocked[0]["statuses"]

    @pytest.mark.asyncio
    async def test_no_current_intent_blocks_gated_tool(self):
        """Missing intent_idx must block the tool with a descriptive reason."""
        registry = _make_registry(verified_paths=["intent[0].phone"])
        state = _make_state()
        state.current_intent_idx = None  # simulate no active intent

        result = await dispatch_with_validation(
            [{"name": "send_sms", "args": {}}],
            state,
            registry,
            _noop_execute,
        )

        assert len(result.blocked) == 1
        assert "no current_intent" in result.blocked[0]["reason"]


# ---------------------------------------------------------------------------
# 3. Regression guards
# ---------------------------------------------------------------------------

class TestGatedToolsBaseRegression:

    def test_gated_tools_base_contains_all_phase6_tools(self):
        """
        Regression: removing a tool from GATED_TOOLS_BASE requires explicit
        justification. Any future PR must update this assertion deliberately.
        """
        expected = {"create_order", "create_reservation", "verify_address", "send_sms"}
        assert set(GATED_TOOLS_BASE.keys()) == expected

    def test_create_order_base_slots(self):
        """Takeaway base must be exactly {phone, items}."""
        assert GATED_TOOLS_BASE["create_order"] == {"phone", "items"}

    def test_create_reservation_base_slots(self):
        assert GATED_TOOLS_BASE["create_reservation"] == {
            "phone", "party_size", "name", "date", "time"
        }

    def test_verify_address_base_slots(self):
        assert GATED_TOOLS_BASE["verify_address"] == {"address"}

    def test_send_sms_base_slots(self):
        assert GATED_TOOLS_BASE["send_sms"] == {"phone"}

    def test_no_question_mark_suffixes_in_base(self):
        """Option A decision: no '?' markers. All entries are plain slot names."""
        for tool, slots in GATED_TOOLS_BASE.items():
            for slot in slots:
                assert not slot.endswith("?"), (
                    f"GATED_TOOLS_BASE[{tool!r}] contains '?'-suffixed slot "
                    f"{slot!r}; use required_slots_for_tool for conditional logic"
                )
