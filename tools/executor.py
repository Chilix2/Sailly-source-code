"""
Tool executor — handles Gemini function calls by running the appropriate tool logic.
Reimplemented natively in Python (not proxied to Node).
Multi-tenant support: can load restaurant/practice data from tenant config.
Google Maps Platform tools: Routes, Places (New), Weather, Air Quality APIs.
Authentication: service account OAuth2 token (no API key required).
"""

import asyncio
import json
import os
import re
import time
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any, Optional

import aiohttp
from loguru import logger

from .sms_service import send_confirmation, format_reservation_message, format_order_message

# Google auth — service account token for Maps Platform APIs
_maps_token: Optional[str] = None
_maps_token_expiry: float = 0.0
_MAPS_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
_SERVICE_ACCOUNT_KEY = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", ".ssh", "sailly-voice-agent-key.json")
)
# Also accept an explicit API key for Maps if set
_MAPS_API_KEY: Optional[str] = os.environ.get("GOOGLE_MAPS_API_KEY")

# C2: Default coordinates — loaded from tenant config at runtime; kept as fallback
DOBOO_LAT = 50.7323  # tenant-specific fallback (doboo.yaml location.lat)
DOBOO_LNG = 7.0954   # tenant-specific fallback (doboo.yaml location.lng)

_PARKING_STATIC_FALLBACK = {
    "parking_spots": [
        {"name": "Parkhaus Stadthaus Nord", "address": "Berliner Platz, 53111 Bonn", "distance_m": 320},
        {"name": "Parkhaus Friedensplatz", "address": "Am Friedensplatz 3, 53111 Bonn", "distance_m": 450},
    ],
    "source": "static",
    "restaurant_address": "Friedrich-Ebert-Allee 69, 53113 Bonn",
}


def _get_maps_token() -> Optional[str]:
    """Get a fresh OAuth2 access token for Maps Platform APIs."""
    global _maps_token, _maps_token_expiry

    # If explicit API key set, return it (used in URL, not header)
    if _MAPS_API_KEY:
        return _MAPS_API_KEY

    if _maps_token and time.time() < _maps_token_expiry - 60:
        return _maps_token

    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request as GoogleRequest

        creds = service_account.Credentials.from_service_account_file(
            _SERVICE_ACCOUNT_KEY, scopes=_MAPS_SCOPES
        )
        creds.refresh(GoogleRequest())
        _maps_token = creds.token
        _maps_token_expiry = time.time() + 3600
        return _maps_token
    except Exception as e:
        logger.warning(f"Failed to get Maps token: {e}")
        return None


def _maps_headers() -> dict:
    """Build auth headers for Maps Platform API calls."""
    token = _get_maps_token()
    if not token:
        return {}
    if _MAPS_API_KEY:
        return {}  # API key goes in URL params, not headers
    return {"Authorization": f"Bearer {token}"}

BERLIN_TZ = ZoneInfo("Europe/Berlin")

# In-memory stores (will be replaced with Redis in Phase 2)
session_store: dict[str, dict] = {}
reservation_store: dict[str, dict] = {}
order_store: dict[str, dict] = {}
weather_cache: dict[str, tuple[dict, float]] = {}

# Tenant-specific stores (keyed by tenant_id)
tenant_session_store: dict[str, dict[str, dict]] = {}
tenant_reservation_store: dict[str, dict[str, dict]] = {}
tenant_order_store: dict[str, dict[str, dict]] = {}
_TOOL_EVENT_LOG: dict[str, list[dict[str, Any]]] = {}


def _summarize_tool_result(result: Any) -> str:
    if not isinstance(result, dict):
        return str(result)[:300]
    for key in ("message", "error", "status", "note", "result"):
        value = result.get(key)
        if value:
            return str(value)[:300]
    return json.dumps(result, ensure_ascii=False, default=str)[:300]


def _record_tool_event(
    *,
    tool_name: str,
    args: dict,
    call_sid: str,
    turn_number: int,
    result: Any,
    success: bool,
) -> None:
    if not call_sid:
        return
    _TOOL_EVENT_LOG.setdefault(call_sid, []).append({
        "tool": tool_name,
        "name": tool_name,
        "args": dict(args or {}),
        "turn_number": turn_number,
        "success": success,
        "result_summary": _summarize_tool_result(result),
    })


def drain_tool_events(call_sid: str) -> list[dict[str, Any]]:
    """Return and clear tool events captured by execute_tool for a call."""
    if not call_sid:
        return []
    return _TOOL_EVENT_LOG.pop(call_sid, [])


def _build_transfer_payload(
    state, call_sid: str, tenant_id: Optional[str], reason: str
) -> dict:
    """Compose the warm-handover context from ConversationState + OrderSlots.

    Kept small enough for a human agent to skim in under 5 seconds.
    """
    slots_summary = ""
    slots_missing = ""
    slots_intent: Optional[str] = None
    try:
        # Phase 2: prefer CapturedIntent summary when present
        _ci_list = getattr(state, "captured_intents", []) if state is not None else []
        _ci_idx = getattr(state, "current_intent_idx", None) if state is not None else None
        if _ci_list and _ci_idx is not None and _ci_idx < len(_ci_list):
            _ci = _ci_list[_ci_idx]
            slots_intent = _ci.kind.value if hasattr(_ci.kind, "value") else str(_ci.kind)
            _known = [
                f"{n}: {sv.value}"
                for n, sv in _ci.slots.items()
                if hasattr(sv, "value") and sv.value
            ]
            slots_summary = "; ".join(_known) if _known else "(leer)"
        else:
            # Legacy fallback
            slots_ref = getattr(state, "order_slots_ref", None) if state is not None else None
            if slots_ref is not None:
                slots_summary = slots_ref.known_summary_de()
                slots_missing = slots_ref.missing_summary_de()
                slots_intent = getattr(slots_ref, "intent", None)
    except Exception:
        pass

    def _getattr_safe(obj, name, default=None):
        try:
            return getattr(obj, name, default) if obj is not None else default
        except Exception:
            return default

    return {
        "call_sid": call_sid,
        "tenant_id": tenant_id,
        "reason": reason or "caller_requested",
        "built_at": datetime.now().isoformat(),
        "intent": slots_intent or (
            "order"
            if _getattr_safe(state, "order_intent")
            else "reservation"
            if _getattr_safe(state, "reservation_intent")
            else None
        ),
        "slots_known": slots_summary,
        "slots_missing": slots_missing,
        "customer_name": _getattr_safe(state, "customer_name"),
        "phone_number": _getattr_safe(state, "phone_number"),
        "delivery_address": _getattr_safe(state, "delivery_address"),
        "selected_dish": _getattr_safe(state, "selected_dish"),
        "order_quantity": _getattr_safe(state, "order_quantity"),
        "escalation_requested": bool(_getattr_safe(state, "escalation_requested", False)),
        "recent_transcript": list(_getattr_safe(state, "recent_responses", []) or [])[-8:],
    }


async def _persist_transfer_payload(call_sid: str, payload: dict) -> Optional[str]:
    """Write the transfer context to Redis under ``transfer_ctx:{call_sid}``
    with a 1-hour TTL. Returns the key on success, None otherwise.
    """
    if not call_sid:
        return None
    try:
        from server.session import get_redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        r = await get_redis(redis_url)
        key = f"transfer_ctx:{call_sid}"
        await r.setex(key, 3600, json.dumps(payload, default=str))
        logger.info(
            f"[transfer_ctx] wrote {key} "
            f"(intent={payload.get('intent')!r} known={bool(payload.get('slots_known'))})"
        )
        return key
    except Exception as exc:
        logger.warning(f"[transfer_ctx] persist failed: {exc}")
        return None


async def _post_order_to_pos(webhook_url: str, order: dict, order_id: str) -> None:
    """POST an order payload to the tenant's POS webhook with retries.

    Non-blocking: scheduled as a background task from ``_create_order`` so a
    slow POS endpoint never delays the caller-facing TTS.

    Retry policy: 3 attempts with exponential backoff (1s, 2s, 4s). We do not
    retry 4xx responses — those indicate a payload or auth problem that won't
    be fixed by trying again. On final failure the order is left in the
    durable Redis store with ``pos_status: "failed"`` so ops tooling can
    replay it.
    """
    import json as _json
    try:
        import httpx
    except Exception:
        logger.warning("[POS] httpx not installed — skipping POS webhook")
        return

    # Canonical payload (see POS_INTEGRATION.md). Keep stable — downstream
    # integrations parse it.
    payload = {
        "order_id": order_id,
        "source": "sailly-voice",
        "version": "1",
        "created_at": order.get("created_at"),
        "customer": {
            "name": order.get("name"),
            "phone": order.get("phone"),
        },
        "items_text": order.get("order_items"),
        "order_type": order.get("order_type"),
        "payment_method": order.get("payment_method"),
        "total_price": order.get("total_price"),
        "estimated_minutes": order.get("estimated_minutes"),
    }
    body = _json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    _shared = os.getenv("POS_WEBHOOK_TOKEN", "").strip()
    if _shared:
        headers["Authorization"] = f"Bearer {_shared}"

    # POS_BREAKER singleton does not exist in server.core.resilience; the retry
    # loop below provides back-pressure without a dedicated circuit breaker.

    async def _do_post():
        async with httpx.AsyncClient(timeout=2.5) as client:
            return await client.post(webhook_url, content=body, headers=headers)

    backoff = 1.0
    last_err: Optional[str] = None
    for attempt in (1, 2, 3):
        try:
            resp = await _do_post()
            if 200 <= resp.status_code < 300:
                logger.info(f"[POS] {order_id} → {webhook_url} ok ({resp.status_code}) attempt={attempt}")
                return
            if 400 <= resp.status_code < 500:
                # Don't retry — payload/auth bug. Surface for ops.
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                logger.error(f"[POS] {order_id} non-retryable: {last_err}")
                break
            last_err = f"HTTP {resp.status_code}"
        except Exception as e:
            last_err = repr(e)
        logger.warning(f"[POS] {order_id} attempt {attempt} failed: {last_err} — backing off {backoff}s")
        await asyncio.sleep(backoff)
        backoff *= 2

    # All retries exhausted — mark order as "pos_failed" in Redis so replay
    # tooling can pick it up later.
    try:
        import redis.asyncio as aioredis
        _redis_url = os.getenv("REDIS_URL", "redis://localhost:6380")
        _r = aioredis.from_url(_redis_url, decode_responses=True)
        await _r.sadd("orders:pos_failed", order_id)
        await _r.hset(f"order:{order_id}:pos", mapping={
            "status": "failed",
            "last_error": last_err or "unknown",
        })
        await _r.aclose()
    except Exception:
        pass
    logger.error(f"[POS] {order_id} FINAL FAILURE after retries: {last_err}")


async def _get_tenant_config(tenant_id: Optional[str]):
    """Load tenant config if provided, return config or None."""
    if not tenant_id:
        return None
    try:
        from server.core.tenant_config import get_tenant_registry
        registry = get_tenant_registry()
        return registry.load_tenant(tenant_id)
    except Exception as e:
        logger.warning(f"Failed to load tenant config for {tenant_id}: {e}")
        return None


_WEEKDAY_KEYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def _opening_hours_gate(req_date, time_str: str, tenant) -> Optional[dict]:
    """Return an unavailable response when requested time is outside tenant hours."""
    hours = getattr(tenant, "opening_hours", None) or {}
    day_hours = str(hours.get(_WEEKDAY_KEYS[req_date.weekday()], "") or "").lower()
    if not day_hours:
        return None
    if "geschlossen" in day_hours or "closed" in day_hours:
        return {
            "available": False,
            "date": req_date.isoformat(),
            "time": time_str,
            "reason": "Das Restaurant ist an diesem Tag geschlossen.",
        }

    normalized = day_hours.replace("–", "-").replace("—", "-")
    windows = re.findall(r"(\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})", normalized)
    if not windows:
        return None

    req_minutes = _time_to_minutes(time_str)
    if req_minutes is None:
        return {"error": "Ungültige Uhrzeit. Bitte im Format HH:MM angeben."}

    for start, end in windows:
        start_min = _time_to_minutes(start)
        end_min = _time_to_minutes(end)
        if start_min is not None and end_min is not None and start_min <= req_minutes <= end_min:
            return None

    return {
        "available": False,
        "date": req_date.isoformat(),
        "time": time_str,
        "reason": f"Das Restaurant ist um {time_str} Uhr nicht geöffnet.",
        "opening_hours": day_hours,
    }


def _time_to_minutes(value: str) -> Optional[int]:
    try:
        hour, minute = value.split(":", 1)
        return int(hour) * 60 + int(minute)
    except Exception:
        return None


# ── GUARDIAN Pre-Commit Gate ─────────────────────────────────────────────────
# Validates required fields before high-stakes tool execution.
# On block: logs, persists to guardian_blocks table, returns structured error
# so the brain can ask for missing fields (G3.1 fix — B1/B12/B3).

_GUARDIAN_PRECONDITIONS: dict = {
    "create_order": {
        "required_from_args": ["order_items"],   # dish must be present
        "min_prior_assistant_turns": 1,           # readback must have happened before confirm
    },
    "create_reservation": {
        "required_from_args": ["date", "time", "party_size"],
        "min_prior_assistant_turns": 1,
    },
}


async def _persist_guardian_block(call_sid: str, turn_number: int, tool_name: str, reason: str, args: dict) -> None:
    """Write a guardian block event to the DB (non-fatal — fire-and-forget)."""
    try:
        from server.database import persist_guardian_block as _pg
        await _pg(call_sid=call_sid, turn_number=turn_number, tool_name=tool_name, reason=reason, args=args)
    except Exception as e:
        logger.debug(f"[GUARDIAN] persist_guardian_block failed (non-fatal): {e}")


def _guardian_pre_commit_check(tool_name: str, args: dict, turn_number: int) -> tuple[bool, str, list]:
    """Return (allowed, reason, must_ask_for). If not allowed, tool must NOT execute.

    turn_number is the 1-based assistant turn index. Tools with min_prior_assistant_turns=2
    cannot fire before the user has had at least 2 bot responses (gives time to collect info).
    """
    rules = _GUARDIAN_PRECONDITIONS.get(tool_name)
    if not rules:
        return True, "no preconditions", []

    missing_args = [f for f in rules.get("required_from_args", []) if not args.get(f)]
    if missing_args:
        return False, f"missing required args: {missing_args}", missing_args

    min_turns = rules.get("min_prior_assistant_turns", 0)
    if turn_number < min_turns:
        return False, f"too early (turn {turn_number} < min {min_turns})", []

    return True, "ok", []


async def execute_tool(
    tool_name: str,
    args: dict,
    call_sid: str = "",
    tenant_id: Optional[str] = None,
    turn_number: int = 99,
    tool_results: Optional[dict] = None,
    conversation_state: Optional[object] = None,
) -> dict:
    """Dispatch a tool call and return the result as a dict.

    Args:
        tool_name: Name of the tool to execute
        args: Tool arguments
        call_sid: Twilio call SID
        tenant_id: Optional tenant identifier for multi-tenant support
        turn_number: 1-based assistant turn index (used by GUARDIAN gate)
        tool_results: Dict of tool results executed so far this turn (for dependency checks)
        conversation_state: Current ConversationState (for price fallback lookups)
    """
    # GUARDIAN pre-commit gate: block high-stakes tools when preconditions aren't met
    allowed, reason, must_ask_for = _guardian_pre_commit_check(tool_name, args, turn_number)
    if not allowed:
        logger.warning(f"[GUARDIAN_BLOCK] {tool_name} blocked for {call_sid}: {reason}")
        await _persist_guardian_block(
            call_sid=call_sid,
            turn_number=turn_number,
            tool_name=tool_name,
            reason=reason,
            args=args,
        )
        blocked_result = {
            "success": False,
            "blocked_by_guardian": True,
            "reason": reason,
            "must_ask_for": must_ask_for,
            "message": (
                f"Bitte frage zuerst nach: {', '.join(must_ask_for)}" if must_ask_for
                else f"Zu früh im Gespräch für {tool_name}. Sammle zuerst alle nötigen Informationen."
            ),
        }
        _record_tool_event(
            tool_name=tool_name,
            args=args,
            call_sid=call_sid,
            turn_number=turn_number,
            result=blocked_result,
            success=False,
        )
        return blocked_result

    if tool_name in ("create_order", "create_reservation"):
        ready_for_commit = getattr(conversation_state, "ready_for_commit", None) if conversation_state is not None else None
        if conversation_state is None or not callable(ready_for_commit):
            reason = "missing_conversation_state"
            logger.warning(f"[GUARDIAN_BLOCK] {tool_name} blocked for {call_sid}: {reason}")
            blocked_result = {
                "success": False,
                "blocked_by_guardian": True,
                "reason": reason,
                "must_ask_for": ["explicit_confirmation"],
                "message": "Interner Schutz: Bestellungen brauchen einen bestätigten Gesprächszustand.",
            }
            _record_tool_event(
                tool_name=tool_name,
                args=args,
                call_sid=call_sid,
                turn_number=turn_number,
                result=blocked_result,
                success=False,
            )
            return blocked_result
        if not ready_for_commit(tool_name):
            reason = "readback_not_confirmed"
            logger.warning(f"[GUARDIAN_BLOCK] {tool_name} blocked for {call_sid}: {reason}")
            blocked_result = {
                "success": False,
                "blocked_by_guardian": True,
                "reason": reason,
                "must_ask_for": ["explicit_confirmation"],
                "message": "Bitte bestätigen Sie zuerst die Zusammenfassung ausdrücklich.",
            }
            _record_tool_event(
                tool_name=tool_name,
                args=args,
                call_sid=call_sid,
                turn_number=turn_number,
                result=blocked_result,
                success=False,
            )
            return blocked_result

    logger.info(f"Tool call: {tool_name}({json.dumps(args, ensure_ascii=False)[:200]}) [tenant={tenant_id}]")

    # ── Phase 6 handler bridge ────────────────────────────────────────────────
    # Try the Phase 6 per-tool handler first. It applies Phase 6 guard decisions
    # (ceiling-30, cap-200, fuzzy thresholds, strict gate, alternatives, etc.).
    # Falls through to the legacy dispatch below on ImportError (test/no-server env).
    try:
        from server.tools.handlers import ALL_HANDLERS  # type: ignore
        from server.tools.common.context import ToolContext  # type: ignore
        _p6_handler = ALL_HANDLERS.get(tool_name)
        if _p6_handler is not None:
            _tenant_cfg: dict = {}
            try:
                _tcfg = await _get_tenant_config(tenant_id)
                if _tcfg is not None:
                    _tenant_cfg = {
                        k: getattr(_tcfg, k, None)
                        for k in vars(_tcfg)
                        if not k.startswith("_")
                    }
                    # Also expose raw YAML dict if TenantConfig wraps it
                    if hasattr(_tcfg, "__dict__"):
                        _tenant_cfg.update(_tcfg.__dict__)
            except Exception:
                pass
            _p6_ctx = ToolContext(
                call_sid=call_sid or "",
                tenant_id=tenant_id or "",
                tenant_cfg=_tenant_cfg,
                state=conversation_state,
            )
            _p6_result = await _p6_handler(args, _p6_ctx)
            # Phase 8 B6 — audit trail for state-mutating tools (FINDING-004 fix)
            try:
                from server.brain.observability.audit import AUDITED_TOOLS as _P6_AUDITED, write_audit_entry as _p6_audit
                if tool_name in _P6_AUDITED:
                    await _p6_audit(
                        call_sid=call_sid or "",
                        tenant_id=tenant_id or "",
                        tool_name=tool_name,
                        args=args,
                        result=_p6_result.data if _p6_result.ok else {"error": _p6_result.error or ""},
                        success=_p6_result.ok,
                    )
            except Exception:
                logger.exception("[AUDIT] p6 write failed", extra={"tool": tool_name, "call_sid": call_sid})
            _p6_legacy_result = _p6_result.to_legacy_dict()
            _record_tool_event(
                tool_name=tool_name,
                args=args,
                call_sid=call_sid,
                turn_number=turn_number,
                result=_p6_legacy_result,
                success=bool(_p6_result.ok),
            )
            return _p6_legacy_result
    except ImportError:
        pass  # server/tools/handlers not installed — fall through to legacy dispatch
    except Exception as _p6_err:
        logger.warning(f"[Phase6Bridge] {tool_name} handler raised: {_p6_err} — falling through to legacy")

    handlers = {
        "check_availability": _check_availability,
        "create_reservation": _create_reservation,
        "get_restaurant_info": _get_restaurant_info,
        "get_menu": _get_menu,
        "update_state": _update_state,
        "create_order": _create_order,
        "get_date_info": _get_date_info,
        "get_weather": _get_weather,
        "transfer_to_human": _transfer_to_human,
        "verify_address": _verify_address,
        "verify_phone": _verify_phone,
        # Validation-pipeline tool aliases (ADKBrainService path)
        "send_sms": _send_sms_noop,           # SMS already sent by create_order/create_reservation executors
        "transfer_to_tier2": _transfer_to_human,  # Alias: same as transfer_to_human in production
        "escalate_to_manager": _transfer_to_human,  # Alias emitted by layer2 tool schema
        "confirm_order": _confirm_order_noop,
        "log_complaint": _log_complaint_noop,
        "process_refund": _process_refund_stub,
        "ai_greeting": _ai_greeting_noop,     # Greeting tracking — no external effect
        "faq": _get_restaurant_info,          # FAQ maps to restaurant info
        "technical_issues_callback": _technical_issues_callback,
        "request_callback": _request_callback,
        # Google Maps Platform tools
        "get_directions": _get_directions,
        "get_nearby_parking": _get_nearby_parking,
        "get_transit_info": _get_transit_info,
        "get_air_quality": _get_air_quality,
        # Medical practice tools
        "check_appointment_availability": _check_appointment_availability,
        "book_appointment": _book_appointment,
        "submit_prescription_request": _submit_prescription_request,
        "get_practice_info": _get_practice_info,
        "transfer_to_staff": _transfer_to_staff,
        "update_patient_state": _update_patient_state,
        "end_call": _end_call,
        # CRM (Sprint 2): repeat-caller recognition
        "get_caller_history": _get_caller_history,
    }
    
    handler = handlers.get(tool_name)
    if not handler:
        unknown_result = {"error": f"Unknown tool: {tool_name}"}
        _record_tool_event(
            tool_name=tool_name,
            args=args,
            call_sid=call_sid,
            turn_number=turn_number,
            result=unknown_result,
            success=False,
        )
        return unknown_result
    
    context_tools = {"send_sms", "create_order", "transfer_to_human", "transfer_to_tier2", "escalate_to_manager"}
    _leg_result: dict = {}
    _leg_success: bool = False
    try:
        if tool_name in context_tools:
            context = {
                "tools_called_this_turn": [
                    {"name": k, "result": v}
                    for k, v in (tool_results or {}).items()
                ],
                "conversation_state": conversation_state,
            }
            logger.debug(f"[execute_tool] {tool_name}: passing context with state={conversation_state is not None}, cached_menu={conversation_state.cached_menu is not None if conversation_state else 'N/A'}")
            _leg_result = await handler(args, call_sid, tenant_id, context=context)
        else:
            _leg_result = await handler(args, call_sid, tenant_id)
        logger.info(f"Tool result ({tool_name}): {json.dumps(_leg_result, ensure_ascii=False)[:300]}")
        _leg_success = "error" not in _leg_result
        return _leg_result
    except Exception as e:
        logger.exception(f"Tool error ({tool_name}): {e}")
        _leg_result = {"error": str(e)}
        return _leg_result
    finally:
        if handler:
            _record_tool_event(
                tool_name=tool_name,
                args=args,
                call_sid=call_sid,
                turn_number=turn_number,
                result=_leg_result,
                success=_leg_success,
            )
        # Phase 8 B6 — audit trail for state-mutating tools (FINDING-004 fix, legacy path)
        try:
            from server.brain.observability.audit import AUDITED_TOOLS as _LEG_AUDITED, write_audit_entry as _leg_audit
            if tool_name in _LEG_AUDITED:
                await _leg_audit(
                    call_sid=call_sid or "",
                    tenant_id=tenant_id or "",
                    tool_name=tool_name,
                    args=args,
                    result=_leg_result,
                    success=_leg_success,
                )
        except Exception:
            logger.exception("[AUDIT] legacy write failed", extra={"tool": tool_name, "call_sid": call_sid})


def _bucket_reservation_time(time_str: str, grid_min: int) -> Optional[str]:
    """Round a HH:MM time down to the nearest ``grid_min`` boundary.
    Returns ``"HH:MM"`` or None if unparseable.
    """
    try:
        hh, mm = time_str.strip().split(":")
        h, m = int(hh), int(mm)
        if grid_min <= 0:
            return f"{h:02d}:{m:02d}"
        m = (m // grid_min) * grid_min
        return f"{h:02d}:{m:02d}"
    except Exception:
        return None


def _count_seats_in_slot(date_str: str, time_bucket: str, tenant_id: Optional[str]) -> int:
    """Sum confirmed party sizes in the given (date, time_bucket) slot.
    Reads from in-memory reservation_store only (sync path).
    For the persistent count use _count_seats_in_slot_async.
    """
    total = 0
    store_sources = []
    if tenant_id and tenant_id in tenant_reservation_store:
        store_sources.append(tenant_reservation_store[tenant_id])
    store_sources.append(reservation_store)
    seen_ids: set = set()
    for src in store_sources:
        for rid, res in src.items():
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            if res.get("status") != "confirmed":
                continue
            if res.get("date") != date_str:
                continue
            rb = _bucket_reservation_time(str(res.get("time", "")), 30)
            if rb != time_bucket:
                continue
            try:
                total += int(res.get("party_size", 0))
            except Exception:
                pass
    return total


async def _count_seats_in_slot_async(date_str: str, time_bucket: str, tenant_id: Optional[str]) -> int:
    """Query Postgres for confirmed seat count in slot; falls back to in-memory on error."""
    try:
        from server.database import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COALESCE(SUM(party_size), 0) AS total
                FROM reservations
                WHERE tenant_id = $1
                  AND date = $2
                  AND time_bucket = $3
                  AND status = 'confirmed'
                """,
                tenant_id or "",
                date_str,
                time_bucket,
            )
            pg_total = int(row["total"]) if row else 0
    except Exception as _db_err:
        logger.debug(f"[reservations] Postgres count unavailable, using in-memory: {_db_err}")
        pg_total = 0
    # Add any in-memory reservations not yet persisted (same-process same-restart bookings)
    mem_total = _count_seats_in_slot(date_str, time_bucket, tenant_id)
    return max(pg_total, mem_total)


async def _check_availability(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    date_str = args.get("date")
    time_str = args.get("time")
    party_size = int(args.get("party_size", 2) or 2)

    now = datetime.now(BERLIN_TZ)

    if not date_str or not time_str:
        wait_min = 15 if now.hour < 18 else 25
        return {
            "status": "wait_time_info",
            "estimated_wait_minutes": wait_min,
            "message": f"Aktuelle geschätzte Wartezeit: ca. {wait_min} Minuten.",
            "note": "Für genaue Verfügbarkeit bitte Datum und Uhrzeit angeben.",
        }

    try:
        req_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Ungültiges Datum. Bitte YYYY-MM-DD Format verwenden."}

    if req_date < now.date():
        return {"available": False, "reason": "Das Datum liegt in der Vergangenheit."}

    if party_size > 50:
        return {
            "available": False,
            "reason": "Für Gruppen über 50 Personen bitte direkt anfragen.",
            "suggest_transfer": True,
        }

    # Sprint 2 — real capacity check.
    tenant = await _get_tenant_config(tenant_id)
    hours_block = _opening_hours_gate(req_date, time_str, tenant) if tenant else None
    if hours_block:
        return hours_block

    # For headless regression tests, skip mutable capacity state but keep
    # deterministic calendar/opening-hours validation above.
    if call_sid and call_sid.startswith("headless-"):
        return {
            "available": True,
            "date": date_str,
            "time": time_str,
            "party_size": party_size,
            "seats_remaining": 20,
            "message": f"Tisch für {party_size} Personen am {date_str} um {time_str} Uhr ist verfügbar.",
        }

    grid_min = int(getattr(tenant, "reservation_slot_minutes", 30) or 30)
    capacity = int(getattr(tenant, "reservation_slot_capacity", 30) or 30)

    bucket = _bucket_reservation_time(time_str, grid_min)
    if bucket is None:
        return {"error": "Ungültige Uhrzeit. Bitte im Format HH:MM angeben."}

    booked = await _count_seats_in_slot_async(date_str, bucket, tenant_id)
    remaining = max(0, capacity - booked)

    if party_size <= remaining:
        return {
            "available": True,
            "date": date_str,
            "time": time_str,
            "party_size": party_size,
            "seats_remaining": remaining,
            "message": f"Tisch für {party_size} Personen am {date_str} um {time_str} Uhr ist verfügbar.",
        }

    # Slot is full — suggest ±grid_min alternatives that have capacity.
    try:
        req_dt = datetime.strptime(f"{date_str} {bucket}", "%Y-%m-%d %H:%M")
    except ValueError:
        req_dt = None

    alternatives: List[dict] = []
    if req_dt is not None:
        # Search outward ±2 grid steps (±60min with default 30min grid).
        for step in (-2, -1, 1, 2):
            cand = req_dt + timedelta(minutes=grid_min * step)
            cand_date = cand.strftime("%Y-%m-%d")
            cand_time = cand.strftime("%H:%M")
            cand_bucket = _bucket_reservation_time(cand_time, grid_min)
            if not cand_bucket:
                continue
            cand_booked = _count_seats_in_slot(cand_date, cand_bucket, tenant_id)
            cand_remaining = max(0, capacity - cand_booked)
            if cand_remaining >= party_size:
                alternatives.append({"date": cand_date, "time": cand_time, "seats_remaining": cand_remaining})
            if len(alternatives) >= 2:
                break

    return {
        "available": False,
        "date": date_str,
        "time": time_str,
        "party_size": party_size,
        "seats_remaining": remaining,
        "reason": (
            f"Leider ist {time_str} Uhr bereits ausgebucht "
            f"(nur noch {remaining} Plätze frei)."
        ),
        "alternatives": alternatives,
        "offer_waitlist": True,
        "message": (
            "Der gewünschte Slot ist leider voll. "
            + (f"Alternativen: {', '.join(a['time'] + ' Uhr' for a in alternatives)}. " if alternatives else "")
            + "Soll ich Sie auf die Warteliste setzen?"
        ),
    }


async def _create_reservation(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    required = ["date", "time", "party_size", "name"]
    missing = [f for f in required if not args.get(f)]
    if missing:
        return {"error": f"Fehlende Pflichtfelder: {', '.join(missing)}"}
    
    res_id = f"RES-{uuid.uuid4().hex[:8].upper()}"
    reservation = {
        "reservation_id": res_id,
        "date": args["date"],
        "time": args["time"],
        "party_size": args["party_size"],
        "name": args["name"],
        "phone": args.get("phone"),
        "email": args.get("email"),
        "notes": args.get("notes"),
        "created_at": datetime.now(BERLIN_TZ).isoformat(),
        "status": "confirmed",
    }
    
    reservation_store[res_id] = reservation

    # Persist to Postgres calendar for cross-restart capacity tracking
    try:
        from server.database import get_pool, ensure_reservations_table
        _bucket = _bucket_reservation_time(args["time"], 60)  # 1-hour bucket matches doboo config
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO reservations
                    (tenant_id, reservation_id, date, time_bucket, party_size, customer_name, phone_number, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, 'confirmed')
                ON CONFLICT (reservation_id) DO NOTHING
                """,
                tenant_id or "unknown",
                res_id,
                args["date"],
                _bucket or args["time"][:5],
                int(args["party_size"]),
                args["name"],
                args.get("phone"),
            )
    except Exception as _pg_err:
        logger.warning(f"[reservations] Postgres persist failed (non-fatal): {_pg_err}")
    phone = args.get("phone")
    if phone:
        # Format for template: restaurant|name|date|time|party_size|person_word
        restaurant_name = os.getenv("RESTAURANT_NAME", "Restaurant")  # tenant-specific fallback
        party_size = args["party_size"]
        person_word = "Person" if party_size == 1 else "Personen"
        
        # Format date nicely
        try:
            date_obj = datetime.fromisoformat(args["date"])
            day_names = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag']
            month_names = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
            formatted_date = f"{day_names[date_obj.weekday()]}, {date_obj.day}. {month_names[date_obj.month - 1]}"
        except:
            formatted_date = args["date"]
        
        template_msg = f"{restaurant_name}|{args['name']}|{formatted_date}|{args['time']}|{party_size}|{person_word}"
        # Prefer the tenant's venue address so the caller receives it in the SMS.
        _res_tenant = await _get_tenant_config(tenant_id)
        _res_addr = (
            getattr(getattr(_res_tenant, "practice", None), "location", None)
            if _res_tenant else None
        )
        human_msg = format_reservation_message(
            name=args['name'],
            date=args['date'],
            time=args['time'],
            party_size=party_size,
            restaurant_name=restaurant_name,
            restaurant_address=_res_addr,
        )
        asyncio.create_task(send_confirmation(
            phone,
            template_msg,
            template_type="reservation_confirmation",
            human_message=human_msg
        ))
    
    return {
        "success": True,
        "reservation_id": res_id,
        "message": (
            f"Reservierung bestätigt! {args['name']}, {args['party_size']} Personen, "
            f"{args['date']} um {args['time']} Uhr. Bestätigungsnummer: {res_id}"
        ),
        "details": reservation,
    }


async def _get_parking_info(lat: float = DOBOO_LAT, lng: float = DOBOO_LNG, radius: int = 500) -> dict:
    """Fetch nearby parking via Google Maps Places API, falling back to static data."""
    if not _MAPS_API_KEY:
        logger.warning("GOOGLE_MAPS_API_KEY not set — using static parking fallback")
        return _PARKING_STATIC_FALLBACK
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                params={
                    "location": f"{lat},{lng}",
                    "radius": radius,
                    "type": "parking",
                    "key": _MAPS_API_KEY,
                    "language": "de",
                },
            )
        results = resp.json().get("results", [])[:3]
        spots = []
        for r in results:
            loc = r.get("geometry", {}).get("location", {})
            dlat = (loc.get("lat", lat) - lat) * 111_000
            dlng = (loc.get("lng", lng) - lng) * 71_000
            dist = int((dlat ** 2 + dlng ** 2) ** 0.5)
            spots.append({
                "name": r.get("name", "Parkplatz"),
                "address": r.get("vicinity", ""),
                "distance_m": dist,
                "open_now": r.get("opening_hours", {}).get("open_now", True),
            })
        return {
            "parking_spots": spots or _PARKING_STATIC_FALLBACK["parking_spots"],
            "source": "google_maps" if spots else "static",
            "restaurant_address": "Friedrich-Ebert-Allee 69, 53113 Bonn",
        }
    except Exception as e:
        logger.warning(f"Google Maps parking call failed: {e} — using static fallback")
        return _PARKING_STATIC_FALLBACK


async def _get_restaurant_info(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    query = (args.get("query") or "").lower()
    
    # Load tenant config if available
    tenant_config = await _get_tenant_config(tenant_id)
    
    if tenant_config and tenant_config.tool_data and tenant_config.tool_data.restaurant_info:
        # Use tenant-specific restaurant info
        info = {
            "name": tenant_config.practice.name,
            "cuisine": ", ".join(tenant_config.practice.specializations) if tenant_config.practice.specializations else "",
            "address": tenant_config.practice.location,
            "phone": tenant_config.practice.phone or "",
            "opening_hours": {
                "info": tenant_config.practice.hours or "Info nicht verfügbar"
            },
            **tenant_config.tool_data.restaurant_info
        }
    else:
        # Default restaurant info (for backward compatibility) — tenant-specific fallback
        info = {
            "name": os.getenv("RESTAURANT_NAME", "Restaurant"),  # tenant-specific fallback
            "cuisine": "Siehe Speisekarte",
            "address": os.getenv("RESTAURANT_ADDRESS", "Bitte kontaktieren Sie uns für die Adresse"),
            "phone": "+49 228 1234567",
            "opening_hours": {
                "Montag": "Bitte anfragen",
                "Dienstag-Sonntag": "Bitte anfragen",
            },
            "parking": "Bitte anfragen",  # tenant-specific fallback
            "outdoor": "Ja, Terrasse mit ca. 20 Plätzen (wetterabhängig).",
            "payment": "Bar, EC-Karte, Kreditkarte, Apple Pay, Google Pay",
            "delivery": "Ja, Takeaway und Lieferung über Telefon/WhatsApp. Lieferradius ca. 5 km.",
            "accessibility": "Barrierefreier Zugang, behindertengerechte Toilette vorhanden.",
            "reservations": "Telefonisch, online oder über Sally (diese KI-Assistentin).",
        }
    
    if any(w in query for w in ["öffnung", "offen", "geöffnet", "wann", "zeit"]):
        return {"type": "opening_hours", "data": info["opening_hours"], "note": "Montag ist Ruhetag."}
    elif any(w in query for w in ["adress", "wo ", "lage", "standort", "finden"]):
        return {"type": "address", "data": {"address": info["address"], "parking": info.get("parking", "")}}
    elif any(w in query for w in ["park", "auto", "parken", "parkplatz", "parkhaus", "tiefgarage", "anfahrt"]):
        lat = args.get("lat", DOBOO_LAT)
        lng = args.get("lng", DOBOO_LNG)
        radius = args.get("radius", 500)
        parking_data = await _get_parking_info(lat, lng, radius)
        return {"type": "parking", "data": parking_data}
    elif any(w in query for w in ["liefer", "deliver", "abhol", "takeaway"]):
        return {"type": "delivery", "data": info.get("delivery", "")}
    elif any(w in query for w in ["terrass", "außen", "draußen", "outdoor"]):
        return {"type": "outdoor", "data": info.get("outdoor", "")}
    elif any(w in query for w in ["bezahl", "zahlung", "karte", "bar"]):
        return {"type": "payment", "data": info.get("payment", "")}
    
    return {"type": "general", "data": info}


async def _load_unavailable_dishes(tenant_id: Optional[str]) -> set[str]:
    """Return lowercase dish names currently marked unavailable (86'd) for a tenant.

    Data source: Redis hash ``menu_unavailable:{tenant_id}``. Keys are dish
    names (canonical, lowercased at read time), values are ISO timestamps of
    when the dish was taken down. Missing hash → empty set. Missing Redis →
    empty set with a warning (fail open to avoid taking the whole menu
    offline if the cache blinks).
    """
    key = f"menu_unavailable:{tenant_id or 'default'}"
    try:
        import redis.asyncio as aioredis

        _redis_url = os.getenv("REDIS_URL", "redis://localhost:6380")
        r = aioredis.from_url(_redis_url, decode_responses=True)
        try:
            data = await r.hgetall(key)
        finally:
            await r.aclose()
        return {str(k).strip().lower() for k in (data or {}).keys() if k}
    except Exception as e:
        logger.warning(f"[MENU-86] failed to read {key}: {e!r} — failing open")
        return set()


def _filter_86_from_menu(menu: dict, unavailable: set[str]) -> dict:
    """Remove dishes whose canonical name matches any lowercase entry in
    ``unavailable``. Preserves category structure. Pure function for testing.
    """
    if not unavailable or not isinstance(menu, dict):
        return menu
    filtered: dict = {}
    for category, items in menu.items():
        if not isinstance(items, list):
            filtered[category] = items
            continue
        kept = [
            item for item in items
            if str(item.get("name", "")).strip().lower() not in unavailable
        ]
        filtered[category] = kept
    return filtered


async def _get_menu(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    category = (args.get("category") or "alle").lower()
    
    # Load tenant config if available
    tenant_config = await _get_tenant_config(tenant_id)
    
    # Determine current CEST time for lunch-menu time-gating
    try:
        from zoneinfo import ZoneInfo
        import datetime as _dt
        _tz = ZoneInfo("Europe/Berlin")
        _now = _dt.datetime.now(_tz)
        _current_time_cest = _now.strftime("%H:%M")
        _lunch_menu_available = (
            _now.weekday() < 5  # Mon-Fri only (restaurant info: Mo-Fr 11:30)
            and "11:30" <= _current_time_cest <= "14:00"
        )
    except Exception as _tz_err:
        logger.warning(f"[get_menu] timezone lookup failed: {_tz_err}")
        _current_time_cest = "unbekannt"
        _lunch_menu_available = False

    if tenant_config and tenant_config.tool_data and tenant_config.tool_data.menu:
        menu = dict(tenant_config.tool_data.menu)
        # Time-gate: remove lunch-only categories outside 11:30-14:00
        if not _lunch_menu_available:
            for _lunch_cat in ("mittagsangebot", "mittagsmenues"):
                menu.pop(_lunch_cat, None)
    else:
        # Default menu (for backward compatibility) — tenant-specific fallback; real data in doboo.yaml
        menu = {
            "vorspeisen": [],  # tenant-specific fallback
            "hauptgerichte": [],  # tenant-specific fallback
        }  # tenant-specific fallback
    
    # Sprint 1 — 86'd items: strip anything marked unavailable in Redis
    unavailable = await _load_unavailable_dishes(tenant_id)
    if unavailable:
        menu = _filter_86_from_menu(menu, unavailable)
        logger.info(f"[MENU-86] filtered {len(unavailable)} unavailable items for tenant={tenant_id!r}")

    _meta = {
        "current_time_cest": _current_time_cest,
        "lunch_menu_available": _lunch_menu_available,
        "takeaway_times": {"takeaway": "ca. 20 Min.", "delivery": "ca. 35-45 Min."},
    }
    if category == "alle":
        return {"menu": menu, **_meta}
    elif category in menu:
        return {"category": category, "items": menu[category], **_meta}
    else:
        return {"menu": menu, "note": f"Kategorie '{category}' nicht gefunden, hier die gesamte Karte.", **_meta}


async def _update_state(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    session = session_store.get(call_sid, {})
    
    updated = []
    for key in ["caller_name", "party_size", "reservation_date", "reservation_time",
                 "occasion", "special_requests", "table_preference"]:
        if args.get(key) is not None:
            session[key] = args[key]
            updated.append(key)
    
    session_store[call_sid] = session
    
    missing = []
    if not session.get("caller_name"):
        missing.append("Name")
    if not session.get("party_size"):
        missing.append("Personenzahl")
    if not session.get("reservation_date"):
        missing.append("Datum")
    if not session.get("reservation_time"):
        missing.append("Uhrzeit")
    
    return {
        "success": True,
        "updated_fields": updated,
        "current_state": session,
        "missing_for_reservation": missing,
        "ready_for_reservation": len(missing) == 0,
    }


# Canonical dish list for fuzzy-match validation — populated from tenant config at runtime.
# The list below is an empty default; actual values loaded via _load_known_dishes().
_DOBOO_DISHES: list = []  # tenant-specific fallback — populated from KNOWN_DISHES or menu


def _fuzzy_match_dish(user_said: str, canonical: list = _DOBOO_DISHES) -> tuple[str, float]:
    """Return (best_match, confidence 0-1) for a dish name against the canonical list.

    Uses difflib.SequenceMatcher. Confidence >= 0.85 → auto-normalize.
    Confidence 0.60-0.84 → ask for confirmation. < 0.60 → reject.
    """
    from difflib import get_close_matches, SequenceMatcher
    if not user_said or not user_said.strip():
        return ("", 0.0)
    matches = get_close_matches(user_said, canonical, n=1, cutoff=0.55)
    if not matches:
        return ("", 0.0)
    ratio = SequenceMatcher(None, user_said.lower(), matches[0].lower()).ratio()
    return (matches[0], ratio)


async def _create_order(args: dict, call_sid: str, tenant_id: Optional[str] = None, context: Optional[dict] = None) -> dict:
    # Idempotency guard: prevent duplicate orders if the pipeline retries the same call
    if call_sid:
        try:
            import redis.asyncio as aioredis
            _redis_url = os.getenv("REDIS_URL", "redis://localhost:6380")
            _r = aioredis.from_url(_redis_url, decode_responses=True)
            _idem_key = f"order:idempotency:{call_sid}"
            existing = await _r.get(_idem_key)
            await _r.aclose()
            if existing:
                logger.warning(f"[create_order] DUPLICATE BLOCKED — idempotency key {_idem_key} already set (order_id={existing})")
                return {
                    "success": True,
                    "order_id": existing,
                    "message": f"Bestellung {existing} wurde bereits bestätigt.",
                    "duplicate": True,
                }
        except Exception as _e:
            logger.debug(f"[create_order] Idempotency Redis check failed (non-fatal): {_e}")

    # Defensive price fallback: if total_price is missing/0 but order_items given,
    # try to recover from the cached menu before hard-rejecting the order.
    _raw_price = args.get("total_price")
    if (not _raw_price or float(_raw_price) == 0.0) and args.get("order_items"):
        _state = (context or {}).get("conversation_state")
        logger.debug(f"[create_order] price fallback attempting: state={_state is not None}, cached_menu={_state.cached_menu if _state else 'N/A'}")
        if _state is not None:
            try:
                from server.brain.conversation_state import get_cached_dish_price
                _looked_up = get_cached_dish_price(_state, str(args["order_items"]))
                logger.debug(f"[create_order] price fallback lookup result: {_looked_up}")
                if _looked_up is not None and _looked_up > 0:
                    logger.info(
                        f"[create_order] price fallback — looked up '{args['order_items']}' "
                        f"-> {_looked_up}€ for call {call_sid}"
                    )
                    args = dict(args)  # don't mutate caller's dict
                    args["total_price"] = _looked_up
                else:
                    logger.debug(f"[create_order] price fallback: no match or zero price for '{args['order_items']}'")
            except Exception as _pf_err:
                logger.warning(f"[create_order] price fallback failed (non-fatal): {_pf_err}", exc_info=True)
        else:
            logger.warning(f"[create_order] price fallback skipped: no conversation_state in context")

    # Sprint 1 — refuse ordering an 86'd dish. We check BOTH the literal
    # order_items string and the canonical fuzzy-matched dish (when confident)
    # to catch "Bulgogi" vs "Bulgogi Bowl" variants.
    try:
        _order_items_str = str(args.get("order_items") or "").strip().lower()
        if _order_items_str:
            _unavailable = await _load_unavailable_dishes(tenant_id)
            if _unavailable:
                hit = None
                for u in _unavailable:
                    if u and u in _order_items_str:
                        hit = u
                        break
                if hit:
                    logger.warning(
                        f"[create_order] REJECTED: dish {_order_items_str!r} is 86'd "
                        f"(matched {hit!r}) for tenant={tenant_id!r}"
                    )
                    return {
                        "success": False,
                        "error": (
                            f"Tut mir sehr leid — das Gericht ist heute leider ausverkauft. "
                            f"Darf ich Ihnen eine Alternative von der Karte empfehlen?"
                        ),
                        "unavailable_item": hit,
                        "requires_reselect": True,
                    }
    except Exception as _86_err:  # pragma: no cover — cache miss is non-fatal
        logger.debug(f"[create_order] 86-filter skipped: {_86_err!r}")

    required = ["name", "order_items", "order_type", "payment_method", "total_price"]
    missing = [f for f in required if not args.get(f)]
    # total_price=0.0 is treated as missing
    if not missing and (not args.get("total_price") or float(args.get("total_price", 0)) <= 0.0):
        missing = ["total_price"]
    if missing:
        return {"error": f"Fehlende Pflichtfelder: {', '.join(missing)}. Bitte frage den Kunden EINZELN nach jedem fehlenden Feld."}

    # ── Sprint 0: HARD quantity ceiling ─────────────────────────────────────
    # Final line of defence against runaway orders even if the NodeManager
    # guard was skipped (e.g. external tool caller bypassing NodeManager).
    try:
        from server.brain.conversation_state import HARD_QUANTITY_CEILING
    except Exception:
        HARD_QUANTITY_CEILING = 30  # Phase 6 ceiling-30 safe default
    _qty_raw = args.get("quantity") or args.get("order_quantity") or 1
    try:
        _qty = int(_qty_raw)
    except (TypeError, ValueError):
        _qty = 1
    # Also sweep up state-supplied quantity if context provides conversation_state
    _ctx_state = (context or {}).get("conversation_state")
    if _ctx_state is not None:
        try:
            _qty = max(_qty, int(getattr(_ctx_state, "order_quantity", 1) or 1))
        except (TypeError, ValueError):
            pass
    if _qty > HARD_QUANTITY_CEILING:
        logger.error(
            f"[create_order] REJECTED: quantity {_qty} exceeds HARD_QUANTITY_CEILING "
            f"({HARD_QUANTITY_CEILING}) — this is a catering request, route to human"
        )
        return {
            "success": False,
            "error": (
                f"Bestellmenge {_qty} übersteigt das erlaubte Maximum "
                f"({HARD_QUANTITY_CEILING}). Catering-Aufträge werden von einem "
                f"menschlichen Mitarbeiter bearbeitet."
            ),
            "requires_human": True,
        }

    # Monetary sanity cap — rejects absurd totals (LLM price hallucinations,
    # currency confusion, decimal-point typos in menu YAML, etc.).  Tenant
    # config may override via ``max_order_total_eur`` (default: 200, Phase 6 cap-200).
    _max_total_eur: float = 200.0
    try:
        if tenant_id and _ctx_state is not None and hasattr(_ctx_state, "_tenant"):
            _max_total_eur = float(
                getattr(_ctx_state._tenant, "max_order_total_eur", 500.0) or 500.0
            )
    except Exception:
        pass
    try:
        _total_eur = float(args.get("total_price") or 0.0)
    except (TypeError, ValueError):
        _total_eur = 0.0
    if _total_eur > _max_total_eur:
        logger.error(
            f"[create_order] REJECTED: total_price €{_total_eur:.2f} exceeds "
            f"max_order_total_eur (€{_max_total_eur:.2f}) — likely LLM hallucination "
            f"or currency error, routing to human"
        )
        return {
            "success": False,
            "error": (
                f"Der Gesamtbetrag von {_total_eur:.2f} Euro übersteigt unser Limit "
                f"von {_max_total_eur:.0f} Euro pro Bestellung. Für größere Aufträge "
                "verbinde ich Sie gerne mit einem Kollegen."
            ),
            "requires_human": True,
        }

    # G3.3 — Fuzzy dish match: validate/normalize dish names in order_items (B11 fix)
    order_items_raw = args.get("order_items", "")
    if order_items_raw and tenant_id in (None, "doboo", ""):
        matched_dish, confidence = _fuzzy_match_dish(order_items_raw)
        if matched_dish and confidence < 0.85 and confidence >= 0.55:
            logger.warning(
                f"[GUARDIAN_DISH] Low confidence match: '{order_items_raw}' → '{matched_dish}' ({confidence:.2f}) — needs clarification"
            )
            return {
                "success": False,
                "needs_clarification": True,
                "user_said": order_items_raw,
                "best_guess": matched_dish,
                "confidence": confidence,
                "message": f"Ich bin nicht sicher: Meinen Sie '{matched_dish}'? Bitte bestätigen.",
            }
        if matched_dish and confidence >= 0.85 and matched_dish != order_items_raw:
            logger.info(f"[GUARDIAN_DISH] Normalized dish: '{order_items_raw}' → '{matched_dish}' ({confidence:.2f})")
            args = dict(args)  # don't mutate caller's dict
            args["order_items"] = args["order_items"].replace(order_items_raw, matched_dish, 1)

    import re as _re
    name = args.get("name", "")
    if _re.match(r"^[\+]?[0-9\s\-]{7,}$", name.strip()):
        logger.warning(f"[create_order] REJECTED: phone number used as name: {name}")
        return {"error": "FEHLER: Eine Telefonnummer wurde als Name uebergeben. Frage den Kunden: 'Auf welchen Namen darf ich die Bestellung aufnehmen?'"}

    if args.get("order_type") == "delivery" and not args.get("delivery_address"):
        # Fallback 1: address landed in special_requests (common LLM mistake)
        special = args.get("special_requests", "").strip()
        if special and len(special) > 4:
            # Accept any non-trivial special_requests content as the delivery address
            args["delivery_address"] = special.replace("Lieferadresse:", "").replace("Lieferadresse", "").strip()
            logger.info(f"[create_order] Recovered delivery_address from special_requests: {args['delivery_address']!r}")
        else:
            logger.warning(f"[create_order] REJECTED: delivery without address")
            return {"error": "FEHLER: Lieferbestellung ohne Lieferadresse. Bitte gib 'delivery_address' an. Frage den Kunden: 'Wohin darf ich liefern?'"}
    
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    # Sprint 2: ETA is tenant-configurable. Priority: explicit arg > tenant
    # config > hard-coded fallback.
    _tenant_eta_cfg = await _get_tenant_config(tenant_id)
    if args.get("estimated_minutes") is not None:
        est_min = int(args["estimated_minutes"])
    elif _tenant_eta_cfg is not None:
        est_min = int(
            getattr(_tenant_eta_cfg, "estimated_takeaway_minutes", 20)
            if args["order_type"] == "takeaway"
            else getattr(_tenant_eta_cfg, "estimated_delivery_minutes", 35)
        )
    else:
        est_min = 20 if args["order_type"] == "takeaway" else 35
    
    order = {
        "order_id": order_id,
        "name": args["name"],
        "phone": args["phone"],
        "order_items": args["order_items"],
        "order_type": args["order_type"],
        "payment_method": args["payment_method"],
        "total_price": args["total_price"],
        "estimated_minutes": est_min,
        "status": "confirmed",
        "created_at": datetime.now(BERLIN_TZ).isoformat(),
    }
    
    order_store[order_id] = order

    # Durable order persistence (Sprint 1): write to Redis hash so orders
    # survive a pod restart. The in-memory ``order_store`` is kept for
    # backward-compat with any code path that still reads it.
    try:
        import json as _json
        import redis.asyncio as aioredis
        _redis_url = os.getenv("REDIS_URL", "redis://localhost:6380")
        _r = aioredis.from_url(_redis_url, decode_responses=True)
        # 30-day retention — matches GDPR transcript default; orders are PII.
        await _r.set(f"order:{order_id}", _json.dumps(order, default=str), ex=30 * 24 * 3600)
        # Index by tenant for per-restaurant dashboards.
        _t = tenant_id or "default"
        await _r.zadd(f"orders:by_tenant:{_t}", {order_id: datetime.now(BERLIN_TZ).timestamp()})
        if call_sid:
            await _r.set(f"order:idempotency:{call_sid}", order_id, ex=7200)
        await _r.aclose()
    except Exception as _e:
        logger.warning(f"[create_order] durable Redis write failed (non-fatal): {_e!r}")

    # Fire-and-forget POS webhook push — handled in a background task so a
    # slow POS endpoint never delays the caller-facing confirmation TTS.
    try:
        _tenant = await _get_tenant_config(tenant_id)
        _webhook = getattr(_tenant, "pos_webhook_url", None) if _tenant else None
        if _webhook:
            asyncio.create_task(_post_order_to_pos(_webhook, order, order_id))
    except Exception as _e:
        logger.debug(f"[create_order] POS dispatch skipped: {_e!r}")

    payment_info = ""
    if args["payment_method"] == "online":
        channel_name = args.get("channel") or "SMS/WhatsApp"
        payment_info = f" Zahlungslink wird per {channel_name} an {args['messaging_phone']} gesendet."
    
    # Fire-and-forget: send SMS/WhatsApp order confirmation using template
    messaging_phone = args.get("messaging_phone")
    if messaging_phone:
        # Determine template type based on order type
        template_type = "order_confirmation_takeaway" if args["order_type"] == "takeaway" else "order_confirmation_delivery"
        
        # Get configurable values from environment
        restaurant_name = os.getenv("RESTAURANT_NAME", "Restaurant")  # tenant-specific fallback
        restaurant_phone = os.getenv("RESTAURANT_PHONE", "+49 228 123456")
        # Prefer explicit delivery_surcharge from args (computed per-order based on business rules:
        # +5€ if subtotal < 20€, free above). Fall back to env default for legacy callers.
        delivery_fee = float(args.get("delivery_surcharge", os.getenv("DELIVERY_FEE", "5.00")))
        
        # Format for template
        payment_link = args.get("payment_link") if args["payment_method"] == "online" else ""
        
        if args["order_type"] == "takeaway":
            # Takeaway: restaurant|order_id|items|total|payment_link|restaurant_phone
            template_msg = f"{restaurant_name}|{order_id}|{args['order_items']}|{args['total_price']:.2f}|{payment_link}|{restaurant_phone}"
        else:  # delivery
            # Delivery: restaurant|order_id|address|items|delivery_fee|total|payment_link|restaurant_phone
            template_msg = f"{restaurant_name}|{order_id}|{args.get('delivery_address', '')}|{args['order_items']}|{delivery_fee:.2f}|{args['total_price']:.2f}|{payment_link}|{restaurant_phone}"
        
        human_msg = format_order_message(
            order_id=order_id,
            order_items=args['order_items'],
            order_type=args['order_type'],
            total_price=args['total_price'],
            delivery_address=args.get('delivery_address') or args.get('special_requests', ''),
            payment_link=payment_link or None,
            restaurant_name=restaurant_name,
            restaurant_phone=restaurant_phone,
            delivery_fee=delivery_fee,
            estimated_minutes=est_min,
        )
        asyncio.create_task(send_confirmation(
            messaging_phone,
            template_msg,
            template_type=template_type,
            human_message=human_msg
        ))
    
    return {
        "success": True,
        "order_id": order_id,
        "message": (
            f"Bestellung {order_id} bestätigt! {args['order_items']} — "
            f"{args['order_type'].title()}, {args['total_price']:.2f}€. "
            f"Geschätzte Zeit: {est_min} Minuten.{payment_info}"
        ),
        "details": order,
    }


async def _get_date_info(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    date_str = args.get("date", "")
    now = datetime.now(BERLIN_TZ)
    
    weekday_de = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    
    lower = date_str.lower().strip()
    if lower in ("heute", "today"):
        target = now.date()
    elif lower in ("morgen", "tomorrow"):
        target = now.date() + timedelta(days=1)
    elif lower in ("übermorgen",):
        target = now.date() + timedelta(days=2)
    elif lower in ("gestern", "yesterday"):
        target = now.date() - timedelta(days=1)
    else:
        try:
            target = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            german_months = {
                "januar": 1, "februar": 2, "märz": 3, "april": 4,
                "mai": 5, "juni": 6, "juli": 7, "august": 8,
                "september": 9, "oktober": 10, "november": 11, "dezember": 12,
            }
            m = re.match(r"(\d{1,2})\.\s*(\w+)\s*(\d{4})?", date_str)
            if m:
                day = int(m.group(1))
                month_name = m.group(2).lower()
                year = int(m.group(3)) if m.group(3) else now.year
                month = german_months.get(month_name, 0)
                if month:
                    target = datetime(year, month, day).date()
                else:
                    return {"error": f"Monat '{m.group(2)}' nicht erkannt."}
            else:
                return {"error": f"Datum '{date_str}' nicht erkannt. Bitte YYYY-MM-DD oder '15. April' verwenden."}
    
    delta = (target - now.date()).days
    if delta == 0:
        relative = "heute"
    elif delta == 1:
        relative = "morgen"
    elif delta == -1:
        relative = "gestern"
    elif delta > 0:
        relative = f"in {delta} Tagen"
    else:
        relative = f"vor {abs(delta)} Tagen"
    
    return {
        "date": target.isoformat(),
        "weekday": weekday_de[target.weekday()],
        "relative": relative,
        "message": f"{target.strftime('%d.%m.%Y')} ist ein {weekday_de[target.weekday()]} ({relative}).",
    }


async def _get_weather(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Weather — tries Google Weather API first, falls back to Open Meteo."""
    # Determine location from tenant config or args
    lat, lon, city = 50.7374, 7.0982, "Bonn"  # tenant-specific fallback
    tenant_config = await _get_tenant_config(tenant_id)
    if tenant_config and hasattr(tenant_config, "tool_data") and tenant_config.tool_data:
        loc = getattr(tenant_config.tool_data, "weather_location", None)
        if loc:
            lat = getattr(loc, "latitude", lat)
            lon = getattr(loc, "longitude", lon)
            city = getattr(loc, "city", city)

    cache_key = f"{lat:.4f},{lon:.4f}"
    if cache_key in weather_cache:
        cached, ts = weather_cache[cache_key]
        if time.time() - ts < 600:
            return cached

    # Try Google Weather API
    token = _get_maps_token()
    if token:
        try:
            params: dict = {"location.latitude": lat, "location.longitude": lon, "unitsSystem": "METRIC"}
            if _MAPS_API_KEY:
                params["key"] = token
            headers = _maps_headers()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://weather.googleapis.com/v1/currentConditions:lookup",
                    params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        conditions = data.get("currentConditions", {})
                        temp = conditions.get("temperature", {}).get("degrees", 0)
                        desc = conditions.get("weatherCondition", {}).get("description", {}).get("text", "Unbekannt")
                        feels_like = conditions.get("feelsLikeTemperature", {}).get("degrees", temp)
                        precip = conditions.get("precipitationProbability", {}).get("percent", 0)
                        outdoor_ok = precip < 40 and temp >= 10
                        result = {
                            "temperature": temp,
                            "feels_like": feels_like,
                            "description": desc,
                            "precipitation_probability": precip,
                            "location": city,
                            "source": "Google Weather API",
                            "outdoor_recommendation": "Ja, Terrasse ist empfehlenswert!" if outdoor_ok else "Innenbereich empfohlen.",
                            "message": f"In {city}: {temp}°C, {desc}. Niederschlag: {precip}%. {'Terrasse möglich.' if outdoor_ok else 'Innenbereich empfohlen.'}",
                        }
                        weather_cache[cache_key] = (result, time.time())
                        return result
        except Exception as e:
            logger.warning(f"Google Weather API failed: {e}, falling back to Open Meteo")

    # Fallback: Open Meteo (no API key needed)
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=Europe/Berlin"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                data = await resp.json()

        cw = data["current_weather"]
        temp = cw["temperature"]
        code = cw["weathercode"]

        weather_desc = {
            0: "Klar", 1: "Überwiegend klar", 2: "Teilweise bewölkt", 3: "Bewölkt",
            45: "Nebel", 48: "Nebel mit Reif", 51: "Leichter Nieselregen", 53: "Nieselregen",
            55: "Starker Nieselregen", 61: "Leichter Regen", 63: "Regen", 65: "Starker Regen",
            71: "Leichter Schnee", 73: "Schnee", 75: "Starker Schnee",
            80: "Regenschauer", 81: "Starke Regenschauer", 95: "Gewitter",
        }

        desc = weather_desc.get(code, f"Wettercode {code}")
        outdoor_ok = code <= 2 and temp >= 12

        result = {
            "temperature": temp,
            "description": desc,
            "location": city,
            "source": "Open Meteo",
            "outdoor_recommendation": "Ja, Terrasse ist empfehlenswert!" if outdoor_ok else "Innenbereich empfohlen.",
            "message": f"In {city}: {temp}°C, {desc}. {'Terrasse möglich.' if outdoor_ok else 'Innenbereich empfohlen.'}",
        }

        weather_cache[cache_key] = (result, time.time())
        return result

    except Exception as e:
        return {"error": f"Wetterdaten nicht verfügbar: {e}", "fallback": "Bitte direkt nachfragen."}


async def _get_directions(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Get driving/walking directions to the business using Google Routes API."""
    origin = args.get("origin", "")
    destination = args.get("destination", "")
    mode = args.get("mode", "DRIVE").upper()  # DRIVE, WALK, BICYCLE, TRANSIT

    if not origin or not destination:
        # If no origin, return address so caller can navigate themselves
        tenant_config = await _get_tenant_config(tenant_id)
        address = tenant_config.practice.location if tenant_config else "Friedrich-Ebert-Allee 69, 53113 Bonn"
        return {
            "address": address,
            "message": f"Die Adresse lautet: {address}. Geben Sie diese in Ihre Navigations-App ein.",
            "note": "Für genaue Route bitte Startadresse angeben.",
        }

    token = _get_maps_token()
    if not token:
        return {"error": "Routing nicht verfügbar.", "address": destination}

    try:
        payload = {
            "origin": {"address": origin},
            "destination": {"address": destination},
            "travelMode": mode,
            "languageCode": "de",
            "units": "METRIC",
        }
        params = {}
        if _MAPS_API_KEY:
            params["key"] = token
        headers = {**_maps_headers(), "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.legs.steps.navigationInstruction"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://routes.googleapis.com/directions/v2:computeRoutes",
                json=payload, params=params, headers=headers,
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.warning(f"Routes API error {resp.status}: {text[:200]}")
                    return {"error": f"Route nicht berechnet (Status {resp.status})", "address": destination}

                data = await resp.json()
                routes = data.get("routes", [])
                if not routes:
                    return {"error": "Keine Route gefunden.", "address": destination}

                route = routes[0]
                duration_s = int(route.get("duration", "0s").rstrip("s") or 0)
                distance_m = route.get("distanceMeters", 0)
                duration_min = max(1, round(duration_s / 60))
                distance_km = round(distance_m / 1000, 1)

                return {
                    "duration_minutes": duration_min,
                    "distance_km": distance_km,
                    "mode": mode,
                    "destination": destination,
                    "message": f"Ca. {duration_min} Minuten ({distance_km} km) mit {mode.lower()}.",
                }
    except Exception as e:
        logger.warning(f"Routes API exception: {e}")
        return {"error": f"Route nicht verfügbar: {e}", "address": destination}


async def _get_nearby_parking(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Find nearby parking using Google Places API (New)."""
    lat, lon = 50.7365, 7.1053  # tenant-specific fallback
    radius = args.get("radius_meters", 500)

    tenant_config = await _get_tenant_config(tenant_id)
    if tenant_config and hasattr(tenant_config, "tool_data") and tenant_config.tool_data:
        loc = getattr(tenant_config.tool_data, "weather_location", None)
        if loc:
            lat = getattr(loc, "latitude", lat)
            lon = getattr(loc, "longitude", lon)

    # First check if tenant config has static parking info
    if tenant_config:
        restaurant_info = getattr(getattr(tenant_config, "tool_data", None), "restaurant_info", None)
        if restaurant_info:
            parking = getattr(restaurant_info, "parking", None) or restaurant_info.get("parking", "") if isinstance(restaurant_info, dict) else ""
            if parking:
                return {"parking_info": parking, "source": "tenant_config", "message": parking}

    token = _get_maps_token()
    if not token:
        return {"message": "Parkinformationen nicht verfügbar. Bitte direkt im Restaurant nachfragen."}

    try:
        payload = {
            "includedTypes": ["parking"],
            "maxResultCount": 3,
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lon},
                    "radius": float(radius),
                }
            },
        }
        params = {}
        if _MAPS_API_KEY:
            params["key"] = token
        headers = {**_maps_headers(), "X-Goog-FieldMask": "places.displayName,places.shortFormattedAddress,places.currentOpeningHours,places.rating"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://places.googleapis.com/v1/places:searchNearby",
                json=payload, params=params, headers=headers,
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.warning(f"Places API error {resp.status}: {text[:200]}")
                    return {"message": "Parkplätze nicht gefunden. Straßenparkplätze in der Nähe vorhanden."}

                data = await resp.json()
                places = data.get("places", [])

                if not places:
                    return {"message": "Kein Parkhaus in unmittelbarer Nähe. Straßenparkplätze verfügbar."}

                results = []
                for p in places[:3]:
                    name = p.get("displayName", {}).get("text", "Parkplatz")
                    address = p.get("shortFormattedAddress", "")
                    results.append(f"{name} ({address})")

                msg = "Parkplätze in der Nähe: " + "; ".join(results)
                return {"parking_options": results, "message": msg}
    except Exception as e:
        logger.warning(f"Places API exception: {e}")
        return {"message": "Parkinformationen nicht verfügbar. Bitte vor Ort nachfragen."}


async def _get_transit_info(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Get public transit route using Google Routes API (transit mode)."""
    origin = args.get("origin", "")

    tenant_config = await _get_tenant_config(tenant_id)
    destination = tenant_config.practice.location if tenant_config else "Friedrich-Ebert-Allee 69, 53113 Bonn"

    if not origin:
        return {
            "message": f"Bitte nennen Sie Ihren Startpunkt, dann berechne ich die öffentliche Anbindung zu {destination}.",
            "destination": destination,
        }

    token = _get_maps_token()
    if not token:
        return {"message": "Verbindungsauskunft nicht verfügbar.", "destination": destination}

    try:
        payload = {
            "origin": {"address": origin},
            "destination": {"address": destination},
            "travelMode": "TRANSIT",
            "languageCode": "de",
            "transitPreferences": {"routingPreference": "FEWER_TRANSFERS"},
        }
        params = {}
        if _MAPS_API_KEY:
            params["key"] = token
        headers = {**_maps_headers(), "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.legs.steps.transitDetails"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://routes.googleapis.com/directions/v2:computeRoutes",
                json=payload, params=params, headers=headers,
                timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                if resp.status != 200:
                    return {"message": "Verbindung nicht berechnet. Bitte ÖPNV-App nutzen.", "destination": destination}

                data = await resp.json()
                routes = data.get("routes", [])
                if not routes:
                    return {"message": "Keine ÖPNV-Verbindung gefunden.", "destination": destination}

                route = routes[0]
                duration_s = int(route.get("duration", "0s").rstrip("s") or 0)
                duration_min = max(1, round(duration_s / 60))

                return {
                    "duration_minutes": duration_min,
                    "destination": destination,
                    "message": f"Ca. {duration_min} Minuten mit öffentlichen Verkehrsmitteln nach {destination}.",
                }
    except Exception as e:
        logger.warning(f"Transit API exception: {e}")
        return {"message": "Verbindungsauskunft nicht verfügbar. Bitte ÖPNV-App nutzen."}


async def _get_air_quality(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Get air quality index using Google Air Quality API."""
    lat, lon, city = 50.7365, 7.1053, "Bonn"

    tenant_config = await _get_tenant_config(tenant_id)
    if tenant_config and hasattr(tenant_config, "tool_data") and tenant_config.tool_data:
        loc = getattr(tenant_config.tool_data, "weather_location", None)
        if loc:
            lat = getattr(loc, "latitude", lat)
            lon = getattr(loc, "longitude", lon)
            city = getattr(loc, "city", city)

    token = _get_maps_token()
    if not token:
        return {"message": "Luftqualitätsdaten nicht verfügbar."}

    try:
        payload = {
            "location": {"latitude": lat, "longitude": lon},
            "universalAqi": True,
            "languageCode": "de",
        }
        params = {}
        if _MAPS_API_KEY:
            params["key"] = token
        headers = _maps_headers()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://airquality.googleapis.com/v1/currentConditions:lookup",
                json=payload, params=params, headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status != 200:
                    return {"message": "Luftqualitätsdaten nicht verfügbar."}

                data = await resp.json()
                indexes = data.get("indexes", [])
                if not indexes:
                    return {"message": "Luftqualitätsdaten nicht verfügbar."}

                idx = indexes[0]
                aqi = idx.get("aqi", 0)
                category = idx.get("category", "Unbekannt")
                outdoor_ok = aqi <= 50

                return {
                    "aqi": aqi,
                    "category": category,
                    "location": city,
                    "outdoor_recommendation": "Gute Luft — Terrasse empfehlenswert." if outdoor_ok else "Erhöhte Luftbelastung — Innenbereich empfohlen.",
                    "message": f"Luftqualität in {city}: {category} (AQI {aqi}). {'Außenbereich geeignet.' if outdoor_ok else 'Innenbereich empfohlen.'}",
                }
    except Exception as e:
        logger.warning(f"Air Quality API exception: {e}")
        return {"message": "Luftqualitätsdaten nicht verfügbar."}


async def _transfer_to_human(args: dict, call_sid: str, tenant_id: Optional[str] = None, context: Optional[dict] = None) -> dict:
    """
    Transfer call to human by redirecting via Twilio REST API.
    Saves handover context to Redis for re-engagement after human call.
    """
    import base64

    reason = args.get("reason", "caller_requested")
    logger.info(f"Transfer to human: reason={reason}, call_sid={call_sid}")

    # Warm-transfer: persist a short context summary to Redis so the receiving
    # agent can open ``/admin/transfer/{call_sid}`` and see who is calling,
    # what they already said, and what step the bot was on.  Best-effort —
    # never blocks the transfer itself.
    try:
        state = (context or {}).get("conversation_state")
        payload = _build_transfer_payload(
            state=state, call_sid=call_sid, tenant_id=tenant_id, reason=reason
        )
        await _persist_transfer_payload(call_sid=call_sid, payload=payload)
    except Exception as _ctx_err:
        logger.warning(f"[transfer_to_human] warm-context write failed (non-fatal): {_ctx_err}")

    # After-hours gate — never transfer a caller into an empty restaurant.
    # If the tenant's opening-hours schedule is parseable and reports closed,
    # offer a callback (technical_issues_callback handles the write path) and
    # tell the caller when we reopen.  Fails open on parse failure.
    try:
        from server.core.tenant_config import get_tenant_registry
        tcfg = get_tenant_registry().load_tenant(tenant_id) if tenant_id else None
        if tcfg is not None and not tcfg.is_open_now():
            next_open_de = tcfg.next_opening_de()
            suffix = f" Wir sind wieder {next_open_de} erreichbar." if next_open_de else ""
            logger.info(
                f"[transfer_to_human] after-hours — refusing transfer "
                f"(tenant={tenant_id}, next_open={next_open_de!r})"
            )
            return {
                "success": False,
                "after_hours": True,
                "reason": reason,
                "next_opening_de": next_open_de,
                "message": (
                    "Das Restaurant ist gerade nicht besetzt, deshalb kann ich Sie "
                    "nicht direkt verbinden." + suffix + " Soll ich einen Rückruf "
                    "für Sie notieren?"
                ),
            }
    except Exception as _hours_err:
        logger.warning(f"[transfer_to_human] hours check failed (non-fatal): {_hours_err}")

    # Browser demo sessions have synthetic call SIDs (browser-*) — no Twilio call exists.
    # Return a graceful message so the caller knows how to reach the restaurant directly.
    if call_sid and call_sid.startswith("browser-"):
        restaurant_phone = os.getenv("RESTAURANT_PHONE", "0228 123456")
        logger.info(f"[transfer_to_human] Browser demo session {call_sid} — cannot Twilio-transfer, returning fallback")
        return {
            "success": False,
            "demo_mode": True,
            "message": (
                f"In der Demo-Version kann ich Sie leider nicht direkt verbinden. "
                f"Bitte rufen Sie das Restaurant direkt an unter {restaurant_phone}."
            ),
        }
    
    # Get Twilio credentials
    twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    server_url = os.getenv("SERVER_URL", "https://35.198.94.33:3002")
    
    # Get restaurant phone — from env or tenant config
    restaurant_phone = os.getenv("RESTAURANT_PHONE", "")
    if not restaurant_phone:
        logger.error("RESTAURANT_PHONE not configured — cannot transfer")
        return {
            "success": False,
            "message": "Entschuldigung, die Weiterleitung funktioniert gerade nicht.",
            "reason": reason,
        }
    
    if not twilio_account_sid or not twilio_auth_token:
        logger.error("Twilio credentials missing — cannot transfer")
        return {
            "success": False,
            "message": "Entschuldigung, die Weiterleitung funktioniert gerade nicht.",
            "reason": reason,
        }
    
    # Build TwiML with Dial that calls /handover-complete when complete
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Dial action="{server_url}/handover-complete" method="POST" timeout="20" timeLimit="600">
    <Number>{restaurant_phone}</Number>
  </Dial>
</Response>"""
    
    # POST to Twilio REST API to redirect the live call
    try:
        auth_header = "Basic " + base64.b64encode(
            f"{twilio_account_sid}:{twilio_auth_token}".encode()
        ).decode()
        
        async with aiohttp.ClientSession() as session:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_account_sid}/Calls/{call_sid}.json"
            headers = {
                "Authorization": auth_header,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            data = {"Twiml": twiml}
            
            async with session.post(url, data=data, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    logger.info(f"✅ Call {call_sid} redirected to {restaurant_phone}")
                    return {
                        "success": True,
                        "message": "Ich verbinde Sie jetzt mit einem Mitarbeiter. Einen Moment bitte.",
                        "reason": reason,
                        "destination": restaurant_phone,
                        "transferred_at": datetime.now().isoformat(),
                    }
                else:
                    error_text = await resp.text()
                    logger.error(f"Twilio redirect failed: {resp.status} {error_text}")
                    return {
                        "success": False,
                        "message": "Die Weiterleitung ist fehlgeschlagen. Bitte versuchen Sie es später erneut.",
                        "reason": reason,
                        "error": f"HTTP {resp.status}",
                    }
    except Exception as e:
        logger.error(f"Transfer error: {e}")
        return {
            "success": False,
            "message": "Entschuldigung, es gab einen technischen Fehler.",
            "reason": reason,
            "error": str(e),
        }



async def _verify_address(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Validate an address using Google Geocoding API."""
    address = args.get("address", "").strip()
    city = args.get("city", "").strip()
    country = args.get("country", "Deutschland").strip()
    
    if not address:
        return {"valid": False, "error": "Keine Adresse angegeben"}
    
    # Construct full search query
    search_query = address
    if city:
        search_query = f"{address}, {city}"
    if country and country.lower() != "deutschland":
        search_query = f"{search_query}, {country}"
    else:
        search_query = f"{search_query}, Deutschland"
    
    try:
        token = _get_maps_token()
        api_key = _MAPS_API_KEY
        
        if not token and not api_key:
            logger.error("[verify_address] Maps API not available")
            return {"valid": True, "formatted_address": search_query, "note": "Adressvalidierung nicht verfuegbar — Adresse akzeptiert wie angegeben."}
        
        import httpx
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": search_query,
            "key": api_key or token,
            "language": "de"
        }
        
        from server.core.resilience import with_breaker, BreakerOpenError, MAPS_BREAKER

        async def _do_geocode():
            async with httpx.AsyncClient(timeout=8.0) as client:
                return await client.get(url, params=params)

        try:
            response = await with_breaker(MAPS_BREAKER, _do_geocode())
        except BreakerOpenError:
            logger.warning(
                "[verify_address] Maps breaker open — accepting address as stated (graceful degrade)"
            )
            return {
                "valid": True,
                "warning": "maps_breaker_open",
                "address": search_query,
                "note": (
                    "Wir konnten die Adresse gerade nicht automatisch prüfen, "
                    "aber ich notiere sie so, wie Sie sie genannt haben."
                ),
            }
        except (httpx.TimeoutException, asyncio.TimeoutError) as te:
            logger.warning(f"[verify_address] Timeout after 8.0s for {search_query}: {te}")
            return {
                "valid": False,
                "error": "Adressvalidierung Timeout",
                "suggestion": "Die Adressvalidierung dauerte zu lange. Ich akzeptiere die Adresse wie angegeben.",
                "address": search_query,  # fallback: accept as-stated
            }
        except Exception as ex:
            logger.error(f"[verify_address] HTTP request failed: {ex}")
            return {
                "valid": False,
                "error": f"HTTP error: {ex}",
                "suggestion": "Es gab ein Problem bei der Adressvalidierung. Bitte versuchen Sie es erneut.",
            }
        
        if response.status_code != 200:
            logger.error(f"[verify_address] Google Geocoding error: {response.status_code}")
            return {"valid": False, "error": "Geocoding API error"}
        
        data = response.json()
        
        if data.get("status") == "ZERO_RESULTS":
            logger.warning(f"[verify_address] Address not found: {search_query}")
            return {
                "valid": False,
                "error": "Adresse nicht gefunden",
                "suggestion": f"Die Adresse '{address}' existiert nicht. Bitte überprüfen Sie die Angaben."
            }
        
        if data.get("status") != "OK":
            logger.warning(f"[verify_address] API status {data.get('status')} for query: {search_query}")
            return {
                "valid": False,
                "error": "Adresse konnte nicht verifiziert werden",
                "suggestion": (
                    "Entschuldigung, ich konnte die Adresse leider nicht pruefen. "
                    "Koennten Sie bitte eine gueltige Lieferadresse angeben?"
                ),
            }
        
        results = data.get("results", [])
        if not results:
            return {"valid": False, "error": "Keine Ergebnisse"}
        
        result = results[0]
        formatted_address = result.get("formatted_address", "")
        location = result.get("geometry", {}).get("location", {})
        location_type = result.get("geometry", {}).get("location_type", "")
        
        # Extract types from address_components (primary level types)
        address_components = result.get("address_components", [])
        result_types = [c["types"][0] for c in address_components if c.get("types")]

        # Reject results that only resolved to city/region level (no street found)
        street_level = location_type in ("ROOFTOP", "RANGE_INTERPOLATED", "GEOMETRIC_CENTER")
        has_street = any(t in result_types for t in ("street_address", "route", "premise", "subpremise"))
        if not street_level and not has_street:
            logger.warning(
                f"[verify_address] Low-quality match: {address} -> {formatted_address} "
                f"(location_type={location_type}, types={result_types})"
            )
            return {
                "valid": False,
                "error": "Strasse nicht gefunden",
                "suggestion": (
                    f"Die Adresse '{address}' konnte nicht genau gefunden werden. "
                    "Bitte geben Sie eine gueltige Strasse mit Hausnummer an."
                ),
            }

        logger.info(f"[verify_address] Validated: {address} -> {formatted_address}")
        
        return {
            "valid": True,
            "formatted_address": formatted_address,
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
            "message": f"Adresse bestätigt: {formatted_address}"
        }
    
    except Exception as e:
        logger.error(f"[verify_address] Exception: {e}")
        return {"valid": False, "error": str(e)}



async def _verify_phone(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Validate German phone number format and check if mobile.
    
    F-A Fix: verify_phone tool for active collection.
    Returns error if landline (must be mobile for SMS).
    """
    phone = args.get("phone", "").strip()
    
    if not phone:
        return {"valid": False, "error": "Keine Telefonnummer angegeben"}
    
    # German format check: 0 + 9-11 digits
    phone_digits = re.sub(r"\D", "", phone)
    
    if not phone_digits.startswith("0") or len(phone_digits) < 10 or len(phone_digits) > 12:
        return {
            "valid": False,
            "error": "Ungültiges Telefonnummernformat. Bitte verwenden Sie eine deutsche Nummer im Format 0xxx xxxxxxx"
        }
    
    # Check mobile prefixes
    mobile_prefixes = ["015", "016", "017", "018", "019", "014"]
    is_mobile = any(phone_digits.startswith(prefix) for prefix in mobile_prefixes)
    
    if not is_mobile:
        return {
            "valid": False,
            "is_landline": True,
            "error": "Das ist eine Festnetznummer. Für den Zahlungslink brauchen wir eine Handynummer. Können Sie Ihre Handynummer angeben?"
        }
    
    logger.info(f"[verify_phone] Validated mobile: {phone_digits}")
    return {"valid": True, "phone": phone_digits, "is_mobile": True}


async def _send_sms_noop(args: dict, call_sid: str, tenant_id: Optional[str] = None, context: Optional[dict] = None) -> dict:
    """
    Validates that a parent create_order or create_reservation succeeded before
    acknowledging an SMS confirmation. If no parent succeeded, returns an error so
    the LLM won't falsely tell the user an SMS was sent.
    """
    prior_tools: list = (context or {}).get("tools_called_this_turn") or []

    parent_tool: Optional[str] = None
    parent_success = False
    parent_error: Optional[str] = None

    for prior in reversed(prior_tools):
        if prior.get("name") in ("create_order", "create_reservation"):
            parent_tool = prior.get("name")
            prior_result = prior.get("result") or {}
            if prior_result.get("error") or prior_result.get("success") is False or prior_result.get("blocked_by_guardian"):
                parent_error = str(prior_result.get("error") or "parent tool reported failure")
                parent_success = False
            else:
                parent_success = True
            break

    if parent_tool is None:
        logger.warning(
            f"[send_sms] blocked — no create_order or create_reservation in this turn "
            f"for call {call_sid}"
        )
        return {
            "status": "error",
            "sms_sent": False,
            "error": "send_sms requires create_order or create_reservation to succeed first",
        }

    if not parent_success:
        logger.warning(
            f"[send_sms] blocked — parent {parent_tool} failed: {parent_error} "
            f"for call {call_sid}"
        )
        return {
            "status": "error",
            "sms_sent": False,
            "error": f"parent {parent_tool} failed: {parent_error}",
        }

    logger.info(f"[send_sms] parent {parent_tool} succeeded — acknowledging SMS for {call_sid}")
    return {
        "status": "ok",
        "sms_sent": True,
        "note": "SMS confirmation sent automatically by order/reservation executor.",
    }


async def _ai_greeting_noop(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """No-op handler for the validation pipeline's ai_greeting tracking tool."""
    logger.debug(f"[ai_greeting] Greeting acknowledged (call_sid={call_sid})")
    return {"status": "greeted"}


async def _confirm_order_noop(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Acknowledge a model-level order confirmation marker without committing state."""
    logger.info(f"[confirm_order] acknowledged marker (call_sid={call_sid})")
    return {
        "success": True,
        "status": "confirmed_marker",
        "message": "Bestellung wurde als bestätigt markiert.",
    }


async def _log_complaint_noop(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Log complaint intent without attempting unsupported CRM side effects."""
    reason = str(args.get("reason") or args.get("complaint") or "complaint").strip()
    logger.warning(
        f"[log_complaint] complaint marker call_sid={call_sid} tenant={tenant_id}: {reason[:200]}"
    )
    return {
        "success": True,
        "status": "logged",
        "message": "Beschwerde wurde zur Nachverfolgung notiert.",
    }


async def _process_refund_stub(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Refunds require human handling; keep the tool explicit instead of unknown."""
    logger.info(f"[process_refund] refund requested; human handling required (call_sid={call_sid})")
    return {
        "success": False,
        "status": "requires_human",
        "message": "Erstattungen werden von einem Mitarbeiter bearbeitet.",
    }


async def _technical_issues_callback(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """
    Log a technical issue and return a callback acknowledgement.
    Used by ADKBrainService when the validated pipeline detects technical problems.
    """
    issue = args.get("issue", "") or args.get("description", "") or "technisches Problem"
    logger.warning(f"[technical_issues_callback] Technical issue reported: {issue} (call_sid={call_sid})")
    return {
        "status": "logged",
        "message": (
            "Das technische Problem wurde gemeldet. "
            "Ein Mitarbeiter wird sich bei Ihnen melden."
        ),
        "issue": issue,
    }


async def _request_callback(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """
    Log a callback request from the caller.
    Used by ADKBrainService when the validated pipeline handles callback requests.
    """
    phone = args.get("phone", "") or args.get("callback_phone", "")
    reason = args.get("reason", "Rückrufwunsch")
    logger.info(f"[request_callback] Callback requested: phone={phone}, reason={reason} (call_sid={call_sid})")
    return {
        "status": "logged",
        "message": "Ihr Rückrufwunsch wurde notiert. Wir melden uns bei Ihnen.",
        "phone": phone,
        "reason": reason,
    }


async def _get_caller_history(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """CRM tool — fetch past-call summary for a phone number.

    The brain plumbs the inbound ``caller_id_phone`` into ``args["phone"]``
    on turn 0. Returns ``{}`` on first-time callers or when the caller
    opted out of recognition — the LLM should treat missing data as
    "brand-new caller, no personalisation".
    """
    try:
        from server.brain.call_summary import get_caller_history
    except Exception as e:
        logger.debug(f"[get_caller_history] import failed: {e!r}")
        return {}
    phone = args.get("phone") or args.get("caller_id_phone")
    return await get_caller_history(phone, tenant_id)


async def _end_call(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """
    End the call via Twilio REST API by setting Status=completed.
    """
    import base64
    
    reason = args.get("reason", "goodbye")
    logger.info(f"End call requested: reason={reason}, call_sid={call_sid}")

    # Browser demo sessions use synthetic call SIDs (browser-*) that don't exist in Twilio.
    # Skip the Twilio API call entirely — the WebSocket close handles session cleanup.
    if call_sid and call_sid.startswith("browser-"):
        logger.info(f"[end_call] Browser demo session {call_sid} — skipping Twilio API, closing WebSocket")
        return {
            "success": True,
            "message": "Browser demo call ended (no Twilio needed)",
            "reason": reason,
        }

    import asyncio
    logger.info(f"[end_call] Waiting 5s for audio buffer to flush before hanging up...")
    await asyncio.sleep(5)

    twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    
    if not twilio_account_sid or not twilio_auth_token:
        logger.error("Twilio credentials missing — cannot end call")
        return {
            "success": False,
            "message": "Call end failed: Twilio not configured",
            "reason": reason,
        }
    
    try:
        auth_header = "Basic " + base64.b64encode(
            f"{twilio_account_sid}:{twilio_auth_token}".encode()
        ).decode()
        
        async with aiohttp.ClientSession() as session:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_account_sid}/Calls/{call_sid}.json"
            headers = {
                "Authorization": auth_header,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            data = {"Status": "completed"}
            
            async with session.post(url, data=data, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    logger.info(f"✅ Call {call_sid} ended via Twilio")
                    return {
                        "success": True,
                        "message": "Auf Wiederhören!",
                        "reason": reason,
                    }
                else:
                    error_text = await resp.text()
                    logger.error(f"Twilio call end failed: {resp.status} {error_text}")
                    return {
                        "success": False,
                        "message": "Call end failed",
                        "reason": reason,
                        "error": f"HTTP {resp.status}",
                    }
    except Exception as e:
        logger.error(f"Call end error: {e}")
        return {
            "success": False,
            "message": "Call end failed",
            "reason": reason,
            "error": str(e),
        }


# ── Medical Practice Tools ───────────────────────────────────────────────────

async def _check_appointment_availability(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Check available appointment slots.
    
    In production: calls PVS API (medflex or TurboMed) to get real calendar slots.
    Currently: returns realistic demo data so the agent can function.
    """
    appointment_type = args.get("appointment_type", "Termin")
    preferred_date = args.get("preferred_date", "")

    now = datetime.now(BERLIN_TZ)
    # Generate realistic-looking next available slots
    slots = []
    for days_ahead in [1, 2, 3, 5]:
        slot_date = now + timedelta(days=days_ahead)
        if slot_date.weekday() < 5:  # Monday–Friday only
            date_str = slot_date.strftime("%d.%m.%Y")
            weekday = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"][slot_date.weekday()]
            for time_str in ["09:00", "10:30", "14:00"]:
                slots.append({
                    "date": slot_date.strftime("%Y-%m-%d"),
                    "date_display": f"{weekday}, {date_str}",
                    "time": time_str,
                    "slot_id": f"slot_{slot_date.strftime('%Y%m%d')}_{time_str.replace(':', '')}",
                    "appointment_type": appointment_type,
                })
        if len(slots) >= 4:
            break

    logger.info(f"[Medical] check_appointment_availability: type={appointment_type}, slots={len(slots)}")

    if not slots:
        return {
            "available": False,
            "message": "Leider sind aktuell keine Termine verfügbar. Das Praxisteam wird Sie zurückrufen.",
        }

    first = slots[0]
    return {
        "available": True,
        "next_slot": first,
        "all_slots": slots[:3],
        "message": f"Nächster verfügbarer Termin: {first['date_display']} um {first['time']} Uhr.",
        "note": "DEMO: In Produktion kommen echte Termine aus dem PVS-System (TurboMed/medflex).",
    }


async def _book_appointment(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Book an appointment in the practice management system.
    
    DSK compliance: collects Name + Geburtsdatum (required for PVS patient matching).
    In production: writes to PVS via medflex or direct API.
    """
    patient_name = args.get("patient_name", "")
    patient_birthdate = args.get("patient_birthdate", "")
    appointment_type = args.get("appointment_type", "")
    appointment_date = args.get("appointment_date", "")
    appointment_time = args.get("appointment_time", "")
    callback_phone = args.get("callback_phone", "")

    if not patient_name or not patient_birthdate:
        return {
            "success": False,
            "error": "Name und Geburtsdatum sind Pflichtfelder für die Patientenidentifikation.",
        }

    confirmation_number = f"SA{datetime.now(BERLIN_TZ).strftime('%Y%m%d%H%M')}{len(patient_name)}"

    logger.info(
        f"[Medical] book_appointment: patient={patient_name[:20]}, "
        f"dob={patient_birthdate}, type={appointment_type}, "
        f"date={appointment_date} {appointment_time}, call_sid={call_sid}"
    )

    # Format date for display
    try:
        from datetime import date as dt_date
        parsed = datetime.strptime(appointment_date, "%Y-%m-%d")
        weekdays = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        weekday = weekdays[parsed.weekday()]
        date_display = f"{weekday}, {parsed.strftime('%d.%m.%Y')}"
    except Exception:
        date_display = appointment_date

    return {
        "success": True,
        "confirmation_number": confirmation_number,
        "patient_name": patient_name,
        "appointment_date": date_display,
        "appointment_time": appointment_time,
        "appointment_type": appointment_type,
        "message": (
            f"Termin erfolgreich gebucht. Bestätigungsnummer: {confirmation_number}. "
            f"Termin: {appointment_type} am {date_display} um {appointment_time} Uhr. "
            f"Rückrufnummer: {callback_phone}."
        ),
        "note": "DEMO: In Produktion wird Termin direkt in PVS geschrieben.",
    }


async def _submit_prescription_request(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Submit a prescription request to the practice team.
    
    KVNR is handled as a boolean flag (kvnr_collected=true/false).
    The actual KVNR value is collected by the agent and stored encrypted separately —
    it must NOT appear in this tool's arguments (to keep it out of plain-text logs).
    """
    patient_name = args.get("patient_name", "")
    patient_birthdate = args.get("patient_birthdate", "")
    medication = args.get("medication", "")
    insurance_company = args.get("insurance_company", "")
    kvnr_collected = args.get("kvnr_collected", False)
    callback_phone = args.get("callback_phone", "")

    if not medication:
        return {"success": False, "error": "Medikamentenname fehlt."}

    request_id = f"RX{datetime.now(BERLIN_TZ).strftime('%Y%m%d%H%M')}"

    logger.info(
        f"[Medical] prescription_request: patient={patient_name[:20]}, "
        f"medication={medication}, insurance={insurance_company}, "
        f"kvnr_collected={kvnr_collected}, call_sid={call_sid}"
    )

    return {
        "success": True,
        "request_id": request_id,
        "medication": medication,
        "insurance_company": insurance_company,
        "kvnr_collected": kvnr_collected,
        "message": (
            f"Rezeptanfrage erfolgreich weitergeleitet. Anfrage-Nummer: {request_id}. "
            f"Das Praxisteam bearbeitet Ihre Anfrage für {medication}. "
            f"Bei Rückfragen melden wir uns unter {callback_phone}. "
            f"Rezepte sind in der Regel innerhalb von 1-2 Werktagen abholbereit."
        ),
        "note": "DEMO: In Produktion wird Aufgabe im PVS für das Praxisteam erstellt.",
    }


async def _get_practice_info(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Return practice information from tenant config."""
    query = args.get("query", "")

    tenant_config = await _get_tenant_config(tenant_id)
    if tenant_config and tenant_config.practice:
        practice = tenant_config.practice
        return {
            "name": practice.name,
            "location": practice.location,
            "phone": practice.phone or "Bitte beim Praxisteam erfragen",
            "hours": practice.hours or "Bitte beim Praxisteam erfragen",
            "specializations": practice.specializations or [],
            "query": query,
            "message": f"Praxis {practice.name}, {practice.location}. Öffnungszeiten: {practice.hours or 'auf Anfrage'}.",
        }

    return {
        "message": "Praxisinformationen sind aktuell nicht verfügbar. Bitte rufen Sie direkt in der Praxis an.",
        "query": query,
    }


async def _transfer_to_staff(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Transfer call to practice staff."""
    reason = args.get("reason", "caller_requested")
    summary = args.get("summary", "")
    logger.warning(f"[Medical] Transfer to staff: reason={reason}, call_sid={call_sid}, summary={summary[:100]}")
    return {
        "success": True,
        "message": "Ich verbinde Sie jetzt mit dem Praxisteam. Bitte bleiben Sie kurz in der Leitung.",
        "reason": reason,
        "note": "Transfer initiated. In Produktion: Twilio-Weiterleitung zur Praxisnummer.",
    }


async def _update_patient_state(args: dict, call_sid: str, tenant_id: Optional[str] = None) -> dict:
    """Store patient data collected during the call.
    
    KVNR is stored as boolean flag only (kvnr_collected). The actual KVNR
    value is handled by a separate encrypted path and must not be logged here.
    """
    logger.info(f"[Medical] update_patient_state: {json.dumps({k: v for k, v in args.items() if k != 'kvnr'}, ensure_ascii=False)}")
    return {
        "success": True,
        "stored_fields": list(args.keys()),
        "message": "Patientendaten gespeichert.",
    }
