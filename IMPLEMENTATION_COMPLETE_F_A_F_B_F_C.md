# Implementation Complete: F-A, F-B, F-C Fixes

**Date**: April 20, 2026  
**Status**: ✅ All code changes complete, service restarted

## What Was Implemented

### F-A Fix: Stop Premature Order Forcing (Active Collection)

**Files Modified**:
- `server/brain/conversation_state.py` - Added state fields and helpers
- `server/brain/node_manager.py` - Added collection gates before forced create_order
- `server/brain/conversation_nodes.py` - Updated ORDERING prompt

**Key Features**:
1. **State Tracking**: Per-field attempt counters, last_field_asked, confirmation flags
2. **Collection Logic**: `next_field_to_ask()` returns which field bot should ask for next
3. **Escalation**: After 3 attempts per field without answer, escalate to human/alternatives
4. **Active Extraction**: name (regex patterns), phone (German 0xxx format + mobile validation), address, delivery choice
5. **Per-Turn Increment**: Attempts only increment when LLM actually asked for field last turn
6. **Language Update**: Bot now distinguishes "Zahlungslink" (offer stage) vs "Bestellbestätigung" (after payment)
7. **Gates in node_manager.py**: Before forcing create_order, check if fields missing or already escalated

### F-B Fix: Dish Validation (Menu Alignment)

**Files Modified**:
- `server/brain/conversation_state.py` - Added `normalize_dish_name()` helper
- `server/brain/node_manager.py` - Added dish validation gate

**Key Features**:
1. **Fuzzy Matching**: Normalizes user-spoken dish against cached_menu (real data) first, KNOWN_DISHES as fallback
2. **Validation Gate**: Before forced create_order, validates selected_dish exists on actual menu
3. **Prevents Hallucination**: If dish not on menu, prevents order commit, lets LLM handle "not available"
4. **Menu Caching**: get_menu results already cached in state (existing code confirmed)

### F-C Fix: Tool Error Visibility (Bot Honesty)

**Files Modified**:
- `server/brain/conversation_state.py` - Added `sanitize_bot_text_against_tool_results()` helper
- `server/brain/adk_turn_processor.py` - Integrated sanitizer before TurnResult

**Key Features**:
1. **Error Detection**: Checks if create_order/create_reservation had errors in tool_results
2. **Response Rewrite**: Replaces "aufgenommen" success language with apology
3. **Integration Point**: Applied after tool execution, before TTS output
4. **Ensures Honesty**: Bot never claims false confirmation when tools fail

### Supporting Infrastructure

**New Tool**:
- `tools/executor.py`: Added `verify_phone()` tool for phone validation
  - Checks German format (0xxxxxxxxx)
  - Validates mobile (015x, 016x, etc.) vs landline
  - Returns error with guidance for landline

**Existing Infrastructure (Verified)**:
- Menu caching: ✅ Already working (get_menu → state.cached_menu)
- Context passing: ✅ Already working (tools receive conversation_state)
- send_sms parent check: ✅ Already working (blocks false SMS confirmations)

## Test Plan

### Test 1: Active Collection Flow (F-A)
**Scenario**: User says only "Ich nehme das Bibimbap"
**Expected**:
1. Bot asks for name (attempt 1/3)
2. User remains silent or says something vague
3. Bot asks for name again (attempt 2/3)
4. User says "Mein Name ist Anna"
5. Bot asks for delivery choice
6. User says "Lieferung"
7. Bot asks for address
8. User provides address; bot validates via verify_address
9. Bot asks for phone (mobile only)
10. User provides phone; bot validates mobile format
11. Order forced with all fields present
✅ Order should succeed with real data

### Test 2: Dish Validation (F-B)
**Scenario**: User says "Ich nehm das Kimchi Jjigae" (spelled exactly)
**Expected**:
1. Bot calls get_menu, caches menu in state
2. User later confirms order with "Kimchi Jjigae"
3. normalize_dish_name() checks cached_menu for "Kimchi Jjigae"
4. If actual menu has only "Kimchi Jeon": normalization returns None
5. check_forced_commits skips order forcing
6. Bot says dish not available, suggests alternatives
✅ Prevents hallucination order

### Test 3: Tool Error Response (F-C)
**Scenario**: User provides all fields, but verify_address fails (invalid address)
**Expected**:
1. All fields present → order forced
2. verify_address fails (returns error)
3. Tool results contain error
4. create_order fails (due to address validation)
5. sanitize_bot_text_against_tool_results() rewrites bot response
6. Instead of "Bestellung aufgenommen", bot says "Entschuldigung, die Adresse konnte nicht verifiziert werden..."
✅ Bot is honest about failure

### Test 4: Phone Validation (verify_phone tool)
**Scenario**: User says "Meine Nummer ist 02261 123456" (landline)
**Expected**:
1. extract logic catches "02261..." as phone
2. Identifies as landline (not 015x/016x prefix)
3. sets phone_is_landline = True
4. next_field_to_ask() returns "phone" again (because phone_is_landline)
5. Bot asks "Haben Sie eine Handynummer?"
✅ Landline rejected, mobile requested

### Test 5: Escalation After 3 Attempts (F-A)
**Scenario**: User refuses to provide name after 3 asks
**Expected**:
1. Bot asks for name (attempt 1)
2. User says "Nicht wichtig"
3. Bot asks again (attempt 2)
4. User says "Lieber nicht"
5. Bot asks third time (attempt 3)
6. User says "Nein, danke"
7. should_escalate() returns True
8. Bot offers alternative: "Kann ich Sie später anrufen? Oder möchten Sie einen Rückruf?"
✅ Escalation triggers instead of forced order

## Deployment Verification

Service restarted successfully on 2026-04-20 11:54:37 UTC.

```bash
# Check service status
sudo systemctl status sailly-browser-demo

# Check logs for new log tags
sudo journalctl -u sailly-browser-demo --since "2 hours ago" | grep -E "\[Collection\]|\[MENU_CACHE\]|\[Sanitize\]|\[verify_phone\]"
```

## Next Steps

1. **Manual Testing**: Execute Tests 1-5 with live calls on sailly.tech/demo-call
2. **Monitor Logs**: Watch for new [Collection], [MENU_CACHE], [Sanitize] log lines
3. **Database Validation**: Check google_tool_calls to verify tool errors and successful attempts
4. **Phase A Regression**: Run existing Phase A scenarios to confirm no regression

## Files Changed Summary

| File | Change Type | Key Additions |
|------|-------------|---|
| `server/brain/conversation_state.py` | Enhancement | 11 new state fields, 3 helper methods, normalize_dish_name(), sanitize_bot_text() |
| `server/brain/node_manager.py` | Logic | F-A gates (collection check), F-B gate (dish validation) |
| `server/brain/conversation_nodes.py` | Prompt | Updated ORDERING node with active collection + offer/confirmation distinction |
| `server/brain/adk_turn_processor.py` | Integration | F-C sanitizer call before TurnResult |
| `tools/executor.py` | New Tool | verify_phone() tool + handler registration |

## Known Limitations

- **First Turn Extraction**: Some extraction (name, phone) may work better if user provides all info at once vs split across turns
- **Language Variance**: German name patterns (regex) may miss some accented names or compound formats
- **Landline Message**: Currently fixed message; could be more conversational if needed
- **Escalation Message**: Not yet customized per field; generic alternatives message
