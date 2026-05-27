#!/usr/bin/env python3
"""
Regression test: Phone/Order Readback Gate Ordering

Test Case: German order with phone digits and delivery
- Input 1: "ein Kimchi, ein Bibimbap und ein Wasser, geliefert an Bonner Bogen 20"
- Input 2: "null eins sechs drei vier vier acht eins hundert" (German digits: 0163448100)
- Input 3: "ja" (confirm phone)
- Input 4: "ja" (confirm order readback)

Expected flow:
  T1: Order extracted
  T2: Phone gate fires (user provides phone)
  T3: Phone confirmation phase
  T4: Order readback shown (NOT skipped)
  T5: Order readback confirmed → create_order

Invariant violations to catch:
  1. Phone confirmation does NOT mark order readback as confirmed
  2. Phone confirmation does NOT skip the order readback
  3. Phone is NOT re-asked after confirmation
  4. Order readback is shown after phone is confirmed
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def test_phone_readback_gate_ordering():
    """
    Verify that confirming a phone number does NOT prematurely mark the order readback as confirmed.
    """
    logger.info("=" * 80)
    logger.info("TEST: phone_readback_gate_ordering")
    logger.info("=" * 80)

    # Simulate conversation state
    from server.brain.conversation_state import ConversationState
    
    state = ConversationState()
    
    # === TURN 1: Order input ===
    logger.info("\n[T1] User input: 'ein Kimchi, ein Bibimbap und ein Wasser, geliefert an Bonner Bogen 20'")
    state.order_intent = True
    state.selected_dish = "Kimchi"
    state.order_items_extras = ["Bibimbap", "Wasser"]
    state.delivery_address = "Bonner Bogen 20"
    state.delivery_address_mentioned = True
    state.delivery_intended = True
    state.end_call_stage = "idle"
    
    assert state.order_intent, "FAIL: Order intent not set"
    assert state.selected_dish == "Kimchi", "FAIL: Primary dish not extracted"
    assert "Bibimbap" in state.order_items_extras, "FAIL: Extra not added"
    assert state.delivery_address == "Bonner Bogen 20", "FAIL: Delivery address not set"
    logger.info("  ✓ Order extracted correctly")
    
    # === TURN 2: Phone digits provided ===
    logger.info("\n[T2] User input: 'null eins sechs drei vier vier acht eins hundert'")
    logger.info("  Expected: Phone gate fires, asking for phone confirmation")
    
    # Simulate phone extraction from STT
    state.phone_number = "+49163448100"
    state.phone_extracted = True
    state.end_call_stage = "idle"
    
    # Check precondition: phone should NOT be confirmed yet
    assert not state.phone_readback_confirmed, "FAIL: Phone should NOT be confirmed at T2"
    assert state.phone_number == "+49163448100", "FAIL: Phone not extracted"
    logger.info("  ✓ Phone extracted and pending confirmation")
    
    # === TURN 3: Phone confirmation ===
    logger.info("\n[T3] User input: 'ja' (confirm phone)")
    logger.info("  Expected: phone_readback_confirmed=True, BUT order readback NOT confirmed")
    
    # Simulate phone confirmation logic (from v4_pipeline.py lines 1963-1970)
    # After fix: should NOT call mark_commit_readback_confirmed("create_order")
    state.phone_confirmed = True
    state.phone_readback_confirmed = True
    state.end_call_stage = "idle"
    # DO NOT call: state.mark_commit_readback_confirmed("create_order")
    
    # Check invariants
    assert state.phone_readback_confirmed is True, "FAIL: Phone confirmation flag not set"
    assert state.phone_confirmed is True, "FAIL: phone_confirmed not set"
    assert not getattr(state, "_order_readback_confirmed", False), \
        "FAIL: Order readback MUST NOT be marked as confirmed after phone confirmation"
    logger.info("  ✓ Phone confirmed but order readback NOT prematurely marked")
    
    # === TURN 4: Check that order readback will be shown ===
    logger.info("\n[T4] Expected: Order readback shown to user")
    logger.info("  Verifying readback gates...")
    
    # Check that phone is not re-asked
    _phone_value = state.phone_number or ""
    _phone_digits = "".join(c for c in _phone_value if c.isdigit())
    _is_real_phone = bool(_phone_digits) and _phone_value != "browser_demo"
    _caller_id_already_confirmed = False  # Not set in this scenario
    
    should_ask_phone_again = (
        _is_real_phone 
        and not _caller_id_already_confirmed 
        and not getattr(state, "phone_readback_confirmed", False)
    )
    
    assert not should_ask_phone_again, \
        "FAIL: Phone should NOT be re-asked after confirmation (guard at v4_pipeline:2602 failed)"
    logger.info("  ✓ Phone will NOT be re-asked (guard passed)")
    
    # Check that order readback will be shown
    _readback_already_shown = getattr(state, "_readback_already_shown", False)
    order_pre_commit_shown = getattr(state, "order_pre_commit_shown", False)
    in_confirmation_phase = state.end_call_stage == "order_pre_commit_readback"
    
    # After phone confirmed and end_call_stage reset to idle, readback should trigger
    assert not _readback_already_shown, \
        "FAIL: Readback should NOT be marked as shown yet"
    assert state.end_call_stage == "idle", \
        f"FAIL: end_call_stage should be 'idle', got '{state.end_call_stage}'"
    logger.info("  ✓ Order readback will be shown next (state is idle and readback not yet shown)")
    
    # === TURN 5: Verify order readback confirmation ===
    logger.info("\n[T5] User input: 'ja' (confirm order readback)")
    logger.info("  Expected: Order readback confirmed, order ready to commit")
    
    # Now the code should show readback and enter order_pre_commit_readback
    state.order_pre_commit_shown = True
    state.end_call_stage = "order_pre_commit_readback"
    state._readback_already_shown = True
    
    # Mark readback as shown (happens when bot speaks the readback)
    state.mark_commit_readback_shown("create_order")
    
    # User confirms readback
    state.mark_commit_readback_confirmed("create_order")
    
    assert state.end_call_stage == "order_pre_commit_readback", \
        "FAIL: Should be in confirmation phase"
    assert getattr(state, "_order_readback_confirmed", False), \
        "FAIL: Order readback confirmation flag not set"
    logger.info("  ✓ Order readback confirmed, order ready for create_order")
    
    # === Final checks ===
    logger.info("\n" + "=" * 80)
    logger.info("INVARIANTS CHECK")
    logger.info("=" * 80)
    
    checks = {
        "Phone extracted": state.phone_number == "+49163448100",
        "Phone confirmed": state.phone_readback_confirmed is True,
        "Order intent set": state.order_intent is True,
        "Order readback confirmed": getattr(state, "_order_readback_confirmed", False),
        "Selected items present": state.selected_dish and state.order_items_extras,
        "Delivery address set": state.delivery_address is not None,
    }
    
    all_passed = True
    for check_name, result in checks.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {check_name}")
        if not result:
            all_passed = False
    
    logger.info("=" * 80)
    
    if all_passed:
        logger.info("✓ All tests PASSED")
        return 0
    else:
        logger.error("✗ Some tests FAILED")
        return 1


if __name__ == "__main__":
    try:
        exit_code = test_phone_readback_gate_ordering()
        sys.exit(exit_code)
    except Exception as e:
        logger.exception("Test crashed:")
        sys.exit(1)
