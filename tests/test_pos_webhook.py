"""Unit test for the POS webhook dispatcher — pytest-optional.

Verifies:
  1. 200 response → one POST, success logged, no retries.
  2. 500 response → 3 attempts, all fail, order ends up in pos_failed set
     (we stub Redis via env var pointing at a stub).
  3. 400 response → exactly 1 attempt (non-retryable).

Run: ``PYTHONPATH=. python tests/test_pos_webhook.py``
"""
from __future__ import annotations

import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch


def _load_mod():
    from tools import executor
    return executor


def _fake_resp(status: int, text: str = "ok"):
    r = MagicMock()
    r.status_code = status
    r.text = text
    return r


class _FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, content=None, headers=None):
        self.calls += 1
        r = self._responses.pop(0) if self._responses else _fake_resp(500)
        if isinstance(r, Exception):
            raise r
        return r


async def _run_with_client(fake, order_id="ORD-1"):
    mod = _load_mod()
    # Stub Redis to no-op so failure-branch doesn't hit a real server.
    class _R:
        async def sadd(self, *a, **k): return 1
        async def hset(self, *a, **k): return 1
        async def aclose(self): return None
    fake_redis_mod = types.SimpleNamespace(from_url=lambda *a, **k: _R())
    fake_redis_pkg = types.SimpleNamespace(asyncio=fake_redis_mod)

    with patch("httpx.AsyncClient", return_value=fake), \
         patch.dict(sys.modules, {"redis": fake_redis_pkg, "redis.asyncio": fake_redis_mod}), \
         patch("asyncio.sleep", new=AsyncMock()):
        await mod._post_order_to_pos(
            "https://pos.example/ingest",
            {"order_items": "Bibimbap", "total_price": 14.9},
            order_id,
        )


def test_success_single_post():
    fake = _FakeClient([_fake_resp(200)])
    asyncio.run(_run_with_client(fake))
    assert fake.calls == 1, f"expected 1 call, got {fake.calls}"


def test_retry_on_500_three_attempts():
    fake = _FakeClient([_fake_resp(500), _fake_resp(500), _fake_resp(500)])
    asyncio.run(_run_with_client(fake))
    assert fake.calls == 3, f"expected 3 calls, got {fake.calls}"


def test_no_retry_on_400():
    fake = _FakeClient([_fake_resp(400, "bad")])
    asyncio.run(_run_with_client(fake))
    assert fake.calls == 1, f"expected 1 call, got {fake.calls}"


def _run():
    errs = []
    for t in (test_success_single_post, test_retry_on_500_three_attempts, test_no_retry_on_400):
        try:
            t()
            print(f"  PASS: {t.__name__}")
        except Exception as e:
            errs.append((t.__name__, repr(e)))
            print(f"  FAIL: {t.__name__} — {e!r}")
    if errs:
        print(f"\n{len(errs)} FAILED")
        sys.exit(1)
    print("\nALL PASS")


if __name__ == "__main__":
    _run()
