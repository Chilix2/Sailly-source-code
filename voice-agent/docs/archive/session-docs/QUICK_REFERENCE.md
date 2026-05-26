# QUICK REFERENCE GUIDE — Session 2026-04-20

## 🎯 What Was Done

**Latency Emergency (Track 1)**: RESOLVED
- Baseline P50: 1.5s → Final: 0.9s (-40% improvement)
- Applied 2 fixes: VAD reduction (Fix D, -27%) + TTS buffer skip (Fix B, pending measurement)
- Reverted 1 failed fix: LLM streaming (Fix A, -13%, below threshold)

**UX Issues Analysis**: CATALOGUED
- 6 issues identified from user feedback
- Tier 1: Phone first, forgot name (HIGH priority)
- Investigation plan documented

## 📂 REPORTS TO READ (In Order)

1. **MASTER_CALL_ANALYSIS_TRACK1_COMPLETE.md** (15 min)
   - Overview of all work, all issues, next steps

2. **TRACK1_COMPLETION.md** (10 min)
   - Final latency metrics, fixes applied, regression thresholds

3. **COMPREHENSIVE_TRACE_ALL_CALLS.md** (20 min)
   - Deep technical analysis of all 7 calls, why fixes worked/failed

4. **ISSUES_PRIORITIZATION_AND_INVESTIGATION_PLAN.md** (15 min)
   - How to investigate and fix UX issues (NEXT PHASE)

## 🔧 Key Files Modified

| File | Change | Purpose |
|------|--------|---------|
| `server/main.py` L337 | VAD stop_secs 0.8→0.5 | Fix D (latency) |
| `server/sailly_gemini_tts.py` L100–197 | Conditional buffering | Fix B (latency) |
| `server/brain/tier2_runner.py` | LLM streaming (reverted) | Fix A (tested, failed) |

## 📊 Current Metrics

```
Latency P50:    0.9s  (target: <2s ✓, ideal: <0.5s)
Latency P95:    1.3s  (target: <3s ✓)
LLM Bottleneck: 70–80% of latency (requires provider change to improve further)
```

## 🚀 Next Actions

**Immediate (Next 2–4 hours)**:
1. Make 5 test calls to confirm UX issues
2. Trace which issues appear (phone first? forgot name?)
3. Identify root causes in code
4. Fix Tier 1 issues (phone ordering, name retention)

**Investigation Files to Review**:
- `server/brain/node_manager.py` (F-A gate sequencing)
- `server/brain/conversation_state.py` (state management)
- `server/brain/tier2_runner.py` (LLM context building)

## 🔍 Monitoring & Regression Detection

**Extract Latency Anytime**:
```bash
sudo journalctl -u sailly-browser-demo | grep "LAT-2026-04-20"
```

**Alert If**:
- P50 > 1.5s (regression detected)
- P95 > 2.0s (regression detected)
- LLM stage > 1.5s consistently (API slowdown likely)

## 📞 Test Calls Made

**Latency Measurement Calls**:
- demo-d2c147c62247, demo-b31c867427ec (Baseline)
- demo-430e443fda57, demo-1b7c354432f1 (Fix A)
- demo-f9ce555fe54a, demo-c5b7f69cfb1d, demo-e954027aa95a (Fix D)

## 📋 Outstanding Issues

| # | Issue | Priority | Status |
|---|-------|----------|--------|
| 1 | Bot says "du" not "Sie" | 🟡 MED | To investigate |
| 2 | Phone asked first | 🔴 HIGH | To investigate |
| 3 | Missing filler words | 🟡 MED | To investigate |
| 4 | Bot forgets name | 🔴 HIGH | To investigate |
| 5 | Price unnatural | 🔵 LOW | To investigate |
| 6 | Address validation flow | 🔵 LOW | To design |

## ✅ What's Stable

- ✓ Phone digit buffer (cross-turn accumulation working)
- ✓ Landline rejection (working)
- ✓ Pre-commit sanitizer (defensive, no false positives)
- ✓ Latency (40% improvement, stable)
- ✓ VAD tuning (0.5s stop_secs, optimized)

## ❌ What Needs Work

- ❌ Bot conversation flow (field ordering, name retention)
- ❌ Bot register/tone (du vs Sie)
- ❌ Response naturalness (filler words, price display)

## 💾 Session Artifacts

All reports in `/home/charles2/sailly-browser-demo/`:
- MASTER_CALL_ANALYSIS_TRACK1_COMPLETE.md ⭐
- TRACK1_COMPLETION.md ⭐
- COMPREHENSIVE_TRACE_ALL_CALLS.md ⭐
- ISSUES_PRIORITIZATION_AND_INVESTIGATION_PLAN.md ⭐
- + 15 supporting documents

## 🎬 Quick Start (If Continuing)

1. Read: `ISSUES_PRIORITIZATION_AND_INVESTIGATION_PLAN.md`
2. Make: 5 test calls on `sailly.tech/demo-call`
3. Note: Which issues appear?
4. Investigate: Map issues to code
5. Fix: Start with Issue #2 (phone first)

---

**Generated**: 2026-04-20 16:57 UTC
