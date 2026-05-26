"""
Phase 1 Integration Test — Verify slot extraction and retention across turns.

Test scenarios:
1. Extract name in turn 1 → verify name in turn 2 without re-asking
2. Extract phone in turn 1 → verify phone persists through turn 2-3
3. Check if missing_slots correctly identifies retained vs new slots
"""

import asyncio
import sys
sys.path.insert(0, '.')

from server.brain.conversation_state import ConversationState, update_state_from_utterance
from server.brain.context_doc_builder import build, _debug_slot_state
from server.brain.v4_pipeline import _state_snapshot_for_gate
from server.brain.intent_session import IntentKind, TurnType
from server.brain.workers import ExecutionResult


def test_slot_extraction_and_retention():
    """Test that slots are extracted and retained correctly."""
    
    print("\n[TEST] Phase 1: Slot Extraction & Retention")
    print("=" * 60)
    
    # Scenario 1: Extract name in turn 1
    print("\n[Scenario 1] Extract name in first turn")
    state1 = ConversationState()
    print(f"  Initial customer_name: {state1.customer_name!r}")
    
    update_state_from_utterance(state1, "Hallo, mein Name ist Hans Mueller")
    print(f"  After extraction: customer_name={state1.customer_name!r}")
    
    if state1.customer_name:
        print("  ✓ Name extracted successfully")
    else:
        print("  ✗ Name NOT extracted!")
        return False
    
    # Scenario 2: Verify name persists in turn 2 without being asked again
    print("\n[Scenario 2] Verify name persists without re-asking")
    state_snap = _debug_slot_state({
        "customer_name": state1.customer_name,
        "phone_number": None,
        "party_size": None,
        "reservation_date": None,
        "reservation_time": None,
        "order_items": None,
    })
    
    print(f"  Slot state snapshot:")
    for slot, info in state_snap.items():
        if info["filled"]:
            print(f"    ✓ {slot}: {info['value']}")
        else:
            print(f"    - {slot}: (not filled)")
    
    # Build context doc with state that has name
    exec_result = ExecutionResult()
    ctx = build(
        intent=IntentKind.RESERVATION,
        turn_type=TurnType.UNCLEAR,
        worker_profile="reservation",
        execution_result=exec_result,
        current_state={
            "customer_name": state1.customer_name,
            "phone_number": None,
            "party_size": 2,
            "reservation_date": "2026-05-01",
            "reservation_time": "19:00",
            "order_items": None,
        }
    )
    
    print(f"\n  ContextDocument analysis:")
    print(f"    missing_slots: {ctx.missing_slots}")
    
    if "customer_name" in ctx.missing_slots:
        print("  ✗ FAIL: customer_name marked as missing even though it's in state!")
        print("    This is the root cause of re-asking bug")
        return False
    else:
        print("  ✓ customer_name NOT in missing_slots (correct)")
    
    # Scenario 3: Extract phone in turn 1, verify in turn 2
    print("\n[Scenario 3] Extract and persist phone number")
    state2 = ConversationState()
    state2.customer_name = state1.customer_name  # already have name
    
    update_state_from_utterance(state2, "Meine Telefonnummer ist 0228 1234567")
    print(f"  Phone extracted: {state2.phone_number!r}")
    
    if state2.phone_number:
        print("  ✓ Phone extracted successfully")
    else:
        print("  ✗ Phone NOT extracted!")
        return False
    
    # Turn 3: verify both name and phone persist
    print("\n[Scenario 4] Turn 3 - both slots should persist")
    ctx2 = build(
        intent=IntentKind.RESERVATION,
        turn_type=TurnType.UNCLEAR,
        worker_profile="reservation",
        execution_result=exec_result,
        current_state={
            "customer_name": state2.customer_name,
            "phone_number": state2.phone_number,
            "party_size": 2,
            "reservation_date": "2026-05-01",
            "reservation_time": "19:00",
            "order_items": None,
        }
    )
    
    print(f"  Missing slots in turn 3: {ctx2.missing_slots}")
    
    missing_required = [s for s in ["customer_name", "phone_number"] if s in ctx2.missing_slots]
    if missing_required:
        print(f"  ✗ FAIL: Should not ask for {missing_required} again!")
        return False
    else:
        print("  ✓ Both name and phone NOT re-asked (correct)")
    
    print("\n[SUMMARY] Phase 1 Slot Retention Test")
    print("=" * 60)
    print("✓ Slot extraction working")
    print("✓ Slot persistence across turns working")
    print("✓ missing_slots calculation correct")
    print("\nConclusion: Slot retention appears to be working correctly")
    print("If re-asking still happens in live calls, the issue is likely:")
    print("  - Slots not being extracted from utterance correctly")
    print("  - State not being passed correctly to context_doc_builder")
    print("  - LLM ignoring VALIDIERTE_FAKTEN section")
    
    return True


if __name__ == "__main__":
    success = test_slot_extraction_and_retention()
    sys.exit(0 if success else 1)
