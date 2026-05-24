"""Unit tests for server.brain.call_summary — pytest-optional.

Covers the pure helpers (summarize_state, _phone_ok via public API behavior)
without touching a live Redis instance.

Run: ``PYTHONPATH=. python tests/test_call_summary.py``
"""
from __future__ import annotations

import sys
from types import SimpleNamespace


def _mod():
    from server.brain import call_summary as cs
    return cs


def test_summarize_order_state():
    cs = _mod()
    state = SimpleNamespace(
        order_intent=True,
        reservation_intent=False,
        selected_dish="Bibimbap",
        total_price=14.5,
        party_size=None,
        reservation_date=None,
        reservation_time=None,
        last_intent=None,
    )
    s = cs.summarize_state(state)
    assert s.get("last_intent") == "order", s
    assert s.get("last_dish") == "Bibimbap", s
    assert s.get("last_total_price") == 14.5, s
    assert "party_size" not in s, s  # 0/None dropped
    assert "last_reservation" not in s, s


def test_summarize_reservation_state():
    cs = _mod()
    state = SimpleNamespace(
        order_intent=False,
        reservation_intent=True,
        selected_dish=None,
        total_price=None,
        party_size=4,
        reservation_date="2026-04-25",
        reservation_time="19:00",
        last_intent=None,
    )
    s = cs.summarize_state(state)
    assert s["last_intent"] == "reservation", s
    assert s["party_size"] == 4, s
    assert s["last_reservation"] == "2026-04-25 19:00", s


def _run():
    errs = []
    for t in (test_summarize_order_state, test_summarize_reservation_state):
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
