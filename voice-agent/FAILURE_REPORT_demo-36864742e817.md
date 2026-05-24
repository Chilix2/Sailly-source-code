# Failure Report: demo-36864742e817
**Date**: 2026-04-20  
**Duration**: 92 seconds  
**Caller**: browser_demo  
**Outcome**: client_disconnect (user hung up)

---

## Executive Summary

The call demonstrates **three critical failures in order processing**:

1. **`create_order` called with `total_price=0.0`** (mandatory field missing)
   - Bot told user order was accepted, but order was silently rejected by backend
   - User never knew the order failed

2. **`send_sms` returned success despite `create_order` failure**
   - SMS backend is a no-op that always claims success
   - Should block execution when parent order failed

3. **Barge-in worked, but user couldn't interrupt during greeting** (expected behavior)
   - Not a bug — greeting protection is functioning as designed
   - Documented for clarity

---

## Detailed Turn-by-Turn Analysis

### Turn 0 (T0): Greeting + Menu Fetch
**User says**: (silent — bot initiates greeting)

**What Should Happen**:
- Bot: deliver hardcoded greeting
- Execute forced tools: `ai_greeting()` (no-op), `get_menu("alle")`
- Result: menu cached in conversation state

**What Actually Happened**:
- ✅ Hardcoded greeting delivered: "Hallo, hier ist Sailly Ihre digitale KI vom DOBOO - Korean Soulfood."
- ✅ `ai_greeting()` executed → `{"status": "greeted"}`
- ✅ `get_menu()` executed → full menu returned with prices:
  - Bibimbap: 14.5€
  - Kimchi Jjigae: 14.5€ (in hauptgerichte)
  - etc.
- ❌ **Menu NOT cached in state for later lookup** — this is the root cause

**Logs**:
```
T0: FORCED ai_greeting
T0: FORCED get_menu (pre-execute for pure-FAQ call)
Tool result (get_menu): {"menu": {"vorspeisen": [...], "hauptgerichte": [...]}}
```

---

### Turn 1 (T1): User repeats greeting
**User says**: "Wie geht's?"

**What Should Happen**:
- Recognize greeting/small-talk
- Stay in greeting node
- Do NOT trigger order flow

**What Actually Happened**:
- ✅ Bot: "Mir geht es hervorragend, danke der Nachfrage!..."
- ✅ Only `ai_greeting()` executed (no premature order trigger)
- ✅ ORDER STALL CHECK: `order_intent=False, selected_dish=None`

---

### Turn 2 (T2): User asks for recommendations
**User says**: "Was kannst Du empfehlen?"

**What Should Happen**:
- Bot gives menu recommendations (from T0 cache)
- Transition to menu_browse node
- Wait for user to select a dish

**What Actually Happened**:
- ✅ Bot recommendations given
- ✅ No tools executed (correct)
- ✅ Barge-in worked — user interrupted: "Ich nehm..."

---

### Turn 3 (T3): User selects dish — FAILURE CASCADE
**User says**: "Ich nehm das Kimchi DJG ein."

**What Should Happen**:
1. Recognize order intent: dish selection identified as "Kimchi Jjigae"
2. Look up price from T0 menu cache: 14.5€
3. Execute `verify_address()` with user's address
4. Execute `create_order()` with:
   - `order_items="Kimchi Jjigae"`
   - **`total_price=14.5`** ← REQUIRED
5. If successful → execute `send_sms()`
6. Bot: "Bestellung aufgenommen, SMS wird gesendet"

**What Actually Happened**:
- ✅ Order intent recognized
- ❌ **Price NOT looked up** — `total_price` defaulted to `0.0`
- ✅ `verify_address()` called, returned `{"valid": false}`
- ❌ `create_order()` called with `total_price=0.0`:
  ```json
  {
    "name": "Anonym",
    "order_items": "Kimchi Jjigae",
    "total_price": 0.0,              // ← MISSING VALUE
    "payment_method": "bar",
    "order_type": "takeaway"
  }
  ```
- ❌ Backend rejected: `"error": "Fehlende Pflichtfelder: total_price"`
- ❌ **Order FAILED** — not stored in database

- ❌ `send_sms()` executed **anyway**:
  - No-op function always returns `{"status": "ok"}`
  - Misleads brain into thinking order was confirmed

- ❌ **Bot told user order was accepted**:
  ```
  "Ich habe Ihre Bestellung für Kimchi Jjigae aufgenommen. Sie erhalten eine SMS-Bestätigung."
  ```
  - User believes order is confirmed
  - **User has NO IDEA order failed**

---

## Root Causes

### RC-1: Menu cache not preserved between turns
**File**: `server/brain/node_manager.py` or `server/brain/tier2_runner.py`

**Problem**: `get_menu()` in T0 returns the menu with all prices, but this data is not stored in the conversation context. On T3, when the LLM needs to look up "Kimchi Jjigae", the price is unavailable, so `total_price` defaults to `0.0`.

**Evidence**:
- T0: `get_menu()` returns full menu (prices included)
- T3: `create_order()` has `total_price=0.0` (should be 14.5)

---

### RC-2: LLM not prompted to look up prices from cached menu
**File**: `server/brain/tier2_runner.py`

**Problem**: The system prompt/context does not instruct the LLM to:
1. Extract prices from the T0 menu result
2. Look up dish names when constructing `create_order` calls
3. Populate `total_price` with the looked-up value

**Evidence**: Despite `order_items="Kimchi Jjigae"` being correct, `total_price` was not populated.

---

### RC-3: send_sms doesn't verify create_order success
**File**: `tools/executor.py` → `_send_sms_noop()` (line ~1311)

**Problem**: The SMS function is a no-op that always returns `{"status": "ok"}`. It should:
1. Check if prior `create_order` succeeded
2. Return error or skip if order failed
3. Only return success if order succeeded

Current code:
```python
def _send_sms_noop(...):
    logger.info("[send_sms] No-op — SMS already sent by create_order/...")
    return {"status": "ok", "note": "SMS confirmation sent automatically..."}
```

---

### RC-4: No defensive fallback for missing total_price
**File**: `tools/executor.py` → `_create_order()` (line ~547)

**Problem**: The executor validates `total_price` presence but doesn't attempt auto-population. Could implement:
1. If `total_price=0.0` and `order_items` provided
2. Look up price from DOBOO_MENU_PRICES dict
3. Auto-populate before validation

This is a defensive fallback (real fix is upstream in RC-1/RC-2).

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│ T0: get_menu() 
│ Returns: {menu: {vorspeisen: [...], hauptgerichte: [...]}}
│ Prices: Bibimbap=14.5, Kimchi Jjigae=14.5, ...
│ ❌ NOT CACHED IN STATE                                   │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ T1-T2: Small talk / menu browsing                        │
│ Menu data LOST (not in conversation context)             │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│ T3: User selects "Kimchi DJG"                            │
│ ❌ LLM HAS NO ACCESS TO MENU PRICES                     │
│ ❌ LLM DEFAULTS total_price = 0.0                        │
│                                                          │
│ create_order({..., total_price=0.0})
│ ❌ Backend validation fails: "Fehlende Pflichtfelder"   │
│ ❌ ORDER NOT STORED IN DATABASE                         │
│                                                          │
│ send_sms({}) [EVEN THOUGH create_order FAILED]
│ ❌ No-op returns "status": "ok"                          │
│ ❌ MISLEADS BRAIN INTO THINKING ORDER SUCCEEDED         │
│                                                          │
│ Bot: "Ich habe Ihre Bestellung aufgenommen..."
│ ❌ USER BELIEVES ORDER WAS CONFIRMED                    │
│ ❌ USER WILL NOT RECEIVE SMS (ORDER FAILED)             │
└─────────────────────────────────────────────────────────┘
```

---

## Impact

- **User**: High — promised an order that never happened
- **Business**: Critical — lost order, silent failure
- **System**: Medium — logs are accurate, issue is reproducible

---

## Fix Priority

| RC | Issue | Effort | Impact |
|----|-------|--------|--------|
| RC-1 | Cache menu in state | Low | High |
| RC-2 | Inject menu into prompt | Low | High |
| RC-4 | Defensive price lookup | Low | Medium |
| RC-3 | Guard send_sms | Medium | High |

**Order**: RC-1 → RC-2 → RC-4 → RC-3

---

## Tool Call Sequence (Complete)

| Turn | Tool | Status |
|------|------|--------|
| 0 | `ai_greeting()` | ✅ success |
| 0 | `get_menu("alle")` | ✅ success, prices returned |
| 1 | `ai_greeting()` | ✅ success |
| 3 | `verify_address("Bonn", "Bonn")` | ⚠️ failed (address invalid) |
| 3 | `create_order({..., total_price: 0.0})` | ❌ FAILED |
| 3 | `send_sms({})` | ✅ FALSE SUCCESS (should be ❌) |

**Critical**: `send_sms` claimed success after `create_order` failure.
