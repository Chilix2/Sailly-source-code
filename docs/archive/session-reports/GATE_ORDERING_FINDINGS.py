#!/usr/bin/env python3
"""
FINDINGS REPORT: Gate Ordering Issues in Sailly v4_pipeline.py

Generated: 2026-05-27

===== TASK 1: PHONE/ORDER READBACK GATE ORDERING =====

CRITICAL BUG FOUND (FIXED):
  Location: server/brain/v4_pipeline.py, lines 1961-1970
  
  Issue: When user confirms phone number in phone_readback_pending phase, the code was
  calling state.mark_commit_readback_confirmed("create_order") at line 1969. This 
  prematurely marks the ORDER readback as confirmed BEFORE the order readback is even shown.
  
  Impact:
    - User confirms phone → order readback gate is marked as confirmed
    - Code skips showing the priced order readback
    - User is never shown what they're ordering with the phone number
    - Direct jump to create_order attempt (which may fail)
  
  Root Cause:
    Conflation of two separate gates:
      1. phone_readback_confirmed (line 1965) — phone number confirmed
      2. _order_readback_confirmed (line 1969 via mark_commit_readback_confirmed)
  
  The code incorrectly assumed phone confirmation = order summary confirmation.
  
  FIX APPLIED (lines 1968-1970):
    OLD:
      _order_readback_confirmed_now = True
      state.mark_commit_readback_confirmed("create_order")
      logger.info("[v4_pipeline] T%d phone readback confirmed → proceeding to order commit", turn_idx)
    
    NEW:
      _order_readback_confirmed_now = False
      logger.info("[v4_pipeline] T%d phone readback confirmed → phone gate complete, awaiting order readback", turn_idx)
  
  This ensures:
    - Phone confirmation only sets phone_readback_confirmed=True
    - Does NOT premature mark _order_readback_confirmed
    - Flow continues to next gate (order readback)


GUARD VERIFICATION (Existing - No Changes Needed):
  Line 2601-2615: Prevents re-asking phone when already confirmed
    ✓ Check: not getattr(state, "phone_readback_confirmed", False)
    ✓ Confirmed phone persists in state.phone_number
    ✓ Won't re-enter phone gate after confirmation


PHONE EXTRACTION PERSISTENCE:
  Line 1986-1987: Phone is NOT reset when user denies confirmation (correct)
  Line 2635-2636: Phone extraction happens before phone readback gate (correct)
  Line 2618-2632: Invalid phone handling preserved (correct)


===== TASK 2: SIMILAR GATE-ORDERING BUGS FOUND =====

Search Pattern: Places where one gate's confirmation might prematurely advance another gate


FINDING 1: Reservation pre-commit → order flow
  Location: server/brain/v4_pipeline.py, lines 3146-3152
  Type: Order-after-reservation flow
  
  Context: If user has both order_intent and reservation_intent, the reservation 
  gate must NOT prematurely mark order readback as confirmed when user confirms 
  reservation details.
  
  Status: SAFE (No premature confirmation found)
    - Line 3152: end_call_stage = "confirmed" is set AFTER reservation confirmed
    - But order intent is checked separately
    - No call to mark_commit_readback_confirmed("create_order") during reservation phase
  

FINDING 2: Correction flow + multiple slot changes
  Location: server/brain/conversation_state.py, lines 2741-2743
  Type: Multi-gate reset on item correction
  
  Scenario: User corrects items → code resets both order_readback AND calls
  reset_commit_readback("create_order", "items_corrected")
  
  Status: CORRECT (Proper gate reset)
    - Lines 2740-2743: When items change, both flags are cleared
    - state._order_readback_confirmed = False
    - state._readback_already_shown = False
    - reset_commit_readback() called
    - This PREVENTS skipping readback with new items
  

FINDING 3: Delivery address change + order readback
  Location: server/brain/conversation_state.py, lines 1648-1655
  Type: Address change triggers full readback reset
  
  Scenario: Delivery address changes during readback phase
  
  Status: CORRECT (Proper gate reset)
    - Line 1654: _order_readback_confirmed = False
    - Line 1655: reset_commit_readback("create_order", "delivery_address_changed")
    - Forces re-showing readback with new address
  

FINDING 4: Phone change during readback phase
  Location: server/brain/conversation_state.py, lines 1668-1669
  Type: Phone number change resets confirmation
  
  Scenario: User changes phone after confirmation phase started
  
  Status: CORRECT (Proper phone gate reset)
    - Line 1669: phone_readback_confirmed = False
    - Separate from order readback reset
    - Phone must be re-confirmed before order commit


FINDING 5: Name correction in pre-commit readback
  Location: server/brain/v4_pipeline.py, lines 1894-1920
  Type: Name change during readback confirmation
  
  Scenario: User corrects name while in order_pre_commit_readback phase
  
  Status: SAFE (No gate ordering issue)
    - Lines 1909-1911: reset_commit_readback called for both order and reservation
    - But only if user explicitly denies (name correction detected)
    - Readback re-shown with corrected name


FINDING 6: Repeated order request during readback
  Location: server/brain/v4_pipeline.py, lines 2023-2026
  Type: User repeats order during confirmation
  
  Scenario: User says "Ja, ich möchte Bibimbap" (yes + new order) during readback
  
  Status: SAFE (Correct confirmation handling)
    - Line 2026: mark_commit_readback_confirmed called only when:
      - User provided LEADING confirmation ("Ja, ich...") 
      - Not just repeating items
    - Readback was already shown before this point


FINDING 7: Loop detection + confirmation gate
  Location: server/brain/v4_pipeline.py, lines 2562-2577
  Type: User complains about repetition during readback
  
  Scenario: User says "you already asked that" during order readback
  
  Status: SAFE (No gate skip)
    - Lines 2566-2577: Prevents forced commit on loop complaint
    - Asks for explicit confirmation again
    - Does NOT skip any gates


===== TASK 3: REGRESSION TEST =====

Test File: test_phone_readback_gate_regression.py

Test Scenario:
  Input 1: "ein Kimchi, ein Bibimbap und ein Wasser, geliefert an Bonner Bogen 20"
  Input 2: "null eins sechs drei vier vier acht eins hundert" (German digits: 0163448100)
  Input 3: "ja" (confirm phone)
  Input 4: "ja" (confirm order readback)

Expected Flow:
  T1: Order extracted (Kimchi + Bibimbap + Wasser, delivery to Bonner Bogen 20)
  T2: Phone extracted (+49163448100)
  T3: Phone confirmation phase (user says "ja")
  T4: Order readback shown (NOT skipped)
  T5: Order readback confirmed (user says "ja")
  → create_order executes

Invariants Verified:
  ✓ Phone confirmation does NOT mark order readback as confirmed
  ✓ Phone confirmation does NOT skip order readback display
  ✓ Phone is NOT re-asked after confirmation (line 2601 guard passes)
  ✓ Order readback is shown after phone is confirmed
  ✓ Order readback confirmation gate fires correctly

Test Status: PASSING
  Command: ./venv/bin/python test_phone_readback_gate_regression.py
  Result: ✓ All tests PASSED


===== SUMMARY OF CHANGES =====

1. server/brain/v4_pipeline.py
   Line 1968: Changed _order_readback_confirmed_now = True → False
   Line 1969: Removed state.mark_commit_readback_confirmed("create_order")
   Line 1970: Updated log message to reflect phone gate completion only

2. server/brain/conversation_state.py
   NO CHANGES (Flag separation is already correct)
   - phone_readback_confirmed (line 1214): separate phone confirmation flag
   - _order_readback_confirmed (line 1319): separate order readback confirmation flag
   - reset_commit_readback() (line 1509): correctly resets only order readback
   - Phone corrections properly handled (line 1669)

3. Test: test_phone_readback_gate_regression.py (new)
   - Regression test for phone/order readback gate ordering
   - Tests full flow: order → phone → phone confirmation → order readback → order creation
   - Verifies invariants: phone confirmation does NOT prematurely mark order readback


===== GATE ORDERING INVARIANTS CONFIRMED =====

After comprehensive search, the following invariants hold:

1. Phone gate (phone_readback_confirmed) is INDEPENDENT of order readback gate
2. Delivery address changes properly reset order readback gate
3. Item corrections properly reset order readback gate  
4. Name corrections properly reset order readback gate
5. Loop detection does NOT skip confirmation gates
6. Reservation gate does NOT interfere with order gate
7. All reset_commit_readback() calls properly cascade to clear both legacy and new flags


===== NO ADDITIONAL GATE-ORDERING BUGS FOUND =====

Comprehensive search across:
  - v4_pipeline.py: All mark_commit_readback_confirmed() calls (verified correct context)
  - conversation_state.py: All reset_commit_readback() calls (verified correct logic)
  - Delivery address gate interactions (verified separate from phone gate)
  - Reservation vs order FSM transitions (verified no premature advancement)
  - Correction flow resets (verified cascading properly)

All other gate transitions maintain proper ordering and prevent premature advancement.
"""

print(__doc__)
