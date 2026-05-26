"""
Deep health check per decision deep-health (9.X7).

/health  -- liveness probe (systemd / load balancer keep-alive)
/ready   -- readiness probe (deploy gating; checks all deps)

Mounted in server/main.py via:
    from server.brain.health import router as _health_router
    app.include_router(_health_router)
"""
from __future__ import annotations

import asyncio
import os
import time
import logging

from fastapi import APIRouter, Response

from server.configs.secrets import get_secret

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness() -> dict:
    return {"status": "alive", "service": "sailly-browser-demo"}


@router.get("/ready")
async def readiness(response: Response) -> dict:
    results = await asyncio.gather(
        _check_redis(),
        _check_postgres(),
        _check_gemini(),
        _check_deepgram(),
        return_exceptions=True,
    )

    checks = {
        "redis":    _result(results[0]),
        "postgres": _result(results[1]),
        "gemini":   _result(results[2]),
        "deepgram": _result(results[3]),
    }

    all_ok = all(r["ok"] for r in checks.values())
    if not all_ok:
        response.status_code = 503

    return {"ready": all_ok, "checks": checks}


def _result(check_result) -> dict:
    if isinstance(check_result, Exception):
        return {"ok": False, "error": str(check_result)[:200]}
    return {"ok": True, "latency_ms": check_result}


async def _check_redis() -> int:
    start = time.monotonic()
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        import aioredis  # type: ignore
        redis = await aioredis.from_url(redis_url, socket_connect_timeout=2)
        await redis.ping()
        await redis.aclose()
    except ImportError:
        import redis.asyncio as _redis  # type: ignore
        r = _redis.from_url(redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
    return int((time.monotonic() - start) * 1000)


async def _check_postgres() -> int:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ConnectionError("DATABASE_URL not set")
    start = time.monotonic()
    import asyncpg  # type: ignore
    conn = await asyncpg.connect(db_url, timeout=3)
    await conn.fetchval("SELECT 1")
    await conn.close()
    return int((time.monotonic() - start) * 1000)


async def _check_gemini() -> int:
    api_key = get_secret("gemini-api-key", default="")
    if not api_key:
        raise ConnectionError("gemini-api-key secret not configured")
    start = time.monotonic()
    import httpx
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            json={"contents": [{"role": "user", "parts": [{"text": "1"}]}],
                  "generationConfig": {"maxOutputTokens": 1}},
        )
        if resp.status_code not in (200, 201):
            raise ConnectionError(f"Gemini returned {resp.status_code}")
    return int((time.monotonic() - start) * 1000)


async def _check_deepgram() -> int:
    api_key = get_secret("deepgram-api-key", default="")
    if not api_key:
        raise ConnectionError("deepgram-api-key secret not configured")
    start = time.monotonic()
    import httpx
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(
            "https://api.deepgram.com/v1/projects",
            headers={"Authorization": f"Token {api_key}"},
        )
        if resp.status_code not in (200, 201):
            raise ConnectionError(f"Deepgram returned {resp.status_code}")
    return int((time.monotonic() - start) * 1000)
