# Fix A Revert & Fix D Applied — Summary

**Timestamp**: 2026-04-20 16:43 UTC

## Fix A Assessment

**Status**: ❌ **REVERTED** — Failed to achieve ≥30% reduction threshold

### What We Found:
- **Expected**: LLM streaming → first token in 0.2-0.4s → TTS starts early → 60%+ reduction
- **Actual**: First token arrives 30-40% faster (0.7-2.5s), but **total brain→tts_text_pushed unchanged** (still 0.9-2.5s)
- **Root Cause**: `process_turn()` awaits **full generator completion** before pushing TTS frame
  - Architecture blocks on final token, not first token
  - Streaming benefits wasted

### Improvement Measured:
- Turns 1-9: **-13% average** (1.5s → 1.3s)
- **Status**: Below 30% threshold, so revert and try next fix

---

## Fix D Implementation

**Status**: ✅ **DEPLOYED** — Service restarted at 2026-04-20 16:43:13 UTC

### What We Changed:
- **File**: `server/main.py` line 337
- **Change**: Silero VAD `stop_secs` **0.8 → 0.5**
- **Mechanism**: Cuts VAD silence floor from 800ms to 500ms after user stops speaking
- **Expected Impact**: ~300ms/turn latency reduction

### Why This Works:
- VAD floor is **independent** of LLM/TTS speed
- Cutting it by 300ms = guaranteed floor reduction
- Low-risk change (tuning parameter only)
- No architectural refactoring needed

### Expected New P50 Latency:
- **Baseline (Turn 1-3 avg)**: ~1.5s → **~1.2s** (300ms saved on VAD floor)
- **Target**: P50 < 1.2s (achieves 40% of the way to <1s ideal)

---

## Next Steps

**Immediate**: Run 3 consecutive 3-turn test calls to measure Fix D impact
- **Expected**: 25-35% reduction in total turn latency
- **Goal**: Verify Fix D meets ≥30% threshold
- **Timeline**: When you're ready, make 3 calls on `sailly.tech/demo-call`

**If Fix D Succeeds** (≥30% reduction):
- Proceed with Phase 4 iteration check
- If p50 still > 2000ms: apply third fix (TTS provider switch or other)

**If Fix D Fails** (< 30% reduction):
- Data will show where latency remains
- Fall back to Fix C (Gemini TTS provider switch) or architectural refactor

---

**Current Status**: Awaiting 3 test calls to measure Fix D effectiveness.
