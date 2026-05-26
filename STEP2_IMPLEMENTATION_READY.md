# Step 2 Implementation — Ready For Live Verification

**Status:** All 7 bug fixes implemented and unit-tested. Service restarted cleanly. Awaiting live call to verify the 12 acceptance questions.

---

## Bug-by-bug

| # | Bug | File(s) | Unit tests |
|---|-----|---------|------------|
| A | Escalation bypass (primary blocker) | `server/brain/conversation_state.py`, `server/brain/node_manager.py` | 13 PASS (A1–A10, E-guard ×10, A9a/b/c) |
| B | Name extractor matches "Ist" / single letters | `server/brain/conversation_state.py` | 12 PASS (B1–B12) |
| C | Address extractor accepts garbage | `server/brain/conversation_state.py` | 6 PASS (C1–C6) |
| D | Phone extractor can't assemble spoken digits | `server/brain/conversation_state.py` | 5 PASS (D1–D5) |
| E | Postcode loop (`address_verified` as user-facing field) | `server/brain/conversation_state.py`, `server/brain/conversation_nodes.py` | 6 PASS (E1–E6) |
| F | Raw `TOOL CALL` / `print(...)` / `[TOOL:]` / JSON in TTS | `server/brain/conversation_state.py`, `server/brain/adk_turn_processor.py` | 6 PASS (F1–F6) |
| G | "Verbindungsprobleme" TTS bypass fires spuriously | `server/main.py` | Tightened thresholds, E2E only |

**Unit test run:** `python3 tests/test_step2_bugs.py` → **ALL STEP 2 UNIT TESTS PASS** (55 checks).

---

## Files Changed

| File | Purpose of change |
|------|-------------------|
| `server/brain/conversation_state.py` | Added `_NAME_BLOCKLIST`, `_is_valid_name_candidate`, `_extract_name_from_utterance`, `_GERMAN_NUMBER_WORDS`, `_convert_number_words`, `_extract_address_from_utterance`, `_extract_phone_digits`, `strip_tool_call_leakage`, `has_valid_name`, `has_valid_phone`, `has_valid_address`, `has_valid_address_or_pickup`; rewrote `fields_to_collect`, `next_field_to_ask`, `should_escalate`; replaced three inline extractors in `update_state_from_utterance`; fixed attempt-increment to use validity not presence. |
| `server/brain/node_manager.py` | Rewrote F-A gate control flow — decoupled "valid" from "escalation". On PROCEED: falls through to commit when all fields valid; escalates only when fields invalid AND attempts capped; never silently skips commit when ready. |
| `server/brain/adk_turn_processor.py` | Wired `strip_tool_call_leakage` as first-pass sanitizer BEFORE `sanitize_bot_text_against_tool_results`, unconditionally (regardless of whether tools fired). |
| `server/brain/conversation_nodes.py` | Removed `Postleitzahl` from `_CONFIRM_DATA_RULE`; in ORDERING step 4 dropped PLZ requirement; added "Adresse wird im Hintergrund geprüft — erwähne das nicht". |
| `server/main.py` | `STTWatchdog` thresholds tightened: `_TIMEOUT` 30→45s, `_COOLDOWN` 30→60s, `_MIN_POST_STT_SEC` 5→10s. Added `[SF_GUARD]` log lines for both FIRING and BLOCKED paths. |
| `tests/test_step2_bugs.py` | **New** — 55 unit-test checks across all 7 bugs. |

---

## Instrumentation preserved

```
$ grep -c "TRACE-2026-04-20" server/brain/adk_turn_processor.py \
    server/brain/node_manager.py server/brain/conversation_state.py \
    tools/executor.py
```
All Phase 1 trace points remain in place (needed for Step 2 live verification).

---

## Service status

```
● sailly-browser-demo.service — active (running) since 2026-04-20 14:50:09 UTC
  Main PID: 1201746 (python3 -m uvicorn server.main:app --host 127.0.0.1 --port 8080)
```
No startup errors, no `await outside async function`, no import errors.

**Trace start time recorded:** `/tmp/trace_step2_final.txt` = `2026-04-20 14:50:21 UTC`

---

## Next step — Live verification call

Please run the live call at `sailly.tech/demo-call` using this exact script:

```
1. Open sailly.tech/demo-call
2. Wait for greeting
3. Say: "Ich möchte etwas bestellen."
4. Say: "Ich nehme Bibimbap."
5. (When asked for name): "Mein Name ist Markus Schmidt."     ← the "Ist" case
6. (When asked pickup/delivery): "Lieferung."
7. (When asked for address): "Friedrichstraße zwanzig Bonn."   ← word-form number
8. (When asked for phone): "null eins fünf zwei eins zwei drei vier fünf sechs sieben acht."
9. (If bot summarizes): "Ja, passt."
10. Let the call complete.
```

After the call completes, provide the `call_sid` (visible in the demo UI) and I will produce the verification report `STEP2_VERIFICATION_<call_sid>.md` answering the 12 acceptance questions with log evidence.
