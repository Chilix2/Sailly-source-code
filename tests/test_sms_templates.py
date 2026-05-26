"""Unit tests for SMS/WhatsApp template formatting fixes (Sprint 2).

Verifies:
  1. ``format_order_message`` always uses "für" (never "fur").
  2. The configured ``estimated_minutes`` ends up verbatim in the body.
  3. Reservation SMS contains the restaurant address when provided.

Run: ``PYTHONPATH=. python tests/test_sms_templates.py``
"""
from __future__ import annotations

import sys


def _mod():
    from tools.sms_service import format_order_message, format_reservation_message
    return format_order_message, format_reservation_message


def test_takeaway_uses_umlaut_and_eta():
    fom, _ = _mod()
    msg = fom(
        order_id="ORD-TEST",
        order_items="Bibimbap x1",
        order_type="takeaway",
        total_price=14.5,
        estimated_minutes=25,
    )
    assert "fur " not in msg, "legacy 'fur' must be gone"
    assert "für" in msg, "expected 'für' with proper umlaut"
    assert "Abholung ca. 25 Min." in msg, msg


def test_delivery_uses_tenant_eta():
    fom, _ = _mod()
    msg = fom(
        order_id="ORD-TEST",
        order_items="Pizza Margherita",
        order_type="delivery",
        total_price=11.50,
        delivery_address="Hohe Straße 12, Köln",
        estimated_minutes=40,
        delivery_fee=5.00,
    )
    assert "Lieferung ca. 40 Min." in msg, msg
    assert "Lieferpauschale 5.00€" in msg, msg


def test_reservation_includes_address():
    _, frm = _mod()
    msg = frm(
        name="Max Müller",
        date="2026-04-25",
        time="19:00",
        party_size=4,
        restaurant_name="DOBOO",
        restaurant_address="Friedrich-Ebert-Allee 69, 53113 Bonn",
    )
    assert "für DOBOO" in msg, msg
    assert "Friedrich-Ebert-Allee 69, 53113 Bonn" in msg, msg
    assert "5 Min. früher" in msg, msg


def _run():
    errs = []
    for t in (test_takeaway_uses_umlaut_and_eta, test_delivery_uses_tenant_eta, test_reservation_includes_address):
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
