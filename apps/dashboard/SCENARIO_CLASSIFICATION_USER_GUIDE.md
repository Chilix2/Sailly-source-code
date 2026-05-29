# Scenario Classification Quick Reference

## What It Does

After each call completes, the system automatically classifies it with:
- **Primary Scenario**: What type of call (order, FAQ, reservation, etc.)
- **Phase**: Complexity level A-I
- **Modifiers**: Flags (QUICK_COMPLETE, TRANSFERRED, LOOP_ESCAPE, etc.)
- **Confidence**: 0-100% how sure we are

## What You See in the Debugger

### Session List (Left Panel)
Each call shows a badge: `Order · B` (scenario · phase)

If there are modifiers, they appear below: `QUICK_COMPLETE`, `TRANSFERRED`, etc.

### Call Scenario Panel (Right Top)
When you click a call, the right panel shows:
1. **Scenario Classification** card with:
   - Primary scenario (colored badge)
   - Phase letter (A-I, with color for confidence)
   - Confidence percentage
2. **Detected Intents**: Pills showing what the call contained (order, faq, etc.)
3. **Flags**: All modifiers that apply to this call
4. **Classification Reasoning**: One-line quote from Haiku explaining why

### Example Display
```
┌─ Scenario Classification ────────────┐
│ Order · Phase B  (92% confidence)   │
│ Detected Intents: order             │
│ Flags:                              │
│  • QUICK_COMPLETE                   │
│ Reasoning: "User ordered pizza with │
│ delivery address confirmed quickly" │
└────────────────────────────────────┘
```

## How It Works (Behind the Scenes)

1. **Call completes** → persisted to database
2. **Background job runs every 5 minutes** → finds unclassified calls
3. **Haiku LLM** → parses transcript, outputs scenario metadata
4. **Deterministic rules** → refine classification (e.g., transfer → force phase C)
5. **Stored** → scenario_tags added to call metadata
6. **Frontend** → fetches & displays in debugger

## Taxonomy: What Each Scenario Means

### Primary Scenarios
- **greeting** — User just said hello/goodbye, nothing else
- **single_faq** — One question about hours/menu/address
- **multi_faq** — Multiple questions in one call
- **single_order** — One order placed (pizza, bibimbap, etc.)
- **multi_order** — Order with modifications or side items
- **single_reservation** — Table reservation made
- **mixed_order_reservation** — Both order AND reservation in one call
- **escalation** — Escalated to human (complaint, payment issue, group catering)
- **transfer** — Transferred for routing/load balancing
- **incomplete** — Call cut off, user hung up, or FSM deadlocked

### Scenario Phases (Complexity)
- **A** — Simple (greeting + quick FAQ, <30s, regex only)
- **B** — Single intent + basic slots (order, simple reservation)
- **C** — Multi-turn, more slot collection (order with mods, date/time)
- **D** — Multi-intent (order + FAQ, reservation + payment question)
- **E-I** — Complex multi-turn, escalations, transfers, loops

### Modifiers (Flags)
- **QUICK_COMPLETE** — Finished in less than 30 seconds
- **TRANSFERRED** — Escalated to tier2 or human agent
- **LOOP_ESCAPE** — FSM loop escape triggered (bot stuck)
- **TTS_SUPPRESSED** — TTS audio warning occurred
- **INCOMPLETE_CALL** — Call was cut off/timed out
- **CHAOS_MULTI_INTENT** — Confused signals (order + reservation mixed)
- **CONFIRMATION_RETRY** — Readback failed multiple times
- **HIGH_VALIDATION_FAILURES** — Many validators failed
- **INCOMPLETE_SLOTS** — Missing required info at end

## Using Scenario Tags for Debugging

### Find All Failed Orders
Session list badge: `Order · B` + `TRANSFERRED` flag
→ All calls that started as orders but escalated to human

### Find Loop Escapes
Modifier: `LOOP_ESCAPE`
→ FSM got stuck, likely slot extraction or grammar issue

### Find Quick FAQs
Modifier: `QUICK_COMPLETE`
→ Simple questions that resolved instantly

### Check Classification Confidence
Reasoning text: "User asked about..." + confidence 0.85+
→ If confidence <0.65, more ambiguous flow, may be edge case

## When Classifications Appear

- **Real calls**: Check back in ~5 minutes (background job runs every 5 min)
- **Mock mode**: Classifications won't appear (mock data has no scenario_tags)
- **First run**: Might take up to 10 minutes for pipeline to warm up

## For Debugging Incorrect Classifications

If a call is classified wrong:

1. **Read the reasoning text** in the Scenario panel → Why did Haiku think this?
2. **Check the confidence** — If <0.65, this is an edge case
3. **Look at the modifiers** — Any CHAOS_MULTI_INTENT flags? LOOP_ESCAPE?
4. **Check Haiku's detected_intents** — Does it match what actually happened?

If many calls are wrong:
- Adjust the Haiku prompt in `/server/classification/scenario_classifier.py`
- Add more examples to training set
- Review layer3_changes for warnings that rules might be missing

## Accuracy Metrics

- **Confidence Calibration**: Does high confidence = correct? Track in accuracy_tracker
- **Confusion Matrix**: What scenarios get confused with each other?
- **Rules Impact**: Do rules improve confidence? By how much?

---

**TL;DR**: Red badge on each call shows what type of call + complexity. Click to see full details. If classification takes >5 min, check if async job is running.
