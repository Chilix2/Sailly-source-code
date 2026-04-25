# Order Flow Runtime Trace — demo-c1c85c04df22

## Call Metadata
- **call_sid**: demo-c1c85c04df22
- **Start time**: 2026-04-20 13:39:20 UTC
- **End time**: 2026-04-20 13:45:40 UTC
- **Duration**: 380 seconds (~6.3 minutes)
- **Total turns**: 15
- **Outcome**: client_disconnect (no order placed)
- **DB tools recorded**: 0 (all tool calls failed — see Bug #1 below)
- **Bot's final spoken message**: "Vielen Dank für die Bestätigung, Herr Schneider. Ich überprüfe nun kurz Ihre Lieferadresse. Gerne nehme ich Ihre Bestellung..."

---

## Critical Bugs Found By This Trace

### Bug #1 (BLOCKING): `async def _create_order` declaration was stripped from executor.py

**Root cause**: My Point 9 instrumentation script corrupted executor.py by inserting the trace block inside `_fuzzy_match_dish` (a sync function) and omitting the `async def _create_order(...)` declaration line entirely. The `_create_order` body then ran at module scope (inside the sync function as dead code). Any `await` expression in that body caused a runtime `SyntaxError: 'await' outside async function`.

**Impact**: EVERY tool call failed silently with this error, including `get_menu`, `ai_greeting`, `verify_address`, `create_order`. The brain still ran (LLM responded) but tools never executed.

**Status**: ✅ **FIXED** — `async def _create_order(...)` declaration restored at line 572. Service restarted cleanly.

**Evidence**:
```
ERROR: T0: TOOL error (get_menu): 'await' outside async function (executor.py, line 585)
ERROR: T1: TOOL error (get_menu): 'await' outside async function (executor.py, line 585)
ERROR: T2: TOOL error (get_menu): 'await' outside async function (executor.py, line 585)
... (every turn, every tool)
```

---

### Bug #2 (HIGH): Name extractor returns `'N'` instead of the full name

**Evidence from trace**:
```
T11/ENTRY  user_text="Du brauchst doch meinen Namen. Du brauchst doch meinen Namen."
T11/POST_EXTRACT  extracted_name='N'   ← matched single 'N'

T12/ENTRY  user_text='Markus Schneider.'
T12/POST_EXTRACT  extracted_name='N'   ← still 'N', did not update!
```

**Two problems**:
1. The name regex matched `'N'` as a name — a single capital letter. The pattern in `update_state_from_utterance` is too loose.
2. Once `customer_name='N'` is set (non-None), it never gets overwritten even when the user says "Markus Schneider." — the extractor doesn't update an already-set name.

**Impact**: `state.customer_name` remains `'N'` through the whole call. The F-A gate sees `name` as populated (non-None truthy... wait, `'N'` is truthy). Actually this means the F-A gate was still skipping on `name` — let me re-check.

Looking at T12 F-A gate: `next_field_to_ask='address'` — so after T11, name was considered filled (because `'N'` is truthy), and the bot moved to asking for address. But "Markus Schneider" said at T12 was not extracted.

**Root cause in `update_state_from_utterance`**:
- Name regex is too aggressive (matches single uppercase letters)
- No override logic when a better name is provided later

---

### Bug #3 (HIGH): Address never extracted despite user stating it

**Evidence**:
```
T5/ENTRY   user_text='Friedrichstraße zwanzig Bonn.'
T5/POST_EXTRACT  extracted_address=None   ← not extracted
```

The address extractor in `update_state_from_utterance` didn't recognize "Friedrichstraße zwanzig Bonn" (number spoken as word "zwanzig" = 20).

**Impact**: `state.delivery_address` stays `None` all call. F-A gate never advances past `address` field.

---

### Bug #4 (MEDIUM): `delivery_choice` attempts counter not incrementing; `address` counter increments on unrelated turns

**Evidence**:
```
T3/POST_EXTRACT  field_attempts={'name': 1, 'delivery_choice': 0, 'address': 0, ...}
T4/ENTRY   user_text='Lieferung.'
T4/POST_EXTRACT  field_attempts={'name': 2, 'delivery_choice': 0, 'address': 0, ...}
   ← delivery_choice stayed 0, but name counter went to 2!

T5/POST_EXTRACT  field_attempts={'name': 2, 'delivery_choice': 0, 'address': 0, ...}
T6/POST_EXTRACT  field_attempts={'name': 2, 'delivery_choice': 0, 'address': 0, ...}
T12/POST_EXTRACT field_attempts={'name': 9, 'delivery_choice': 0, 'address': 1, ...}
   ← name counter hit 9, delivery_choice always 0, address only incremented at T12
```

The attempt counter increments `name` on every turn where name is empty — not just turns where the bot asked for name. This is the bug you identified earlier: `check_forced_commits` increments on every call instead of once per bot ask.

---

## The Trace (chronological)

```
T0/ENTRY: user="Guten Tag, wie geht's dir?" node=greeting order_intent=False
T0/POST_EXTRACT: name=None phone=None address=None dish=None order_intent=False attempts={all 0}
check_forced_commits ENTRY: node=greeting order_intent=False
ready_for_order_commit: False (no intent)
sanitize: not triggered

T1/ENTRY: user="Was kannst Du empfehlen?" node=greeting → transitions to menu_browse
T1/POST_EXTRACT: all None, order_intent=False
check_forced_commits ENTRY: node=menu_browse order_intent=False
ready_for_order_commit: False

T2/ENTRY: user="Ich nehme das Kimchi." node=menu_browse → transitions to ordering
T2/POST_EXTRACT: dish='Kimchi Jjigae' order_intent=True  ← dish auto-mapped by extractor
check_forced_commits ENTRY: node=ordering order_intent=True dish='Kimchi Jjigae'
F-A gate CHECK: next_field='name' should_escalate=False
F-A gate DECISION: SKIP_FORCE (missing name)  ← ✅ gate works

T3/ENTRY: user="Ja," node=ordering
T3/POST_EXTRACT: name=None, attempts={name:1}
F-A gate: SKIP (name still missing)

T4/ENTRY: user="Lieferung." node=ordering
T4/POST_EXTRACT: delivery_intended=True, attempts={name:2}  ← name++ again on wrong turn
F-A gate: SKIP (name still missing)

T5/ENTRY: user="Friedrichstraße zwanzig Bonn." node=ordering
T5/POST_EXTRACT: address=None  ← not extracted (number as word)
F-A gate check: node=ordering (not shown — F-A section missing here)
   NOTE: bot spoke raw TOOL CALL text out loud: "TOOL CALL: print(verify_address(...))"
   ← LLM hallucinating Python syntax in spoken response

T6: user="So, eins, sechs, drei, vier, fünf. Neun acht drei drei." (phone given)
T6/POST_EXTRACT: phone=None  ← phone not extracted!
   (digits spoken individually, extractor doesn't reassemble)

T7-T9: user asks bot to stop re-asking for phone it already collected
   Bot keeps asking → neither phone nor address in state

T10: should_escalate=True (name attempts ≥ 3 threshold)
F-A gate: next_field=None, should_escalate=True → PROCEED  ← escalate bypassed gate!

T11: user="Du brauchst doch meinen Namen."
T11/POST_EXTRACT: name='N'  ← regex matched single 'N'!

T12: user="Markus Schneider."
T12/POST_EXTRACT: name='N'  ← not updated (already set)
F-A gate: next_field='address' (name='N' is truthy → moves to address)

T13-T14: address still None, should_escalate=True
T14: F-A gate PROCEED (escalate=True overrides missing address)
   Call ended: client_disconnect
```

---

## Decision Path Summary: Where Does `create_order` Get Forced?

**In this call: never fired.** The F-A gate blocked it on every turn except when `should_escalate=True` (turns 10 and 14). On those turns, the gate returned PROCEED — but by then the call ended due to frustration.

**Key finding**: The F-A gate IS working as designed. The ordering commit was blocked on 12 of 15 turns. The problem was upstream:

1. Tools all failed (Bug #1 — now fixed)
2. Name and address extractors are broken (Bugs #2 and #3)
3. The bot couldn't actually collect the fields because extraction doesn't work

---

## What Args Went To create_order vs What Was In State

**create_order was never called** — F-A gate prevented it every turn except the final escalate turns, and the call ended before that.

---

## F-A Gate: Working or Not?

✅ **The F-A gate IS working.** Evidence:
- Turns 2, 3, 4: gate correctly identified `next_field='name'`, returned SKIP_FORCE
- Turn 10: gate correctly escalated after 3+ attempts
- Turn 11: gate returned SKIP_FORCE for `next_field='address'` (name='N' was truthy by then)
- create_order was never prematurely forced

❌ **But escalation path bypasses the gate** — when `should_escalate=True` and `next_field=None`, gate says PROCEED even though fields are actually empty (name='N' is truthy but wrong, address=None). The gate needs to check field values, not just field presence.

---

## Sanitizer Invocation

Sanitizer was invoked every turn (11 calls). `was_sanitized=False` every time — the tool results dict was empty (`{}`) because all tools failed. Sanitizer cannot help with a completely empty tool_results.

---

## Barge-In Timeline

Barge-in enabled after greeting completed (normal). No state changes during the call body.

---

## Root Cause Summary — Three Bugs Blocking End-to-End Flow

| # | Bug | Severity | Status |
|---|-----|----------|--------|
| 1 | `async def _create_order` stripped — ALL tools fail | BLOCKING | ✅ Fixed |
| 2 | Name extractor matches `'N'` instead of full name; doesn't override | HIGH | ❌ Open |
| 3 | Address extractor misses spoken-number addresses ("zwanzig" = 20) | HIGH | ❌ Open |
| 4 | Phone not extracted from individually-spoken digits | MEDIUM | ❌ Open |
| 5 | Attempt counter increments name on every turn, not on bot-ask | MEDIUM | ❌ Open |
| 6 | `should_escalate=True` bypasses F-A gate even when fields invalid | MEDIUM | ❌ Open |
| 7 | Bot speaks raw Python TOOL CALL text aloud (T5) | HIGH | ❌ Open |

---

## Immediate Next Actions

1. **Verify Bug #1 fix works** — make a test call, confirm `get_menu` executes and no `await` errors in logs

2. **Fix Bug #2 — name extractor**: Tighten the name regex (require ≥2 words, or ≥3 chars, or both), and allow override when a better name comes in later

3. **Fix Bug #3 — address extractor**: Either (a) don't extract address in `update_state_from_utterance` at all (let the LLM handle it and rely on `verify_address` tool result), or (b) use a broader pattern that accepts word-form numbers

4. **Fix Bug #4 — phone extractor**: Handle individually-spoken digits ("eins sechs drei vier fünf")

5. **Fix Bug #6 — escalation bypass**: When `should_escalate=True` and `next_field=None`, check if fields actually have real values before PROCEED — a name of `'N'` or address of `None` should re-trigger asking

6. **Fix Bug #7 — raw TOOL CALL in spoken text**: The sanitizer should strip `TOOL CALL: print(...)` patterns before text reaches TTS
