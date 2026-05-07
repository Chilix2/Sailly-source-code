"""
Tool dispatcher with validation gate — Phase 6.

Per gate-all (decision 5.5.6): every state-mutating tool must pass validation
before firing. This module owns the gate framework and per-tool slot wiring
(populated in Phase 6).

`GATED_TOOLS_BASE` maps tool name → set of required slot names. All slot names
are plain strings — no '?' suffix. Channel-conditional requirements (e.g.
address only for delivery orders) are handled by `required_slots_for_tool`.

Decision (PR-6): Option A — channel-aware required set. `required_slots_for_tool`
encodes the takeaway-vs-delivery logic explicitly so no optional-marker parsing
is needed and future readers can trace exactly which slots gate which tools.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from server.brain.conversation_state import ConversationState
    from server.brain.layer1.validation.registry import ValidationRegistry


# ── Gate registry ─────────────────────────────────────────────────────────────
# Per gate-all: every state-mutating tool is listed here. All slot names are
# plain strings (no '?' suffix). Channel-conditional slots are handled by
# `required_slots_for_tool`. Read-only tools (get_menu, faq, get_date_info,
# transfer_to_human) are NOT listed here and always pass through.
GATED_TOOLS_BASE: dict[str, set[str]] = {
    "create_order": {
        "phone",
        "items",
        # "address" is conditionally added for delivery channel by
        # required_slots_for_tool. Takeaway orders never fill address,
        # so the slot is absent — absent slots don't require validation.
    },
    "create_reservation": {
        "phone",
        "party_size",
        "name",
        "date",
        "time",
    },
    "verify_address": {
        "address",
    },
    "send_sms": {
        "phone",
    },
}


def required_slots_for_tool(tool_name: str, args: dict) -> set[str]:
    """
    Return the set of slot names that must be VERIFIED before *tool_name* fires.

    Per Phase 6 + Phase 5.5 gate-all: only VERIFIED slots satisfy the gate.
    PENDING, FAILED, UNVALIDATED all block the tool.

    Channel logic for create_order: delivery orders require an address that has
    passed verify_address. Takeaway orders never have an address slot, so the
    gate does not check it. This avoids an "address?" optional-marker and keeps
    the gate logic explicit.

    Tools not in GATED_TOOLS_BASE return an empty set — they are never blocked.
    """
    base = GATED_TOOLS_BASE.get(tool_name, set()).copy()
    if tool_name == "create_order" and args.get("channel") == "delivery":
        base.add("address")
    return base


# ── Result shape ──────────────────────────────────────────────────────────────

@dataclass
class ToolResult:
    name: str
    result: Any
    error: Optional[str] = None


@dataclass
class DispatchResult:
    successes: list[ToolResult] = field(default_factory=list)
    failures: list[ToolResult] = field(default_factory=list)
    blocked: list[dict] = field(default_factory=list)  # Phase 5.5 addition


# ── Public API ────────────────────────────────────────────────────────────────

async def dispatch_with_validation(
    tool_calls: list[dict],
    state: "ConversationState",
    registry: "ValidationRegistry",
    execute_fn: Any,
) -> DispatchResult:
    """
    Per gate-all: partition tool_calls into allowed and blocked before executing.

    Tools absent from GATED_TOOLS_BASE (via required_slots_for_tool) are always
    allowed (read-only or unmanaged, e.g. get_menu, faq, get_date_info). Gated
    tools must have all required slots in VERIFIED state.

    Args:
        tool_calls:  List of {"name": str, "args": dict} dicts from the LLM.
        state:       Current ConversationState.
        registry:    Per-call ValidationRegistry.
        execute_fn:  Async callable(tool_name, args, call_sid, tenant_id,
                     conversation_state) → result dict. Typically
                     tools.executor.execute_tool.

    Returns:
        DispatchResult with successes, failures, and blocked entries.
    """
    allowed: list[dict] = []
    blocked: list[dict] = []

    for tc in tool_calls:
        required = required_slots_for_tool(tc["name"], tc.get("args") or {})
        if not required:
            # Not a gated tool — pass through unconditionally
            allowed.append(tc)
            continue

        intent_idx = getattr(state, "current_intent_idx", None)
        if intent_idx is None:
            blocked.append({
                "name": tc["name"],
                "reason": "no current_intent (cannot resolve required slot paths)",
            })
            continue

        slot_paths: list[str] = []
        for slot_name in required:
            slot_paths.append(f"intent[{intent_idx}].{slot_name}")

        # Allow in-flight validators a brief window to complete before gating
        await _wait_for_pending_validators(state, max_wait_s=0.2)

        if registry.is_committable(slot_paths):
            allowed.append(tc)
        else:
            statuses = {p: registry.get_status(p).value for p in slot_paths}
            logger.warning(
                "tool_blocked_by_validation",
                extra={
                    "tool": tc["name"],
                    "statuses": statuses,
                    "call_sid": getattr(state, "call_sid", ""),
                    "turn_idx": getattr(state, "turn_idx", 0),
                },
            )
            blocked.append({
                "name": tc["name"],
                "reason": "validation",
                "statuses": statuses,
            })

    result = DispatchResult(blocked=blocked)
    await _execute_allowed(allowed, state, execute_fn, result)
    return result


async def _execute_allowed(
    tool_calls: list[dict],
    state: "ConversationState",
    execute_fn: Any,
    out: DispatchResult,
) -> None:
    """
    Run each allowed tool call and populate out.successes / out.failures.

    Phase 8 B6: write an audit entry after every state-mutating tool execution.
    Audit writes are fire-and-forget; failures do NOT crash the call.
    """
    call_sid = getattr(state, "call_sid", "")
    tenant_id = getattr(state, "tenant_id", "")

    for tc in tool_calls:
        name = tc["name"]
        args = tc.get("args") or tc.get("arguments") or {}
        success = False
        res = None
        exc_ref = None
        try:
            res = await execute_fn(
                name,
                args,
                call_sid,
                tenant_id,
                conversation_state=state,
            )
            success = bool(res.get("success", True)) if isinstance(res, dict) else True
            out.successes.append(ToolResult(name=name, result=res))
            # Phase 9 B1 — collect error_code from ToolResult for metrics
            if isinstance(res, dict) and res.get("error_code"):
                _error_codes = getattr(state, "_turn_error_codes", None)
                if _error_codes is None:
                    state._turn_error_codes = []  # type: ignore[attr-defined]
                state._turn_error_codes.append(res["error_code"])  # type: ignore[attr-defined]
        except Exception as exc:
            exc_ref = exc
            logger.error(
                "tool_execution_failed",
                extra={"tool": name, "error": str(exc)[:200]},
            )
            out.failures.append(ToolResult(name=name, result=None, error=str(exc)[:200]))

        # Phase 8 B6 — append-only audit trail for state-mutating tools
        try:
            from server.brain.observability.audit import write_audit_entry
            result_for_audit = res if res is not None else {"error": str(exc_ref)[:200]}
            asyncio.ensure_future(
                write_audit_entry(
                    call_sid=call_sid,
                    tenant_id=tenant_id,
                    tool_name=name,
                    args=args,
                    result=result_for_audit,
                    success=success,
                )
            )
        except Exception as audit_exc:
            logger.debug("[dispatcher] audit write skipped: %s", audit_exc)


async def _wait_for_pending_validators(
    state: "ConversationState",
    max_wait_s: float = 0.2,
) -> None:
    """
    Allow in-flight validators a brief window to complete before gating.

    If they don't finish within max_wait_s, slot stays PENDING and the
    tool is blocked. The bot routes to a clarification turn and re-prompts
    the caller for the missing slot.
    """
    pending = getattr(state, "_pending_validation_tasks", None)
    if not pending:
        return
    incomplete = [t for t in pending if not t.done()]
    if not incomplete:
        return
    try:
        await asyncio.wait(incomplete, timeout=max_wait_s)
    except Exception:
        pass
