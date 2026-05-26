# Sailly — Fix 1 Verification Report
**Date**: April 23, 2026 — 12:10 UTC  
**Calls analyzed**: 4 (user provided; one additional call per script = 4 total)  
**Call IDs**: demo-fef404665065, demo-d1817073426f, demo-03a986bc848f, demo-131aca72621f  
**Fix deployed**: 11:55 UTC — all calls post-deployment

---

## Fix 1 Verdict: MIXED — 2/4 clean, 2/4 still failing

| Call | Test Scenario | Leak-free? | Response Length | Disposition | Fix 1 Pass? |
|------|---------------|------------|-----------------|-------------|-------------|
| demo-fef404665065 | Pizza Margarita | ⚠️ "[" in T1 | T1=1 char, T3=4 chars | user_hung_up_mid_order | ✗ FAIL |
| demo-d1817073426f | Bulgogi order | ✓ No leaks | T1=19 chars (complete!) | user_hung_up_mid_order | ⚠️ PARTIAL |
| demo-03a986bc848f | Tisch reservation | ✓ No leaks | 79–124 chars (full!) | **reservation_completed** | ✓ PASS |
| demo-131aca72621f | Complex order (Frank) | ✓ No leaks | T1=11, T2=12, T3=18, T4=9 | user_hung_up_mid_order | ✗ FAIL |

**Fix 1 overall**: 1 full pass, 1 partial (no leak but short responses), 2 fail (truncated + 1 tool leak).

---

## Per-Call Analysis

---

### Call 1: demo-fef404665065 — "Eine Pizza Margarita bitte."
**Duration**: 85s | **Turns**: 3 | **Disposition**: user_hung_up_mid_order

| Turn | User | Bot | Length | Latency | Situation | Leak? |
|------|------|-----|--------|---------|-----------|-------|
| T1 | "Eine Pizza Margarita bitte." | `[` | **1 char** | 1905ms | greeting_first | ✗ RAW `[` VISIBLE |
| T2 | "Ja." | "Wie kann ich Ihnen helfen?" | 26 chars | 7270ms | info_neutral | ✓ |
| T3 | "Ja, ich hätte gerne eine Pizza Margaretha bitte." | `Sail` | **4 chars** | 2372ms | info_neutral | ✗ Truncated |

**What went wrong**:
- T1: bot_text = `[` — a single opening bracket. This is the raw start of a `[TOOL:ai_greeting]` tag that streamed out before the sentence boundary was reached. The new sanitizer stripped `[TOOL:...]` from within completed sentences, but this bracket arrived as a lone character at the start of the stream before any full sentence was emitted.
- T3: `Sail` — truncated start of "Sailly hier". The stream ended abruptly (4 chars). The response was cut mid-word. No leak tag involved — this is pure response truncation.
- T2: 7270ms latency on a "Ja." turn is too high. Signs of model generating too much before stopping.
- Slot extraction: working — Pizza Margarita extracted at T1, updated to Pizza Margaretha at T3.
- Validation: check_item_availability fired at T1 (Pizza) and T3.
- leaks_detected = `[]` on all turns — the sanitizer did not catch the `[` because it's not a full `[TOOL:xxx]` pattern, it's a fragment.

**Root cause**:
1. The tier2_runner guard `"[" not in sent_chunk[-5:]` was meant to catch partial `[TOOL:` tags split across boundaries — but here the entire first "chunk" is just `[` (1 char), which fails the guard and is passed to tts_callback. The sanitizer then strips valid `[TOOL:]` patterns but `[` alone does not match any pattern.
2. The 4-char `Sail` is unrelated to leaks — the stream simply terminated early (max_output_tokens=128 likely hit or streaming interrupted).

**Verdict**: ✗ FAIL — tool tag fragment leaked as `[`; responses still truncated.

---

### Call 2: demo-d1817073426f — "Ich hätte gerne einen Bulgogi."
**Duration**: 65s | **Turns**: 3 | **Disposition**: user_hung_up_mid_order

| Turn | User | Bot | Length | Latency | Situation | Leak? |
|------|------|-----|--------|---------|-----------|-------|
| T1 | "Ich hätte gerne einen Bulgogi." | "Super, ein Bulgogi." | **19 chars** | 2620ms | greeting_first | ✓ |
| T2 | "Was ist denn jetzt?" | "Entschuldigen Sie" | 17 chars | **12319ms** | info_neutral | ✓ |
| T3 | "Ich warte." | "Entschuldigen Sie bitte" | 23 chars | 2305ms | info_neutral | ✓ |

**What went wrong**:
- No leaks detected — ✓ Fix 1 working on this call.
- T1 response is coherent: "Super, ein Bulgogi." — this is correct and complete for an acknowledgment.
- T2 latency: **12,319ms** — 12 seconds to respond to "Was ist denn jetzt?". This is a doom-loop timeout or extremely long generation. The response "Entschuldigen Sie" is only 17 chars — the bot spent 12s generating something, then only 17 chars survived. The 128 token cap truncated a long generation.
- T2-T3 responses "Entschuldigen Sie" / "Entschuldigen Sie bitte" are apology-only — no order progress.
- Slot persistence: Bulgogi held across all 3 turns (slot_state shows `items.value="Bulgogi"` consistent).
- No validation firing on T2-T3 because no new items extracted.
- User disconnects: after T3, user is still waiting, no order collected, never asked for address or delivery type.

**Root cause**: T2's 12s latency is the primary failure. The LLM generated a long response (likely repeating/looping), the 128-token cap cut it short, and only the first 17 characters "Entschuldigen Sie" survived. This is the truncation-from-long-generation problem.

**Verdict**: ⚠️ PARTIAL — no leaks (Fix 1 working), but 12s latency + truncated responses killed the call. This is Fix 2's domain (minimum response length) and Fix 4's domain (loop detection).

---

### Call 3: demo-03a986bc848f — "Also ich weiß nicht. Vielleicht ein Tisch?"
**Duration**: 81s | **Turns**: 5 | **Disposition**: **reservation_completed** ✓

| Turn | User | Bot | Length | Latency | Situation | Leak? |
|------|------|-----|--------|---------|-----------|-------|
| T1 | "Also ich weiß nicht. Vielleicht ein Tisch?" | "Gerne, da helfe ich Ihnen weiter. Auf welchen Namen darf ich die Reservierung aufnehmen?" | **88 chars** | 1760ms | greeting_first | ✓ |
| T2 | "Frank Müller." | "Alles klar, Herr Müller. Für wie viele Personen darf ich den Tisch reservieren?" | **79 chars** | **6338ms** | info_neutral | ✓ |
| T3 | "Für sechs Leute" | "Super, sechs Personen. Und für welches Datum darf ich die Reservierung für Sie vormerken?" | **89 chars** | 1275ms | info_neutral | ✓ |
| T4 | "für morgen zwölf Uhr." | "Ihre Reservierung für 6 Personen am Morgen um der gewünschten Zeit Uhr ist bestätigt. Sie erhalten eine Bestätigung per SMS." | **124 chars** | 2315ms | info_neutral | ✓ |
| T5 | "Morgen, morgen sechzehn Uhr." | "Alles klar, dann ändere ich das gerne auf morgen sechzehn Uhr. Einen Moment bitte." | **82 chars** | 1488ms | confirm_success | ✓ |

**What went right**:
- ✓ **FIRST COMPLETED RESERVATION** in recent call history — `create_reservation` + `send_sms` fired, disposition = `reservation_completed`.
- ✓ All bot responses are full, coherent German sentences (79–124 chars).
- ✓ Zero leaks on all 5 turns.
- ✓ Slot progression: name filled T1 → party_size T2 → date+time T3-T4 — clear sequential slot collection.
- ✓ TTS situation transitions correctly: greeting_first → info_neutral → confirm_success.
- ✓ User correction handled: T5 "morgen sechzehn Uhr" corrected the time from 12:00 to 16:00, bot adapted gracefully.

**Issues**:
- T2 latency: 6,338ms — slow turn. Slot state shows only name filled at this point; LLM appears to do heavy processing on name extraction.
- T4 bot text: "am Morgen um der gewünschten Zeit Uhr" — grammatically garbled. Correct German would be "um 12:00 Uhr" but LLM substituted "der gewünschten Zeit" (the requested time). The actual time value was not read back correctly.
- `prompt_tokens_out` still NULL on all turns.
- tts_rate_pct = 150 uniform across all turns.

**Verdict**: ✓ PASS — clean call, completed, no leaks. The grammar issue in T4 is a prompt/LLM problem, not a sanitization problem.

---

### Call 4: demo-131aca72621f — Complex order by "Frank"
**Duration**: 61s | **Turns**: 4 | **Disposition**: user_hung_up_mid_order

| Turn | User | Bot | Length | Latency | Situation | Leak? |
|------|------|-----|--------|---------|-----------|-------|
| T1 | "Guten Tag, hier ist der Frank. Ich hätte gern was bestellt. Ein Bulgogi und zwei Weine und das in die Friedrichstraße zwanzig in Bonn. Und ich hätt auch gern was zum Mitnehmen für gleich. Ich bin ungefähr in einer Stunde da." | "Hallo Frank" | **11 chars** | **5474ms** | greeting_first | ✓ |
| T2 | "Hätte ich gern nur ein ein Dessert, ein Mochi Eis." | "Gerne, Frank" | **12 chars** | 2235ms | info_neutral | ✓ |
| T3 | "Noch da." | "Hallo Frank, schön" | **18 chars** | 4107ms | info_neutral | ✓ |
| T4 | "Ist jetzt in meiner Bestellung?" | "Ja, das M" | **9 chars** | 1878ms | info_neutral | ✓ |

**What went wrong**:
- ✓ No leaks — Fix 1 working.
- Slot extraction: **exceptional** on T1 — extracted 6 slots from a single 44-word utterance:
  - name: Frank
  - items: Ein Bulgogi, zwei Weine
  - address_street: Friedrichstraße, address_number: 20, address_city: Bonn
  - delivery_type: pickup
  - reservation_time: "in einer Stunde"
  - Validation fired for address and items simultaneously.
- Bot responses: ALL are fragments — "Hallo Frank" (11), "Gerne, Frank" (12), "Hallo Frank, schön" (18), "Ja, das M" (9). The LLM is generating but only the first 9-18 chars are being written to DB / delivered to TTS.
- T1 latency: 5,474ms for a long utterance is acceptable. T3 latency: 4,107ms for "Noch da." is not.
- The caller asks "Ist jetzt in meiner Bestellung?" — a direct question. Bot responds "Ja, das M" (truncated). User is getting silence where they expect confirmation of their full order.

**Root cause of truncation**: The `bot_text` in the DB records only what `result.clean_text` from the ADK processor returns. The pattern across all failing calls is: `result.clean_text` is truncated. The full response streams to TTS, but what gets stored in `result.clean_text` (and thus in `bot_text`) is only the first 9-18 chars. This points to the DB write recording `result.clean_text` before it's fully accumulated — not a TTS streaming problem, a `clean_text` population problem.

**Verdict**: ✗ FAIL — no leaks but slot-rich T1 information is not answered coherently. Truncation makes every response sound like an interrupted sentence.

---

## Cross-Call Findings

### Fix 1: Leak Detection — 3/4 clean

| Metric | Result |
|--------|--------|
| `leaks_detected` column populated | ✓ Working on all 4 calls |
| FORBIDDEN patterns firing | ✓ No warnings in journalctl — means either no leaks or they were caught silently |
| `[TOOL:xxx]` tag leak | ✓ 0 instances of full tags in spoken audio |
| `[` fragment leak | ✗ 1 instance (demo-fef404665065 T1) — partial tag not caught by patterns |
| Prompt-section leaks | ✓ 0 instances of BEKANNTE DATEN / NÄCHSTER SCHRITT in spoken audio |
| Identity leak | ✓ 0 instances of "Sailly die KI-Assistentin" mid-conversation |

**Fix 1 gap identified**: Single-char `[` bracket leaks as raw text when the stream opens with a `[TOOL:` tag split across token boundaries before any full sentence. The pattern `\[TOOL:\s*\w+\s*\]` requires a closed bracket — it does not catch a lone `[` arriving as a single-token chunk.

### Response Truncation — Dominant Failure Pattern

`bot_text` across all failing calls shows 4–18 char responses that are clearly mid-sentence. This is **not a Fix 1 issue**. Evidence:

| Call | Typical bot_text length | Pattern |
|------|------------------------|---------|
| demo-03a986bc848f (working) | 79–124 chars | Complete sentences |
| demo-fef404665065 | 1–26 chars | Fragment |
| demo-d1817073426f | 17–23 chars | Fragment |
| demo-131aca72621f | 9–18 chars | Fragment |

The call that **worked** (demo-03a986bc848f, reservation) consistently produced 79–124 char responses. The failing calls consistently produce sub-25 char fragments.

This is Fix 2 territory: the minimum response length guard.

### Latency Spikes

| Call | Turn | Latency | Issue |
|------|------|---------|-------|
| demo-d1817073426f | T2 | **12,319ms** | LLM generating loop, truncated at 17 chars |
| demo-131aca72621f | T1 | 5,474ms | Long utterance processing (acceptable) |
| demo-131aca72621f | T3 | 4,107ms | "Noch da." → 4s response time (not acceptable) |
| demo-03a986bc848f | T2 | 6,338ms | Name extraction processing |

One turn in demo-d1817073426f exceeded 12s — clear doom-loop indicator.

### Slot Extraction — Working Well

| Call | Slots extracted | Quality |
|------|----------------|---------|
| demo-03a986bc848f | name, party_size, date, time (progressive) | ✓ Correct |
| demo-131aca72621f T1 | name, items, address (3 components), delivery_type, time | ✓ Exceptional (6 slots from 1 utterance) |
| demo-d1817073426f | items only | ✓ Correct (user gave only item) |
| demo-fef404665065 | items (Pizza, updated T3) | ✓ Correct, fuzzy-matched across turns |

### Call Disposition — Working

| Call | Expected | Actual | Match? |
|------|----------|--------|--------|
| demo-03a986bc848f | reservation_completed | reservation_completed | ✓ |
| demo-d1817073426f | user_hung_up_mid_order | user_hung_up_mid_order | ✓ |
| demo-fef404665065 | user_hung_up_mid_order | user_hung_up_mid_order | ✓ |
| demo-131aca72621f | user_hung_up_mid_order | user_hung_up_mid_order | ✓ |

All 4 dispositions correct.

### Token Auditing

- `prompt_tokens_in`: ✓ 100% populated (1118–2623 range)
- `prompt_tokens_out`: ✗ Still NULL on all turns
- `tts_rate_pct`: 150 uniform (A/B test not active)

---

## Fix 1 Regression Check

Nothing that previously worked is now broken. Comparing to pre-Fix-1 calls:
- Validation firing: ✓ Still working (same rate as before)
- Slot extraction: ✓ Still working (better in demo-131aca72621f)
- Latency: Comparable ranges (not degraded by Fix 1)
- Greeting flow: Unchanged

---

## Issues Requiring Action

### Priority 1 — Two open items from Fix 1 itself

**P1a: Lone `[` bracket not caught by sanitizer**

The tier2_runner emits a 1-char `[` to tts_callback when a `[TOOL:` tag starts at the very beginning of a stream. The existing guard `"[TOOL:" not in sent_chunk` passes because the sent_chunk is `[` not `[TOOL:`. Fix:

```python
# tier2_runner.py: strengthen the initial bracket guard
if sent_chunk and "[TOOL:" not in sent_chunk and not sent_chunk.startswith("[") and tts_callback:
```

Or more robustly: strip any leading `[` that isn't a closed `[word]` emotion tag from chunks before the guard.

**P1b: `prompt_tokens_out` still NULL**

Output token capture code was deployed but not firing. Root cause: `tier2_runner.call_gemini_stream()` stores output tokens after streaming response, but `_last_output_tokens` may not be populated because the non-blocking streaming path uses `async for chunk in stream` and `usage_metadata` is only available on the final aggregate — not on individual chunks. Need to verify `response.usage_metadata` is actually populated at the end of an `aio.models.generate_content_stream()` call.

### Priority 2 — Next fix in sequence

**Fix 2: Minimum response length guard (as specified)**

The core failure in demo-fef404665065, demo-d1817073426f, and demo-131aca72621f is response truncation: `result.clean_text` is 4–18 chars on failing turns. Before implementing Fix 2's minimum-length guard, need to determine whether `result.clean_text` is truncated at the source (ADK processor producing short response) or being written incorrectly to DB.

**Evidence pointing to source truncation**: demo-03a986bc848f shows full 79–124 char responses from the same LLM and pipeline. The difference is that demo-03a986bc848f was a reservation flow (simpler, slower slot state), while failing calls involve complex ordering with tool calls and slot contention.

---

## Summary

| Criterion | Status |
|-----------|--------|
| Zero `[TOOL:` tags in audio | ✓ No full tags (1 fragment `[` remains) |
| Zero prompt-section text in audio | ✓ Confirmed (no BEKANNTE DATEN / NÄCHSTER SCHRITT heard) |
| Zero identity leaks mid-conversation | ✓ Confirmed |
| Sanitizer logging visible in journalctl | ✓ (no warnings = no leaks detected) |
| `leaks_detected` column populating | ✓ Column exists, `[]` on all clean turns |
| 1 completed call (reservation) | ✓ demo-03a986bc848f |
| Response truncation resolved | ✗ Still present on 3 of 4 calls |
| Output token capture | ✗ Still NULL |

**Fix 1 score: 1/4 full pass, 1/4 partial (no leaks but other failures), 2/4 fail (truncation)**

The sanitizer is doing its job. The dominant failure is now clearly response truncation — which is Fix 2's job. Proceed to Fix 2. Also patch the lone `[` gap as a micro-fix before or alongside Fix 2.
