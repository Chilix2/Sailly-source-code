# SAILLY VALIDATION FAILURE ANALYSIS REPORT

**Generated**: 2026-05-06 12:25 UTC
**System**: Sailly Voice Agent - Stress Test Phase A
**Status**: CRITICAL - All batches below 80/100 threshold

---

## EXECUTIVE SUMMARY

The validation pipeline completed 3 batches (A1.1_D1, A1.2_D2, A1.3_D3) with **universally poor scores**:
- Average Composite Score: 49.6/100 (target: 80+)
- Total Pass Rate: 32.5% (7/21 scenarios)
- Critical failures in: **Tool Calling (avg 53/100)**, **Flow (avg 32/100)**, **Deterministic Logic (avg 36/100)**

---

## BATCH RESULTS SUMMARY

### A1.1_D1 (Difficulty Level 1 - Baseline/Greeting)
- **Status**: COMPLETE (Attempt 3/3 - max attempts reached)
- **Pass Rate**: 2/7 (28.6%)
- **Composite Score**: 65.7/100
- **Metrics Breakdown**:
  - Tool Accuracy: 70/100 ⚠️ MODERATE
  - Flow: 55/100 ❌ POOR
  - Linguistic: 93/100 ✅ EXCELLENT
  - Deterministic: 48/100 ❌ CRITICAL
- **Error Flags**: 6 detected
  - BOT_LOOP (repeating same response)
  - State confusion (asking for already-provided slots)
- **Fixes Applied**: YES (attempts 2-3)
- **Result**: Minimal improvement (attempt 1: unknown, attempt 3: 65.7)

### A1.2_D2 (Difficulty Level 2)
- **Status**: COMPLETE (Attempt 2/3)
- **Pass Rate**: 2/7 (28.6%)
- **Composite Score**: 40.0/100 **← REGRESSION**
- **Metrics Breakdown**:
  - Tool Accuracy: 40/100 ❌ CRITICAL
  - Flow: 20/100 ❌❌ SEVERE
  - Linguistic: 90/100 ✅ EXCELLENT
  - Deterministic: 30/100 ❌❌ SEVERE
- **Error Flags**: 16 detected (HIGHEST)
  - Heavy tool calling failures
  - Conversation flow breaking down
  - Deterministic path not triggering
- **Fixes Applied**: YES (attempt 2 from attempt 1 baseline)
- **Result**: **SCORE REGRESSED** (Baseline → 40.0: WORSE after fixes)

### A1.3_D3 (Difficulty Level 3)
- **Status**: COMPLETE (Attempt 3/3 - max attempts reached)
- **Pass Rate**: 3/7 (42.9%)
- **Composite Score**: 43.2/100
- **Metrics Breakdown**:
  - Tool Accuracy: 50/100 ⚠️ MODERATE-POOR
  - Flow: 20/100 ❌❌ SEVERE
  - Linguistic: 85/100 ✅ GOOD
  - Deterministic: 30/100 ❌❌ SEVERE
- **Error Flags**: 11 detected
- **Fixes Applied**: YES (attempts 2-3)
- **Result**: Minimal improvement despite fixes

---

## ROOT CAUSE ANALYSIS - FAILURE CATEGORIZATION

### 1. TOOL CALLING FAILURES (Avg Score: 53/100)
**Symptoms Observed**:
- Tool accuracy declining: 70 → 40 → 50 (inconsistent)
- create_reservation not firing when slots complete
- check_availability called but result not processed
- Caller bot detects tools not being invoked: "tools=7/0" (7 turns, 0 tools executed)

**Root Causes Identified**:
1. **Policy Gate Malfunction** (`_validate_tool_call` in `adk_turn_processor.py` lines 86-108)
   - `create_reservation` blocked because `check_availability` not in `all_tools` list
   - Flag `check_availability_called` not persisting correctly across turns
   - **Evidence**: A1.2_D2 shows tool accuracy dropping to 40 after fixes attempted

2. **Slot State Not Committed Before Tool Validation**
   - Extracted slots from Grok caller not being saved to `state` before LLM generation
   - `all_tools` list only reflects previous turns, not current turn's tools
   - **Fix Applied in v4_pipeline.py (line 643)**: Reset `check_availability_called = False` when unavailable
   - **Why Still Failing**: The flag reset happens TOO LATE - after LLM has already been called with stale tool list

3. **Tool Execution Loop**
   - Tools called in sequence but results not propagated back to state
   - No feedback loop from tool executor to conversation state
   - **Impact**: A1.2_D2 attempt 2 regressed to 40/100 - fixes made it worse

### 2. FLOW FAILURES (Avg Score: 32/100) ← MOST CRITICAL
**Symptoms Observed**:
- Bot asking for slots already provided
- Conversation jumping between states
- No coherent turn-by-turn progression
- Caller detecting loops and state confusion

**Root Causes Identified**:
1. **Deterministic Clarify Not Triggering**
   - Code at `v4_pipeline.py` lines 712-740 should emit hardcoded slot questions
   - **Condition**: `ctx_doc.next_action == "clarify" AND ctx_doc.missing_slots AND end_call_stage == "idle"`
   - **Why Failing**: `ctx_doc.missing_slots` computed incorrectly or `next_action` set wrong
   - **Evidence**: A1.2_D2 and A1.3_D3 show Flow = 20/100 (nearly complete failure)

2. **Missing Slot Computation Bug** (`context_doc_builder.py`)
   - Slots marked as "missing" even after extraction from user utterance
   - `OrderSlots` status not reflecting extracted values
   - **Example from logs**: User says "zwei Personen" → bot still asks "Für wie viele Personen?"

3. **State Machine Stuck in Wrong Node**
   - `end_call_stage` not transitioning correctly after tool execution
   - Example: `reservation_start` → should advance to `readback_pending` → but stays in `reservation_start`
   - **Result**: Bot loops asking for same slot

### 3. DETERMINISTIC LOGIC FAILURES (Avg Score: 36/100) ← SECOND MOST CRITICAL
**Symptoms Observed**:
- LLM-generated responses when hardcoded questions should be used
- Unnecessary complexity added to simple slot-filling turns
- Prompt stuffing causing model confusion

**Root Causes Identified**:
1. **Deterministic Path Bypass**
   - Even when conditions met, code falls through to LLM generation
   - **Code Path**: Lines 712-740 in v4_pipeline.py should SHORT-CIRCUIT
   - **Why Not**: `first_missing` not being selected correctly or slot questions dict incomplete

2. **LLM System Prompt Degradation**
   - Previous Haiku attempts injected prompt stuffing (reverted but effects linger?)
   - LLM now generating verbose responses instead of concise slot-fill questions
   - **Evidence**: Caller detects bot repeating same long confirmation repeatedly

3. **No Fallback to Deterministic When LLM Fails**
   - If LLM response invalid → should fall back to deterministic slot question
   - Currently returns error to caller instead

---

## FIXES APPLIED AND WHY THEY FAILED

### Fix #1: `v4_pipeline.py` - Reset check_availability_called on Unavailable (Line 648)
**Applied**: Added `state.check_availability_called = False` when table unavailable
**Intent**: Prevent skip of availability check on next turn
**Result**: ❌ **FAILED** - A1.2_D2 regressed to 40/100
**Why Failed**: 
- Fix was applied TOO LATE in the flow
- By the time `check_availability_called` is reset, LLM has already been called
- Policy gate `_validate_tool_call` still blocks `create_reservation` due to stale `all_tools` list
- **Root Issue Not Addressed**: The real problem is `all_tools` list is computed at turn start, before current turn's tools

### Fix #2: Haiku Model Upgrade (haiku_fix_generator.py)
**Applied**: Claude 3.5 Sonnet → Claude Sonnet 4.6
**Intent**: Larger context window (200k → 1M) for better code reasoning
**Result**: ✅ **MODEL LOADED** but ❌ **FIXES INEFFECTIVE**
**Why Failed**:
- Model can now see full context (v4_pipeline.py lines 250-660)
- But Haiku is generating prompt-rewrite fixes for architectural problems
- **Evidence**: A1.2_D2 attempt 2 shows score regressed from baseline
- **Problem**: Haiku not implementing surgical fixes for state machine issues
- **Fix Strategy**: Haiku should target `v4_pipeline.py` state transitions, not system_prompt.py

### Fix #3: Max Tokens Increase (haiku_fix_generator.py, line 262)
**Applied**: 4096 → 8192 → 16384 tokens
**Intent**: Prevent Haiku response truncation
**Result**: ✅ **NO MORE TRUNCATION** but ❌ **FIXES STILL REGRESSIVE**
**Why Ineffective**:
- Haiku now completes full response
- But response contains ineffective fixes (prompt rewrites instead of state machine fixes)
- Real issue is architectural, not in context window size

---

## PROCESSES NOT WORKING

### 1. **Tool Calling Policy Gate** (adk_turn_processor.py lines 86-108)
**Status**: ❌ BROKEN
**Function**: `_validate_tool_call(tool, state, all_tools)`
**Issue**: 
- Blocks `create_reservation` because `all_tools` reflects only previous turns
- Current turn's `check_availability` result not in `all_tools` yet
- **Fix Needed**: Refactor to check `state.check_availability_called` FIRST before checking `all_tools`

### 2. **Missing Slot Detection** (context_doc_builder.py)
**Status**: ❌ BROKEN
**Function**: Compute `ctx_doc.missing_slots`
**Issue**:
- After slot extraction, slots not marked as filled in state
- Caller bot: "zwei Personen" → State still thinks `party_size` missing
- **Fix Needed**: Sync `OrderSlots` status with extracted values from current turn

### 3. **Deterministic Clarify Gate** (v4_pipeline.py lines 712-740)
**Status**: ⚠️ CONDITIONAL FAILURE
**Function**: Emit hardcoded slot questions instead of LLM generation
**Issue**:
- Condition logic correct but missing slots dict not populated
- Falls through to LLM generation when should use hardcoded question
- **Fix Needed**: Ensure `ctx_doc.missing_slots` is non-empty when entering this block

### 4. **State Transition Logic** (v4_pipeline.py line 651, 671)
**Status**: ⚠️ PARTIAL FAILURE
**Function**: Update `end_call_stage` from `reservation_start` → `readback_pending`
**Issue**:
- Transition happens but bot loops asking same question
- Suggests state not actually persisting across turns or being reset mid-flow
- **Fix Needed**: Verify Redis persistence of state object

### 5. **Fix Generation Strategy** (haiku_fix_generator.py lines 171-257)
**Status**: ❌ WRONG STRATEGY
**Function**: Determine fix type based on score and issue analysis
**Issue**:
- Currently uses score-based decision: score<90 → prompt rewrite
- But A1.2_D2 shows architectural issues REQUIRE surgical fixes
- Prompt rewrites cause regression (40/100 < baseline)
- **Fix Needed**: Implement issue-gated strategy (tool_analysis keywords → surgical; tone/wording → prompt)

### 6. **Regression Circuit Breaker** (scenario_based_loop.py)
**Status**: ⚠️ NOT TRIGGERED WHEN SHOULD
**Function**: Detect score regression and revert fixes
**Issue**:
- A1.2_D2: baseline unknown → attempt 2 = 40, but no revert triggered
- Circuit breaker only checks: `baseline - attempt_score > 3`
- **Fix Needed**: Ensure baseline is captured and comparison works

---

## DETAILED FAILURE LOG - ERROR FLAGS BY BATCH

### A1.1_D1 Error Flags (6 total)
```
Turn 2: BOT_LOOP — repeating confirmation
Turn 4-5: NAME_LOOP — asking for name repeatedly
Turn 6: SLOT_STATE_LOST — party_size forgotten
```

### A1.2_D2 Error Flags (16 total) ← WORST BATCH
```
Turn 2: BOT_LOOP — same answer repeated
Turn 3: FLOW_BROKEN — conversation state corrupted
Turn 4: NO_TOOL_CALLED — reservation not invoked
Turn 5-7: AVAILABILITY_CHECK_FAILED — table unavailable, bot tries commit anyway
Turn 8-10: NAME_LOOP — bot asking for name 3x
Turn 11+: DETERMINISTIC_FAILED — hardcoded questions not used
```

### A1.3_D3 Error Flags (11 total)
```
Turn 2: UHRZEIT_FALSCH — time confusion
Turn 3-4: BOT_LOOP — same confirmation repeated
Turn 5: SLOT_STATE_LOST — date forgotten
Turn 6-7: FLOW_BROKEN — conversation doesn't progress
```

---

## SUMMARY OF BROKEN PROCESSES

| Process | Status | Impact | Priority |
|---------|--------|--------|----------|
| Tool Calling Policy Gate | ❌ BROKEN | Tools blocked unfairly | 🔴 CRITICAL |
| Missing Slot Computation | ❌ BROKEN | Slots appear missing when filled | 🔴 CRITICAL |
| Deterministic Clarify Gate | ⚠️ FAILING | LLM over-used, bot verbose | 🔴 CRITICAL |
| State Transition Logic | ⚠️ PARTIAL | State not persisting/resetting | 🔴 CRITICAL |
| Fix Strategy (Score-based) | ❌ WRONG | Fixes regress scores | 🟠 HIGH |
| Regression Detection | ⚠️ WEAK | Doesn't catch all regressions | 🟠 HIGH |
| Haiku Fix Generation | ⚠️ INEFFECTIVE | Generates prompt rewrites not surgical fixes | 🟠 HIGH |

---

## RECOMMENDATIONS FOR EXTERNAL ANALYSIS

**What to Focus On**:
1. **Tool Calling Architecture** - The policy gate is fundamentally flawed
   - `all_tools` list timing issue
   - `check_availability_called` flag persistence
   
2. **State Management** - Slots being lost mid-conversation
   - Redis persistence verification needed
   - Slot extraction → state sync pipeline broken
   
3. **Deterministic Path** - Not being used when it should be
   - Missing slot detection algorithm failing
   - No fallback when conditions aren't met
   
4. **Fix Generation** - Haiku applying wrong fix type
   - Score-based strategy fundamentally wrong
   - Need issue-gated strategy instead

**Data for Analysis**:
- All batch results with full metrics: Above
- Error categorization: Above  
- Root cause mapping: Above
- Process status: Above

---

END REPORT
