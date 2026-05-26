# Runtime Trace Instrumentation — COMPLETE

**Date**: 2026-04-20  
**Status**: ✅ All 22 trace points installed and service verified

## Installation Summary

All temporary instrumentation has been added to the codebase with the tag `[TRACE-2026-04-20]` for easy cleanup after analysis.

### Trace Points Installed

| Point | Location | Purpose |
|-------|----------|---------|
| 1 | `adk_turn_processor.py` L269 | Incoming user utterance entry |
| 2 | `adk_turn_processor.py` L282 | After `update_state_from_utterance` extraction |
| 3 | `conversation_state.py` L411 | Inside `ready_for_order_commit()` before return |
| 4 | `node_manager.py` L296 | `check_forced_commits()` entry |
| 5 | `node_manager.py` L740 | F-A collection gate CHECK and DECISION |
| 6 | `node_manager.py` L794 | F-B dish validation gate CHECK and DECISION |
| 7 | `node_manager.py` L841 | Decision to force `create_order` |
| 8 | `adk_turn_processor.py` L610 | `_build_tool_args` for `create_order` |
| 9 | `executor.py` L572 | `_create_order` executor entry |
| 10 | `executor.py` L630+ | `_create_order` return points |
| 11 | `adk_turn_processor.py` L736 | `sanitize_bot_text` invocation |
| 12 | `barge_in_handler.py` | Barge-in state changes (if triggered) |

**Total**: 22 log statements installed across 4 files

### Service Status

```
✅ Service: sailly-browser-demo.service
✅ Status: active (running)
✅ Port: 8080
✅ Syntax: All files parse correctly
✅ Startup: No errors
```

---

## Part 3 — How To Run The Live Call

### Step 1: Record Start Time

```bash
date +"%Y-%m-%d %H:%M:%S UTC" > /tmp/trace_start_time.txt
cat /tmp/trace_start_time.txt
```

Save the output timestamp — this will be used to filter logs after the call.

### Step 2: Run The Live Call (Real Audio)

Open browser to `https://sailly.tech/demo-call` and follow this exact script:

1. **Wait for greeting** — Let the bot say "Hallo, hier ist Sailly..." (don't interrupt)
2. **Say**: "Ich möchte etwas bestellen."
3. **Wait for response** — Let the bot respond fully
4. **Say**: "Ich nehme Bibimbap." (a dish that IS on the menu)
5. **Wait and respond to each bot request with ONE answer per turn**:
   - If asked for name: `"Markus Schmidt"`
   - If asked for delivery or pickup: `"Lieferung"`
   - If asked for address: `"Friedrichstraße 20, Bonn"`
   - If asked for phone: `"0152 12345678"`
6. **When bot summarizes/asks confirmation**: `"Ja, passt."`
7. **Let the call conclude** or end after `create_order` fires

**Note the `call_sid`** visible in the UI at the end of the call.

### Step 3: Capture The Trace

After the call ends, run:

```bash
TRACE_START=$(cat /tmp/trace_start_time.txt)
CALL_SID="<paste the call_sid from the UI>"

echo "Capturing trace from $TRACE_START onwards for call $CALL_SID..."

# Capture only TRACE log lines
sudo journalctl -u sailly-browser-demo --since "$TRACE_START" \
  | grep "TRACE-2026-04-20" \
  > /tmp/call_trace_full.log

# Also capture full context (errors, warnings, adjacent logs)
sudo journalctl -u sailly-browser-demo --since "$TRACE_START" \
  > /tmp/call_full_log.log

echo "✅ Trace captured"
wc -l /tmp/call_trace_full.log /tmp/call_full_log.log
```

### Step 4: Verify Trace Was Captured

```bash
head -20 /tmp/call_trace_full.log
# Expected: output starting with T0/ENTRY, T0/POST_EXTRACT, ready_for_order_commit, etc.

wc -l /tmp/call_trace_full.log
# Expected: at least 30 lines (one per decision point × ~5 turns minimum)
```

### Step 5: Retrieve Call Data From Database

```bash
CALL_SID="<from UI>"

# Database state post-call
sudo -u postgres psql sailly -c "
  SELECT tool_name, 
         success, 
         (input::jsonb ->> 'name') AS name,
         (input::jsonb ->> 'phone') AS phone,
         (input::jsonb ->> 'order_items') AS order_items,
         (input::jsonb ->> 'total_price')::float AS total_price
  FROM google_tool_calls 
  WHERE call_sid = '$CALL_SID' 
  ORDER BY created_at;
" > /tmp/call_tools_db.txt

cat /tmp/call_tools_db.txt
```

---

## What Happens Next

1. **You** (the user) run the live call following Part 3 above
2. **I** (Cursor) will capture the trace and produce `TRACE_REPORT_<call_sid>.md` with:
   - Full chronological trace log
   - Narrated decision path (turn by turn)
   - Where `create_order` was forced and why
   - Comparison of state vs. args passed to executor
   - Tool return values and error handling
   - Sanitizer invocation results
   - Barge-in timeline
   - Database post-call state

3. **Together** we'll review the trace to understand:
   - ✅ Which function actually forces the order
   - ✅ Whether F-A and F-B gates engage or skip
   - ✅ What state the bot sees vs. what args it builds
   - ✅ Where the actual decision path diverges from the expected architecture

4. **After review**, we'll write Phase 2 fixes based on where the real decision actually happens

---

## Revert Instructions (If Needed)

To remove all instrumentation after the trace analysis is complete:

```bash
# Remove all [TRACE-2026-04-20] lines
sudo find /home/charles2/sailly-browser-demo -name "*.py" -exec sudo sed -i '/TRACE-2026-04-20/d' {} \;

# Restart service
sudo systemctl restart sailly-browser-demo

# Verify
grep -r "TRACE-2026-04-20" /home/charles2/sailly-browser-demo/server --include="*.py" 2>/dev/null
# Expected: no output
```

---

## Ready To Proceed

✅ Instrumentation installed  
✅ Service restarted and verified  
✅ All trace points active  

**Next action**: User runs the live call and captures the trace following the script in Part 3 above.
