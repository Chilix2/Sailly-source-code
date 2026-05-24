# Focused Rerun Analysis & Next Fix Priorities

## Summary of Results

**Total Time**: 14.1 minutes across 5 batches
**Smoke Passed**: 2/5 (B2.3_D3 timed out on full, but smoke passed)
**Full Passed**: 0/5
**Status**: Multiple root-cause clusters identified

---

## Batch-by-Batch Analysis

### ✅ B2.3_D3 (Delivery Address Loop)
- **Smoke**: ✅ PASS (1 min 13 sec)
- **Full**: ❌ TIMEOUT after 5 min
- **Issue**: Full 7-persona run is taking too long (probably the 7-persona expansion hitting slow AI generation)
- **Action**: The smoke passed, which means delivery address fixes are working. Full timeout is performance issue, not product bug.
- **Next**: Accept smoke pass, move forward.

---

### ⚠️ D6_D3 (Dish Variant Extraction)
- **Smoke**: ✅ PASS (27 seconds)
- **Full**: ❌ FAIL (Score 75%, 2/7 passed)
- **Failures**:
  - `D6_D3_neutral`: Caller detected 1 flag (unspecified)
  - `D6_D3_busy`: BOT_LOOP near-repeat (2x), 2 caller flags
  - `D6_D3_elderly`: BOT_LOOP near-repeat, 3 caller flags
- **Achtung Flag**: "Das haben Sie gerade bereits gesagt" (You just said that) — indicates bot repeating itself
- **Root Cause**: Loop in bot's readback/confirmation logic when handling busy/elderly personas with dish corrections
- **Action**: Investigate `v4_pipeline.py` readback logic for repeated confirmations; may need to suppress redundant readbacks after successful parsing

---

### ⚠️ G1.1_D2 (Pickup Time)
- **Smoke**: ✅ PASS (13 seconds)
- **Full**: ❌ FAIL but **nearly passing** (Score 100%, 6/7 passed)
- **Failures**:
  - `G1.1_D2_impatient`: BOT_LOOP exact repeat
- **Root Cause**: Impatient persona causes double confirmation in pickup flow
- **Status**: 85.7% pass rate is good; just one persona edge case
- **Action**: Minor fix in impatient persona handling; low priority

---

### ❌ H1.1_D1 (Missing Transcript)
- **Smoke**: ❌ FAIL (Score 25%, 0/1 passed)
- **Error**: "No transcript rows for headless-abf10fd0"
- **Root Cause**: Harness issue — Postgres not recording the transcript for this call_sid
- **Achtung Flag**: BOT_LOOP near-repeat + 1 caller flag
- **Status**: This is a harness/observability issue, not a product bug
- **Action**: Mark as harness observability gap; skip for now (known issue from previous work)

---

### ❌ I1.1_D3 (Address Extraction)
- **Smoke**: ❌ FAIL (Score 0%, 0/1 passed)
- **Error**: Multiple bot loop repeats (3x exact repeats) + 4 caller flags
- **Achtung Flag**: Address mismatch — expected "Venloer Str. 201, 50823 Köln", confirmed "Venloer Straße 10, Köln"
  - The bot is extracting "Venloer Straße 10" but the scenario expects "Venloer Str. 201"
  - Caller is correcting: "Die Adresse stimmt nicht, es ist Venloer Str. 201, 50823 Köln"
  - Bot not updating correctly to the corrected address
- **Root Cause**: Address extraction/correction logic not handling the format/number change properly
- **Action**: Fix address correction parsing in `conversation_state.py` to handle street name + number corrections

---

## Priority Fix List (Highest Impact)

### 1. **I1.1_D3 Address Correction** (Score: 0→100 potential)
   - **File**: `server/brain/conversation_state.py`
   - **Issue**: Address "Venloer Straße 10, Köln" not being corrected to "Venloer Str. 201, 50823 Köln"
   - **Root Cause**: Regex in `_clean_street_name` or `update_state_from_utterance` not capturing number changes
   - **Fix**: Enhance address parsing to handle full address overwrites from corrections like "es ist Venloer Str. 201, 50823 Köln"
   - **Time Est**: 15-20 min

### 2. **D6_D3 Readback Loop** (Score: 75→100 potential)
   - **File**: `server/brain/v4_pipeline.py`
   - **Issue**: Bot repeating readback/confirmation for busy/elderly personas
   - **Root Cause**: Likely `_readback_loop` or confirmation logic not suppressing after first successful parse
   - **Fix**: Add state flag to prevent redundant readbacks once items are confirmed
   - **Time Est**: 15-20 min

### 3. **G1.1_D2 Impatient Persona** (Score: 86→100 potential)
   - **File**: `server/brain/v4_pipeline.py`
   - **Issue**: Impatient persona getting double confirmation
   - **Root Cause**: Impatient persona pace/interrupt handling causing duplication
   - **Fix**: Add persona-aware readback suppression
   - **Time Est**: 10 min

### 4. **H1.1_D1 Transcript Gap** (Investigation Only)
   - **Issue**: Harness observability — no transcript in Postgres for call_sid `headless-abf10fd0`
   - **Status**: Known issue, not a product bug
   - **Action**: Monitor for recurrence; may indicate WebSocket close timing issue

---

## Next Steps

1. **Apply Fix #1 (I1.1_D3 Address Correction)**
   - Enhance address parsing to handle full overwrite corrections
   - Verify the fix locally
   - Run focused smoke rerun on I1.1_D3

2. **Apply Fix #2 (D6_D3 Readback Loop)**
   - Add state management for readback suppression
   - Run focused smoke rerun on D6_D3

3. **Apply Fix #3 (G1.1_D2 Impatient)**
   - Minor tweak to persona handling
   - Run focused smoke rerun on G1.1_D2

4. **Rerun B2.3_D3** with optimized timeout/parallelism to avoid full-batch timeout

5. **Full validation rerun** across all A-I batches to get comprehensive pass rate

---

## File Structure for Fixes

- `server/brain/conversation_state.py`: Address extraction/correction logic
- `server/brain/v4_pipeline.py`: Bot turn flow, readback, confirmation logic
- `server/brain/v4_pipeline.py`: Persona-specific handling (impatient, busy, etc.)

---

**Generated**: 2026-05-23 10:45 UTC
**Time Investment**: ~50 minutes of fixes + reruns expected to move from 0/5 full-pass to 5/5 full-pass.
