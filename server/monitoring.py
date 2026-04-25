"""
Production monitoring for Sailly voice agent.

Tracks per-call metrics and aggregates across calls for health dashboards and alerts.
Designed for dashboard.sailly.tech / sailly.tech: Redis-backed history, runtime config,
and rich per-call rows for overview + drill-down.

Metrics:
  - task_success_rate, latency P50/P95, tool / intent / end_reason distributions
  - Per-call: tenant, source (twilio_cascade | gemini_live | browser_demo), brain (adk | vertex)

Environment (defaults; overridden by Redis hash ``MONITOR_CONFIG_REDIS_KEY`` when set):
    MONITOR_SUCCESS_THRESHOLD=80
    MONITOR_LATENCY_P95_MS=3000
    MONITOR_WINDOW_SECS=1800
    MONITOR_ALERT_WEBHOOK=...
    MONITOR_ALERT_COOLDOWN_SECS=300
    MONITOR_MIN_CALLS_FOR_RATE_ALERT=5
    MONITOR_LOOP_ESCAPE_RATIO=0.3
    MONITOR_ERROR_FALLBACK_RATIO=0.1

Redis:
    MONITOR_REDIS_ENABLE=1          — LPUSH each completed call (JSON); **recommended in production**
    MONITOR_REDIS_LIST_KEY=monitor:completed_calls
    MONITOR_REDIS_MAXLEN=5000
    MONITOR_CONFIG_REDIS_KEY=monitor:config   — hash: success_threshold, latency_p95_ms, window_secs, alert_webhook
    MONITOR_ADMIN_TOKEN=...         — required for PUT /api/dashboard/monitor/config
    REDIS_URL=redis://...

Usage:
    register_call_monitoring_context(call_sid, tenant_id=..., source=\"twilio_cascade\", brain=\"adk\", caller=...)
    await record_call_metric(call_sid, \"latency_ms\", ms)
    await record_call_metric(call_sid, \"outcome\", {...})
    await finalize_call_monitoring(call_sid, session_data, end_reason=\"...\")

API:
    GET  /api/dashboard/monitor           — overview + snapshot (memory + Redis)
    GET  /api/dashboard/monitor/calls     — recent completed rows (detail table)
    GET  /api/dashboard/monitor/config    — effective config
    PUT  /api/dashboard/monitor/config    — update Redis config (Bearer token)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Env defaults (Redis hash overrides when present) ───────────────────────
_ENV_SUCCESS_THRESHOLD = int(os.getenv("MONITOR_SUCCESS_THRESHOLD", "80"))
_ENV_LATENCY_P95_LIMIT_MS = int(os.getenv("MONITOR_LATENCY_P95_MS", "3000"))
_ENV_WINDOW_SECS = int(os.getenv("MONITOR_WINDOW_SECS", "1800"))
_ENV_ALERT_WEBHOOK = os.getenv("MONITOR_ALERT_WEBHOOK", "")
_ENV_ALERT_COOLDOWN_SECS = int(os.getenv("MONITOR_ALERT_COOLDOWN_SECS", "300"))
_ENV_MIN_CALLS_FOR_RATE = int(os.getenv("MONITOR_MIN_CALLS_FOR_RATE_ALERT", "5"))
_ENV_LOOP_ESCAPE_RATIO = float(os.getenv("MONITOR_LOOP_ESCAPE_RATIO", "0.3"))
_ENV_ERROR_FALLBACK_RATIO = float(os.getenv("MONITOR_ERROR_FALLBACK_RATIO", "0.1"))

_MONITOR_REDIS_ENABLE = os.getenv("MONITOR_REDIS_ENABLE", "").lower() in ("1", "true", "yes")
_MONITOR_REDIS_LIST_KEY = os.getenv("MONITOR_REDIS_LIST_KEY", "monitor:completed_calls")
_MONITOR_REDIS_MAXLEN = int(os.getenv("MONITOR_REDIS_MAXLEN", "5000"))
_MONITOR_CONFIG_REDIS_KEY = os.getenv("MONITOR_CONFIG_REDIS_KEY", "monitor:config")
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
_MONITOR_ADMIN_TOKEN = os.getenv("MONITOR_ADMIN_TOKEN", "")


@dataclass
class CallMetric:
    """Metrics for a single completed (or in-flight) call."""

    call_sid: str
    timestamp: float
    intent: str = "unknown"
    fulfilled: bool = False
    tools_called: List[str] = field(default_factory=list)
    turn_count: int = 0
    end_reason: str = ""
    latency_ms_list: List[float] = field(default_factory=list)
    tenant_id: str = ""
    source: str = ""
    brain: str = ""
    caller: str = ""
    transferred_from: str = ""
    duration_secs: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def latency_p50(self) -> Optional[float]:
        if not self.latency_ms_list:
            return None
        s = sorted(self.latency_ms_list)
        return s[len(s) // 2]

    @property
    def latency_p95(self) -> Optional[float]:
        if not self.latency_ms_list:
            return None
        s = sorted(self.latency_ms_list)
        return s[int(len(s) * 0.95)]


_recent_calls: deque = deque(maxlen=500)
_active_metrics: Dict[str, CallMetric] = {}

_last_alert_ts: float = 0.0


def _metric_to_payload(m: CallMetric) -> dict:
    return {
        "call_sid": m.call_sid,
        "ts": m.timestamp,
        "intent": m.intent,
        "fulfilled": m.fulfilled,
        "tools_called": m.tools_called,
        "turn_count": m.turn_count,
        "end_reason": m.end_reason,
        "latency_ms_list": m.latency_ms_list,
        "tenant_id": m.tenant_id,
        "source": m.source,
        "brain": m.brain,
        "caller": m.caller,
        "transferred_from": m.transferred_from,
        "duration_secs": m.duration_secs,
        "extra": dict(m.extra),
    }


def register_call_monitoring_context(
    call_sid: str,
    *,
    tenant_id: str = "",
    source: str = "",
    brain: str = "",
    caller: str = "",
    transferred_from: str = "",
    extra: Optional[Dict[str, Any]] = None,
    **more: Any,
) -> None:
    """
    Attach stable per-call dimensions as soon as CallSid is known (before first metric).
    Unknown keys go into ``extra`` for forward-compatible dashboards.
    """
    if not call_sid or call_sid == "unknown":
        return
    if call_sid not in _active_metrics:
        _active_metrics[call_sid] = CallMetric(call_sid=call_sid, timestamp=time.time())
    m = _active_metrics[call_sid]
    if tenant_id:
        m.tenant_id = tenant_id
    if source:
        m.source = source
    if brain:
        m.brain = brain
    if caller:
        m.caller = caller
    if transferred_from:
        m.transferred_from = transferred_from
    if extra:
        m.extra.update(extra)
    for k, v in more.items():
        if v is not None:
            m.extra[str(k)] = v


def _enrich_metric_from_session(m: CallMetric, session_data: Optional[dict]) -> None:
    if not session_data:
        return
    dur = session_data.get("duration_secs")
    if dur is not None:
        try:
            m.duration_secs = float(dur)
        except (TypeError, ValueError):
            pass
    if not m.tenant_id and session_data.get("tenant_id"):
        m.tenant_id = str(session_data["tenant_id"])
    if not m.caller and session_data.get("from_number"):
        m.caller = str(session_data["from_number"])
    transcripts = session_data.get("transcripts") or []
    m.extra.setdefault("transcript_turns", len(transcripts))
    m.extra.setdefault("user_turns", sum(1 for t in transcripts if t.get("role") == "user"))
    m.extra.setdefault("tool_call_count", len(session_data.get("tool_calls") or []))


def _copy_outcome_extras_from_dict(metric: CallMetric, value: dict) -> None:
    for attr in ("tenant_id", "source", "brain", "caller", "transferred_from"):
        if attr in value and value[attr]:
            setattr(metric, attr, str(value[attr]))
    if "duration_secs" in value:
        try:
            metric.duration_secs = float(value["duration_secs"])
        except (TypeError, ValueError):
            pass
    ex = value.get("monitoring_extra")
    if isinstance(ex, dict):
        metric.extra.update(ex)


async def get_effective_monitor_config() -> dict:
    """Env defaults merged with Redis hash ``MONITOR_CONFIG_REDIS_KEY`` (if Redis up)."""
    base = {
        "success_threshold": _ENV_SUCCESS_THRESHOLD,
        "latency_p95_ms": _ENV_LATENCY_P95_LIMIT_MS,
        "window_secs": _ENV_WINDOW_SECS,
        "alert_webhook": _ENV_ALERT_WEBHOOK,
        "alert_cooldown_secs": _ENV_ALERT_COOLDOWN_SECS,
        "min_calls_for_rate_alert": _ENV_MIN_CALLS_FOR_RATE,
        "loop_escape_ratio": _ENV_LOOP_ESCAPE_RATIO,
        "error_fallback_ratio": _ENV_ERROR_FALLBACK_RATIO,
        "redis_list_key": _MONITOR_REDIS_LIST_KEY,
        "redis_enabled": _MONITOR_REDIS_ENABLE,
        "config_redis_key": _MONITOR_CONFIG_REDIS_KEY,
    }
    try:
        from server.session import get_redis

        r = await get_redis(_REDIS_URL)
        raw = await r.hgetall(_MONITOR_CONFIG_REDIS_KEY)
        if raw:
            def _dec(b):
                return b.decode() if isinstance(b, (bytes, bytearray)) else str(b)

            h = {_dec(k): _dec(v) for k, v in raw.items()}
            if "success_threshold" in h:
                base["success_threshold"] = int(float(h["success_threshold"]))
            if "latency_p95_ms" in h:
                base["latency_p95_ms"] = int(float(h["latency_p95_ms"]))
            if "window_secs" in h:
                base["window_secs"] = int(float(h["window_secs"]))
            if "alert_webhook" in h and h["alert_webhook"].strip():
                base["alert_webhook"] = h["alert_webhook"].strip()
            if "alert_cooldown_secs" in h:
                base["alert_cooldown_secs"] = int(float(h["alert_cooldown_secs"]))
            if "min_calls_for_rate_alert" in h:
                base["min_calls_for_rate_alert"] = int(float(h["min_calls_for_rate_alert"]))
            if "loop_escape_ratio" in h:
                base["loop_escape_ratio"] = float(h["loop_escape_ratio"])
            if "error_fallback_ratio" in h:
                base["error_fallback_ratio"] = float(h["error_fallback_ratio"])
    except Exception as e:
        logger.debug(f"[Monitor] Config load from Redis skipped: {e}")
    return base


async def save_monitor_config_updates(updates: dict) -> dict:
    """Persist allowed keys to Redis hash. Returns new effective config."""
    allowed = {
        "success_threshold",
        "latency_p95_ms",
        "window_secs",
        "alert_webhook",
        "alert_cooldown_secs",
        "min_calls_for_rate_alert",
        "loop_escape_ratio",
        "error_fallback_ratio",
    }
    to_write = {k: str(v) for k, v in updates.items() if k in allowed and v is not None}
    if not to_write:
        return await get_effective_monitor_config()
    from server.session import get_redis

    r = await get_redis(_REDIS_URL)
    await r.hset(_MONITOR_CONFIG_REDIS_KEY, mapping=to_write)
    return await get_effective_monitor_config()


def verify_monitor_admin_token(header_value: Optional[str]) -> bool:
    if not _MONITOR_ADMIN_TOKEN:
        return False
    if not header_value or not header_value.startswith("Bearer "):
        return False
    return header_value[7:].strip() == _MONITOR_ADMIN_TOKEN


async def record_call_metric(call_sid: str, metric_type: str, value) -> None:
    if call_sid not in _active_metrics:
        _active_metrics[call_sid] = CallMetric(call_sid=call_sid, timestamp=time.time())

    metric = _active_metrics[call_sid]

    if metric_type == "latency_ms" and isinstance(value, (int, float)):
        metric.latency_ms_list.append(float(value))

    elif metric_type == "outcome" and isinstance(value, dict):
        metric.intent = value.get("intent", "unknown")
        metric.fulfilled = bool(value.get("fulfilled", False))
        metric.tools_called = list(value.get("tools_called", []))
        metric.turn_count = int(value.get("turn_count", 0))
        metric.end_reason = value.get("end_reason", "")
        metric.timestamp = time.time()
        _copy_outcome_extras_from_dict(metric, value)

        _recent_calls.append(metric)
        _active_metrics.pop(call_sid, None)

        logger.info(
            f"[Monitor] Call {call_sid}: intent={metric.intent}, "
            f"fulfilled={metric.fulfilled}, tools={metric.tools_called}, "
            f"turns={metric.turn_count}, p95={metric.latency_p95}"
        )

        asyncio.create_task(_maybe_redis_append_completed(metric))
        asyncio.create_task(_check_alerts())


def monitoring_outcome_already_recorded(call_sid: str) -> bool:
    for m in reversed(_recent_calls):
        if m.call_sid == call_sid:
            return True
    return False


async def monitoring_call_completed_in_redis(call_sid: str) -> bool:
    if not _MONITOR_REDIS_ENABLE or not call_sid:
        return False
    try:
        from server.session import get_redis

        r = await get_redis(_REDIS_URL)
        entries = await r.lrange(_MONITOR_REDIS_LIST_KEY, 0, min(_MONITOR_REDIS_MAXLEN, 5000) - 1)
        for raw in entries:
            s = raw.decode() if isinstance(raw, (bytes, bytearray)) else raw
            try:
                d = json.loads(s)
                if d.get("call_sid") == call_sid:
                    return True
            except json.JSONDecodeError:
                continue
    except Exception as e:
        logger.debug(f"[Monitor] Redis dedup scan failed: {e}")
    return False


def infer_outcome_from_session(session_data: dict) -> dict:
    tool_calls = session_data.get("tool_calls") or []
    tools_ordered: List[str] = []
    for tc in tool_calls:
        nm = tc.get("tool") or tc.get("name") or ""
        if nm:
            tools_ordered.append(nm)

    transcripts = session_data.get("transcripts") or []
    user_turns = sum(1 for t in transcripts if t.get("role") == "user")
    turn_count = max(user_turns, len(tools_ordered), 1)

    intent = "unknown"
    if "create_order" in tools_ordered:
        intent = "order"
    elif "create_reservation" in tools_ordered:
        intent = "reservation"
    elif "transfer_to_human" in tools_ordered or "transfer_to_tier2" in tools_ordered:
        intent = "transfer"
    elif "get_restaurant_info" in tools_ordered or "faq" in tools_ordered:
        intent = "faq"

    def _tool_ok(name: str) -> bool:
        for tc in tool_calls:
            if tc.get("tool") == name:
                rs = (tc.get("result_summary") or "").lower()
                if "error" in rs or "failed" in rs or "exception" in rs:
                    return False
                return True
        return False

    fulfilled = False
    if "create_order" in tools_ordered:
        fulfilled = _tool_ok("create_order")
    elif "create_reservation" in tools_ordered:
        fulfilled = _tool_ok("create_reservation")
    elif intent == "transfer":
        fulfilled = True
    elif "end_call" in tools_ordered and intent in ("faq", "unknown"):
        fulfilled = True

    return {
        "intent": intent,
        "fulfilled": fulfilled,
        "tools_called": list(tools_ordered),
        "turn_count": turn_count,
        "end_reason": "disconnect",
    }


async def _maybe_redis_append_completed(metric: CallMetric) -> None:
    if not _MONITOR_REDIS_ENABLE:
        return
    try:
        from server.session import get_redis

        r = await get_redis(_REDIS_URL)
        payload = json.dumps(_metric_to_payload(metric), ensure_ascii=False)
        await r.lpush(_MONITOR_REDIS_LIST_KEY, payload)
        await r.ltrim(_MONITOR_REDIS_LIST_KEY, 0, max(0, _MONITOR_REDIS_MAXLEN - 1))
    except Exception as e:
        logger.debug(f"[Monitor] Redis append skipped: {e}")


async def finalize_call_monitoring(
    call_sid: str,
    session_data: Optional[dict],
    *,
    end_reason: str = "disconnect",
) -> None:
    if monitoring_outcome_already_recorded(call_sid):
        return
    if await monitoring_call_completed_in_redis(call_sid):
        return

    inferred = infer_outcome_from_session(session_data or {})
    inferred["end_reason"] = end_reason or inferred.get("end_reason") or "disconnect"

    now = time.time()
    if call_sid in _active_metrics:
        m = _active_metrics.pop(call_sid)
        m.intent = inferred["intent"]
        m.fulfilled = inferred["fulfilled"]
        m.tools_called = inferred["tools_called"]
        m.turn_count = inferred["turn_count"]
        m.end_reason = inferred["end_reason"]
        m.timestamp = now
        _enrich_metric_from_session(m, session_data)
        completed = m
    else:
        completed = CallMetric(
            call_sid=call_sid,
            timestamp=now,
            intent=inferred["intent"],
            fulfilled=inferred["fulfilled"],
            tools_called=inferred["tools_called"],
            turn_count=inferred["turn_count"],
            end_reason=inferred["end_reason"],
            latency_ms_list=[],
        )
        _enrich_metric_from_session(completed, session_data)

    _recent_calls.append(completed)

    logger.info(
        f"[Monitor] Finalized {call_sid}: intent={completed.intent}, "
        f"fulfilled={completed.fulfilled}, tools={completed.tools_called}, "
        f"end_reason={completed.end_reason!r}"
    )
    await _maybe_redis_append_completed(completed)
    asyncio.create_task(_check_alerts())


def _rows_from_memory(window_secs: float, now: float) -> List[dict]:
    cutoff = now - window_secs
    return [_metric_to_payload(m) for m in _recent_calls if m.timestamp >= cutoff]


async def _rows_from_redis(window_secs: float, now: float) -> List[dict]:
    if not _MONITOR_REDIS_ENABLE:
        return []
    cutoff = now - window_secs
    rows: List[dict] = []
    try:
        from server.session import get_redis

        r = await get_redis(_REDIS_URL)
        entries = await r.lrange(_MONITOR_REDIS_LIST_KEY, 0, min(_MONITOR_REDIS_MAXLEN, 10000) - 1)
        for raw in entries:
            s = raw.decode() if isinstance(raw, (bytes, bytearray)) else raw
            try:
                d = json.loads(s)
                ts = float(d.get("ts", 0) or 0)
                if ts >= cutoff:
                    rows.append(d)
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
    except Exception as e:
        logger.debug(f"[Monitor] Redis read for snapshot failed: {e}")
    return rows


def _dedupe_rows_by_callsid(rows: List[dict]) -> List[dict]:
    best: Dict[str, dict] = {}
    for row in rows:
        sid = row.get("call_sid")
        if not sid:
            continue
        ts = float(row.get("ts", 0) or 0)
        if sid not in best or ts > float(best[sid].get("ts", 0) or 0):
            best[sid] = row
    return list(best.values())


def _aggregate_from_rows(rows: List[dict], active_calls: int) -> dict:
    if not rows:
        return {
            "window_secs": 0,
            "total_calls": 0,
            "fulfilled_calls": 0,
            "task_success_rate": 0.0,
            "latency_p50_ms": None,
            "latency_p95_ms": None,
            "tool_distribution": {},
            "intent_distribution": {},
            "end_reason_distribution": {},
            "source_distribution": {},
            "brain_distribution": {},
            "tenant_distribution": {},
            "active_calls": active_calls,
            "avg_duration_secs": None,
        }

    total = len(rows)
    fulfilled = sum(1 for r in rows if r.get("fulfilled"))
    success_rate = (fulfilled / total * 100) if total > 0 else 0.0

    all_latencies: List[float] = []
    durations: List[float] = []
    for r in rows:
        for x in r.get("latency_ms_list") or []:
            try:
                all_latencies.append(float(x))
            except (TypeError, ValueError):
                pass
        try:
            d = float(r.get("duration_secs", 0) or 0)
            if d > 0:
                durations.append(d)
        except (TypeError, ValueError):
            pass
    all_latencies.sort()
    p50 = all_latencies[len(all_latencies) // 2] if all_latencies else None
    p95 = all_latencies[int(len(all_latencies) * 0.95)] if all_latencies else None

    tool_dist: Dict[str, int] = {}
    intent_dist: Dict[str, int] = {}
    end_dist: Dict[str, int] = {}
    source_dist: Dict[str, int] = {}
    brain_dist: Dict[str, int] = {}
    tenant_dist: Dict[str, int] = {}

    for r in rows:
        intent = r.get("intent") or "unknown"
        intent_dist[intent] = intent_dist.get(intent, 0) + 1
        er = r.get("end_reason") or ""
        end_dist[er] = end_dist.get(er, 0) + 1
        src = r.get("source") or "unknown"
        source_dist[src] = source_dist.get(src, 0) + 1
        br = r.get("brain") or "unknown"
        brain_dist[br] = brain_dist.get(br, 0) + 1
        tn = r.get("tenant_id") or "_none"
        tenant_dist[tn] = tenant_dist.get(tn, 0) + 1
        for t in r.get("tools_called") or []:
            tool_dist[str(t)] = tool_dist.get(str(t), 0) + 1

    avg_dur = sum(durations) / len(durations) if durations else None

    return {
        "window_secs": 0,
        "total_calls": total,
        "fulfilled_calls": fulfilled,
        "task_success_rate": round(success_rate, 1),
        "latency_p50_ms": round(p50, 0) if p50 else None,
        "latency_p95_ms": round(p95, 0) if p95 else None,
        "tool_distribution": dict(sorted(tool_dist.items(), key=lambda x: -x[1])),
        "intent_distribution": intent_dist,
        "end_reason_distribution": end_dist,
        "source_distribution": source_dist,
        "brain_distribution": brain_dist,
        "tenant_distribution": tenant_dist,
        "active_calls": active_calls,
        "avg_duration_secs": round(avg_dur, 1) if avg_dur else None,
    }


def get_metrics_snapshot(window_secs: int = _ENV_WINDOW_SECS) -> dict:
    """
    In-memory only (fast, sync). After process restart, use ``get_metrics_snapshot_async``
    with Redis enabled for full history.
    """
    now = time.time()
    rows = _rows_from_memory(window_secs, now)
    snap = _aggregate_from_rows(rows, len(_active_metrics))
    snap["window_secs"] = int(window_secs)
    snap["data_source"] = "memory_only"
    return snap


async def get_metrics_snapshot_async(
    window_secs: int = _ENV_WINDOW_SECS,
    *,
    use_redis: bool = True,
) -> dict:
    """Merge in-process ring buffer with Redis list (deduped by call_sid)."""
    now = time.time()
    mem = _rows_from_memory(window_secs, now)
    redis_rows = await _rows_from_redis(window_secs, now) if use_redis and _MONITOR_REDIS_ENABLE else []
    merged = _dedupe_rows_by_callsid(mem + redis_rows)
    snap = _aggregate_from_rows(merged, len(_active_metrics))
    snap["window_secs"] = int(window_secs)
    snap["data_source"] = "memory+redis" if (use_redis and _MONITOR_REDIS_ENABLE) else "memory_only"
    snap["redis_enabled"] = _MONITOR_REDIS_ENABLE
    return snap


async def get_recent_monitoring_calls(
    window_secs: int = 86400,
    limit: int = 100,
    *,
    use_redis: bool = True,
) -> List[dict]:
    """Recent completed calls (newest first) for dashboard detail tables."""
    now = time.time()
    mem = _rows_from_memory(window_secs, now)
    redis_rows = await _rows_from_redis(window_secs, now) if use_redis and _MONITOR_REDIS_ENABLE else []
    merged = _dedupe_rows_by_callsid(mem + redis_rows)
    merged.sort(key=lambda r: float(r.get("ts", 0) or 0), reverse=True)
    return merged[: max(1, min(limit, 500))]


async def get_monitor_overview_bundle(window_secs: Optional[int] = None) -> dict:
    cfg = await get_effective_monitor_config()
    w = int(window_secs if window_secs is not None else cfg["window_secs"])
    snapshot = await get_metrics_snapshot_async(w, use_redis=True)
    snapshot["window_secs"] = w
    health_hints = []
    if snapshot["total_calls"] >= cfg["min_calls_for_rate_alert"]:
        if snapshot["task_success_rate"] < cfg["success_threshold"]:
            health_hints.append(
                f"task_success_rate {snapshot['task_success_rate']}% "
                f"< threshold {cfg['success_threshold']}%"
            )
    if snapshot["latency_p95_ms"] and snapshot["latency_p95_ms"] > cfg["latency_p95_ms"]:
        health_hints.append(
            f"p95_latency {snapshot['latency_p95_ms']}ms > threshold {cfg['latency_p95_ms']}ms"
        )
    ok = len(health_hints) == 0
    return {
        "ok": ok,
        "health_hints": health_hints,
        "snapshot": snapshot,
        "config": {k: v for k, v in cfg.items() if k != "alert_webhook"},
        "config_alert_webhook_set": bool(cfg.get("alert_webhook")),
    }


async def _check_alerts() -> None:
    global _last_alert_ts

    cfg = await get_effective_monitor_config()
    now = time.time()
    if now - _last_alert_ts < cfg["alert_cooldown_secs"]:
        return

    snapshot = await get_metrics_snapshot_async(cfg["window_secs"], use_redis=True)
    alerts: List[str] = []
    min_c = cfg["min_calls_for_rate_alert"]
    thr = cfg["success_threshold"]
    lat_lim = cfg["latency_p95_ms"]

    if snapshot["total_calls"] >= min_c:
        if snapshot["task_success_rate"] < thr:
            alerts.append(
                f"Task success rate {snapshot['task_success_rate']:.0f}% < "
                f"{thr}% threshold over last {cfg['window_secs'] // 60} min "
                f"({snapshot['fulfilled_calls']}/{snapshot['total_calls']} calls)"
            )

    if snapshot["latency_p95_ms"] and snapshot["latency_p95_ms"] > lat_lim:
        alerts.append(
            f"P95 latency {snapshot['latency_p95_ms']:.0f}ms > {lat_lim}ms threshold"
        )

    total = snapshot["total_calls"]
    if total >= min_c:
        ler = cfg["loop_escape_ratio"]
        efr = cfg["error_fallback_ratio"]
        forced_ends = snapshot["end_reason_distribution"].get("forced_end_loop", 0)
        if forced_ends / total > ler:
            alerts.append(
                f"Loop escape fired in {forced_ends}/{total} calls — bot may be stuck"
            )
        errors = snapshot["end_reason_distribution"].get("error_fallback", 0)
        if errors / total > efr:
            alerts.append(
                f"Error fallback in {errors}/{total} calls — check API/tool logs"
            )

    if alerts:
        _last_alert_ts = now
        alert_msg = "\n".join(f"⚠️  {a}" for a in alerts)
        logger.warning(f"[Monitor] ALERT — {len(alerts)} threshold(s) breached:\n{alert_msg}")

        webhook = cfg.get("alert_webhook") or ""
        if webhook.strip():
            await _send_webhook_alert(alerts, snapshot, webhook.strip())


async def _send_webhook_alert(alerts: List[str], snapshot: dict, webhook_url: str) -> None:
    try:
        import aiohttp

        payload = {
            "text": "🚨 Sailly Production Alert",
            "alerts": alerts,
            "snapshot": snapshot,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status in (200, 201, 202, 204):
                    logger.info(f"[Monitor] Alert webhook sent: {resp.status}")
                else:
                    logger.warning(f"[Monitor] Alert webhook returned {resp.status}")
    except Exception as e:
        logger.warning(f"[Monitor] Alert webhook failed: {e}")


async def weekly_review_report_async(n_failed_calls: int = 5) -> str:
    snapshot = await get_metrics_snapshot_async(7 * 24 * 3600, use_redis=True)
    lines = [
        "═══ Sailly Weekly Review Report ═══",
        "Period: last 7 days (memory + Redis when enabled)",
        f"Total calls: {snapshot['total_calls']}",
        f"Task success: {snapshot['task_success_rate']:.1f}%",
        f"P50 latency: {snapshot['latency_p50_ms']} ms",
        f"P95 latency: {snapshot['latency_p95_ms']} ms",
        "",
        "Tool distribution:",
    ]
    for tool, count in list(snapshot["tool_distribution"].items())[:10]:
        lines.append(f"  {tool}: {count}")
    lines.append("")
    lines.append("Intent distribution:")
    for intent, count in snapshot["intent_distribution"].items():
        lines.append(f"  {intent}: {count}")
    lines.append("")
    lines.append("End reasons:")
    for reason, count in snapshot["end_reason_distribution"].items():
        lines.append(f"  {reason}: {count}")
    lines.append("")
    lines.append(
        f"Action: Review the {n_failed_calls} most recent failed calls "
        "and add scenarios to fix_validation_buckets.py"
    )
    return "\n".join(lines)


def weekly_review_report(n_failed_calls: int = 5) -> str:
    """Sync wrapper: memory-only window (may be incomplete after restart)."""
    snapshot = get_metrics_snapshot(window_secs=7 * 24 * 3600)
    lines = [
        "═══ Sailly Weekly Review Report (memory only) ═══",
        f"Total calls: {snapshot['total_calls']}",
        f"Task success: {snapshot['task_success_rate']:.1f}%",
        "",
        "Use weekly_review_report_async() for Redis-backed 7-day stats.",
    ]
    return "\n".join(lines)
