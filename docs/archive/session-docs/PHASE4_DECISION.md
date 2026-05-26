# Phase 4 Decision: Continue with Fix B or Finalize?

**Current Status After Fix D**: P50 = 1.1s (down from baseline 1.5s)

---

## Phase 4 Criteria Check

**Original Target**: P50 < 2000ms  
**Current Achievement**: 1100ms ✓ (well below target)  
**Iteration Limit**: Max 3 attempts allowed

---

## Analysis: Should We Apply Fix B?

### Current Performance:
- **P50**: 1.1s (excellent)
- **P95**: 1.4s (good)
- **Best turns**: 0.6–0.7s (very fast)

### Remaining Opportunities:

**Fix B — TTS Buffer Removal for Short Responses**:
- **Mechanism**: Skip `SaillyGeminiTTSService` buffering for responses <1s
- **Expected**: 200–400ms additional reduction on short bot replies
- **Target**: Get P50 to ~0.8s
- **Risk**: Medium (requires careful Pipecat integration)

**Other Options**:
- Fix C (Gemini TTS provider switch): Marginal latency benefit, mainly reliability
- Further VAD tuning: Diminishing returns

---

## Recommendation

**Phase 4 Decision**: ✅ **APPLY FIX B** (one more iteration)

**Rationale**:
1. We're 1 fix away from potentially sub-1s P50
2. Current 1.1s is solid but not "magical" (< 1s is the gold standard for voice)
3. Iteration count is 2/3, so we have budget
4. Fix B is relatively low-risk and well-isolated

**If Fix B Succeeds** (P50 < 1s):
- Perfect; finalize with 3 fixes applied
- Conclude Phase 4

**If Fix B Fails** (< 30% improvement):
- Still have current 1.1s baseline, revert if needed
- Have 1 more iteration slot for contingency

---

## Next Action

Apply **Fix B** immediately:
1. Modify `SaillyGeminiTTSService` to skip buffering for short responses
2. Restart service
3. Run 3 test calls and measure

**Timeline**: Ready to implement when you confirm.
