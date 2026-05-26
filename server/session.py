"""
Session manager — Redis-backed call session tracking.
Stores per-call state (caller info, reservation data, tool results) in Redis.
"""

import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import redis.asyncio as aioredis
from loguru import logger

BERLIN_TZ = ZoneInfo("Europe/Berlin")

_pool: aioredis.Redis | None = None


async def get_redis(url: str = "redis://localhost:6379") -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(url, decode_responses=True)
    return _pool


class CallSession:
    """Manages per-call session data in Redis with TTL of 24h.
    
    Supports multi-tenant: Redis keys are prefixed with tenant_id if provided.
    """

    TTL = 86400  # 24 hours

    def __init__(self, call_sid: str, redis_client: aioredis.Redis, tenant_id: str | None = None):
        self.call_sid = call_sid
        self.redis = redis_client
        self.tenant_id = tenant_id
        # Namespace Redis key by tenant if provided
        if tenant_id:
            self._key = f"{tenant_id}:session:{call_sid}"
        else:
            self._key = f"session:{call_sid}"

    async def start(self, caller: str = "", from_number: str = ""):
        """Initialize a new call session."""
        existing = await self.get()
        if existing:
            logger.info(f"Session resumed: {self.call_sid} from {from_number}")
            try:
                await self.append_live_trace(
                    "session",
                    "call_resumed",
                    {"caller": caller, "from_number": from_number},
                )
            except Exception:
                pass
            return existing

        now = datetime.now(BERLIN_TZ)
        data = {
            "call_sid": self.call_sid,
            "caller": caller,
            "from_number": from_number,
            "started_at": now.isoformat(),
            "started_ts": time.time(),
            "state": {},
            "tool_calls": [],
            "transcripts": [],
            # §201 StGB — consent is implied when caller stays after the <Say> disclosure.
            # The disclosure fires before the WebSocket connects (Twilio <Say> in TwiML).
            # We record the timestamp as soon as the WebSocket session begins.
            "recording_consent_at": now.isoformat(),
            "emergency_detected": False,
            "emergency_events": [],
            "insurance_data_collected": False,
        }
        await self.redis.setex(self._key, self.TTL, json.dumps(data, ensure_ascii=False))
        logger.info(f"Session started: {self.call_sid} from {from_number} — consent logged at {now.isoformat()}")
        try:
            await self.append_live_trace(
                "session",
                "call_started",
                {"caller": caller, "from_number": from_number},
            )
        except Exception:
            pass
        return data

    async def append_live_trace(
        self,
        phase: str,
        event: str,
        detail=None,
        *,
        level: str = "info",
    ) -> None:
        """Append one timeline event (validation-style live monitoring)."""
        from server.live_call_trace import append_live_event

        await append_live_event(
            self.redis, self.tenant_id, self.call_sid, phase, event, detail, level=level
        )

    async def get(self) -> dict:
        """Get the full session data."""
        raw = await self.redis.get(self._key)
        if not raw:
            return {}
        return json.loads(raw)

    async def update_state(self, updates: dict):
        """Merge new fields into the session state."""
        data = await self.get()
        if not data:
            return
        state = data.get("state", {})
        state.update({k: v for k, v in updates.items() if v is not None})
        data["state"] = state
        await self.redis.setex(self._key, self.TTL, json.dumps(data, ensure_ascii=False))

    async def add_tool_call(self, tool_name: str, args: dict, result: dict, duration_ms: int = 0):
        """Record a tool call in the session."""
        data = await self.get()
        if not data:
            return
        data.setdefault("tool_calls", []).append({
            "tool": tool_name,
            "args": args,
            "result_summary": str(result)[:500],
            "duration_ms": duration_ms,
            "timestamp": datetime.now(BERLIN_TZ).isoformat(),
        })
        await self.redis.setex(self._key, self.TTL, json.dumps(data, ensure_ascii=False))
        try:
            err = result.get("error") if isinstance(result, dict) else None
            await self.append_live_trace(
                "tool",
                "tool_completed",
                {
                    "tool": tool_name,
                    "duration_ms": duration_ms,
                    "error": err,
                    "result_ok": not bool(err),
                },
                level="error" if err else "info",
            )
        except Exception:
            pass

    async def get_tools_called(self) -> list[str]:
        """Return ordered list of tool names called so far in this session."""
        data = await self.get() or {}
        return [t.get("tool", "") for t in data.get("tool_calls", []) if t.get("tool")]

    async def add_transcript(self, role: str, text: str):
        """Add a transcript entry (user or assistant)."""
        data = await self.get()
        if not data:
            return
        data.setdefault("transcripts", []).append({
            "role": role,
            "text": text,
            "timestamp": datetime.now(BERLIN_TZ).isoformat(),
        })
        await self.redis.setex(self._key, self.TTL, json.dumps(data, ensure_ascii=False))
        try:
            await self.append_live_trace(
                "transcript",
                f"{role}_utterance",
                {"text": (text or "")[:400], "chars": len(text or "")},
            )
        except Exception:
            pass

    async def log_emergency(self, detection: dict):
        """Record an emergency detection event in the session."""
        data = await self.get()
        if not data:
            return
        data["emergency_detected"] = True
        data.setdefault("emergency_events", []).append(detection)
        await self.redis.setex(self._key, self.TTL, json.dumps(data, ensure_ascii=False))
        logger.warning(f"Emergency logged to session: {self.call_sid} tier={detection.get('tier')} keyword={detection.get('keyword')}")
        try:
            await self.append_live_trace("safety", "emergency", detection, level="error")
        except Exception:
            pass

    async def set_insurance_collected(self, insurance_company: str = ""):
        """Flag that KVNR/insurance data was collected in this call."""
        data = await self.get()
        if not data:
            return
        data["insurance_data_collected"] = True
        if insurance_company:
            data["insurance_company"] = insurance_company
        await self.redis.setex(self._key, self.TTL, json.dumps(data, ensure_ascii=False))

    async def end(self) -> dict:
        """Finalize the session and return the full data."""
        data = await self.get()
        if not data:
            return {}
        data["ended_at"] = datetime.now(BERLIN_TZ).isoformat()
        data["duration_secs"] = round(time.time() - data.get("started_ts", time.time()), 1)
        await self.redis.setex(self._key, self.TTL, json.dumps(data, ensure_ascii=False))
        logger.info(f"Session ended: {self.call_sid} — duration: {data['duration_secs']}s")
        try:
            from server.live_call_trace import checkpoint_from_session

            await checkpoint_from_session(
                self.redis,
                self.tenant_id,
                self.call_sid,
                "session_end",
                reason="session.end()",
                session_data=data,
            )
        except Exception:
            pass
        return data
