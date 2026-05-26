"""Post-call summary for CRM / repeat-caller recognition.

At the end of a call we persist a compact summary record per caller phone
number. The next time that number calls, the ``get_caller_history`` tool
surfaces last-order and last-reservation info so Sally can offer a warm
"welcome back" greeting.

Data model (Redis):
  Key:   ``caller_history:{tenant_id}:{e164_phone}``
  Value: JSON dict
    {
      "phone":            "+491701234567",
      "last_call_at":     "2026-04-21T14:32:01+02:00",
      "last_intent":      "order" | "reservation" | "faq" | ...,
      "last_dish":        "Bibimbap",
      "last_total_price": 29.80,
      "last_reservation": "2026-04-25 19:00",
      "party_size":       4,
      "call_count":       3,
      "opt_in_recognition": true
    }
  TTL:   matches TRANSCRIPT_RETENTION_DAYS (GDPR alignment).

All writes are idempotent upserts — a tenant's history only grows for real
callers, never synthetic demo sessions (those use the ``browser_demo``
placeholder which we filter out at write time).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from loguru import logger

try:
    import redis.asyncio as aioredis
except Exception:  # pragma: no cover
    aioredis = None  # type: ignore


_REDIS_URL_ENV = "REDIS_URL"
_DEFAULT_REDIS_URL = "redis://localhost:6380"
_PLACEHOLDER_PHONES = {"browser_demo", "", "unknown", None}


def _phone_ok(phone: Optional[str]) -> bool:
    return phone is not None and phone not in _PLACEHOLDER_PHONES and str(phone).strip() != ""


def _key(tenant_id: Optional[str], phone: str) -> str:
    return f"caller_history:{tenant_id or 'default'}:{phone.strip()}"


def _retention_seconds() -> int:
    try:
        days = int(os.getenv("TRANSCRIPT_RETENTION_DAYS", "90"))
    except ValueError:
        days = 90
    return max(1, days) * 24 * 3600


async def _get_redis():
    if aioredis is None:
        raise RuntimeError("redis.asyncio not available")
    return aioredis.from_url(os.getenv(_REDIS_URL_ENV, _DEFAULT_REDIS_URL), decode_responses=True)


def summarize_state(state: Any) -> Dict[str, Any]:
    """Extract the CRM-relevant fields from a ConversationState.

    Pure function — doesn't touch Redis. Kept separate so a unit test can
    drive it with a stub state object.
    """
    summary: Dict[str, Any] = {
        "last_intent": getattr(state, "last_intent", None) or (
            "order" if getattr(state, "order_intent", False) else
            "reservation" if getattr(state, "reservation_intent", False) else
            "faq"
        ),
        "last_dish": getattr(state, "selected_dish", None),
        "last_total_price": getattr(state, "total_price", None),
        "party_size": getattr(state, "party_size", None),
    }
    res_date = getattr(state, "reservation_date", None)
    res_time = getattr(state, "reservation_time", None)
    if res_date and res_time:
        summary["last_reservation"] = f"{res_date} {res_time}"
    return {k: v for k, v in summary.items() if v not in (None, "", 0)}


async def persist_call_summary(
    phone: Optional[str],
    state: Any,
    tenant_id: Optional[str] = None,
) -> bool:
    """Write a call summary keyed by caller phone. Returns True on success.

    Never raises — on any failure it logs and returns False so the caller
    (brain shutdown path) can continue cleanly.
    """
    if not _phone_ok(phone):
        return False
    try:
        r = await _get_redis()
    except Exception as e:
        logger.debug(f"[CRM] summary skipped, no Redis: {e!r}")
        return False
    key = _key(tenant_id, str(phone))
    try:
        raw = await r.get(key)
        existing: Dict[str, Any] = {}
        if raw:
            try:
                existing = json.loads(raw)
            except Exception:
                existing = {}
        existing.update(summarize_state(state))
        existing["phone"] = str(phone)
        existing["last_call_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        existing["call_count"] = int(existing.get("call_count", 0)) + 1
        # Opt-in defaults to True — §a(1) LfDI guidance treats basic repeat-
        # caller recognition as a legitimate-interest data use, but we still
        # let callers say "vergessen Sie mich" to flip this off.
        existing.setdefault("opt_in_recognition", True)
        await r.set(key, json.dumps(existing, ensure_ascii=False, default=str), ex=_retention_seconds())
        logger.info(f"[CRM] summary upserted phone={phone} tenant={tenant_id} call_count={existing['call_count']}")
        return True
    except Exception as e:
        logger.warning(f"[CRM] persist failed: {e!r}")
        return False
    finally:
        try:
            await r.aclose()
        except Exception:
            pass


async def get_caller_history(
    phone: Optional[str],
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch a caller's historic summary. Returns ``{}`` when unknown.

    Exposed as the Category A tool ``get_caller_history`` — the brain pulls
    it on the first turn whenever ``caller_id_phone`` is set.
    """
    if not _phone_ok(phone):
        return {}
    try:
        r = await _get_redis()
    except Exception:
        return {}
    try:
        raw = await r.get(_key(tenant_id, str(phone)))
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except Exception:
            return {}
        if not data.get("opt_in_recognition", True):
            return {}
        return data
    except Exception as e:
        logger.debug(f"[CRM] fetch failed: {e!r}")
        return {}
    finally:
        try:
            await r.aclose()
        except Exception:
            pass


async def forget_caller(
    phone: Optional[str],
    tenant_id: Optional[str] = None,
) -> bool:
    """GDPR Art. 17 right-to-erasure — wipe CRM record for a caller."""
    if not _phone_ok(phone):
        return False
    try:
        r = await _get_redis()
    except Exception:
        return False
    try:
        deleted = await r.delete(_key(tenant_id, str(phone)))
        logger.info(f"[CRM] forget_caller phone={phone} tenant={tenant_id} deleted={deleted}")
        return bool(deleted)
    except Exception as e:
        logger.warning(f"[CRM] forget failed: {e!r}")
        return False
    finally:
        try:
            await r.aclose()
        except Exception:
            pass
