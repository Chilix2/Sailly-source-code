"""
transfer_to_human — warm handoff with full context payload + callback fallback.

Phase 6 decision:
  - tool-transfer-human: current-payload
    Pass everything the human agent needs:
      - call_sid (for transcript/recording lookup)
      - captured_intents (kind, status, slots)
      - tenant_id
      - reason for transfer
      - last 5 turns of transcript
    Twilio redirect carries a signed payload_id; receiving CRM pulls the
    full dict from Redis via /admin/transfer/{call_sid}.

Phase 8 decision:
  - callback-fallback (8.S9): if Twilio transfer fails (no answer, busy,
    error), capture caller details and schedule a callback. Never lose the lead.
"""
from __future__ import annotations

import logging

from server.tools.common.context import ToolContext
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "transfer_to_human"


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args:
      reason: str — why the transfer is happening (e.g. "caller_requested",
              "catering_request", "complaint", "after_hours")
    """
    reason = str(args.get("reason") or "unspecified")

    # ── Build full context payload ────────────────────────────────────────────
    payload = _build_payload(ctx, reason)

    # ── Delegate to legacy executor (handles Redis persist + Twilio redirect) ─
    try:
        from tools.executor import _transfer_to_human as _legacy  # type: ignore
        legacy_ctx = {"conversation_state": ctx.state}
        result = await _legacy(args, ctx.call_sid, ctx.tenant_id, context=legacy_ctx)

        # Per callback-fallback (8.S9): transfer failure → schedule callback
        if result.get("success") is False and not result.get("demo_mode"):
            logger.warning(
                "[transfer_to_human] transfer failed (call_sid=%s reason=%s) — scheduling callback",
                ctx.call_sid, reason,
            )
            return await _schedule_callback(payload, ctx)

        # Transfer succeeded — augment result with full payload
        result["context_payload"] = payload
        return ToolResult(ok=result.get("success", True), data=result)

    except ImportError:
        return ToolResult(
            ok=True,
            data={"payload": payload, "note": "legacy executor not available"},
        )
    except Exception as exc:
        logger.error(
            "[transfer_to_human] exception during transfer (call_sid=%s): %s",
            ctx.call_sid, exc,
        )
        return await _schedule_callback(payload, ctx)


def _build_payload(ctx: ToolContext, reason: str) -> dict:
    """Construct the warm-transfer context blob per current-payload decision."""
    state = ctx.state
    payload: dict = {
        "call_sid": ctx.call_sid,
        "tenant_id": ctx.tenant_id,
        "transfer_reason": reason,
        "captured_intents": [],
        "shared_slots": {},
        "recent_transcript": [],
    }

    try:
        payload["captured_intents"] = [
            {
                "kind": i.kind.value if hasattr(i.kind, "value") else str(i.kind),
                "status": i.status.value if hasattr(i.status, "value") else str(i.status),
                "slots": {
                    n: s.value
                    for n, s in i.slots.items()
                    if s.value is not None
                },
            }
            for i in (getattr(state, "captured_intents", None) or [])
        ]
    except Exception as e:
        logger.debug("[transfer_to_human] captured_intents build error: %s", e)

    try:
        payload["shared_slots"] = {
            n: s.value
            for n, s in (getattr(state, "shared_slots", None) or {}).items()
            if getattr(s, "value", None) is not None
        }
    except Exception as e:
        logger.debug("[transfer_to_human] shared_slots build error: %s", e)

    try:
        recent_turns = getattr(state, "recent_responses", None) or []
        # recent_responses is list of str; take last 5
        payload["recent_transcript"] = [
            {"role": "bot", "text": t}
            for t in recent_turns[-5:]
            if t
        ]
    except Exception as e:
        logger.debug("[transfer_to_human] transcript build error: %s", e)

    return payload


async def _schedule_callback(payload: dict, ctx: ToolContext) -> ToolResult:
    """
    Per callback-fallback (8.S9) + FINDING-015 fix: persist failed-transfer
    callbacks to Postgres so they survive server restarts and the operator
    dashboard query against `callback_queue` returns live data.

    On DB failure the result is returned as ok=False so the LLM can tell
    the caller we couldn't schedule, rather than silently losing the lead.
    """
    from datetime import datetime, timedelta, timezone

    state = ctx.state
    phone = _extract_phone(state)
    name = _extract_name(state)
    context_summary = payload.get("transfer_reason", "unspecified")
    scheduled_for = datetime.now(timezone.utc) + timedelta(hours=1)

    if not phone:
        logger.error(
            "callback_schedule_no_phone",
            extra={"call_sid": ctx.call_sid, "tenant_id": ctx.tenant_id},
        )
        return ToolResult(
            ok=False,
            error="cannot schedule callback — no phone available",
            error_code="ERR_CALLBACK_NO_PHONE",
            data={
                "transfer_failed": True,
                "callback_scheduled": False,
            },
        )

    try:
        pool = await _get_db_pool()
        async with pool.acquire() as conn:
            row_id = await conn.fetchval(
                """
                INSERT INTO callback_queue
                    (call_sid, tenant_id, phone, name,
                     context_summary, scheduled_for)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                ctx.call_sid,
                ctx.tenant_id,
                phone,
                name,
                context_summary,
                scheduled_for,
            )
        logger.info(
            "callback_scheduled",
            extra={
                "call_sid": ctx.call_sid,
                "callback_id": row_id,
                "scheduled_for": scheduled_for.isoformat(),
                "phone_redacted": (str(phone)[:4] + "***") if phone else "none",
            },
        )
        return ToolResult(
            ok=True,
            data={
                "transfer_failed": True,
                "callback_scheduled": True,
                "callback_id": row_id,
                "scheduled_for": scheduled_for.isoformat(),
                "caller_facing_message": (
                    "Es tut mir leid, ich kann Sie gerade nicht verbinden. "
                    "Ein Mitarbeiter ruft Sie zurück."
                ),
            },
        )
    except Exception as exc:
        logger.exception(
            "callback_schedule_db_failed",
            extra={
                "call_sid": ctx.call_sid,
                "phone_redacted": (str(phone)[:4] + "***") if phone else "none",
            },
        )
        return ToolResult(
            ok=False,
            error=str(exc),
            error_code="ERR_CALLBACK_DB_FAILED",
            data={
                "transfer_failed": True,
                "callback_scheduled": False,
            },
        )


async def _get_db_pool():
    """Lazy-import DB pool — avoids circular imports at module load time."""
    try:
        from server.database import get_pool  # type: ignore
        return await get_pool()
    except ImportError:
        raise RuntimeError("DB pool not available; set POSTGRES_DSN in environment")


def _extract_phone(state) -> str | None:
    try:
        slots = getattr(state, "shared_slots", {}) or {}
        sv = slots.get("phone") or slots.get("messaging_phone")
        return getattr(sv, "value", None) if sv else getattr(state, "caller_phone", None)
    except Exception:
        return None


def _extract_name(state) -> str | None:
    try:
        slots = getattr(state, "shared_slots", {}) or {}
        sv = slots.get("name") or slots.get("customer_name")
        return getattr(sv, "value", None) if sv else None
    except Exception:
        return None
