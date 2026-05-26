"""
Live call trace — validation-loop-style timeline + checkpoints in Redis.

Each real call gets an append-only list ``live_trace:{call_sid}`` (or ``{tenant}:live_trace:{call_sid}``)
so interrupts, drops, and gate blocks are visible without waiting for session.end().

Use :func:`read_trace_cli_summary` from ``scripts/read_live_call_trace.py`` or
``GET /api/dashboard/live/{call_sid}/trace``.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from zoneinfo import ZoneInfo

from loguru import logger

BERLIN_TZ = ZoneInfo("Europe/Berlin")

_LIVE_TRACE_ENABLE = os.getenv("LIVE_TRACE_ENABLE", "1").lower() not in ("0", "false", "no")
_LIVE_TRACE_MAX_EVENTS = int(os.getenv("LIVE_TRACE_MAX_EVENTS", "2500"))
_LIVE_TRACE_STRING_MAX = int(os.getenv("LIVE_TRACE_STRING_MAX", "500"))


def live_trace_enabled() -> bool:
    return _LIVE_TRACE_ENABLE


def live_trace_key(tenant_id: Optional[str], call_sid: str) -> str:
    if tenant_id:
        return f"{tenant_id}:live_trace:{call_sid}"
    return f"live_trace:{call_sid}"


def _truncate(s: str, n: int = _LIVE_TRACE_STRING_MAX) -> str:
    if len(s) <= n:
        return s
    return s[: n - 3] + "..."


def _sanitize_detail(obj: Any, depth: int = 0) -> Any:
    if depth > 4:
        return "<max_depth>"
    if obj is None:
        return None
    if isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        return _truncate(obj)
    if isinstance(obj, dict):
        return {str(k): _sanitize_detail(v, depth + 1) for k, v in list(obj.items())[:40]}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_detail(x, depth + 1) for x in obj[:50]]
    return _truncate(str(obj))


async def append_live_event(
    redis,
    tenant_id: Optional[str],
    call_sid: str,
    phase: str,
    event: str,
    detail: Any = None,
    level: str = "info",
) -> None:
    if not _LIVE_TRACE_ENABLE or not call_sid or call_sid == "unknown":
        return
    try:
        key = live_trace_key(tenant_id, call_sid)
        payload = {
            "ts": time.time(),
            "iso": datetime.now(BERLIN_TZ).isoformat(),
            "phase": phase,
            "event": event,
            "level": level,
            "detail": _sanitize_detail(detail),
        }
        await redis.rpush(key, json.dumps(payload, ensure_ascii=False))
        await redis.expire(key, 86400)
        await redis.ltrim(key, -_LIVE_TRACE_MAX_EVENTS, -1)
    except Exception as e:
        logger.debug(f"[LiveTrace] append skipped: {e}")


async def checkpoint_from_session(
    redis,
    tenant_id: Optional[str],
    call_sid: str,
    name: str,
    *,
    reason: str = "",
    session_data: Optional[dict] = None,
    level: str = "info",
) -> None:
    """Persist a snapshot checkpoint (works even if the call never reaches session.end)."""
    if not _LIVE_TRACE_ENABLE or not call_sid or call_sid == "unknown":
        return
    data = session_data or {}
    tcalls = data.get("tool_calls") or []
    trans = data.get("transcripts") or []
    last_user = ""
    for t in reversed(trans):
        if t.get("role") == "user":
            last_user = str(t.get("text") or "")
            break
    snap = {
        "checkpoint": name,
        "reason": reason,
        "tool_calls_n": len(tcalls),
        "transcripts_n": len(trans),
        "last_tools": [t.get("tool") for t in tcalls[-8:]],
        "last_user_text": _truncate(last_user, 300),
        "state_keys": list((data.get("state") or {}).keys())[:30],
        "has_ended_at": bool(data.get("ended_at")),
        "duration_secs": data.get("duration_secs"),
    }
    await append_live_event(redis, tenant_id, call_sid, "checkpoint", name, snap, level=level)


async def trace_session_if_available(session, phase: str, event: str, detail=None, level: str = "info") -> None:
    if session is None or not _LIVE_TRACE_ENABLE:
        return
    try:
        await session.append_live_trace(phase, event, detail, level=level)
    except Exception as e:
        logger.debug(f"[LiveTrace] session trace skipped: {e}")


async def fetch_live_trace(
    redis,
    tenant_id: Optional[str],
    call_sid: str,
    start: int = 0,
    end: int = -1,
) -> List[dict]:
    key = live_trace_key(tenant_id, call_sid)
    raw = await redis.lrange(key, start, end)
    out: List[dict] = []
    for line in raw:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({"parse_error": True, "raw": line[:200]})
    return out


async def discover_trace_key(redis, call_sid: str) -> Optional[tuple[str, Optional[str]]]:
    """Return (redis_key, tenant_id) for this CallSid (prefers single unambiguous key)."""
    found: list[tuple[str, Optional[str]]] = []
    k0 = live_trace_key(None, call_sid)
    try:
        if await redis.exists(k0):
            found.append((k0, None))
    except Exception:
        pass
    try:
        async for k in redis.scan_iter(match=f"*:live_trace:{call_sid}", count=200):
            kk = k.decode() if isinstance(k, (bytes, bytearray)) else str(k)
            if kk == k0:
                continue
            tenant = kk.split(":live_trace:")[0] if ":live_trace:" in kk else None
            found.append((kk, tenant))
    except Exception:
        pass
    if not found:
        return None
    if len(found) > 1:
        logger.warning(f"[LiveTrace] Multiple trace keys for {call_sid}: {[f[0] for f in found]} — using first")
    return found[0]
