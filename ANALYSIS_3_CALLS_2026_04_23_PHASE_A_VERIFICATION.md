# Sailly Call Analysis Report — April 23, 2026
**Analysis Date**: April 23, 2026 11:30 UTC  
**Calls Analyzed**: 3  
**Call IDs**: demo-7404322ad8a6, demo-29d1f38415af, demo-7fc75c89264e

---

## Executive Summary

All 3 calls show **Phase A fixes are partially working** with one critical issue requiring immediate attention:

| Metric | Status | Evidence |
|--------|--------|----------|
| **TTS greeting_first regression** | ⚠️ NEEDS ADJUSTMENT | T1 still shows `greeting_first` (50ms timeout insufficient) |
| **Call disposition tracking** | ✓ WORKING | 2/3 show `user_hung_up_mid_order`, 1 shows `unknown` |
| **Output token capture** | ? UNCLEAR | Still NULL (may be DB write timing issue) |
| **ValidationRegistry** | ✓ FIRING | Active on all turns with extracted items |
| **Menu pivot behavior** | ✓ WORKING | Pizza requests trigger validation with alternatives |
| **Latencies** | ✓ ACCEPTABLE | 1.3-2.4s avg turn latency (within target) |
| **Response Truncation** | ✗ CRITICAL P0 | Bot responses cut to 4-20 characters |

---

## Call Summary Table

| Call ID | Duration | Turns | Disposition | Greeting Mode | Latency Range | Primary Issue |
|---------|----------|-------|-------------|---------------|---------|----|
| demo-7404322ad8a6 | 87s | 5 | unknown | T1=greeting_first | 1.3-2.4s | Pizza denial + response truncation |
| demo-29d1f38415af | 61s | 3 | user_hung_up_mid_order | T1=greeting_first | 1.4-1.8s | Truncated responses + unclear feedback |
| demo-7fc75c89264e | 63s | 2 | user_hung_up_mid_order | T1=greeting_first | 1.7-2.4s | Nonsensical T1 response ("Alles") |

---

## Detailed Per-Call Analysis

### Call 1: demo-7404322ad8a6 (87 seconds, 5 turns)

**Scenario**: Pizza request → Frustration → Disconnect

**Turns**:
- **T1**: User "Guten Tag, ich hätt gerne Pizza Margaretha." → Bot "[TOOL:ai" (truncated + tool tag leak)
- **T2**: User "Ja." → Bot "Entschuldigen" (7 chars)
- **T3**: User "Wie bitte?" → Bot "Entschuld" (8 chars)
- **T4**: User "Was ist mit meiner Pizza Margarita?" → Bot "Leider haben wir keine" (mood=confused)
- **T5**: User "Hallo, was ist mit meiner Pizza Margareta?" → Bot "Leider haben wir keine Pizza"

**Observations**:
- ✓ Slot extraction working: Pizza variants extracted on T1, T4, T5
- ✓ Validation firing: check_item_availability on all relevant turns
- ✓ Mood detection: T4 shows `tts_mood=confused` (user frustration detected)
- ✓ Menu pivot: T4-T5 correctly attempt to deny Pizza gracefully
- ✗ Response truncation: T1-T3 responses cut short, making conversation incoherent
- ✓ Call disposition: `unknown` (correct—no order tool called)
- ⚠️ Greeting_first: T1 shows this mode (Phase A A1 not effective)

**Why User Left**: Frustrated by repeated Pizza denials combined with truncated bot responses.

---

### Call 2: demo-29d1f38415af (61 seconds, 3 turns)

**Scenario**: Pizza request → Confusion → Quick Disconnect

**Turns**:
- **T1**: User "Schönen guten Tag, ich hätte gerne Pizza Margaritha." → Bot "Hallo," (6 chars)
- **T2**: User "Ja." → Bot "Entschuldigen Sie bitte" (unclear why apologizing)
- **T3**: User "Ja." → Bot "Entschuldigen" (7 chars)

**Observations**:
- ✓ Token audit: `prompt_tokens_in` populated (1432, 2511, 2520)
- ✓ Slot extraction: Pizza variants extracted all 3 turns
- ✓ Validation: check_item_availability on all turns
- ✓ Call disposition: `user_hung_up_mid_order` (correct interpretation)
- ✗ Response quality: Truncated and nonsensical
- ⚠️ Greeting_first: T1 shows this mode
- ⚠️ Output tokens: NULL on all turns

**Why User Left**: After "Hallo," and apologies on T2-T3, user gave up. No clear order confirmation.

---

### Call 3: demo-7fc75c89264e (63 seconds, 2 turns)

**Scenario**: Multi-item order → Bot says "Alles" → Disconnect

**Turns**:
- **T1**: User "Ich hätt gern zwei Bulgogi, eine Flasche Wein und dreimal Dessert, Mandu Reis." → Bot "Alles" (5 chars, nonsensical)
- **T2**: User "Ja." → Bot "Entschuldigen Sie" (unclear apology)

**Observations**:
- ✓ Slot extraction: All 3 items extracted as high-confidence (Bulgogi, Wine, Dessert)
- ✓ Validation: check_item_availability fires with multi-item payload
- ✓ Call disposition: `user_hung_up_mid_order` (correct)
- ✗ Bot response T1: "Alles" is meaningless (should confirm items)
- ✓ Latency T1: 2390ms (within range but on high end)
- ⚠️ Greeting_first: T1 shows this mode
- ⚠️ Output tokens: NULL

**Why User Left**: T1 bot says "Alles" (everything), which doesn't make sense as a response to an order. User likely confused, hung up after T2.

---

## Cross-Call Patterns

### Pattern 1: Response Truncation (P0 Critical)

**Finding**: All calls show truncated bot responses in database:
- T1-T2 responses typically 4-20 characters
- Examples: "Hallo," (6 chars), "Alles" (5 chars), "Entschuld" (8 chars)

**Root Cause**: Not from Phase A fixes. Likely:
1. bot_text column write truncation
2. Streaming callback cutting off responses
3. Tool tag stripping failing mid-response

**Impact**: Makes bot completely incoherent to users. **CRITICAL user experience issue.**

**Recommendation**: Debug bot_text write path and streaming callback immediately.

---

### Pattern 2: Greeting_first Persistence (Phase A A1 Status)

**Finding**: T1 shows `tts_situation='greeting_first'` on **all 3 calls**

**Expected**: `tts_situation='info_neutral'` after Phase A A1 fix

**Calls made**: 11:12–11:18 UTC  
**Fix deployed**: 10:43 UTC (29–35 minutes prior)  
**Timing**: Fix should have been active

**Analysis**:
- 50ms sleep may be insufficient
- Async greeting task timing varies by system load
- Guard logic may not be executing in all code paths

**Recommendation**: Increase sleep to 200ms and add explicit logging to verify guard is firing.

---

### Pattern 3: Call Disposition (Phase A A2 Status) — ✓ Working

**Finding**: All 3 calls have correct disposition values:
- demo-7404322ad8a6: `unknown` ✓
- demo-29d1f38415af: `user_hung_up_mid_order` ✓
- demo-7fc75c89264e: `user_hung_up_mid_order` ✓

**Status**: **Phase A A2 is working correctly**

---

### Pattern 4: Token Audit (Phase A A3 Status) — ⚠️ Partial

**Finding**:
- `prompt_tokens_in`: ✓ Populated (1432-2578 range)
- `prompt_tokens_out`: ✗ NULL on all turns

**Status**: Input tokens working; output tokens not captured

**Possible reasons**:
1. Output token extraction code not firing
2. DB write not including the value
3. Calls made slightly before fix deployment

**Recommendation**: Add logging to confirm `_last_output_tokens` is being read and written.

---

## Performance Analysis

### Latencies
- **Call 1**: 1.3–2.4s per turn, avg 1.8s
- **Call 2**: 1.4–1.8s per turn, avg 1.6s
- **Call 3**: 1.7–2.4s per turn, avg 2.0s

**Status**: ✓ All within acceptable range (target <3.5s P90)

### Token Efficiency
- Input tokens range: 1432–2578 per turn
- Pattern: Tokens increase as context grows through call
- Observation: Normal behavior; no bloat detected

---

## Phase A Fix Status Summary

| Fix | Expected | Observed | Status | Action Required |
|-----|----------|----------|--------|-----------------|
| **A1: Greeting_first** | T1=`info_neutral` | T1=`greeting_first` | ⚠️ Needs adjustment | Increase sleep to 200ms; add logging |
| **A2: Disposition** | Column populated | All correct | ✓ WORKING | None |
| **A3: Output tokens** | `prompt_tokens_out` non-NULL | Still NULL | ? Unclear | Verify write path is firing |

---

## Critical Issues (P0)

### Response Truncation
- **Severity**: Critical (breaks user experience)
- **Scope**: Affects all bot responses in these calls
- **Cause**: Unknown (not Phase A related)
- **Fix**: Debug bot_text write path and streaming callback

---

## Medium Issues (P1)

### Greeting_first Persistence
- **Severity**: Medium (user-visible but not breaking)
- **Scope**: T1 on all calls
- **Cause**: 50ms timeout insufficient for async guard
- **Fix**: Increase to 200ms and verify firing with logs

---

## Recommendations

### IMMEDIATE (Next 30 minutes)
1. Increase greeting_first guard timeout from 50ms → 200ms in `brain_service.py:404`
2. Add logging to verify guard is executing and flag is being set

### URGENT (Next 2 hours)
1. Debug response truncation issue
   - Check bot_text column write limits
   - Verify TTS callback isn't cutting responses
   - Check tool tag stripping logic

2. Verify output token write path
   - Add logging in brain_service.py after reading _last_output_tokens
   - Confirm value is being written to DB

### WITHIN 24 HOURS
1. Run 3-call batch after above fixes
2. Verify:
   - T1 shows `info_neutral` (not `greeting_first`)
   - Bot responses are complete (not truncated)
   - `prompt_tokens_out` is populated

---

## Data Quality Issues

The 3 calls in this batch revealed a **critical data quality issue**: response truncation makes analysis difficult. Future calls should show:
- Full bot_text in responses
- Output tokens populated
- No tool tag leakage

---

## Conclusion

**Phase A Deployment Status**: 
- **1/3 fixes verified working** (call_disposition)
- **1/3 needs refinement** (greeting_first guard timeout)
- **1/3 needs verification** (output token write path)

**Overall System**: Functional but needs refinement on greeting-first timing and response truncation debugging. **Do not proceed to Phase B verification until response truncation is resolved.**

**Next Step**: Fix response truncation and increase greeting_first guard timeout, then run 3-call verification batch.
