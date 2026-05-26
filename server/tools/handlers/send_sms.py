"""
send_sms — sends order/reservation confirmation messages.

Phase 6 decisions:
  - tool-send-sms-routing: current-cascade
    Try WhatsApp template first; fall back to plain SMS if WhatsApp fails
    or the recipient hasn't opted in.

  - tool-send-sms-gating: strict-gate
    Fires ONLY after caller explicitly confirmed in the current turn.
    `state.last_caller_confirmation_turn == state.turn_idx` must hold.

Per Phase 4 mi-sms-combined:per-intent — multi-intent calls send one
confirmation message per intent, not one combined message.
"""
from __future__ import annotations

import logging
from typing import Any

from server.tools.common.context import ToolContext
from server.tools.common.error_codes import ErrorCode
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "send_sms"


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args:
      phone:       str — recipient phone number
      message:     str — message body (optional; built from template if absent)
      intent_kind: str — "order" | "reservation" (for per-intent routing)
      template:    str — optional template name for WhatsApp
    """
    # ── Strict gate ───────────────────────────────────────────────────────────
    if not _is_caller_confirmed_this_turn(ctx):
        logger.warning(
            "[send_sms] strict-gate blocked (call_sid=%s turn_idx=%s last_confirm=%s)",
            ctx.call_sid,
            getattr(ctx.state, "turn_idx", None),
            getattr(ctx.state, "last_caller_confirmation_turn", None),
        )
        return ToolResult(
            ok=False,
            data={},
            error=(
                "strict_gate: SMS requires caller confirmation in same turn. "
                "Obtain explicit confirmation before sending."
            ),
            error_code=ErrorCode.STRICT_GATE_FAILED,
        )

    phone = str(args.get("phone") or "").strip()
    if not phone:
        return ToolResult(ok=False, error="Keine Telefonnummer angegeben", error_code=ErrorCode.MISSING_REQUIRED_SLOT)

    message = str(args.get("message") or "").strip()
    intent_kind = str(args.get("intent_kind") or "").strip()

    # ── WhatsApp → SMS cascade ────────────────────────────────────────────────
    wa_result = await _try_whatsapp(phone, message, intent_kind, ctx)
    if wa_result is not None and wa_result.get("ok"):
        return ToolResult(
            ok=True,
            data={"channel": "whatsapp", "message_id": wa_result.get("message_id")},
        )

    sms_result = await _try_sms(phone, message, intent_kind, ctx)
    if sms_result is not None and sms_result.get("ok"):
        return ToolResult(
            ok=True,
            data={"channel": "sms", "message_id": sms_result.get("message_id")},
        )

    return ToolResult(
        ok=False,
        data={"channel": "none"},
        error="both_whatsapp_and_sms_failed",
        error_code=ErrorCode.SMS_SEND_FAILED,
    )


# ── Gate helper ───────────────────────────────────────────────────────────────

def _is_caller_confirmed_this_turn(ctx: ToolContext) -> bool:
    """
    Strict gate — caller must have confirmed within this exact turn.
    Also accepts if a parent create_order/create_reservation succeeded this
    turn (legacy path where send_sms is called after the create tool).
    """
    state = ctx.state
    if state is None:
        return False

    # New path: extractor sets last_caller_confirmation_turn
    last_confirm = getattr(state, "last_caller_confirmation_turn", None)
    turn_idx = getattr(state, "turn_idx", None)
    if last_confirm is not None and turn_idx is not None and last_confirm == turn_idx:
        return True

    # Legacy path: check if create_order or create_reservation succeeded
    tool_results = getattr(state, "tool_results", None) or {}
    for tool_name in ("create_order", "create_reservation"):
        result = tool_results.get(tool_name)
        if isinstance(result, dict) and result.get("success") and not result.get("error"):
            return True

    return False


# ── Channel implementations ───────────────────────────────────────────────────

async def _try_whatsapp(
    phone: str, message: str, intent_kind: str, ctx: ToolContext
) -> dict | None:
    """Attempt WhatsApp template send. Returns {ok, message_id} or None on error."""
    try:
        from tools.sms_service import send_confirmation  # type: ignore
        template_type = (
            "order_confirmation" if intent_kind == "order"
            else "reservation_confirmation"
        )
        await send_confirmation(
            phone,
            message,
            template_type=template_type,
            human_message=message,
        )
        return {"ok": True, "message_id": None}
    except Exception as e:
        logger.warning("[send_sms] WhatsApp failed (falling back to SMS): %s", e)
        return None


async def _try_sms(
    phone: str, message: str, intent_kind: str, ctx: ToolContext
) -> dict | None:
    """Attempt plain SMS send. Returns {ok, message_id} or None on error."""
    try:
        from tools.sms_service import send_confirmation  # type: ignore
        await send_confirmation(phone, message, template_type=None, human_message=message)
        return {"ok": True, "message_id": None}
    except Exception as e:
        logger.warning("[send_sms] SMS failed: %s", e)
        return None
