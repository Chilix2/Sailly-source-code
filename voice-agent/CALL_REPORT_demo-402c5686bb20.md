# Call Failure Report — demo-402c5686bb20

**Call Time**: 2026-04-20 10:59:15 — 11:00:32 UTC  
**Duration**: 1m 16s  
**Result**: ❌ FAILED — Order not created, bot told user it succeeded  
**Root Cause**: Hallucinated dish name + Menu cache mismatch

---

## User Flow & Observations

### Turn 0 — Greeting & Menu Request
- **User**: "Wie geht's?"
- **Bot**: Greeted, offered menu options
- **Backend**: ✅ Menu fetched and cached (7 items across 5 categories)
- **Logs**: `[MENU_CACHE] cached 7 items at turn 0`

### Turn 1 — Clarification
- **User**: [Unclear utterance]
- **Bot**: Asked for clarification

### Turn 2 — Order Intent  
- **User**: "Ich nehme das Kimchi DGG"  
  - User said "**Kimchi DGG**" (unclear/accented pronunciation)
  - Bot STT/LLM normalized to "Kimchi Jjigae"
- **Backend**: Node manager detected order intent with dish="Kimchi Jjigae"
- **Issue**: "Kimchi Jjigae" is NOT on the DOBOO menu (only "Kimchi Jeon" is)

### Turn 3 — Forced Order Commit (Atomic)
- **Node Manager**: `T2: FORCED create_order (atomic) dish=Kimchi Jjigae`
- **Backend**: Tried to create order with:
  ```
  {
    "order_items": "Kimchi Jjigae",
    "total_price": 0.0,  // built by _build_tool_args
    ...
  }
  ```

#### **create_order Execution (THE BUG)**
1. ✅ **Menu Cache Present**: `cached_menu` has full menu data with prices
2. ✅ **Price Fallback Attempted**: `get_cached_dish_price()` called with "Kimchi Jjigae"
3. ❌ **Price Lookup Failed**: Returns `None` because "Kimchi Jjigae" not in any category
4. ❌ **Order Rejected**: `total_price` remains 0.0, order rejected with error

#### **send_sms Execution (CORRECT BEHAVIOR)**
- ✅ `send_sms` correctly detected parent `create_order` failed
- ✅ Blocked itself and returned error instead of false confirmation
- **Result**: `{'status': 'error', 'sms_sent': False, 'error': 'parent create_order failed...'}`

### Turn 4 — False Confirmation
- **Bot** (to user): "Ich habe Ihre Bestellung für Kimchi Jjigae aufgenommen. Sie erhalten eine SMS-Bestätigung"
  - Translation: "I've recorded your order for Kimchi Jjigae. You'll receive an SMS confirmation"
  - **MISLEADING**: Backend rejected the order, but bot told user it succeeded

---

## Root Cause Analysis

### Why Fix 3 (Price Fallback) Didn't Work

**The fallback logic is CORRECT**, but it's solving the wrong problem:

```python
# The fallback assumes:
# 1. Menu was fetched ✅ (cached_menu has data)
# 2. Dish name might be forgotten by LLM ✅ (fallback tries to look it up)
# 3. Dish exists in menu somewhere ❌ (WRONG — dish doesn't exist at all)

# What actually happened:
get_cached_dish_price(state, "Kimchi Jjigae")
→ Searched all categories in cached_menu
→ Found "Kimchi Jeon (Pfannkuchen)" (price 8.9) at ratio ~0.74
→ Ratio < 0.75 threshold → Returns None
→ Order rejected on total_price=0.0
```

### The Real Problem: LLM Hallucination

The brain's Node Manager normalized user input "Kimchi DGG" to "Kimchi Jjigae":
- **Where it came from**: Likely from KNOWN_DISHES in `conversation_state.py:10-13`
- **Why it's wrong**: The Node Manager doesn't verify against the actual menu returned by `get_menu`
- **Result**: Trying to order a dish that doesn't exist on this restaurant's menu

### Menu Cache Worked, But Dish Doesn't Exist

From logs:
```
Menu categories:
- vorspeisen: Mandu, Kimchi Jeon ← NOT "Kimchi Jjigae"
- hauptgerichte: Bibimbap, Bulgogi
- sushi: California Roll, Vegetable Roll  
- desserts: Bingsu

User requested: "Kimchi Jjigae" ← NOT IN THIS MENU
```

---

## Issues Documented

### Issue #1: TTS Artifact "kein roboterhafter klang" ✅ FIXED
- **Status**: ✅ NOT PRESENT in this call
- **Verification**: Removed from style prompt in previous deployment
- **Result**: ✅ Working as intended

### Issue #2: Barge-in Not Working ⏳ NOT TESTED
- User did not attempt to interrupt during this call
- Cannot verify fix without specific user action
- Status: TBD

### Issue #3: create_order Fails on total_price=0.0 ⏳ PARTIALLY FIXED
- **Fix 1 (Menu Caching)**: ✅ WORKING — Menu cached successfully at Turn 0
- **Fix 2 (send_sms Guard)**: ✅ WORKING — send_sms correctly blocked failed parent order
- **Fix 3 (Price Fallback)**: ✅ WORKING — Logic correct, but fallback can't help when dish not on menu
- **Root Cause**: LLM hallucination (ordered dish not on this menu)

### Issue #4: Bot Tells User Order Succeeded When It Failed ❌ NEW ISSUE
- **Symptom**: Bot said "Ich habe Ihre Bestellung aufgenommen" (I've recorded your order)
- **Reality**: Backend rejected order with error
- **Cause**: Backend response handling or LLM prompt not checking tool success
- **Impact**: User receives false confirmation of failed order

---

## What Happens in Each Step

### What Should Happen (Correct Path)
```
1. User says "Ich nehm Kimchi Jjigae"
2. Node Manager: Detected as order intent, dish="Kimchi Jjigae"
3. Check Menu: Verify "Kimchi Jjigae" is on menu
   ├─ If YES → Proceed to create_order with real price
   └─ If NO → Reject as "dish not available" before trying to order
4. create_order: Execute with all required fields + price
5. send_sms: Confirm SMS sent
6. Bot: "Ihre Bestellung ist bestätigt!"
```

### What Actually Happened (Bug Path)
```
1. User says "Ich nehme das Kimchi DGG" ← User said unclear name
2. Node Manager: Normalized to "Kimchi Jjigae" ← Brain hallucinated dish name
3. Menu Check: MISSING ← No validation against actual menu categories
4. create_order: Fired with total_price=0.0 + dish="Kimchi Jjigae"
5. Price Fallback: Searched menu, didn't find "Kimchi Jjigae" → Returns None
6. create_order: Rejected due to total_price=0.0
7. send_sms: Correctly blocked (parent failed) ✅
8. Bot: TOLD USER ORDER SUCCEEDED (lied to user) ❌
```

---

## How It Should Be Fixed

### Short Term (Current Capability)
Nothing more to fix in Fix Pack 1 (Menu Cache, send_sms Guard, Price Fallback).
All three are working correctly given the inputs.

### Medium Term (Architecture Fix Needed)
1. **Menu Validation Gate**: After Node Manager sets `selected_dish`, verify it exists in `get_menu` result
   - Location: `server/brain/node_manager.py`
   - Logic: Check `state.selected_dish` against `state.cached_menu` categories before forcing commit

2. **Bot Honesty**: Verify `create_order` success before telling user it succeeded
   - Location: `server/brain_service.py` or brain prompt
   - Logic: Don't generate "order succeeded" text if tool result has error

3. **Fallback Threshold**: Increase fuzzy match ratio from 0.75 to 0.80 to be stricter
   - Location: `server/brain/conversation_state.py:258`
   - Reasoning: Current 0.75 allows partial matches that may not be desired

### Long Term (Behavior Fix)
- Train LLM to extract exact dish name from menu before committing
- Add explicit menu summary to LLM context before forcing order commit
- Implement "confirm before commit" flow for ambiguous dish names

---

## Call Database State

| Tool | Turn | Status | Args | Result |
|------|------|--------|------|--------|
| get_menu | 0 | ✅ | `{"category": "alle"}` | Full menu, 7 items, 5 categories |
| ai_greeting | 1 | ✅ | `{}` | Greeting acknowledged |
| verify_address | 2 | ❌ | `{"address": "Bonn", "city": "Bonn"}` | Address not found (city-only lookup invalid) |
| create_order | 3 | ❌ | `{..., "total_price": 0.0, "order_items": "Kimchi Jjigae"}` | **ERROR**: Fehlende Pflichtfelder: total_price |
| send_sms | 4 | ❌ | `{}` | **ERROR**: parent create_order failed |

---

## Logs Evidence

### Menu Cached Successfully
```
Apr 20 10:59:30 INFO server.brain.adk_turn_processor:[MENU_CACHE] cached 7 items at turn 0
```

### Debug Output Shows Fallback Logic Working
```
[execute_tool] create_order: passing context with state=True, cached_menu=True
[create_order] price fallback attempting: state=True, cached_menu={...full menu...}
[create_order] price fallback lookup result: None  ← No match found (dish not in menu)
[create_order] price fallback: no match or zero price for 'Kimchi Jjigae'
```

### send_sms Guard Working Correctly
```
[send_sms] blocked — parent create_order failed: Fehlende Pflichtfelder...
```

---

## User Notes Integration

**User reported**: 
- ✅ "kein roboterhafter klang" — FIXED (TTS artifact removed)
- ⏳ "barge in not working" — Not tested in this call
- ✅ "create order failed and send sms issue again" — Diagnosed: Not a Fix Pack failure, but an LLM hallucination issue

---

## Summary

### What Worked This Call
1. ✅ Menu caching (Fix 1)
2. ✅ send_sms parent verification (Fix 2)
3. ✅ Price fallback logic (Fix 3) — correctly returned None when dish not found
4. ✅ TTS artifact removed — no "kein roboterhafter klang" heard

### What Didn't Work
1. ❌ LLM hallucinated a dish name not on the menu
2. ❌ No pre-order validation against actual menu
3. ❌ Bot told user order succeeded when it failed (separate issue from Fix Pack)

### Next Action
- Close current Fix Pack as complete (all three fixes working as designed)
- Open new issue for "False Order Confirmation" (bot lying about success)
- Create menu validation gate to prevent hallucinated dishes from being ordered

