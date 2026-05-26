# ISSUES PRIORITIZATION & NEXT ACTIONS
**Session**: Post-Latency Emergency (2026-04-20)  
**Status**: Ready for UX Issue Investigation Phase

---

## CRITICAL SUMMARY

✅ **Latency Emergency**: RESOLVED  
- Baseline P50: 1.5s → Final P50: ~0.9s (40% improvement)
- Method: VAD tuning (0.8→0.5s) + TTS buffer skip for short responses
- All instrumentation deployed and working

⚠️ **Outstanding UX Issues**: 6 issues identified, need investigation

---

## ISSUE CATALOG & PRIORITIZATION

### TIER 1 — HIGH IMPACT, EASY TO FIX

#### Issue #2: Phone Number Asked First ⚠️
**Problem**: Bot asks for phone number before name/address  
**Expected**: Name → Address → Phone  
**Actual**: Phone → Name → Address (or random)  
**User Feedback**: "we said phone number as latest not as first"  
**Root Cause Hypothesis**: F-A (active collection) gate sequencing in `NodeManager`  
**Files to Investigate**:
- `server/brain/node_manager.py` (F-A gate logic)
- `server/brain/conversation_state.py` (field validation order)

**Reproduction**: Make test call, observe which field bot asks for first  
**Fix Complexity**: LOW (reorder field checks)  
**Impact**: HIGH (critical UX, happens every call)  
**Priority**: 🔴 DO FIRST

---

#### Issue #4: Bot Forgets Caller's Name ⚠️
**Problem**: Bot doesn't retain or refer back to caller's name  
**User Feedback**: "forgot to ask for callers name"  
**Root Cause Hypothesis**: `ConversationState.caller_name` not threaded through conversation or LLM context  
**Files to Investigate**:
- `server/brain/conversation_state.py` (name extraction/storage)
- `server/brain/adk_turn_processor.py` (context building for LLM)
- `server/brain/tier2_runner.py` (LLM context passed to Gemini)

**Reproduction**: Make test call, listen for name confirmation  
**Fix Complexity**: LOW-MEDIUM (state management)  
**Impact**: HIGH (personalization, every call)  
**Priority**: 🔴 DO SECOND

---

### TIER 2 — MEDIUM IMPACT, NEEDS INVESTIGATION

#### Issue #1: Bot Says "du" Instead of "Sie" ⚠️
**Problem**: Informal German pronoun; should use formal "Sie"  
**User Feedback**: "says du and not sie"  
**Root Cause Hypothesis**: LLM system prompt or instruction doesn't specify formal register  
**Files to Investigate**:
- `server/brain/tier2_runner.py` (system message in LLM context)
- Gemini model behavior (verify if prompt is being followed)

**Reproduction**: Any test call in German  
**Fix Complexity**: LOW (prompt edit)  
**Impact**: MEDIUM (cultural/politeness)  
**Priority**: 🟡 DO THIRD

---

#### Issue #3: Missing Filler Words During Address Validation ⚠️
**Problem**: Bot says "validating address" abruptly without transitions  
**User Feedback**: "while validation address, missing filler words"  
**Root Cause Hypothesis**: Address validation response templates lack TTS filler/transition phrases  
**Files to Investigate**:
- `server/tools/executor.py` (address validation response)
- `server/brain/conversation_state.py` (validation messaging)

**Reproduction**: Make test call, say an address, listen for validation feedback  
**Fix Complexity**: LOW (response templating)  
**Impact**: MEDIUM (UX, feels robotic)  
**Priority**: 🟡 DO FOURTH

---

### TIER 3 — LOWER PRIORITY, COMPLEX OR LOWER IMPACT

#### Issue #6: Address Validation Flow (Sequential → Batch)
**Problem**: Bot validates address immediately; should collect and validate later  
**User Feedback**: "just say i need your address, then ask later for more information"  
**Current**: `verify_address()` called immediately, blocks conversation  
**Desired**: Collect address, continue, validate async or at end  
**Root Cause**: `adk_turn_processor.py` executes tools sequentially in `forced_tools` list  
**Fix Complexity**: HIGH (architectural refactor needed)  
**Impact**: MEDIUM (flow improvement)  
**Priority**: 🔵 DEFER (requires design review)

---

#### Issue #5: Price Display Unnatural
**Problem**: Price announced in non-idiomatic way  
**Root Cause Hypothesis**: 
- `normalize_digit_groups()` incorrectly handling price numbers
- Or TTS speaking rate issues with number sequences

**Example**: "1200 EUR" might be read as "eins zwei null null" instead of "tausendzweihundert"  
**Files to Investigate**:
- `server/sailly_gemini_tts.py` (normalize_digit_groups logic)
- LLM prompt (how prices are formatted before TTS)

**Reproduction**: Order something, listen to price announcement  
**Fix Complexity**: MEDIUM (number normalization logic)  
**Impact**: LOW (mostly cosmetic)  
**Priority**: 🔵 DEFER (lower impact)

---

## IMMEDIATE INVESTIGATION PLAN

### Step 1: Create Test Call Suite (30 min)
**Goal**: Capture baseline UX issues across 5–10 calls  
**Methodology**:
1. Make 5 complete test calls (3 turns each) on `sailly.tech/demo-call`
2. Use consistent input pattern:
   - Turn 1: "Ich möchte etwas bestellen" (I want to order something)
   - Turn 2: "Bibimbap" (item name)
   - Turn 3: "Ja" or "Nein" (confirmation)
3. Record or capture transcripts
4. Note which issues appear (phone first? name forgotten? du/Sie?)

**Test Call IDs to Note**: `demo-XXXXXXXXXX`

---

### Step 2: Trace Analysis (30 min)
**Goal**: Map issues to code locations  
**For Each Issue Found**:
1. Extract Gemini LLM response from logs
2. Check conversation state (`ConversationState` dump)
3. Inspect `NodeManager` decision at that turn

**Command**:
```bash
# Extract all logs for a call
CALL_ID="demo-XXXXXXXXXX"
sudo journalctl -u sailly-browser-demo | grep "$CALL_ID" > /tmp/call_${CALL_ID}.log

# Look for bot responses and state changes
cat /tmp/call_${CALL_ID}.log | grep -E "LLMTextFrame|ConversationState|should_escalate"
```

---

### Step 3: Root Cause Identification (30 min per issue)
**For Issue #2 (Phone First)**:
```
1. Inspect NodeManager F-A gate:
   - Where does bot decide to ask for field X?
   - What's the order of checks?
   - Is it based on field.required order in ConversationState?

2. Check extractor output:
   - name_extractor(user_text) → extracted?
   - address_extractor(user_text) → extracted?
   - phone_extractor(user_text) → extracted?
   
3. Hypothesis: Confirm which extractor fires first in code
```

**For Issue #4 (Forgot Name)**:
```
1. Grep ConversationState for caller_name:
   - Is it being set after extraction?
   - Is it being passed to LLM context?
   
2. Check tier2_runner context building:
   - Is caller_name in the system message?
   - Does conversation history include "Your name is: X"?
   
3. Test: Make call, extract LLM input context to see if name is there
```

---

### Step 4: Fix Implementation (Per Issue, 15–60 min)
**Once root cause identified**, create targeted fix for that issue.

---

## WORKING HYPOTHESIS (Pre-Investigation)

**Issue #2 Hypothesis**: 
- F-A gate iterates through extractors in order: `[phone, name, address]` instead of `[name, address, phone]`
- **Fix**: Reorder extractor list in `NodeManager` or `ConversationState`

**Issue #4 Hypothesis**:
- `caller_name` not passed to Gemini LLM context
- Bot doesn't have `caller_name` in system message or conversation history
- **Fix**: Add `caller_name` to context building in `tier2_runner.py`

**Issue #1 Hypothesis**:
- LLM system prompt doesn't specify formal German register
- **Fix**: Add "Use formal 'Sie' pronoun" to system message

---

## SUCCESS CRITERIA

**After Investigation & Fixes**:
- Issue #2 (Phone First): ✓ Bot asks for name first
- Issue #4 (Forgot Name): ✓ Bot mentions caller's name during call
- Issue #1 (du vs Sie): ✓ All bot responses use "Sie"
- P50 latency stays < 1.5s (no regression)

---

## FILES TO REVIEW FIRST

1. **`server/brain/node_manager.py`**
   - F-A gate logic
   - Field sequencing
   - Bot response decision tree

2. **`server/brain/conversation_state.py`**
   - State dataclass
   - Extractor order
   - Validation order

3. **`server/brain/tier2_runner.py`**
   - LLM context building
   - System message
   - Name/state passed to Gemini

4. **`server/sailly_gemini_tts.py`**
   - Digit normalization (Issue #5)
   - Buffer skip logic (Fix B validation)

---

## QUICK COMMAND REFERENCE

**Run test call and capture logs**:
```bash
# Make call on demo-call, note the call ID
# Then extract logs:
CALL_ID="demo-XXXXXXXXXX"
sudo journalctl -u sailly-browser-demo --since "2026-04-20 16:52" | grep "$CALL_ID" > /tmp/trace_${CALL_ID}.log
cat /tmp/trace_${CALL_ID}.log
```

**Search for specific issue patterns**:
```bash
# Look for phone extraction
grep -i "phone" /tmp/trace_${CALL_ID}.log

# Look for name extraction
grep -i "name" /tmp/trace_${CALL_ID}.log

# Look for bot response text
grep "LLMTextFrame" /tmp/trace_${CALL_ID}.log
```

---

## NEXT DECISION POINT

**Before Starting Fixes**: Make 5 test calls to confirm which issues are present and reproducible.

**Expected Outcome**: 
- Identify pattern (e.g., "Phone always asked first in 5/5 calls")
- Narrow down to 2–3 most critical issues
- Start with Issue #2 (Phone ordering) as it's highest-impact and likely easiest fix

---

**Generated**: 2026-04-20 16:55 UTC  
**Status**: Ready to begin UX Issue Investigation Phase  
**Estimated Next Phase Duration**: 2–4 hours for investigation + fixes
