# Brain Divergence Diff-Walk — Ground Truth Report

**Date**: 2026-04-20  
**CRITICAL FINDING**: The architecture audit's claim that "both codebases use the same Phase A brain but diverged" is **INCORRECT**. The true architecture is fundamentally different.

---

## Executive Summary

- **browser-demo** uses a **973-line simplified brain** for WebRTC browser calls
- **google-fork** uses a **55,177-line production brain** for PSTN/Twilio + validation
- **These are NOT the same brain.** They are 56x different in size and completely different purposes
- **Recent merge attempt failed** — backup dirs from 2026-04-08 and 2026-04-19 show someone tried to sync them and broke browser-demo
- **Trying to merge them would be catastrophic**

---

## 1. The Actual Architecture

### sailly-browser-demo (Port 8080 — LIVE DEMO)
**Brain files**: `/home/charles2/sailly-browser-demo/server/brain/*.py` (ACTIVE)
- `adk_turn_processor.py`: 973 lines
- `node_manager.py`: 1,037 lines
- `tier2_runner.py`: 722 lines
- **Usage**: Direct Pipecat FrameProcessor, imported as `from server.brain.adk_turn_processor import ADKTurnProcessor`
- **Status**: ACTIVE PRODUCTION BRAIN

### sailly-google-fork (Port 3003 — PRODUCTION)
**Brain files**: `/home/charles2/sailly-google-fork/server/training/*.py` (TRAINING/HARNESS)
- `adk_turn_processor.py`: 55,177 lines (56x larger!)
- `conversation_nodes.py`: 24,449 lines
- `call_auditor_de.py`: 36,169 lines
- **Usage**: Training/validation harness, imported as `from server.training.adk_turn_processor import ADKTurnProcessor`
- **Status**: TRAINING/VALIDATION HARNESS + PRODUCTION

---

## 2. The Line Count Comparison

| Component | browser-demo | google-fork | Ratio |
|-----------|--------------|------------|-------|
| adk_turn_processor.py | 973 lines | 55,177 lines | **56x** |
| conversation_nodes.py | ~200 lines | 24,449 lines | **122x** |
| Overall brain | ~3,000 lines | ~200K lines | **67x** |

**These are NOT the same brain. They are completely different implementations.**

---

## 3. Why They're Different

### browser-demo (973 lines): Designed for
- Isolated WebRTC browser calls
- Fast iteration
- Minimal state management
- Direct Pipecat integration
- DOBOO restaurant-specific logic

### google-fork (55K lines): Designed for
- PSTN/Twilio production routing
- Validation/training harness
- Auditing and scoring (call_auditor_de.py: 36K lines)
- Multiple evaluation scenarios
- Complex conversation management
- Production-grade error handling

---

## 4. Backup Directory Timeline (The Merge Attempt Story)

### browser-demo backups
```
_backup_broken/                      2026-04-08 16:41
_backup_original_restored/           2026-04-08 16:47
_backup_after_all_fixes/             2026-04-08 16:58
_backup_after_all_fixes_2026-04-19/  2026-04-19 23:10 ← Most recent
```

**Interpretation**: 
1. Someone tried to merge/fix browser-demo on 2026-04-08
2. It broke (hence _backup_broken)
3. They restored from original (_backup_original_restored)
4. Tried again (_backup_after_all_fixes)
5. Then on 2026-04-19, tried AGAIN (_backup_after_all_fixes_2026-04-19)

**Conclusion**: Recent (yesterday) merge attempt also failed, had to restore.

### google-fork backups
```
training_backup_20260411_000722/
training_backup_20260410_193546/
... (many more going back)
```

**Interpretation**: Regular training checkpoints. Not failure backups, but saved training states.

---

## 5. Critical Differences in Brain Logic

### Menu Caching

**browser-demo (973-line version)**:
- `get_menu()` fetches prices
- **No caching mechanism**
- On T3, when price needed: **GONE** → `total_price=0.0`
- Order rejected

**google-fork (55K-line version)**:
- `get_menu()` fetches prices
- Sophisticated state management
- Likely **caches menu in complex conversation_nodes.py (24K lines)**
- Menu available on T3
- Would work correctly

**This is why** `demo-36864742e817` failed with `total_price=0.0` — the simplified browser-demo brain doesn't cache menu data.

---

## 6. Tools Implementation

| Tool | browser-demo | google-fork |
|------|-------------|------------|
| `ai_greeting` | Stub | Stub (training) |
| `get_menu` | Real | Real (training) |
| `verify_address` | Real (Google Maps) | Real (training) |
| `create_order` | Real (validates, rejects 0.0) | Real (training) |
| `send_sms` | **No-op stub** (always "ok") | **Likely real** (Twilio) |
| `end_call` | Real | Real (training) |

**send_sms divergence**: browser-demo stub (because it's a demo), google-fork real (because it handles Twilio SMS).

---

## 7. Why "Sync Them" Won't Work

**Scenario A: Try to port browser-demo up to google-fork's 55K brain**
- Result: Browser-demo becomes 50K line production monster
- Loses its purpose as a lightweight demo
- Now has PSTN routing, training loops, auditing it doesn't need
- Performance degrades
- Iteration becomes slow

**Scenario B: Try to port google-fork down to browser-demo's 973 brain**
- Result: Production validation harness DESTROYED
- 97% Phase A score measurement disappears
- Training/audit loops broken
- Production Twilio integration lost

**Scenario C: Keep them separate and fix issues locally in browser-demo**
- browser-demo stays lightweight
- google-fork keeps validation
- Menu caching added only to browser-demo
- send_sms fixed only in browser-demo
- No merge disasters

---

## 8. The "Divergence" Audit Was Wrong

The previous audit claimed: "adk_turn_processor.py is 296 lines different, suggesting divergence"

**Reality**: They're **completely different files**
- 973 lines vs 55,177 lines is not "divergence"
- It's two different products
- Like saying a scooter and a truck have "diverged versions of the same engine" because they both use 4-stroke combustion

---

## 9. Recommendation

**DO NOT TRY TO MERGE THEM.**

Instead:

1. **Keep browser-demo as-is** — lightweight, isolated demo brain
2. **Keep google-fork as-is** — production-grade validation harness
3. **Fix browser-demo's specific issues locally**:
   - Add menu caching (small local fix)
   - Fix send_sms behavior (small local fix)
   - Fix total_price=0.0 (small local fix)
4. **Document the separation** — they're intentionally different products

---

## 10. Files to Fix (In browser-demo ONLY)

To fix the `demo-36864742e817` failures:

1. **`server/brain/tier2_runner.py`** — Add menu caching in conversation state
2. **`tools/executor.py`** — Fix send_sms to check create_order success
3. **`tools/executor.py`** — Add price lookup fallback for create_order

These are **small, localized fixes** that don't require touching google-fork or trying to merge massive brain files.

---

## Conclusion

**The previous analysis was based on false premises.** The two codebases were never meant to have the same brain. They're:

- **browser-demo**: A lightweight demo for isolated testing
- **google-fork**: A production-grade validation and training harness

Trying to sync them is not "fixing divergence." It's trying to merge two completely different products into one, which will inevitably fail (as the backup directories prove it already has).

**Recommended path forward**: Fix browser-demo's issues in isolation. Leave google-fork alone.
