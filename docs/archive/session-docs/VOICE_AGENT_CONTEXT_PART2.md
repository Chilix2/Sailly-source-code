# VOICE_AGENT_CONTEXT_PART2 — Detailed Implementation, Test Scenarios, and Code Diffs

**Document Status:** PART 2 / 3+ (continuation from PART 1)
**For:** Deep architectural analysis and fix validation
**Focus:** Exact code changes, test cases, and integration risks

---

## 1. EXACT CODE DIFFS FOR ALL FOUR FIXES

### FIX #1: Replace Generic Pre-Commit Summary (v4_pipeline.py, line 522)

**Current code (BROKEN):**

```python
def _build_readback_v4(state) -> str:
    """Build deterministic verbal readback of the committed reservation."""
    from server.brain.conversation_state import _iso_to_spoken_german

    if getattr(state, "reservation_created", False):  # ← Only True AFTER tool execution
        iso = getattr(state, "reservation_date", None) or ""
        spoken_date = _iso_to_spoken_german(iso) if iso else "dem vereinbarten Termin"
        spoken_time = getattr(state, "reservation_time", None) or "der vereinbarten Zeit"
        party = getattr(state, "party_size", None) or 2
        name = getattr(state, "customer_name", None)
        if not name:
            logger.error("[v4_pipeline] _build_readback_v4 called with no customer_name")
            return "Ich habe Ihre Reservierung eingetragen."
        plural = "Person" if party == 1 else "Personen"
        return (
            f"Ich habe {party} {plural} "
            f"für {spoken_date} um {spoken_time} Uhr auf den Namen {name} reserviert."
        )

    if getattr(state, "order_created", False):
        # ... order readback ...
        pass

    return "Ich habe Ihre Anfrage eingetragen."  # ← ALWAYS returns this for pre-commit
```

**When called at line 522 (pre-commit):**

```python
# Line 517–532 (reservation commit gate, BEFORE tool execution)
if _is_reservation_intent and _not_yet_committed and _all_slots:
    if not getattr(state, "pre_commit_shown", False):
        state.pre_commit_shown = True
        state.end_call_stage = "pre_commit_readback"
        summary = _build_readback_v4(state) + " Stimmt das so?"  # ← Line 522
        # Result: "Ich habe Ihre Anfrage eingetragen. Stimmt das so?"
        # (generic, reservation_created is still False!)
```

**Fixed code:**

Add new function BEFORE `_build_readback_v4()` (around line 93):

```python
def _build_pre_commit_summary_v4(state) -> str:
    """Pre-commit summary: reads slot values directly, not reservation_created flag.
    
    Called BEFORE tool execution so the flag is always False. This function
    builds the summary from raw slot values to show the caller what we're about
    to book.
    """
    from server.brain.conversation_state import _iso_to_spoken_german

    if _state_slot_filled(state, "reservation_date"):
        iso = getattr(state, "reservation_date", "")
        spoken_date = _iso_to_spoken_german(iso) if iso else "dem gewünschten Termin"
    else:
        spoken_date = "dem gewünschten Termin"
    
    spoken_time = getattr(state, "reservation_time", None) or "der gewünschten Zeit"
    party = getattr(state, "party_size", None) or 2
    name = getattr(state, "customer_name", None) or "Ihrem Namen"
    
    plural = "Person" if party == 1 else "Personen"
    return (
        f"Ich würde {party} {plural} "
        f"für {spoken_date} um {spoken_time} Uhr auf den Namen {name} reservieren."
    )
```

Then replace line 522:

```python
# BEFORE:
summary = _build_readback_v4(state) + " Stimmt das so?"

# AFTER:
summary = _build_pre_commit_summary_v4(state) + " Stimmt das so?"
```

**Why this works:**

- `_build_pre_commit_summary_v4()` reads slot values directly (e.g., `getattr(state, "reservation_date")`)
- It doesn't check `reservation_created` flag, so it works before tool execution
- It uses "würde" (would) instead of "habe" (have) to indicate a proposal, not a done deal
- Caller now hears exactly what slots were collected: "Ich würde 2 Personen für Montag um 19 Uhr auf den Namen Schmidt reservieren. Stimmt das so?"

---

### FIX #2: Reset Pre-Commit Flag on Correction (v4_pipeline.py, line 344)

**Current code (INCOMPLETE):**

```python
# Lines 340–345
if end_call_stage == "correction_pending":
    state.end_call_stage = "idle"
    end_call_stage = "idle"
    # Also reset check_availability_called so a new check fires for corrected date/time
    state.check_availability_called = False
    logger.info(f"[v4_pipeline] T{turn_idx} correction received → reset to idle + clear check_availability_called")
```

**Fixed code:**

```python
# Lines 340–346
if end_call_stage == "correction_pending":
    state.end_call_stage = "idle"
    end_call_stage = "idle"
    # Also reset check_availability_called so a new check fires for corrected date/time
    state.check_availability_called = False
    state.pre_commit_shown = False  # ← ADD THIS LINE
    logger.info(f"[v4_pipeline] T{turn_idx} correction received → reset to idle + clear check_availability_called + pre_commit_shown")
```

**Why this works:**

- When user corrects a slot ("Eigentlich Dienstag statt Montag"), `end_call_stage = "correction_pending"` is set
- On the next turn, this block resets the state machine back to "idle"
- By also resetting `pre_commit_shown = False`, the next time we enter the commit gate, the pre-commit check at line 519 (`not pre_commit_shown`) evaluates to True
- So the updated summary is shown again before re-committing

**Test case:** 
```
T1: "Ich möchte einen Tisch für 2 Personen am Montag um 19 Uhr reservieren auf den Namen Schmidt"
    → All slots filled → pre_commit_shown=True → summary shown
T2: "Ja" → User confirms
    → (pre_commit summary skipped, goes straight to tool execution—correct)
    → readback_pending state
T3: "Nein, ich meinte Dienstag" → User corrects
    → correction_pending state
T4: New turn, user says nothing (system asks "Was möchten Sie ändern?")
    → correction_pending → reset to idle, pre_commit_shown = False
T5: Worker re-extracts date as "Dienstag"
    → All slots still filled, but pre_commit_shown = False now
    → Updated summary shown: "Ich würde 2 Personen für Dienstag um 19 Uhr auf den Namen Schmidt reservieren. Stimmt das so?"
```

---

### FIX #3: Add Pre-Commit Pattern to Order Flow (v4_pipeline.py, lines 408–461)

**Current code (NO PRE-COMMIT):**

```python
# Lines 408–444
if _is_order_intent and _order_not_committed and _order_slots_ok:
    commit_tools_run: list[str] = []
    try:
        from tools.executor import execute_tool

        items = getattr(state, "selected_items", None) or []
        order_args = {
            "name": getattr(state, "customer_name", "") or "",
            "phone": getattr(state, "phone_number", "") or caller_phone or "",
            "order_items": ", ".join(items) if isinstance(items, list) else str(items),
            "order_type": "delivery" if getattr(state, "delivery_address_mentioned", False) else "takeaway",
            "payment_method": "bar",
            "delivery_address": getattr(state, "delivery_address", "") or "",
        }
        # ← IMMEDIATE TOOL EXECUTION — no verification step!
        order_result = await execute_tool(
            "create_order", order_args, call_sid, tenant_id
        )
        commit_tools_run.append("create_order")
        # ... rest of execution ...
```

**Fixed code:**

First, add helper function (around line 120, after reservation helpers):

```python
def _build_pre_commit_order_summary_v4(state) -> str:
    """Pre-commit summary for orders: reads slot values directly.
    
    Similar to _build_pre_commit_summary_v4() but for order path.
    Shows items + name before committing order to POS system.
    """
    items = getattr(state, "selected_items", None) or []
    name = getattr(state, "customer_name", None) or "Ihrem Namen"
    
    if not items:
        # Fallback if somehow no items
        items_str = "Ihre Bestellung"
    elif isinstance(items, list):
        items_str = ", ".join(items)
    else:
        items_str = str(items)
    
    return (
        f"Ich würde also {items_str} auf den Namen {name} aufnehmen."
    )
```

Then replace the order commit gate (lines 408–461):

```python
# Lines 408–461 (ENTIRE ORDER COMMIT GATE - REWRITTEN)
if _is_order_intent and _order_not_committed and _order_slots_ok:
    
    # ← FIX 4: Pre-commit readback (mirror reservation pattern)
    if not getattr(state, "order_pre_commit_shown", False):
        state.order_pre_commit_shown = True
        state.end_call_stage = "pre_commit_readback"
        summary = _build_pre_commit_order_summary_v4(state) + " Stimmt das so?"
        logger.info(f"[v4_pipeline] T{turn_idx} pre-commit order summary: {summary!r}")
        if tts_callback:
            try:
                await tts_callback(summary)
            except Exception as _cb_err:
                logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")
        return _quick_return(
            summary, "order_start", intent_result, t0,
            tools=scheduled_run, next_action="clarify", should_end=False,
        )
    
    # User confirmed on previous turn → now execute order
    commit_tools_run: list[str] = []
    try:
        from tools.executor import execute_tool

        items = getattr(state, "selected_items", None) or []
        order_args = {
            "name": getattr(state, "customer_name", "") or "",
            "phone": getattr(state, "phone_number", "") or caller_phone or "",
            "order_items": ", ".join(items) if isinstance(items, list) else str(items),
            "order_type": "delivery" if getattr(state, "delivery_address_mentioned", False) else "takeaway",
            "payment_method": "bar",
            "delivery_address": getattr(state, "delivery_address", "") or "",
        }
        order_result = await execute_tool(
            "create_order", order_args, call_sid, tenant_id
        )
        commit_tools_run.append("create_order")
        logger.info(f"[v4_pipeline] T{turn_idx} create_order → {order_result}")

        state.order_created = True
        state.end_call_stage = "readback_pending"
        readback = _build_readback_v4(state) + " Stimmt das so?"
        logger.info(f"[v4_pipeline] T{turn_idx} ORDER COMMITTED → readback: {readback!r}")

        if tts_callback:
            try:
                await tts_callback(readback)
            except Exception as _cb_err:
                logger.warning(f"[v4_pipeline] tts_callback raised: {_cb_err}")

        return _quick_return(
            readback, "order_start", intent_result, t0,
            tools=scheduled_run + commit_tools_run,
            next_action="commit",
            should_end=False,
        )
    except Exception as commit_err:
        logger.error(f"[v4_pipeline] T{turn_idx} order commit failed: {commit_err}", exc_info=True)
        error_text = (
            "Einen Moment — es gab ein Problem bei der Bestellung. "
            "Bitte versuchen Sie es nochmals oder rufen Sie uns direkt an."
        )
        if tts_callback:
            try:
                await tts_callback(error_text)
            except Exception:
                pass
        return _quick_return(
            error_text, profile, intent_result, t0,
            tools=scheduled_run + commit_tools_run,
            next_action="clarify",
            should_end=False,
        )
```

**Also add this to the `correction_pending` reset block (line 345):**

```python
# Lines 340–347 (ADD order_pre_commit_shown reset)
if end_call_stage == "correction_pending":
    state.end_call_stage = "idle"
    end_call_stage = "idle"
    state.check_availability_called = False
    state.pre_commit_shown = False
    state.order_pre_commit_shown = False  # ← ADD THIS LINE
    logger.info(f"[v4_pipeline] T{turn_idx} correction received → reset to idle + clear check_availability_called + pre_commit_shown + order_pre_commit_shown")
```

**Why this works:**

- Orders now follow the same two-step verification as reservations
- User sees exactly what items they're ordering before it goes to POS/kitchen
- If user denies ("Nein, ich wollte nur einen Bibimbap"), the system asks "Was möchten Sie ändern?" and loops
- Prevents accidental double-orders or wrong items from reaching the kitchen

---

### FIX #4: Add Grounding Gate Patterns (tiny_generator.py, lines 44–48)

**Current code (INCOMPLETE GUARD):**

```python
_TOPIC_REQUIRES_ENTITY: dict[str, str] = {
    r"wetter|temperatur|grad celsius|sonnig|bewölkt|bewoelkt|regnet": "weather_temp",
    r"speisekarte|menü\b|menue\b|auf der karte":                       "menu_data",
    r"öffnungszeit|geöffnet|geschlossen":                              "today_date",
}
```

**Fixed code:**

```python
_TOPIC_REQUIRES_ENTITY: dict[str, str] = {
    r"wetter|temperatur|grad celsius|sonnig|bewölkt|bewoelkt|regnet": "weather_temp",
    r"speisekarte|menü\b|menue\b|auf der karte":                       "menu_data",
    r"öffnungszeit|geöffnet|geschlossen":                              "today_date",
    # ← NEW: Guard against hallucinated reservation confirmations
    r"reserviert|reservierung\s*(ist\s+)?bestätigt|reservierung\s*(ist\s+)?bestaetigt|tisch\s*(ist\s+)?gebucht|haben\s+reserviert": "reservation_confirmed",
    # ← NEW: Guard against hallucinated order confirmations
    r"bestellung.*aufgenommen|bestellung.*notiert|habe.*bestellt|ihre.*bestellung|order.*confirmed|order.*placed": "order_confirmed",
}
```

**Explanation of regex patterns:**

**Reservation patterns:**
- `reserviert` — "Ihre Reservierung ist bestätigt" (literally: your reservation is confirmed)
- `reservierung\s*(ist\s+)?bestätigt` — "Die Reservierung ist bestätigt" (is confirmed)
- `tisch\s*(ist\s+)?gebucht` — "Der Tisch ist gebucht" (the table is booked)
- `haben\s+reserviert` — "Ich habe reserviert" (I have reserved)

**Order patterns:**
- `bestellung.*aufgenommen` — "Ich habe Ihre Bestellung aufgenommen" (I have taken your order)
- `bestellung.*notiert` — "Ihre Bestellung ist notiert" (your order is noted)
- `habe.*bestellt` — "Ich habe bestellt" (I have ordered)
- `order.*confirmed` — English fallback (in case model switches language)

**Why these entities are never set:**

The current v4_pipeline only sets `resolved_entities` via:
1. Worker outputs (line 301–307)
2. Pre-executed tool results injection (line 309–333)

Neither of these sources produces `reservation_confirmed` or `order_confirmed` keys. These keys are **intentionally artificial**—they act as blockers. If TinyGenerator tries to assert a confirmation, the grounding gate checks for these keys (which don't exist) and rejects the output.

**Test case:**

```
Scenario: User says "Ja" to order pre-commit summary.
Pipeline state:
  - order_created = False (tool hasn't run yet)
  - resolved_entities = {...order_items, customer_name, ...}
  - No "order_confirmed" key

Model attempts to generate:
  "Ich habe Ihre Bestellung aufgenommen."

Grounding gate (line 51–68):
  - Regex matches "bestellung.*aufgenommen"
  - Checks if "order_confirmed" in ctx.resolved_entities
  - NOT FOUND → grounding=False
  - Reject output, regenerate with constraint "Antwort ohne Bestellbestätigung"

Result:
  Model outputs: "Perfekt, ich schicke Ihre Bestellung zur Küche."
  (Or fallback if regeneration also fails.)
```

---

## 2. INTEGRATION POINTS & RISK ANALYSIS

### 2.1 How Fixes Interact with Existing Systems

**Interaction Matrix:**

| Fix | Affects | Compatibility |
|-----|---------|---------------|
| Fix #1 (pre-commit summary) | Reservation path only | ✓ Non-breaking; only changes text |
| Fix #2 (reset flag) | Correction state machine | ✓ Non-breaking; fixes existing bug |
| Fix #3 (order pre-commit) | Order path + correction logic | ⚠️ Changes behavior; test required |
| Fix #4 (grounding gate) | TinyGenerator + all intents | ⚠️ May reject valid model output; needs tuning |

---

### 2.2 Potential Interactions with ADKTurnProcessor

The file `server/brain/adk_turn_processor.py` still exists and may be active. **Key risk:**

If ADKTurnProcessor is still being called for some flows, it has its own state management and might conflict with v4_pipeline state tracking.

**Recommendation:** Verify in call trace that ALL calls route through v4_pipeline, not ADKTurnProcessor.

---

### 2.3 Grounding Gate Tuning Risk

Fix #4 adds regex patterns that might reject legitimate model outputs. **Examples that could be false positives:**

```
Model: "Ihre Reservierung für nächsten Montag: können Sie mir noch verifizieren?"
Regex: Matches "reservierung" but NOT a confirmation claim
Result: Incorrectly rejected (false positive)

Model: "Perfekt, die Bestellung der Bibimbap ist notiert und geht zur Küche."
Regex: Matches "bestellung.*notiert"
Result: Rejected even though model is saying order was noted (correctly)
```

**Mitigation:**

1. **Make patterns more specific:**
   - Instead of `bestellung.*notiert`, use `ich.*habe.*bestellung.*notiert|ihre.*bestellung.*notiert`
   - Look for first-person or possessive before the claim

2. **Monitor rejection rate:**
   - Log every grounding gate rejection with the pattern that matched
   - If rejection rate > 5%, tune patterns

3. **Staged rollout:**
   - A/B test: 10% of traffic with new patterns, 90% without
   - Compare user satisfaction before expanding to 100%

---

## 3. COMPREHENSIVE TEST SCENARIOS

### 3.1 Reservation Flow Tests

**Test Case R1: Happy Path (No Corrections)**

```
Setup:
  - User calls in
  - Tenant: DOBOO (German-language restaurant)

T0 (Greeting):
  User: "Ich möchte einen Tisch reservieren"
  Intent: RESERVATION
  Action: Clarify missing slots

T1:
  User: "Für 2 Personen am Montag um 19 Uhr"
  Workers extract: party_size=2, reservation_date=2026-05-12, reservation_time=19:00
  Remaining slots: customer_name, phone_number
  Action: Clarify

T2:
  User: "Auf den Namen Schmidt"
  Workers extract: customer_name=Schmidt
  Remaining slots: phone_number
  Action: Clarify

T3:
  User: "01234567890"
  Workers extract: phone_number=01234567890
  All slots now filled (T3, end-of-turn)
  
  Commit gate check:
    - _is_reservation_intent = True
    - _not_yet_committed = True
    - _all_slots = True (all 5 present)
    - pre_commit_shown = False
  
  Action: **Show pre-commit summary (FIX #1)**
    Summary text: "Ich würde 2 Personen für Montag um 19 Uhr auf den Namen Schmidt reservieren. Stimmt das so?"
    state.pre_commit_shown = True
    state.end_call_stage = "pre_commit_readback"
    Return with next_action="clarify" (wait for confirmation)

T4:
  User: "Ja, das stimmt"
  _is_confirmation_v4(user_text) = True
  end_call_stage == "pre_commit_readback" = True
  
  Reset to idle:
    state.end_call_stage = "idle"
    end_call_stage = "idle"
  
  Fall through to commit gate check (line 517):
    - pre_commit_shown = True (stays True, user just confirmed)
    - Proceed to execute commit tools (skip pre-commit again—correct)
  
  Execute check_availability:
    Result: "available": True
    state.check_availability_called = True
  
  Execute create_reservation:
    Result: success, reservation_id=RES123
    state.reservation_created = True
    state.end_call_stage = "readback_pending"
  
  **Build readback (FIX #1 relevance):**
    Now _build_readback_v4(state):
      - reservation_created = True (now set!)
      - Returns detailed: "Ich habe 2 Personen für Montag um 19 Uhr auf den Namen Schmidt reserviert."
    Append " Stimmt das so?" → "Ich habe 2 Personen für Montag um 19 Uhr auf den Namen Schmidt reserviert. Stimmt das so?"
    Return with next_action="commit"

T5:
  User: "Ja"
  end_call_stage == "readback_pending" = True
  _is_confirmation_v4(user_text) = True
  
  Execute:
    state.end_call_stage = "confirmed"
    Farewell: "Vielen Dank und auf Wiederhören!"
    Return with should_end=True

Expected result:
  ✓ Reservation created in DB
  ✓ User heard two distinct confirmations (pre-commit summary, then readback)
  ✓ User confirmed both before system committed
```

---

**Test Case R2: User Denies Pre-Commit Summary**

```
Same as R1 up to T3...

T3: Pre-commit summary shown
  Summary: "Ich würde 2 Personen für Montag um 19 Uhr auf den Namen Schmidt reservieren. Stimmt das so?"
  state.pre_commit_shown = True
  state.end_call_stage = "pre_commit_readback"

T4:
  User: "Nein, ich meinte Dienstag"
  _is_confirmation_v4(user_text) = False
  end_call_stage == "pre_commit_readback" = True
  
  Execute:
    state.end_call_stage = "correction_pending"
    Return: "Was möchten Sie ändern?"

T5:
  User: "Ja, Dienstag um 19 Uhr"
  Workers extract: reservation_date=2026-05-13 (Tuesday)
  end_call_stage == "correction_pending" = True
  
  Reset (FIX #2 relevance):
    state.end_call_stage = "idle"
    state.check_availability_called = False
    state.pre_commit_shown = False  # ← FIX #2
  
  Fall through to commit gate check (line 471):
    - _all_slots_present = True (still have name, phone; date just updated)
    - pre_commit_shown = False (reset by FIX #2!)
  
  Action: **Show updated pre-commit summary**
    Summary: "Ich würde 2 Personen für Dienstag um 19 Uhr auf den Namen Schmidt reservieren. Stimmt das so?"
    state.pre_commit_shown = True
    state.end_call_stage = "pre_commit_readback"
    Return with next_action="clarify"

T6:
  User: "Ja"
  (Same as T4 in R1: confirm → execute check_availability → execute create_reservation)

Expected result:
  ✓ Reservation created for TUESDAY (corrected), not Monday
  ✓ Pre-commit summary was re-shown with corrected date
  ✓ Without FIX #2, would have skipped pre-commit and booked Monday by mistake
```

---

### 3.2 Order Flow Tests

**Test Case O1: Happy Path (Order Pre-Commit - NEW)**

```
Setup:
  - User calls in
  - Tenant: DOBOO

T0 (Greeting):
  User: "Ich möchte etwas bestellen"
  Intent: TAKEAWAY (or DELIVERY)
  Action: Clarify missing slots

T1:
  User: "Einen Bibimbap und einen Bulgogi, bitte"
  Workers extract: selected_items=["Bibimbap", "Bulgogi"]
  Remaining slots: customer_name, phone_number
  Action: Clarify

T2:
  User: "Auf den Namen Müller"
  Workers extract: customer_name=Müller
  Remaining slots: phone_number
  Action: Clarify

T3:
  User: "09876543210"
  Workers extract: phone_number=09876543210
  All slots now filled (3 of 3: order_items, customer_name, phone_number)
  
  Order commit gate check (FIX #3):
    - _is_order_intent = True
    - _order_not_committed = True
    - _order_slots_ok = True (all 3 present)
    - order_pre_commit_shown = False (NEW FLAG)
  
  Action: **Show pre-commit order summary (FIX #3)**
    Summary text: "Ich würde also Bibimbap und Bulgogi auf den Namen Müller aufnehmen. Stimmt das so?"
    state.order_pre_commit_shown = True
    state.end_call_stage = "pre_commit_readback"
    Return with next_action="clarify"

T4:
  User: "Ja"
  end_call_stage == "pre_commit_readback" = True
  _is_confirmation_v4(user_text) = True
  
  Reset to idle:
    state.end_call_stage = "idle"
  
  Fall through to order commit gate (line 408):
    - order_pre_commit_shown = True (stays True, user confirmed)
    - Proceed to execute create_order (skip pre-commit again—correct)
  
  Execute create_order:
    Args: {items: ["Bibimbap", "Bulgogi"], name: "Müller", phone: "09876543210"}
    Result: success, order_id=ORD456
    state.order_created = True
    state.end_call_stage = "readback_pending"
  
  Build readback:
    _build_readback_v4(state):
      - order_created = True
      - Returns: "Ich habe Bibimbap und Bulgogi für Sie aufgenommen."
    Append " Stimmt das so?" → full readback
    Return with next_action="commit"

T5:
  User: "Ja"
  end_call_stage == "readback_pending" = True
  
  Execute:
    state.end_call_stage = "confirmed"
    Farewell: "Vielen Dank und auf Wiederhören!"
    Return with should_end=True

Expected result:
  ✓ Order created in DB (POS system notified)
  ✓ User heard two distinct confirmations (pre-commit summary, then readback)
  ✓ User confirmed both before system sent to kitchen
  ✓ Consistent UX with reservation path
```

---

**Test Case O2: Grounding Gate Rejects Hallucinated Order Confirmation (FIX #4)**

```
Setup:
  - Order pre-commit confirmed, waiting for post-commit readback (T4 in O1)
  - end_call_stage = "readback_pending"
  - Next turn would be TinyGenerator

Scenario:
  Imagine a bug or model hallucination where TinyGenerator attempts:
    "Ich habe Ihre Bestellung Bibimbap und Bulgogi aufgenommen und wird in 20 Minuten bereit sein."

Grounding gate check (FIX #4, line 51–68):
  1. Parse response → spoken = "Ich habe Ihre Bestellung Bibimbap und Bulgogi aufgenommen und wird in 20 Minuten bereit sein."
  2. Check each pattern in _TOPIC_REQUIRES_ENTITY:
     - "bestellung.*aufgenommen" regex MATCHES
     - Check if "order_confirmed" in ctx.resolved_entities
     - NOT FOUND (key never set by pipeline)
  3. Return (spoken, grounded=False)
  
  In TinyGenerator.generate() (line 204–210):
    if not was_clean:
        # Regenerate with tighter constraint
        ctx.response_constraints.must_include.append("Antwort ohne Bestellbestätigung")
        prompt2 = _build_prompt(ctx, last_turns)
        raw2 = await self._call_llm(prompt2, model)
        _, spoken2 = _parse_response(raw2)
  
  Model regenerates with constraint:
    "Wunderbar! Ihre Bestellung geht gleich zur Küche. Sie bekommen einen Anruf, wenn alles bereit ist."

Expected result:
  ✓ Original hallucinated confirmation rejected
  ✓ Model regenerated with safer text
  ✓ User never hears false confirmation
```

---

### 3.3 Grounding Gate Edge Cases

**Test Case G1: False Positive in Grounding Gate**

```
Model generates:
  "Die Reservierung ist für nächsten Montag — können Sie mir noch Ihre Mobilnummer geben?"

Regex "reservierung\s*(ist\s+)?bestätigt" does NOT match:
  - Pattern looks for "reservierung" + "ist" + "bestätigt" or "bestaetigt"
  - Actual text: "reservierung" + "ist" + "für nächsten Montag"
  - No "bestätigt" → pattern does NOT match

Result:
  ✓ NOT rejected (false positive avoided)
  ✓ Grounding gate only rejects claims with confirmation verbs
```

**Test Case G2: Catch Mixed German/English Hallucination**

```
Model generates (in German intent context):
  "Great! Your order is confirmed and will be ready in 20 minutes."

Regex "order.*confirmed" MATCHES:
  Check if "order_confirmed" in resolved_entities
  NOT FOUND
  Reject output

Model regenerates:
  "Perfekt! Ihre Bestellung wird gleich zur Küche geschickt."

Result:
  ✓ English hallucination caught and corrected
```

---

## 4. PERFORMANCE & OBSERVABILITY

### 4.1 Logging Checklist for Debugging

After deploying all fixes, check logs for these markers:

```python
# FIX #1 logs:
"[v4_pipeline] T{turn_idx} pre-commit summary: {summary!r}"
→ Should show: "Ich würde X Personen für [date] um [time] Uhr auf den Namen [name] reservieren."

# FIX #2 logs:
"[v4_pipeline] T{turn_idx} correction received → reset to idle + clear check_availability_called + pre_commit_shown"
→ Shows flag was reset after user denies

# FIX #3 logs:
"[v4_pipeline] T{turn_idx} pre-commit order summary: {summary!r}"
→ Should show order summary before commit

# FIX #4 logs (tiny_generator.py, line 63–66):
"[TinyGenerator] grounding gate REJECT: spoken mentions topic 'reserviert|...' but 'reservation_confirmed' not in resolved_entities"
→ Shows hallucination was caught
```

### 4.2 Metrics to Monitor

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Pre-commit summary shown rate (reservations) | 95–99% | < 90% |
| Pre-commit summary shown rate (orders) | 95–99% | < 90% |
| User confirmation rate (pre-commit) | 85–95% | < 70% |
| Grounding gate rejection rate | 1–5% | > 10% |
| Tool execution latency (check_availability + create_reservation) | < 2s | > 3s |
| Hallucinated confirmation attempts prevented (FIX #4) | Monitor | Any > 0 is good (means gate is working) |

---

## 5. ROLLOUT STRATEGY

### Phase 1: Fix #1 & #2 (Low Risk)

**Changes:** Text readback + flag reset
**Impact:** Reservation path only; improves UX, no behavior change
**Rollout:** Direct to 100% (can test in staging/beta first)
**Rollback plan:** Revert line 522 to old `_build_readback_v4()` call

### Phase 2: Fix #4 (Medium Risk)

**Changes:** Add grounding gate patterns
**Impact:** Tiny generator may reject valid output (false positives possible)
**Rollout:** A/B test 10% → 50% → 100%
**Monitoring:** Watch for grounding gate rejection spikes
**Rollback plan:** Remove new patterns from `_TOPIC_REQUIRES_ENTITY`

### Phase 3: Fix #3 (Higher Risk)

**Changes:** Order pre-commit behavior change
**Impact:** All takeaway/delivery orders now require two-step confirmation
**Rollout:** Staged 10% → 25% → 50% → 100% with user feedback collection
**Monitoring:** Track "user denies order pre-commit" rate; adjust flow if > 30%
**Rollback plan:** Remove order pre-commit block (lines 408–420)

---

## 6. APPENDIX: Regex Pattern Validation

**Quick test of FIX #4 patterns (Python):**

```python
import re

_TOPIC_REQUIRES_ENTITY = {
    r"wetter|temperatur|grad celsius|...": "weather_temp",
    r"speisekarte|menü\b|menue\b|auf der karte": "menu_data",
    r"öffnungszeit|geöffnet|geschlossen": "today_date",
    r"reserviert|reservierung\s*(ist\s+)?bestätigt|reservierung\s*(ist\s+)?bestaetigt|tisch\s*(ist\s+)?gebucht|haben\s+reserviert": "reservation_confirmed",
    r"bestellung.*aufgenommen|bestellung.*notiert|habe.*bestellt|ihre.*bestellung|order.*confirmed|order.*placed": "order_confirmed",
}

# Test cases
tests = [
    ("Ich habe 2 Personen für Montag um 19 Uhr auf den Namen Schmidt reserviert.", True, "reservation_confirmed"),
    ("Die Reservierung ist bestätigt.", True, "reservation_confirmed"),
    ("Der Tisch ist gebucht.", True, "reservation_confirmed"),
    ("Ihre Bestellung aufgenommen.", True, "order_confirmed"),
    ("Ich habe Ihre Bestellung notiert.", True, "order_confirmed"),
    ("Die Reservierung ist für nächsten Montag — können Sie mir noch Ihre Mobilnummer geben?", False, None),
    ("Perfekt, die Bestellung wird zur Küche geschickt.", False, None),
]

for text, should_match, expected_key in tests:
    matched = False
    for pattern, key in _TOPIC_REQUIRES_ENTITY.items():
        if re.search(pattern, text, re.IGNORECASE):
            print(f"✓ MATCH: {text[:50]}... → {key}")
            matched = True
            break
    if not matched and should_match:
        print(f"✗ FALSE NEGATIVE: {text[:50]}... should match {expected_key}")
    elif matched and not should_match:
        print(f"✗ FALSE POSITIVE: {text[:50]}... should NOT match")
```

---

**[PART 2 COMPLETE — ~60k tokens combined with PART 1 (~85k) = ~145k. Token threshold approaching. Ready for final PART 3 with test scripts and integration checklist.]**

