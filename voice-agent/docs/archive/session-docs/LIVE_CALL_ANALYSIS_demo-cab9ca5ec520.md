---
call_sid: demo-cab9ca5ec520
started_at: 2026-04-20 00:06:30 UTC  (02:06 Berlin local)
ended_at_actual: 2026-04-20 00:08:38 UTC  (user disconnect)
ended_at_persisted: 2026-04-20 00:07:22 UTC  (premature finalize)
duration_persisted: 51s
duration_real: ~128s
turns_persisted: 3  (T0–T2)
turns_real: 6  (T0–T5)
outcome: end_call_tool (forced, never reached goodbye)
verdict: FAIL — critical content + architecture bugs
severity: S (blocking)
---

# Live Call Error Analysis — `demo-cab9ca5ec520`

## TL;DR

User greeted the bot and asked for a food recommendation. **Within 17 seconds the bot claimed to have placed a Bibimbap order and confirmed an SMS** — neither was real. When the user corrected it, the bot fell into a `verify_address("Bonn")` → `end_call` loop and silently lost the final 3 turns due to a premature `_finalize_session()` that ran while the pipeline was still alive.

**Root cause:** the stall-detector in `node_manager.py` forces `create_order` on turn 1 even without a dish/address/price, and the GUARDIAN gate does not block it. Two additional architecture bugs compound the damage.

---

## 1. What the user experienced (transcript)

| # | Role | Text |
|---|---|---|
| 0 | bot | Hallo, hier ist Sailly Ihre digitale KI vom DOBOO - Korean Soulfood. |
| 1 | user | Hallo, hier ist der Markus. **Ich hätte gern Essen bestellt. Was kannst Du empfehlen?** |
| 2 | bot | Hallo Markus, schön, dass Sie bei uns bestellen möchten |
| 3 | user | Was kannst Du empfehlen? |
| 4 | bot | **Ich habe Ihre Bestellung für Bibimbap aufgenommen. Sie erhalten eine SMS-Bestätigung.** *(hallucinated)* |
| 5 | user | **Ich habe gefragt, was Du empfehlen kannst.** *(user corrects)* |
| 6 | bot | Entschuldigen Sie bitte. Eine beliebte Empfehlung ist unser Bibimbap, ein traditionelles koreanisches Gericht… |
| *— call record ends here in DB; turns below only in logs —* |
| 7 | user | Ich nehme ein Kimchi. |
| 8 | bot | Kimchi ist bei uns keine Hauptspeise, aber wir haben Kimchi Jjigae, einen würzig… |
| 9 | user | Ich nehme das. |
| 10 | bot | Verstanden, Sie möchten also ein Kimchi Jjigae bestellen. Soll es eine Lieferung… |
| 11 | user | Eine Lieferung. |
| 12 | bot | Sehr gut. Für die Lieferung des Kimchi Jjigae benötige ich bitte noch Ihre Liefe… |

Observations:
- Bot skips directly from "willing to order" to **"order placed"** in one turn — no dish chosen, no price, no address.
- Bot doubles down by claiming an SMS was sent.
- User corrects the bot three times; bot apologises on T6 but continues in an order flow.
- Real call lasted ~2 minutes; only first 51 seconds are in `google_calls`.

---

## 2. Tool calls issued (raw)

| Turn | Tool | Args | Result |
|---|---|---|---|
| 0 | `ai_greeting` | `{}` | `{"status":"greeted"}` |
| 0 | `get_menu` | `{"category":"alle"}` | ok (full menu) |
| 1 | `create_order` | `{"name":"Anonym","phone":"browser_demo","order_type":"delivery","order_items":"Bibimbap","total_price":0.0,"delivery_address":""}` | **ERROR: `Fehlende Pflichtfelder: total_price`** |
| 1 | `send_sms` | `{}` | `{"status":"ok"}` *(no-op, but returns positive status)* |
| 2 | `verify_address` | `{"city":"Bonn","address":"Bonn"}` | `{"valid":false,"error":"Strasse nicht gefunden"}` |
| 2 | `end_call` | `{"reason":"goodbye"}` | **Twilio 404** (call_sid is a demo-prefixed sid, not a Twilio call) |

Key facts:
- `create_order` **FAILED** server-side — no row was written — yet the bot's transcript confirmed it to the user.
- `send_sms` returned `ok` despite the parent order failing — this is the no-op path that trusts the upstream order executor to have sent the SMS. It did not.
- `verify_address("Bonn","Bonn")` is a nonsense payload (city in both slots); the bot invented it.
- `end_call` 404'd (Twilio doesn't know about browser demo call_sids) but its 5-second audio-flush delay was still observed, holding the pipeline hostage.

---

## 3. Root causes (ranked)

### RC-1 (CRITICAL) — STALL DETECTOR FIRES create_order ON TURN 1

Log:
```
T1: ORDER STALL CHECK: order_intent=True, selected_dish=None, verify_address=False,
    node=ordering, turns_in_node=0, end_call_in_response=False,
    all_tools=['ai_greeting','get_menu']
T1: STALLED ORDER FALLBACK (get_menu+verify_address, no create_order after 1 turns, dish=Bibimbap)
```

`node_manager.py` detects "stall" and synthesises a `create_order` even though:
- `selected_dish` is **None** (the user never picked one — the fallback invented `dish=Bibimbap`)
- `verify_address` is **False**
- `turns_in_node=0` — user has literally just arrived in the ordering node

**Fix:** stall detector must require `selected_dish != None AND verify_address == True AND turns_in_node >= 2` before synthesising `create_order`. On turn 1 it should instead force `get_menu` or ask a clarifying question.

File: `server/brain/node_manager.py` — `_order_stall_check`.

---

### RC-2 (CRITICAL) — GUARDIAN PRE-COMMIT GATE DID NOT BLOCK

`create_order` was invoked with `total_price=0.0`, `delivery_address=""`, `order_items="Bibimbap"` (not user-selected). The `_guardian_pre_commit_check` in `tools/executor.py` should have rejected this before dispatch. Either:
- the pre-commit check is not wired on this code path (the stall-detector goes around `executor.execute_tool` perhaps), or
- the check only fires for `create_reservation`

Proof the gate is not blocking:
```
$ psql sailly -c "SELECT count(*) FROM guardian_blocks WHERE call_sid='demo-cab9ca5ec520';"
0
```

**Fix:** Wire `_guardian_pre_commit_check` into every `create_order`/`create_reservation` dispatch path, including the `forced_commits` branch in `node_manager.py`. Pre-conditions to check:
- `selected_dish in menu_items` (fuzzy OK)
- `verify_address_ok == True`
- `total_price > 0`
- `delivery_address != ""` when `order_type == "delivery"`

Log every block into `guardian_blocks` with reason.

---

### RC-3 (CRITICAL) — PREMATURE `_finalize_session` DROPS 3 TURNS

Log timeline:
```
00:07:22  BRAIN: Ending: end_call_tool          ← _finalize_session ran here
00:07:23  PostgreSQL: 7 transcripts, 6 tool_calls, 3 turn_metrics written
00:07:40  User: 'Ich nehme ein Kimchi.'         ← but the pipeline is still alive
00:08:00  User: 'Ich nehme das.'
00:08:13  User: 'Eine Lieferung.'
00:08:38  Pipeline cancelled (client disconnect) — session is already None, nothing extra persisted
```

`_finalize_session` sets `self.session = None` as a reentry guard, so later `add_transcript` calls silently no-op. Those three turns never land in `google_*` tables.

Call Analysis therefore shows `turn_count=3` / `outcome=end_call_tool` and ends at 00:07:22 even though the real call continued ~75 s longer.

**Fix (two-layer):**
1. When `result.should_end` is true, **do not** finalize immediately. Push `EndFrame` first, let pipecat drain, then finalize in the `on_client_disconnected` / `EndFrame` path (single entry point).
2. Or: keep finalize where it is but also `await self.push_frame(EndFrame())` AND make the FastAPI WS transport actually close on EndFrame so the pipeline terminates. The current code does push EndFrame (`brain_service.py:116`) but the transport ignores it — investigate propagation through `BrowserToolsBroadcaster` → `tts` → `transport.output()`.

---

### RC-4 (HIGH) — `send_sms` NO-OP RETURNS `ok` EVEN WHEN PARENT ORDER FAILED

`executor.py:_send_sms_noop`:
```
[send_sms] No-op — SMS already sent by create_order/create_reservation executor
```

Returns `{"status":"ok"}` unconditionally. When the upstream `create_order` fails (as here), no SMS ever goes out, but the bot tells the caller "Sie erhalten eine SMS-Bestätigung."

**Fix:** `_send_sms_noop` inspects the session for `last_order_status`. If the most recent `create_order` returned an error, return `{"status":"blocked","reason":"upstream_order_failed"}` so the GUARDIAN and the prompt see the truth.

---

### RC-5 (MEDIUM) — `end_call` TOOL HITS TWILIO API FOR BROWSER CALLS

```
Twilio call end failed: 404  .../Calls/demo-cab9ca5ec520.json was not found
[end_call] Waiting 5s for audio buffer to flush before hanging up...
```

For browser demo calls the `call_sid` is `demo-<hex>` and has no Twilio counterpart. The tool still makes the REST call and burns 5 seconds waiting.

**Fix:** in `tools/executor._end_call`, short-circuit when `call_sid.startswith("demo-")` or `caller_number == "browser_demo"` — just return success and skip the Twilio call and the 5-second sleep.

---

### RC-6 (MEDIUM) — STALL DETECTOR KEEPS FIRING AFTER USER CORRECTION

Even after the user explicitly said "I asked what you recommend" (T2 user), the node manager forces `verify_address` on T2/T3 because the sticky `delivery_flag` is still set. The bot apologises but the underlying state machine is already committed to the ordering branch.

**Fix:** reset `delivery_flag`, `selected_dish` and `order_intent` on any user utterance that contains an intent-reset cue (`"entschuldigung ich wollte..."`, `"ich habe gefragt..."`, `"nein..."`).

---

### RC-7 (LOW) — `verify_address("Bonn", "Bonn")` ACCEPTED

The bot fabricated the address payload with both `city` and `address` = "Bonn". Google Maps returned `location_type=APPROXIMATE`. The executor already flags low-quality matches, but the tool should reject same-value-for-both-slots pre-flight (pure garbage-in).

**Fix:** in `tools/executor._verify_address`, reject when `city == address` or `len(address.split()) < 2`.

---

## 4. Turn-latency breakdown

| Turn | user_text | bot_text (prefix) | llm_latency_ms |
|---|---|---|---|
| 1 | Hallo, hier ist der Markus. Ich hätte gern... | Hallo Markus, schön, dass Sie bei uns... | 2615 |
| 2 | Was kannst Du empfehlen? | Ich habe Ihre Bestellung für Bibimbap... | **1276** (dangerously fast hallucination) |
| 3 | Ich habe gefragt, was Du empfehlen kannst. | Entschuldigen Sie bitte. Eine beliebte... | 6204 |

T2 took only 1.3 s because the stall-fallback path short-circuits the LLM with a templated "order placed" response — the bot didn't even think about the user's question before claiming the order was done.

---

## 5. What's working (to keep)

- Greeting is now the exact hardcoded string ("Hallo, hier ist Sailly Ihre digitale KI vom DOBOO - Korean Soulfood.")
- STT transcription quality is good (German with proper names).
- `on_client_disconnected` handler fires immediately — no more 120 s idle wait.
- `google_turn_metrics` now populated (3 rows, with user_text/bot_text/latencies).
- All other DB fields (transcripts content, tool args, tool results) now populated.

---

## 6. Recommended next actions (priority order)

| # | Action | File(s) | Est. |
|---|---|---|---|
| 1 | Harden stall-detector: require `selected_dish` + `verify_address_ok` + `turns_in_node>=2` before forcing `create_order` | `server/brain/node_manager.py` | 30 min |
| 2 | Wire `_guardian_pre_commit_check` into forced-commit path in `node_manager.py`; enforce pre-conditions; persist blocks | `server/brain/node_manager.py`, `tools/executor.py` | 1 h |
| 3 | Fix premature finalize: push `EndFrame` first, finalize in single path (`on_client_disconnected` or `EndFrame`) | `server/brain_service.py`, `server/main.py` | 45 min |
| 4 | Short-circuit `_end_call` for `call_sid.startswith("demo-")` — no Twilio, no 5 s sleep | `tools/executor.py` | 10 min |
| 5 | `_send_sms_noop` returns blocked status when upstream order failed | `tools/executor.py` | 15 min |
| 6 | Intent-reset detector on user correction cues ("ich habe gefragt...") | `server/brain/node_manager.py` | 30 min |
| 7 | Reject `verify_address` when `city == address` or single-token address | `tools/executor.py` | 10 min |

All seven fixes are local and low-risk — estimate ~3.5 dev-hours to land with unit tests.

---

## 7. Acceptance criteria for the re-test

After fixes, the same conversation should produce:

- T1 bot response: *"Gerne! Unsere beliebtesten Empfehlungen sind Bibimbap, Bulgogi und Kimchi Jjigae. Was darf es sein?"* — no `create_order`.
- `guardian_blocks` has **0 rows** (because no bad `create_order` is ever attempted).
- `google_turn_metrics` has **all turns** for the call, not just the first 3.
- `duration_seconds` in `google_calls` equals the real call length ±2 s.
- `tool_distribution` for the call: `ai_greeting:1, get_menu:1, end_call:1` — no `create_order`/`send_sms` without confirmed dish+address+price.
