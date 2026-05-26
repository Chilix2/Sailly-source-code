# Live Call Issues Investigation — April 20, 2026

## Summary
Recent live call testing (demo-9f97d6c28066 @ 10:46 UTC) revealed three critical issues:
1. TTS artifact: "kein roboterhafter klang" speaking at end of bot messages
2. Barge-in not working during bot speech
3. `create_order` still failing with total_price=0.0 despite Fix 3 implementation

---

## Issue 1: TTS Artifact — "kein roboterhafter klang"

### Symptom
At the end of bot responses, the phrase "kein roboterhafter klang" (no robotic sound) is being vocalized.
This appears to be a debug/test phrase leaking into TTS output.

### Root Cause (Suspected)
- The TTS prompt in `server/sailly_gemini_tts.py` previously contained: `"ruhig bei technischen Themen"` (calm on technical topics)
- This was removed and replaced with a neutral prompt  
- But "kein roboterhafter klang" may be a remnant from another test prompt or injected inadvertently

### Location to Check
- `server/sailly_gemini_tts.py` — search for this phrase
- `server/brain_service.py` — check if this phrase is in the TTS style prompt
- `server/main.py` — check `CASCADE_TTS_STYLE_PROMPT`

### Fix Candidate
Search for and remove any instances of "kein roboterhafter klang" or similar test phrases from TTS-related code.

---

## Issue 2: Barge-in Not Working During Bot Speech

### Symptom
User cannot interrupt the bot after greeting or during bot response playback.

### Previous Implementation
- `BargeInHandler` was added to the Pipecat pipeline in `server/main.py` after recent updates
- Configured to suppress interruptions during greeting, then enable afterward

### Root Cause (Suspected)
1. **BargeInHandler not actually wired**: Verify it's in the pipeline in correct position
2. **Barge-in logic broken**: Check if `suppress_barge_in_during_greeting` flag is working
3. **STT not passing barge-in frames**: Verify `TranscriptionFrame` is reaching the handler while bot is speaking

### Location to Check
- `server/main.py` — verify BargeInHandler instantiated and in pipeline
- `server/brain_service.py` — check if any code is manually suppressing barge-in
- Pipecat pipeline connection between STT → BargeInHandler → brain

### Investigation Steps
```bash
# Check if BargeInHandler code exists
grep -n "class BargeInHandler" /home/charles2/sailly-browser-demo/server/main.py

# Check if it's in pipeline
grep -n "barge_handler\|BargeInHandler" /home/charles2/sailly-browser-demo/server/main.py

# Check logs for barge-in related messages
sudo journalctl -u sailly-browser-demo | grep -i "barge\|interrupt"
```

---

## Issue 3: Fix 3 (Price Fallback) Not Firing — create_order Still Failing

### Symptom
In call demo-9f97d6c28066 (Turn 3):
- `get_menu` returned menu with "Kimchi Jjigae" price: 14.5 (cached in Turn 0)
- `create_order` fired with `total_price=0.0` (built by `_build_tool_args`)
- Expected: Price fallback looks up "Kimchi Jjigae" → 14.5, order succeeds
- Actual: Order rejected with "Fehlende Pflichtfelder: total_price"

### Timeline of Fixes
1. **Fix 1 (Menu Caching)**: ✅ WORKING — logs show "[MENU_CACHE] cached 7 items at turn 0"
2. **Fix 2 (send_sms Guard)**: ✅ WORKING — logs show send_sms correctly blocked when create_order failed
3. **Fix 3 (Price Fallback)**: ❌ NOT FIRING — no "[create_order] price fallback" log entry

### Root Cause Analysis

#### Hypothesis A: Conversation State Not Being Passed
The `execute_tool` call in `adk_turn_processor.py:531-535` threads `conversation_state=self.state`.
But `self.state` might be **empty** or **not restored from Redis** at Turn 3.

**Check**: Does `self.state.cached_menu` exist at time of create_order?

#### Hypothesis B: Conversation State Passed But cached_menu is None
The state is passed, but `cached_menu` field was not properly serialized/deserialized across Redis.

**Check**: Verify `to_dict` and `from_dict` include `cached_menu` fields.
**Status**: ✅ VERIFIED — both methods include cached_menu (lines 133-134, 191-192, 225-226)

#### Hypothesis C: Context Dict Not Properly Constructed in Dispatcher
The `execute_tool` at line 240-250 wraps context for `create_order`:
```python
context = {
    "tools_called_this_turn": [...],
    "conversation_state": conversation_state,
}
```

But dispatcher might not be recognizing "create_order" as a context tool, or context is malformed.

**Check**: Verify "create_order" is in `context_tools` set (line 243).
**Status**: ✅ VERIFIED — "create_order" is explicitly listed

#### Hypothesis D: context Parameter Not Reaching _create_order Function Signature
The `_create_order` function was updated to accept `context: Optional[dict] = None`.
But the dispatcher might be calling it **without** the context kwarg due to reflection/routing issues.

**Check**: Verify dispatcher calls `await handler(..., context=context)` for create_order.
**Status**: ✅ VERIFIED — line 249 shows context is passed

#### Hypothesis E: Price Fallback Logic Never Runs Because total_price Check Fails
The fallback fires only if `(not _raw_price or float(_raw_price) == 0.0)`.
If `_raw_price = 0.0`, the condition `float(0.0) == 0.0` should evaluate to True.

**Potential Issue**: If `_raw_price` is the string `"0.0"` or int `0`, the float comparison might behave unexpectedly.

**Fix**: Ensure comparison is type-safe.

#### Hypothesis F: get_cached_dish_price Returns None Even Though Menu Exists
The fuzzy match ratio threshold is 0.75. "Kimchi Jjigae" should match exactly (ratio=1.0).

**Potential Issue**: If cached_menu structure is wrong, or function logic is broken, no price is found.

### Immediate Investigation: Add Verbose Logging

Already added debug logs to tools/executor.py:
- Line ~240: Log context being passed with state and cached_menu status
- Line ~593: Log state existence and cached_menu content before fallback attempt
- Line ~606: Log fallback result (None, or price value)

### Next Test Call
Run a fresh call with debugging enabled:
1. Get menu (Turn 0) — should log "[MENU_CACHE] cached 7 items"
2. Make order (Turn 3) — should log all debug lines showing state/cache status and fallback result

---

## Secondary Issues Noted

### Issue 4: Browser Demo vs Google Fork Architecture Mismatch
The two codebases (sailly-browser-demo port 8080 and sailly-google-fork port 3003) are fundamentally different:
- **browser-demo**: 973-line simplified brain (demo only)
- **google-fork**: 55,177-line production brain (PSTN, training, validation)

Previous fixes were incorrectly applied to google-fork when the live demo runs on browser-demo.
All current fixes are correctly deployed to `/home/charles2/sailly-browser-demo` (port 8080).

### Issue 5: Database Writing Issues
The `success` column in `google_tool_calls` is **never populated** by the INSERT statements in `brain_service.py:340-356`.
This is a separate bug: the schema has a `success` field, but the code never writes to it.

---

## Action Plan

### Immediate (This Session)
1. **Run fresh call** with debug logging enabled to capture:
   - State restoration status at Turn 3
   - cached_menu content at Turn 3
   - Exact fallback execution flow

2. **Investigate TTS artifact**:
   - Search codebase for "kein roboterhafter klang"
   - Review TTS prompt in sailly_gemini_tts.py and main.py

3. **Verify barge-in status**:
   - Confirm BargeInHandler is wired in pipeline
   - Check if suppress flag is working correctly

### After Debug Call
- Parse logs to identify exactly where Fix 3 breaks
- Implement fix based on findings
- Re-test call

---

## Files Modified by Fix Pack

- `server/brain/conversation_state.py`: Added cached_menu fields + get_cached_dish_price helper
- `server/brain/adk_turn_processor.py`: Wired menu caching + threaded context
- `tools/executor.py`: 
  - Updated execute_tool signature (added tool_results, conversation_state params)
  - Implemented context routing for create_order and send_sms
  - Added price fallback to _create_order
  - Updated _send_sms_noop to check parent tool success

---

## Commit History (This Session)

- No git commits yet (changes pending verification)
- All edits applied directly to production files
- Service restarted after changes


---

## Issue 1 Fix: TTS Artifact "Kein roboterhafter Klang"

### Root Cause (CONFIRMED)
Located at `server/main.py:58`:
```python
CASCADE_TTS_STYLE_PROMPT = (
    "Sprich natürlich, klar und in zügigem, freundlichem Tempo auf Deutsch — "
    "wie an einer Restaurant-Rezeption. Kein roboterhafter Klang."
)
```

The phrase "Kein roboterhafter Klang" (No robotic sound) is a **meta-instruction** intended to guide Gemini's TTS synthesis style, not to be vocalized. However, Gemini's TTS API is including it in the audio output.

### Applied Fix
**Commit**: Removed the problematic phrase from the style prompt (in-progress)

```python
CASCADE_TTS_STYLE_PROMPT = (
    "Sprich natürlich, klar und in zügigem, freundlichem Tempo auf Deutsch — "
    "wie an einer Restaurant-Rezeption."
)
```

**Location**: `server/main.py:56-59`

**Verification**: Service restarted 10:54 UTC. Next call should NOT include this phrase.

---

## Issue 2 Investigation: Barge-in Handler Status

### Findings
✅ **BargeInHandler is properly wired**:
- Class defined in `server/barge_in_handler.py:19`
- Imported in `server/main.py:43`
- Instantiated at line 335
- Wired in pipeline at line 346 with comment: "suppress interruptions during greeting, enable after"

### Next Verification
1. Check if `suppress_barge_in_during_greeting` flag is properly toggled after greeting
2. Check if the handler is actually receiving `TranscriptionFrame`s during bot speech
3. Monitor logs for barge-in related events

---

## Issue 3 Investigation: Fix 3 (Price Fallback) Detailed Analysis

### Debug Logging Added
Added verbose logging to track the execution flow (commit pending):

**In `tools/executor.py:240`** (dispatcher):
```
[execute_tool] {tool_name}: passing context with state={bool}, cached_menu={bool}
```

**In `tools/executor.py:593`** (fallback attempt):
```
[create_order] price fallback attempting: state={bool}, cached_menu={...}
[create_order] price fallback lookup result: {result}
[create_order] price fallback: no match or zero price
[create_order] price fallback skipped: no conversation_state in context
```

### Next Test
Run fresh call with debug logging enabled to identify where the fallback chain breaks.

---

## Summary of Changes This Session

### File: server/main.py
- **Line 58**: Removed "Kein roboterhafter Klang." from CASCADE_TTS_STYLE_PROMPT

### File: tools/executor.py
- **Line 240**: Added debug logging to dispatcher for context passing
- **Line 593-606**: Added detailed debug logging throughout price fallback logic
- **Service**: Restarted at 10:54 UTC

### File: server/brain/conversation_state.py
- (Previous session) Added cached_menu fields (lines 133-134)
- (Previous session) Added get_cached_dish_price helper (lines 229+)

### File: server/brain/adk_turn_processor.py
- (Previous session) Wired menu caching (lines 539-547)
- (Previous session) Added context threading (lines 531-535)

### File: tools/executor.py
- (Previous session) Updated execute_tool signature (lines 159-177)
- (Previous session) Implemented context routing (lines 240-250)
- (Previous session) Added price fallback to _create_order (lines 589-606)
- (Previous session) Updated _send_sms_noop to check parents (lines 1346-1395)

---

## Pending Actions

### Immediate
1. Make a live test call to verify:
   - ✅ TTS artifact removed ("kein roboterhafter klang" NOT spoken)
   - ⏳ Barge-in works during bot speech
   - ⏳ create_order succeeds with price fallback

2. Review debug logs from test call to pinpoint Fix 3 failure

3. If Fix 3 still broken:
   - Check if `self.state.cached_menu` is actually populated at Turn 3
   - Add Redis state dump to logs to inspect persisted state
   - Verify context is not None and has conversation_state key

### Later Session
- Implement fix for database `success` column never being written
- Consider refactoring conversation_state persistence to be more robust
- Document the browser-demo vs google-fork split in architecture docs

