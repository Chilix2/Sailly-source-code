# Step 1 Verification Trace — demo-2fda73022c01

## Purpose
Verify that Bug #1 (stripped `async def _create_order`) is fully fixed and tools execute normally.

---

## Pre-Flight Results

| Check | Result |
|-------|--------|
| `async def _create_order` present at line 572 | PASS |
| `_fuzzy_match_dish` is clean sync function (no leaked body) | PASS |
| TRACE-2026-04-20 instrumentation counts (adk:7, node:11, state:2, executor:2) | PASS |
| `executor.py` AST parses clean | PASS |
| `adk_turn_processor.py` AST parses clean | PASS |
| Service restarted cleanly — no startup errors | PASS |
| `await outside async` errors in startup log | NONE |

All five pre-flight checks passed. Proceeded to live call.

---

## Call Metadata

- **call_sid**: demo-2fda73022c01
- **Start time**: 2026-04-20 14:19:40 UTC
- **End time**: 2026-04-20 14:26:25 UTC
- **Duration**: 405 seconds (~6.7 min)
- **Total turns**: 21
- **Outcome**: client_disconnect (no order placed)
- **DB tool rows written**: 0 (create_order never reached executor — see verdict)

---

## Tool Execution Evidence

### DB state for this call
```
 turn_number | tool_name | success | dish | price | error 
(0 rows)
```
No tool calls recorded in DB. `get_menu` and `ai_greeting` executed but are not written to `google_tool_calls` (only `create_order`, `create_reservation`, `send_sms`, etc. write rows). `create_order` never reached the executor.

### Evidence checklist

- [x] `[MENU_CACHE] cached N items` — **YES**, T0: `[MENU_CACHE] cached 7 items at turn 0`
- [ ] `[TRACE-2026-04-20] _create_order EXECUTOR received_args` — **NO** — `create_order` never reached the executor (see Why below)
- [ ] `[TRACE-2026-04-20] _create_order RETURNING` — **NO** — same reason
- [x] `SyntaxError: await outside async function` count — **ZERO** ✅
- [x] `TOOL error` count — **ZERO** ✅

### get_menu executor evidence (from journal, T0)
```
14:19:54 executor:execute_tool:201  Tool call: get_menu({"category": "alle"}) [tenant=doboo]
14:19:54 executor:execute_tool:255  Tool result (get_menu): {"menu": {"vorspeisen": [...], ...}}
14:19:54 adk_turn_processor:        T0: TOOL executed: get_menu -> {'menu': {'vorspeisen': ...
14:19:54 adk_turn_processor:        [MENU_CACHE] cached 7 items at turn 0
```

Tools execute. No `await` errors. Bug #1 is gone.

---

## The Three Verdict Questions

### 1. Did `get_menu` execute successfully and cache a menu?

**YES.**

Line evidence from T0:
```
INFO tools.executor: Tool call: get_menu({"category": "alle"}) [tenant=doboo]
INFO tools.executor: Tool result (get_menu): {"menu": {"vorspeisen": [...]...}}
INFO adk_turn_processor: [MENU_CACHE] cached 7 items at turn 0
```

`get_menu` hit the real executor, returned real DOBOO menu data, and cached it into state. Previously this call produced `TOOL error: await outside async function`. It no longer does.

### 2. Did `create_order` reach the executor during this call?

**NO** — but not because of Bug #1.

`create_order` was blocked throughout by the combination of the F-A gate and the escalation path. Here is the exact sequence:

- **T1–T3**: F-A gate correctly said SKIP (name missing, attempts 0/3).
- **T4–T20**: F-A gate said PROCEED (`next_field=None`, `should_escalate=True`). But immediately after logging PROCEED, the code hits `if state.should_escalate(): return bot_response`. This is Bug #5b: the escalation branch returns early even on the PROCEED path, so `check_forced_commits` never reaches the main `ready_for_order_commit()` check and never injects `[TOOL:create_order]` into the response.

The extractor bugs (#2, #3, #4) also compounded this: `customer_name` stayed `None` (or became `'Ist'` from "Mein Name **ist** Markus Schmidt"), `phone_number` stayed `None` (spoken digits not assembled), and address stayed `'Friedrichstraße zwanzig von'` (garbled STT + no PLZ). Because `name` and `phone` never became valid, `next_field` was non-None most of the time, keeping the gate in SKIP.

**`create_order` not reaching the executor is caused by Bug #5b (escalation bypass), not Bug #1.**

### 3. Are there zero `await outside async function` errors?

**YES.**

```
grep -c "await.*outside|SyntaxError" call_errors_v2.log → 0
```

Zero occurrences across the entire call window.

---

## Bug #1 Verdict

**Bug #1 is confirmed fixed.**

`async def _create_order` is restored at line 572. `_fuzzy_match_dish` is a clean sync function. Tools execute without `await` errors. `get_menu` returned real data and the menu was cached. The `await outside async function` error that broke every tool call in the previous trace is gone.

The reason `create_order` was not reached is **not** Bug #1. It is Bug #5b (escalation bypass returning early even on PROCEED path) combined with Bugs #2/3/4 (extractors not populating name, phone, or address into state).

**Step 2 is authorized.**

---

## New Observations (visible in this trace, not in previous)

1. **Escalation fires every turn from T4 onward**: `ESCALATION TRIGGERED — field collection failed after 3+ attempts (attempts: {'name': N, ...})`. The name counter increments every single turn because nothing in state changes — confirming Bug #5 (attempt counter increments unconditionally).

2. **Name extractor matched 'Ist'**: At T15 user said "Mein Name **ist** Markus Schmidt." The extractor extracted `'Ist'` (the verb "ist" = "is"), not the actual name. This is worse than the previous call where it matched `'N'`. The regex is matching German function words.

3. **Phone spoken as digits was not extracted**: User said "null eins fünf zwei eins zwei drei vier fünf sechs sieben acht" — `phone_number` stayed `None` all call. Extractor does not handle spoken-digit phone numbers.

4. **Address extracted as 'Friedrichstraße zwanzig von'**: Partial match with noise ("von"). The state has a partial corrupted address, not a valid one.

5. **Gemini TTS 429 quota errors**: Multiple TTS quota-exceeded errors from T13 onward caused significant silent periods. Unrelated to the current fix pack but worth noting as a user-facing issue.

6. **`ready_for_order_commit()` only logged at T0**: It was never called after T0, confirming the F-A gate + escalation path intercepts all subsequent turns before the commit check is reached.

7. **`address_verified` treated as a required field**: F-A gate started blocking on `next_field='address_verified'` at T15+, even though the user never got a `verify_address` tool execution. This is a flow problem: `address_verified` is in `fields_to_collect()` as required, but `verify_address` never fires because `create_order` is blocked, so the bot is stuck in a loop asking for PLZ (postal code) while the actual blocker is the extractor.

---

## Raw Trace Log (first 60 lines)

```
Apr 20 14:19:53 T0/ENTRY user='Guten Tag, Reeds.' node=greeting dish=None name=None phone=None order_intent=False
Apr 20 14:19:53 T0/POST_EXTRACT name=None phone=None address=None delivery=False dish=None intent=False attempts={all:0}
Apr 20 14:19:54 check_forced_commits ENTRY node=greeting turn=0 intent=False dish=None
Apr 20 14:19:54 ready_for_order_commit() returning False — intent=False dish=None order_created=False name=None phone=None address=None
Apr 20 14:19:54 sanitize INPUT: 'Guten Tag, hier ist Sailly...' tools=[(None,False),(None,False)]
Apr 20 14:19:54 sanitize OUTPUT: was_sanitized=False

Apr 20 14:20:09 T1/ENTRY user='Ich möchte etwas bestellen.' node=greeting dish=None name=None intent=False
Apr 20 14:20:09 T1/POST_EXTRACT name=None phone=None dish=None intent=True attempts={name:0,...}
Apr 20 14:20:10 check_forced_commits ENTRY node=ordering turn=1 intent=True dish=None
Apr 20 14:20:10 F-A gate CHECK node='ordering' next_field='name' should_escalate=False
Apr 20 14:20:10 F-A gate DECISION: SKIP_FORCE (missing name)

Apr 20 14:20:19 T2/ENTRY user='Ein Kimchi bitte.' node=ordering dish=None name=None intent=True
Apr 20 14:20:19 T2/POST_EXTRACT dish='Kimchi Jjigae' intent=True name=None attempts={name:1,...}
Apr 20 14:20:22 check_forced_commits ENTRY node=ordering turn=2 intent=True dish='Kimchi Jjigae'
Apr 20 14:20:22 F-A gate CHECK next_field='name' should_escalate=False → SKIP_FORCE

Apr 20 14:20:41 T3/ENTRY user='Ja, kein Problem.' dish='Kimchi Jjigae' name=None
Apr 20 14:20:41 T3/POST_EXTRACT name=None attempts={name:2,...}
Apr 20 14:20:43 F-A gate CHECK next_field='name' should_escalate=False → SKIP_FORCE

Apr 20 14:21:07 T4/ENTRY user='Ja, hätte ich gern.' dish='Kimchi Jjigae' name=None
Apr 20 14:21:07 T4/POST_EXTRACT name=None attempts={name:3,...}
Apr 20 14:21:09 F-A gate CHECK next_field=None should_escalate=True → PROCEED
  [then escalation path returns early — create_order never injected]

Apr 20 14:21:26 T5/ENTRY user='Lieferung.' delivery_intended=True
Apr 20 14:21:26 T5/POST_EXTRACT delivery_intended=True attempts={name:4,...}
Apr 20 14:21:27 F-A gate CHECK next_field=None should_escalate=True → PROCEED [early return]

... (continues T6-T20, all PROCEED+escalate, create_order never reached) ...

Apr 20 14:23:47 T15/ENTRY user='Mein Name ist Markus Schmidt.'
Apr 20 14:23:47 T15/POST_EXTRACT extracted_name='Ist'  ← wrong, matched verb "ist"

Apr 20 14:26:18 T20/ENTRY: last turn, create_order still never reached
```

## Raw Error Log Summary

- **Zero**: `await outside async function` or `SyntaxError`
- **Zero**: `TOOL error`
- **Non-zero (unrelated)**: Gemini TTS 429 quota errors (T13–T16 window)
- **Non-zero (expected)**: ESCALATION TRIGGERED warnings (T4 onward, every turn)
- **Non-zero (harmless)**: VAD stop_secs warning (pipecat config, not our code)
