"""Unit test for capacity-aware reservation check.

Covers:
  1. Available slot → available=True.
  2. Full slot (capacity exceeded) → available=False, alternatives offered.
  3. Invalid time format → friendly error.

Run: ``PYTHONPATH=. python tests/test_reservation_capacity.py``
"""
from __future__ import annotations

import asyncio
import sys


def _mod():
    from tools import executor as e
    return e


def _reset():
    e = _mod()
    e.reservation_store.clear()
    e.tenant_reservation_store.clear()


def _add(date, time, party, tenant=None, status="confirmed"):
    e = _mod()
    res_id = f"R{len(e.reservation_store)}"
    e.reservation_store[res_id] = {
        "reservation_id": res_id,
        "date": date,
        "time": time,
        "party_size": party,
        "status": status,
    }


async def _call(args, tenant=None):
    return await _mod()._check_availability(args, "test-sid", tenant)


def test_slot_available():
    _reset()
    r = asyncio.run(_call({"date": "2099-12-31", "time": "19:00", "party_size": 4}))
    assert r.get("available") is True, r


def test_slot_full_offers_alternatives():
    _reset()
    # Fill the 19:00 bucket close to default capacity (30).
    _add("2099-12-31", "19:00", 28)
    _add("2099-12-31", "19:15", 4)  # same 19:00 bucket (30min grid)
    r = asyncio.run(_call({"date": "2099-12-31", "time": "19:00", "party_size": 4}))
    assert r.get("available") is False, r
    assert r.get("offer_waitlist") is True
    # Alternatives should be non-empty (other slots are still empty).
    assert isinstance(r.get("alternatives"), list) and len(r["alternatives"]) >= 1, r


def test_invalid_time_format():
    _reset()
    r = asyncio.run(_call({"date": "2099-12-31", "time": "not-a-time", "party_size": 2}))
    assert "error" in r, r


def _run():
    errs = []
    for t in (test_slot_available, test_slot_full_offers_alternatives, test_invalid_time_format):
        try:
            t()
            print(f"  PASS: {t.__name__}")
        except Exception as ex:
            errs.append((t.__name__, repr(ex)))
            print(f"  FAIL: {t.__name__} — {ex!r}")
    if errs:
        print(f"\n{len(errs)} FAILED")
        sys.exit(1)
    print("\nALL PASS")


if __name__ == "__main__":
    _run()
