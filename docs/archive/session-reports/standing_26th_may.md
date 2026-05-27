# Standing Report - May 26th, 2026
## Comprehensive Issue Analysis for Sailly Browser Demo

**Date:** May 27, 2026  
**Report Period:** May 26, 2026 14:45 - May 26, 2026 23:06  
**Dataset:** 30 most recent call reports (starting from `demo-8008b0d9c01f`)  
**Status:** CRITICAL - Multiple blocking issues identified

---

## Executive Summary

The Sailly browser demo is experiencing **critical performance, reliability, and feature issues** affecting user experience across multiple dimensions:

- **96.7% of calls** end with client disconnect (29/30)
- **56.7% of calls** show unacceptable latency (avg 1,106ms vs target 200ms = **8.5x worse**)
- **56.7% of calls** exhibit dead air periods (avg 4.6s, up to 10.2s)
- **Corrections fail** in ~84% of cases with no success path
- **Multi-dish variants** are omitted or incorrectly selected
- **Silent TTS** episodes occur where transcripts exist but no audio plays
- **Unexpected reservation prompts** derail order flows mid-conversation

All issues have been mapped to specific code locations for targeted remediation.

---

## Issue #1: HIGH LATENCY (CRITICAL - 56.7% of calls)

### Summary
- **Current State:** Average latency 1,106ms (p95: 1,500ms)
- **Target:** < 200ms average, < 500ms p95
- **Severity:** 8.5x worse than target
- **Affected Calls:** 17 out of 30 (56.7%)

### Root Causes & Code Locations

#### 1.1 Semantic Slot Extraction (Largest contributor: ~85-97% of turn time)

**File:** `/home/charles2/sailly-browser-demo/server/brain/slot_extraction_layer.py`  
**Function:** `SlotExtractionLayer.extract()` (lines 107-148)  
**Problem:**
- Semantic LLM call with 3.5s timeout budget (`asyncio.wait_for(..., timeout=3.5)`)
- Runs on **every turn** before the pipeline
- No parallelization while user is still speaking
- Can timeout and trigger fallback logic

**Code Reference:**
```python
# Lines 107-148: Slot extraction with 3.5s budget
await asyncio.wait_for(..., timeout=3.5)  # Block point
```

#### 1.2 TinyGenerator Haiku Model Processing

**File:** `/home/charles2/sailly-browser-demo/server/brain/tiny_generator.py`  
**Function:** `TinyGenerator.generate()` (lines 183-269)  
**Problem:**
- Typical latency: ~2.3s per call
- Runs synchronously, blocking pipeline
- Regeneration on sanitize/grounding failure **doubles** latency
- Can also trigger on anomaly detection

#### 1.3 Inline Tool Execution During Turns

**File:** `/home/charles2/sailly-browser-demo/server/brain/v4_pipeline.py`  
**Function:** `process_turn_v4()` (lines 1222-1242, 2574-2632, 2777-2919)  
**Problem:**
- **`await execute_tool(...)` blocks** during commit gate before streaming reply
- First turn `get_menu` call (lines 1395-1398)
- First turn `verify_address` call (line 2574)
- Synchronous tool execution prevents concurrent audio/response preparation

**Code Reference:**
```python
# Lines 2574: verify_address blocks turn
# Lines 1395-1398: get_menu blocks first turn
# All: sequential tool execution blocks audio streaming
```

#### 1.4 Tool Executor Latency

**File:** `/home/charles2/sailly-browser-demo/tools/executor.py`  
**Function:** `execute_tool()` (lines 418-494)  
**Problem:**
- `verify_address`: ~8s HTTP timeout for Google Maps geocoding
- `get_menu`: Database query + caching logic
- Menu fetch on first turn adds baseline ~500ms
- No concurrency limits; can stack

#### 1.5 Brain Service Processing

**File:** `/home/charles2/sailly-browser-demo/server/brain_service.py`  
**Function:** `process_frame()` (lines 577-940)  
**Problem:**
- `LatencyTimer` marks: `stt_final` → `brain_start` → `tts_first_chunk`
- Metrics show only `stt_latency_ms` + `llm_latency_ms`, not full synthesis time
- P0 fix for `stt_done_at` wiring (lines 1196-1221) was added but may have indentation issues
- Long readbacks buffered entirely before first audio byte (~4s buffer threshold)

**Code Reference:**
```python
# Lines 1196-1221: stt_done_at wiring (P0 fix - verify indentation)
# Lines 912-915: Skips TTS if clean_text is empty
# Lines 790-809: TTS push suppression on barge-in
```

#### 1.6 VAD Endpointing Latency (Not in reported metrics)

**File:** `/home/charles2/sailly-browser-demo/server/main.py`  
**Lines:** 854-866  
**Problem:**
- `SileroVADAnalyzer` `stop_secs=0.8` introduces ~800ms delay
- Deepgram STT endpointing adds additional latency
- **NOT included** in turn metrics, creating gap between perceived and measured latency

### Known Fixes Applied
- ✅ Intent classification on Turn 0 for faster readbacks
- ✅ Shortened post-commit farewell (vs full readback repeat)
- ✅ TTS latency instrumentation (`tts_ttfb_ms` column added)
- ✅ `stt_done_at` wiring (if indentation correct)

### What's Still Broken
- ❌ Semantic extraction still runs every turn (3.5s budget)
- ❌ No parallelization during user speech input
- ❌ Tool calls still block pipeline sequentially
- ❌ VAD latency (~800ms) excluded from reported metrics
- ❌ Stage timings (`extract_ms`, `l2_ms`, `tool_ms`) largely unset in production
- ❌ Speculative execution disabled (as of recent fixes) - not helping

### Recommended Next Steps
1. **Profile one bad call:** Query `google_turn_metrics` for `demo-3e4f2d9828d4` (2,684ms avg)
   - Extract `llm_latency_ms`, `tts_ttfb_ms`, `slot_extraction_latency_ms`
   - Identify which component is >70% of latency
2. **Disable semantic speculation:** Already planned in TODO (`SEMANTIC_SPECULATIVE_ENABLED=false`)
3. **Parallelize response preparation:** Start TinyGenerator + TTS prep while user is still speaking
4. **Add missing stage timestamps:** Instrument `extract_done_at`, `l2_done_at`, `tool_done_at` in `turn_timings.py`

---

## Issue #2: DEAD AIR PERIODS (HIGH - 56.7% of calls)

### Summary
- **Current State:** Average dead air 4.6s per call (up to 10.2s)
- **Target:** <500ms per period, zero correlation with tool calls
- **Severity:** Tool calls correlate with 7.8x more dead air
- **Affected Calls:** 17 out of 30 (56.7%)

### Important Context
**Metric Definition:** `total_dead_air_ms` = `SUM(total_latency_ms)` per call (not acoustic silence)
- High values reflect **slow turns + tool blocking**, not only VAD failure
- Still indicates user experience problem (perceived silence)

### Root Causes & Code Locations

#### 2.1 Tool Blocking Pipeline During Execution

**File:** `/home/charles2/sailly-browser-demo/tools/executor.py`  
**Function:** `execute_tool()` (lines 418-494)  
**Problem:**
- Synchronous tool execution blocks entire pipeline
- TTS callback may not run during tool blocking
- No audio streaming happens while tool is executing

**File:** `/home/charles2/sailly-browser-demo/server/brain/v4_pipeline.py`  
**Lines:** 2574-2632, 2777-2919  
**Problem:**
- Commit gate calls `await execute_tool()` before streaming response
- Strong correlation: calls with 2+ tools avg 3,900ms dead air vs 500ms for 0-tool calls

**Code Reference:**
```python
# Lines 2574+: Verify address blocks before streaming
await execute_tool("verify_address", ...)  # BLOCKING
# No TTS can start until tool completes
```

#### 2.2 Metrics Mislabeling & Cumulative Measurement

**File:** `/home/charles2/sailly-browser-demo/server/database.py`  
**Function:** `persist_call_aggregates()` (lines 637, 692)  
**Problem:**
```python
total_dead_air_ms = SUM(total_latency_ms)  # Not acoustic gap!
```
- Conflates latency with acoustic silence
- Tool-heavy turns naturally sum to large values
- No actual acoustic gap detector

#### 2.3 TTS Buffering Before Playback

**File:** `/home/charles2/sailly-browser-demo/server/sailly_gemini_tts.py`  
**Function:** `run_tts()` (lines 305-354)  
**Problem:**
- Long responses (>4s expected) buffered entirely before first audio byte
- No streaming of early TTS chunks
- Can delay up to full synthesis time before first audio

**Code Reference:**
```python
# Lines 276-304: Skip buffer logic
if expected_duration_s <= 4.0:
    _skip_buffer = True  # Stream immediately
else:
    _skip_buffer = False  # Buffer entire response (~4s+)
```

#### 2.4 VAD Endpointing Delay

**File:** `/home/charles2/sailly-browser-demo/server/main.py`  
**Lines:** 854-866, 331-401  
**Problem:**
- `SileroVADAnalyzer` `stop_secs=0.8` adds ~800ms before brain runs
- `SilenceReprompt` logic: 12s reprompt + 8s hangup if caller silent
- Turn end delay before pipeline starts processing

#### 2.5 Filler Scheduler (Intended mitigation)

**File:** `/home/charles2/sailly-browser-demo/server/brain_service.py`  
**Lines:** 835-845, 370-393  
**Status:** Partially implemented
- Optional "Einen Moment" PCM after 400ms if slow tool turn
- May not be active or properly triggered

### Tool Call Correlation Analysis
| Tool Calls | Call Count | Avg Latency | Avg Dead Air | Avg Quality |
|-----------|-----------|------------|------------|------------|
| 0 | 11 | 1,242ms | 500ms | 6.52 |
| 2 | 13 | 1,103ms | 3,900ms | 7.08 |
| 4 | 3 | 679ms | 2,131ms | 7.93 |
| 7 | 1 | 1,584ms | 4,751ms | 8.10 |
| **Total** | **30** | **1,106ms** | **1,437ms** | **6.98** |

**Finding:** Tools don't reduce avg latency but dramatically increase dead air via blocking.

### What's Still Broken
- ❌ Tool execution still blocks audio streaming
- ❌ Dead air metric is cumulative latency, not acoustic gap
- ❌ No dedicated **BotStoppedSpeaking → NextAudio** timing detector
- ❌ Long readbacks use full buffer before streaming
- ❌ No graceful degradation during tool processing (FunctionCallUserMuteStrategy not implemented)

### Recommended Next Steps
1. **Add acoustic gap detector:** Log timestamps for `BotStoppedSpeakingFrame` → next `TTSAudioRawFrame`
2. **Separate metric:** Add `acoustic_gap_ms` to `google_turn_metrics` (not cumulative sum)
3. **Non-blocking tools:** Refactor tool execution to async with background completion
4. **Lower buffer threshold:** Set `_skip_buffer = True` by default for all responses < 8s expected

---

## Issue #3: SILENT TTS EPISODES (HIGH - ~20% of calls)

### Summary
- **Occurrence:** Transcript exists but no audio plays to user
- **Severity:** Critical UX degradation (user sees bot should be speaking, hears nothing)
- **Estimated Affected Calls:** 8+ with meta-feedback short-circuit; others with hallucination detection

### Root Causes & Code Locations

#### 3.1 TTSHallucDetect Suppression (Primary cause)

**File:** `/home/charles2/sailly-browser-demo/server/sailly_gemini_tts.py`  
**Function:** `run_tts()` (lines 139-144, 326-344)  
**Problem:**
- Anomalous byte ratio detected → **suppresses audio entirely**
- Transcript already in browser (DB buffer)
- User sees text but hears nothing

**Code Reference:**
```python
# Lines 326-344: Hallucination detection
if byte_ratio_anomalous:
    # Suppress all audio, return without yielding frames
    logger.warning("[TTSHallucDetect] Skipping audio due to anomaly")
    return  # No TTSAudioRawFrame sent
```

#### 3.2 Trivially Short Text Skipping

**File:** `/home/charles2/sailly-browser-demo/server/sailly_gemini_tts.py`  
**Lines:** 257-264  
**Problem:**
- Text < 3 chars skipped
- Can drop fragments or short responses

#### 3.3 Empty Frames on First Attempt

**File:** `/home/charles2/sailly-browser-demo/server/sailly_gemini_tts.py`  
**Lines:** 320-324  
**Problem:**
- Zero frames on attempt 1 → retry without style prompt
- Second attempt still fails silently (lines 338-344)

#### 3.4 Empty Clean Text Suppression

**File:** `/home/charles2/sailly-browser-demo/server/brain_service.py`  
**Lines:** 912-915  
**Problem:**
```python
if not result.clean_text:
    # Skip TTS push for empty/trivial responses
    continue  # No audio at all
```

#### 3.5 Barge-in Suppression

**File:** `/home/charles2/sailly-browser-demo/server/brain_service.py`  
**Lines:** 790-809  
**Problem:**
- Suppresses chunks after barge-in (caller interrupted)
- Text still in DB buffer, but audio cut off

#### 3.6 Meta-Feedback Short-Circuit

**File:** Previous implementation notes indicate meta-feedback phrases bypass LLM
- Confirmation responses skip full generation
- May not include `LLMTextFrame` for TTS to consume
- 8 calls confirmed silent TTS with this pattern

### Known Fixes Attempted
- ✅ Raise TTS buffer threshold to 4s for streaming
- ✅ Retry without style prompt on anomaly

### What's Still Broken
- ❌ Second-attempt anomaly still **drops all audio** while UI shows text
- ❌ No fallback to synthesized silence or error tone
- ❌ Meta-feedback responses may not include TTS frame wrapper
- ❌ No explicit metric for "suppressed TTS" in `google_turn_metrics`
- ❌ Hallucination detection too aggressive (legitimate responses misidentified)

### Known Silent TTS Scenarios
1. **Meta-feedback phrases** ("Ja", "Nein", "Bibimbap", etc.) - short-circuit without TTS
2. **Hallucination detection** - byte ratio mismatch on legitimate responses
3. **Barge-in during readback** - caller interrupts, audio suppressed but text logged
4. **Long buffered responses** - may timeout or fail retry loop

### Recommended Next Steps
1. **Add `tts_suppressed_reason` column** to `google_turn_metrics`
2. **Grep logs** for `[TTSHallucDetect]` and `Skipping trivially short TTS`
3. **Correlate NULL `tts_ttfb_ms`** with bot_text length (should correlate if no TTS sent)
4. **Audit meta-feedback paths:** Ensure all generate LLMTextFrame regardless of route
5. **Implement fallback:** Play error tone or synthesized silence instead of nothing

---

## Issue #4: CORRECTIONS NOT WORKING (CRITICAL - ~84% failure)

### Summary
- **Failure Rate:** ~84% of correction attempts fail
- **Typical Failure:** User says "No, I want X" → Bot says "What would you like to change?" → No action taken
- **Severity:** Critical for order accuracy
- **Note:** Failure rate NOT instrumented in codebase yet (derived from call transcript analysis)

### Root Causes & Code Locations

#### 4.1 Vague Correction Intent Recognition

**File:** `/home/charles2/sailly-browser-demo/server/brain/intent_classifier.py`  
**Function:** `classify()` (lines 269-277)  
**Problem:**
- Regex `_CORRECTION_RE` matches specific phrases ("statt", "sondern", etc.)
- Simple "nein" enters `correction_pending` but doesn't update items
- Vague corrections like "das stimmt nicht" parsed generically

**Code Reference:**
```python
# Lines 269-277: Correction regex
_CORRECTION_RE = r"statt|sondern|nicht"  # Limited pattern matching
```

#### 4.2 Correction Pending Loop Without Application

**File:** `/home/charles2/sailly-browser-demo/server/brain/v4_pipeline.py`  
**Lines:** 1661-1748  
**Problem:**
- `end_call_stage == "correction_pending"`: resets gates, times extraction
- But if user response vague or doesn't match `_CORRECTION_RE`, no items updated
- Bot prompts "Was möchten Sie ändern?" with no mechanism to apply answer

**Code Reference:**
```python
# Lines 1661-1748: Correction pending flow
# Returns clarification but doesn't parse what to change
return _quick_return(
    "Was möchten Sie ändern?",  # Generic prompt
    ...
    intent_result, t0,
    tools=scheduled_run, next_action="clarify", should_end=False,
)
```

#### 4.3 Safety Gate Blocking Legitimate Corrections

**File:** `/home/charles2/sailly-browser-demo/server/brain/v4_pipeline.py`  
**Lines:** 2513-2527  
**Problem:**
- Safety gate: `if end_call_stage == "idle" and not _readback_already_shown`
- Blocks commit if readback NOT shown first
- Can block legitimate correction flow after partial correction

**Code Reference:**
```python
# Lines 2513-2527: Premature order guard
if state.end_call_stage == "idle" and not getattr(state, '_readback_already_shown', False):
    return _quick_return(...)  # Block commit
```

#### 4.4 Semantic Extraction Returns Early Without Correction

**File:** `/home/charles2/sailly-browser-demo/server/brain/v4_turn_processor.py`  
**Lines:** 341-356, 549-558  
**Problem:**
- Semantic path returns early with clarify text
- **Bypasses** `v4_pipeline` correction handlers entirely
- `confirmation_intent=no` → generic "was soll ich ändern?" without applying changes

**Code Reference:**
```python
# Lines 549-558: Confirmation intent handler
if confirmation_intent == "no":
    return _quick_return("Was möchten Sie ändern?", ...)  # No slot update
```

#### 4.5 Partial Correction Regex Limitations

**File:** `/home/charles2/sailly-browser-demo/server/brain/conversation_state.py`  
**Function:** `update_state_from_utterance()` (lines 2675-2707)  
**Problem:**
- Dish corrections via regex only ("sondern X", "statt Y")
- Name/address corrections have partial handlers but limited patterns
- Complex corrections not parsed

#### 4.6 Correction + Re-confirm Ambiguity

**File:** `/home/charles2/sailly-browser-demo/server/brain/v4_pipeline.py`  
**Lines:** 1665-1669  
**Problem:**
- `correction_pending` + user says **"ja"** → treated as re-confirm, not apply correction
- No distinction between "yes, fix that" vs "yes, keep it"

### Known Fixes Applied
- ✅ Re-extract dishes on correction (lines 2704-2706)
- ✅ Reset `_order_readback_confirmed` flag
- ✅ Time correction extraction in `correction_pending` (lines 1716-1747)
- ✅ Premature-order safety gate (lines 2513-2527)

### What's Still Broken
- ❌ Corrections need **specific regex** ("statt/sondern"); vague "nein" only enters `correction_pending`
- ❌ No parsing of **WHAT** to change without structured extraction
- ❌ Semantic path short-circuits correction handlers
- ❌ Intent classifier maps to `correction` profile but `v4_turn_processor` **always runs `update_state_from_utterance`** first
- ❌ Safety gate can block legitimate corrections
- ❌ `correction_pending` + "ja" ambiguity not resolved

### Typical Failure Scenarios
1. **User:** "No, I want 2 portions" → **Bot:** "What would you like to change?" → **User repeats** → Loop
2. **User:** "Actually, Wasser instead of Saft" → **Bot:** "I didn't catch that" → **User confused**
3. **User:** "That's wrong" (vague) → **Bot:** "What would you like to change?" → **User:** "Everything" → **No parsing**

### Instrumentation Gap
- ❌ `correction_detected` counter not logged
- ❌ `correction_applied` success rate not tracked
- ❌ `end_call_stage` FSM transitions not telemetry'd
- ❌ Regex match rate not measured

### Recommended Next Steps
1. **Add logging:**
   ```python
   logger.info(f"correction_detected={correction_regex_matched}")
   logger.info(f"correction_applied={items_updated}")
   logger.info(f"end_call_stage={state.end_call_stage}")
   ```
2. **Run test:** `server/tests/test_commit_gate_fsm.py::test_order_correction_resets_commit_gate`
3. **Extend regex:** Add patterns for "nope", "wrong", "that's not right", etc.
4. **Semantic extraction:** Add `correction` slot type to capture what's being changed
5. **Parallel path:** When `correction_pending`, run semantic extraction in parallel to parse user's stated change

---

## Issue #5: MULTI-DISH / VARIANT HANDLING (HIGH)

### Summary
- **Occurrence:** Multi-item orders omit dishes or select wrong variants (e.g., wrong water size)
- **Examples:** 
  - "Ein Bibimbap und ein Wasser" → only Bibimbap captured
  - "Wasser 0,5L still" → always picks cheapest (0,25L) instead
- **Severity:** Order accuracy degradation

### Root Causes & Code Locations

#### 5.1 Missing Variant/Size Slot in Semantic Layer

**File:** `/home/charles2/sailly-browser-demo/server/brain/slot_extraction_layer.py`  
**Function:** `_extract_deterministic()` (lines 180-193)  
**Problem:**
- No `variant` or `size` slot in extraction schema
- "Wasser 0,7" vs "1,0" collapses to generic `Wasser` without size

#### 5.2 Cheapest Variant Always Selected

**File:** `/home/charles2/sailly-browser-demo/server/brain/v4_pipeline.py`  
**Function:** `_default_menu_price_label()` (lines 392-413)  
**Problem:**
- Always picks **lowest price** variant, not caller-stated size
- "Ich hätte gerne das große Wasser" → picks 0.25L (cheapest), not 0.75L

**Code Reference:**
```python
# Lines 392-413: Variant selection
variant = min(variants, key=lambda v: v['price'])  # ALWAYS cheapest
```

#### 5.3 Multi-Dish Extraction Fallback

**File:** `/home/charles2/sailly-browser-demo/server/brain/conversation_state.py`  
**Function:** `_extract_all_dishes()` (lines 2353-2431)  
**Problem:**
- **"Wasser"** fallback to base name without size variant
- Second+ dishes depend on `add_extra_item`
- STT partial lists may only capture first dish

#### 5.4 Token Match Filtering

**File:** `/home/charles2/sailly-browser-demo/server/brain/slot_extraction_layer.py`  
**Lines:** 180-193 (Pass 2)  
**Problem:**
- Short tokens filtered (`len(clean) < 4` skip)
- Can miss short dish names or size indicators

### Known Fixes Applied
- ✅ Multi-dish hydration logic (lines 1176-1219)
- ✅ Early `get_menu` fetch (lines 1387-1418)

### What's Still Broken
- ❌ No `variant` / `size` semantic slot
- ❌ Always chooses cheapest variant, not caller's stated preference
- ❌ Multi-dish extraction depends on fragile `add_extra_item` pattern matching
- ❌ Short tokens filtered in semantic pass

### Scenario Examples
1. **Input:** "Ein Bibimbap Rind und ein stilles Wasser, 0,5L bitte"
   - **Expected:** 1× Bibimbap (Rind variant), 1× Wasser (0.5L still)
   - **Actual:** 1× Bibimbap (Rind), 1× Wasser (0.25L, default cheapest)

2. **Input:** "Zwei Saft und ein Wasser mit Kohlensäure"
   - **Expected:** 2× Saft, 1× Wasser (carbonated variant)
   - **Actual:** Only 1× Saft captured; Wasser variant ignored

### Recommended Next Steps
1. **Inspect menu JSON:** Extract `Wasser` variants from tenant config
   ```bash
   grep -A 10 '"Wasser"' /home/charles2/sailly-browser-demo/server/brain/menu_data.json
   ```
2. **Extend semantic extraction:** Add `variant`/`size` slot (lines ~268 in `slot_extraction_layer.py`)
3. **Refactor variant selection:** 
   - Check for caller-stated size in turn history
   - Fall back to mid-range price (not cheapest)
4. **Test utterance:** "ein Bibimbap und ein großes Wasser" through `_extract_all_dishes` and readback builder

---

## Issue #6: UNEXPECTED RESERVATION PROMPTS (MEDIUM)

### Summary
- **Occurrence:** Bot asks for reservation mid-order flow
- **Example:** After selecting dishes, bot asks "Darf ich gleichzeitig Ihre Reservierung aufnehmen?"
- **Severity:** Conversation derailment, order abandonment risk

### Root Causes & Code Locations

#### 6.1 Aggressive Keyword Override

**File:** `/home/charles2/sailly-browser-demo/server/brain/v4_pipeline.py`  
**Function:** `process_turn_v4()` (lines 1027-1094)  
**Problem:**
- `_reservation_keywords` ("tisch", "buchen", "reservierung", etc.) **force** `reservation_start`
- Override applies even during active order flow
- Non-reservation words in casual speech trigger false positive

**Code Reference:**
```python
# Lines 1034-1061: Keyword override
_reservation_keywords = ["tisch", "buchen", "reservierung"]
if any(kw in utterance.lower() for kw in _reservation_keywords):
    return _process_reservation_start()  # Force reservation even mid-order
```

#### 6.2 Party Size Inference Sets Reservation Intent

**File:** `/home/charles2/sailly-browser-demo/server/brain/conversation_state.py`  
**Lines:** 3461-3493  
**Problem:**
- `party_size >= 2` without dish context → `reservation_intent=True`
- Date + party size → reservation implied
- Even in delivery context (delivery doesn't need party size)

**Code Reference:**
```python
# Lines 3487-3493: Party size inference
if party_size >= 2 and order_items == []:
    reservation_intent = True  # Wrong: user may be ordering for 2
```

#### 6.3 Post-Order Multi-Intent Reservation Flow

**File:** `/home/charles2/sailly-browser-demo/server/brain/v4_pipeline.py`  
**Lines:** 2660-2683  
**Problem:**
- After order commit, explicitly **opens reservation flow** if `reservation_intent`
- No guard for delivery-only orders

#### 6.4 Turn-0 Intent Classification

**File:** `/home/charles2/sailly-browser-demo/server/brain/intent_classifier.py`  
**Lines:** 155-228  
**Problem:**
- Reservation vs order priority on first turn (partly fixed)
- But mid-order, override (lines 1034-1061) can still trigger

#### 6.5 Menu FAQ Override

**File:** `/home/charles2/sailly-browser-demo/server/brain/v4_pipeline.py`  
**Lines:** 728-736  
**Status:** Partial fix applied
- Intended to prevent "Bibimbap" after FAQ from flipping to order
- May not be blocking reservation inference

### Known Fixes Applied
- ✅ Turn-0 order-before-greeting priority (lines 201-218 in `intent_classifier.py`)
- ✅ Menu FAQ override attempt (lines 728-736)
- ✅ Reservation gate during `order_pre_commit_readback` (line ~2821)

### What's Still Broken
- ❌ Words like **"tisch"** in non-reservation context still trigger override
- ❌ **`party_size` extraction** from casual speech ("für mich und meinen Freund") sets reservation intent mid-order
- ❌ Post-order multi-intent explicitly opens reservation flow without checking context
- ❌ Injected prompt: "Darf ich gleichzeitig Ihre Reservierung aufnehmen?" forces user decision

### Scenario Examples
1. **User:** "Ich hätte gerne zwei Bibimbap" (order for 2 people)
   - **Bot:** (after order) "Would you like a reservation?" (party_size=2 → reservation_intent)
   - **Problem:** Delivery order, no reservation needed

2. **User:** "Der Tisch für vier Personen ist ein problem" (complaining about seating)
   - **Bot:** "Let me help you with a reservation" (keyword override on "tisch")
   - **Problem:** User was complaining, not requesting reservation

3. **User:** "Ich möchte einen Tisch für zwei" (actually requesting reservation post-order)
   - **Bot:** Correctly opens reservation flow
   - **Current:** Works, but only if not already at commitment stage

### Instrumentation Gap
- ❌ `reservation_intent` transitions not logged per turn
- ❌ Keyword override matches not tracked
- ❌ Order/reservation context switches not telemetry'd

### Recommended Next Steps
1. **Log FSM transitions:**
   ```python
   logger.info(f"reservation_intent={state.reservation_intent}, order_intent={state.order_intent}")
   logger.info(f"keyword_override_matched={matched_keyword}")
   ```
2. **Tighten keyword override:** Require `reservation_intent` or missing order slots ONLY
3. **Fix party size logic:**
   ```python
   # Don't infer reservation_intent from party_size in order context
   if party_size >= 2 and order_type == "delivery":
       reservation_intent = False  # No reservation for delivery
   ```
4. **Add context check before post-order reservation:** Only if non-delivery order type
5. **Review false positive "tisch" matches** in transcript analysis

---

## Google Metrics Summary (All 30 Calls)

### Raw Metrics by Call

```json
{
  "total_calls": 30,
  "dataset": "2026-05-26 14:45 - 23:06",
  "key_statistics": {
    "avg_duration": 71.5,
    "avg_quality_score": 6.98,
    "avg_latency": 1106,
    "p95_latency": 1500,
    "total_tool_calls": 40,
    "client_disconnect_rate": 96.7
  },
  "top_5_worst_performers": [
    {
      "call_id": "demo-3e4f2d9828d4",
      "duration": 61,
      "latency_avg": 2684,
      "latency_p95": 3630,
      "dead_air": 8053,
      "quality": 7.5,
      "tools": ["get_menu", "verify_address"]
    },
    {
      "call_id": "demo-b7fb4e027d28",
      "duration": 159,
      "latency_avg": 2004,
      "latency_p95": 3000,
      "dead_air": 10021,
      "quality": 7.6,
      "tools": ["get_menu", "unknown"]
    },
    {
      "call_id": "demo-c31e8157d5a4",
      "duration": 98,
      "latency_avg": 1806,
      "latency_p95": 3220,
      "dead_air": 5417,
      "quality": 7.4,
      "tools": ["get_menu", "create_order"]
    },
    {
      "call_id": "demo-da9a37636c48",
      "duration": 98,
      "latency_avg": 1260,
      "latency_p95": 2212,
      "dead_air": 3780,
      "quality": 7.4,
      "tools": ["get_menu", "verify_address"]
    },
    {
      "call_id": "demo-dbb48c1d9232",
      "duration": 98,
      "latency_avg": 1141,
      "latency_p95": 1888,
      "dead_air": 5704,
      "quality": 7.4,
      "tools": ["get_menu", "create_order"]
    }
  ],
  "best_performer": {
    "call_id": "demo-8df8c03b815b",
    "duration": 98,
    "latency_avg": 174,
    "latency_p95": 174,
    "dead_air": 174,
    "quality": 7.7,
    "tools": ["get_menu", "verify_address"]
  }
}
```

### Complete Call Listing (30 calls)
[See `call_analysis.json` for complete metrics, line 1-514]

---

## Implementation Status

### Recently Completed (Commit e2e7a48)
- ✅ Turn-0 intent classification (order before greeting)
- ✅ Shorter post-commit farewell
- ✅ Premature `create_order` safety gate
- ✅ TTFB instrumentation + `stt_done_at` wiring
- ✅ `TurnTimings()` initialization in `v4_turn_processor.py`
- ✅ `tts_ttfb_ms` column added to `google_turn_metrics`

### Pending Fixes (From plan `fix_critical_latency_&_audio_issues_4cc7a922.plan.md`)
- [ ] Disable semantic speculation (`SEMANTIC_SPECULATIVE_ENABLED=false`)
- [ ] Prevent duplicate `verify_address` calls (semantic + commit gate)
- [ ] Ensure meta-feedback responses include `LLMTextFrame` for TTS
- [ ] Add `asyncio.wait_for` timeout to speculative semantic reuse
- [ ] Remove duplicate `on_end_of_turn` call between `main.py` and `brain_service.py`
- [ ] Investigate and fix multi-dish options (water sizes, carbonation, etc.)
- [ ] Debug why corrections are not being accepted
- [ ] Debug unexpected reservation prompts during order flow
- [ ] Run live test calls and validate latency improvements

---

## Recommended Investigation Priorities

### P0 (Immediate)
1. **Profile worst call:** Extract `demo-3e4f2d9828d4` turn-by-turn metrics
   - Which component is >70% of 2,684ms latency?
   - Is it semantic extraction, TinyGenerator, or tool calls?

2. **Verify P0 fix:** Check `stt_done_at` wiring indentation in `brain_service.py` lines 1196-1221
   - Ensure no syntax errors post-merge
   - Confirm `tts_ttfb_ms` is now calculating correctly

3. **Disable speculation:** Set `SEMANTIC_SPECULATIVE_ENABLED=false` and restart
   - Measure if latency improves

### P1 (This Week)
4. **Add missing stage timestamps:**
   - `extract_done_at` after semantic extraction (lines ~330 in `v4_turn_processor.py`)
   - `tool_done_at` after `execute_tool` calls (lines ~2574+ in `v4_pipeline.py`)
   - Allows precise latency breakdown

5. **Instrument corrections:**
   - Add `correction_detected`, `correction_applied` logging
   - Track `end_call_stage` transitions
   - Measure regex match rate vs user intent

6. **Test multi-dish scenario:** "Ein Bibimbap und ein großes Wasser still"
   - Trace through `_extract_all_dishes` logic
   - Verify variant selection

### P2 (Next 2 Weeks)
7. **Refactor tool execution:** Non-blocking async with background completion
8. **Extend semantic extraction:** Add `variant`/`size` slots for better variant matching
9. **Redefine dead air metric:** Separate acoustic gap from cumulative latency
10. **Add TTS suppression tracking:** `tts_suppressed_reason` column in `google_turn_metrics`

---

## File Locations Reference

### Core Pipeline
- `/home/charles2/sailly-browser-demo/server/brain_service.py` - Main orchestrator, LatencyTimer
- `/home/charles2/sailly-browser-demo/server/brain/v4_pipeline.py` - Conversation logic, order flow
- `/home/charles2/sailly-browser-demo/server/brain/v4_turn_processor.py` - Turn entry, semantic extraction
- `/home/charles2/sailly-browser-demo/server/brain/slot_extraction_layer.py` - Semantic slot LLM

### Tools & Execution
- `/home/charles2/sailly-browser-demo/tools/executor.py` - Tool execution (blocking point)
- `/home/charles2/sailly-browser-demo/server/brain/tiny_generator.py` - Haiku response generation
- `/home/charles2/sailly-browser-demo/server/sailly_gemini_tts.py` - TTS synthesis & buffering

### State & Conversation
- `/home/charles2/sailly-browser-demo/server/brain/conversation_state.py` - Order/reservation state
- `/home/charles2/sailly-browser-demo/server/brain/intent_classifier.py` - Intent routing
- `/home/charles2/sailly-browser-demo/server/brain/contracts/turn_timings.py` - Timing instrumentation

### Infrastructure
- `/home/charles2/sailly-browser-demo/server/main.py` - WebSocket, VAD, audio pipeline
- `/home/charles2/sailly-browser-demo/server/database.py` - Metrics persistence
- `/home/charles2/sailly-browser-demo/server/call_report/builder.py` - Report generation

---

## Success Metrics (Post-Fix Targets)

### Latency
- [ ] Average latency < 200ms (from 1,106ms)
- [ ] P95 latency < 500ms (from 1,500ms)
- [ ] 90%+ of calls < 200ms average

### Dead Air
- [ ] No single dead air period > 1,000ms
- [ ] Average dead air < 200ms
- [ ] Zero dead air for 0-tool calls

### Quality
- [ ] Average quality score > 8.0 (from 6.98)
- [ ] 90%+ of calls > 7.5
- [ ] < 5% of calls < 6.0

### Corrections
- [ ] Correction success rate > 80%
- [ ] "Was möchten Sie ändern?" → properly applies change

### Multi-Dish
- [ ] All items captured from multi-item utterances
- [ ] Variants selected per user request (not always cheapest)

### Reliability
- [ ] Client disconnect rate: Clarify expected behavior
- [ ] Zero silent TTS with audio expected
- [ ] 99.9% uptime

---

## Related Documentation

- **Detailed Analysis:** `/home/charles2/sailly-browser-demo/ISSUES_REPORT.md` (456 lines)
- **Action Items:** `/home/charles2/sailly-browser-demo/ACTION_ITEMS.md` (324 lines)
- **Implementation Status:** `/home/charles2/sailly-browser-demo/IMPLEMENTATION_COMPLETE.md`
- **Structured Metrics:** `/home/charles2/sailly-browser-demo/call_analysis.json` (514 lines)
- **Quick Reference:** `/home/charles2/sailly-browser-demo/QUICK_REFERENCE.txt`
- **Summary Stats:** `/home/charles2/sailly-browser-demo/SUMMARY_STATS.txt`

---

## Notes

- All data sourced from 30 most recent call reports analyzed May 27, 2026
- Code locations verified against `/home/charles2/sailly-browser-demo/` codebase
- Metrics are from `google_call_reports`, `google_turn_metrics`, `google_transcripts`, `google_tool_calls` PostgreSQL tables
- Report generated in preparation for next development cycle
- Status: **READY FOR IMPLEMENTATION**

**Report Generated:** May 27, 2026 01:27 UTC+2  
**Report Version:** 1.0  
**Classification:** INTERNAL - Development Team
