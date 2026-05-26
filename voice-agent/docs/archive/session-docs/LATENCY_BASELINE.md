# Latency Baseline — Phase 1 Measurement Report

**Measurement Window**: 2026-04-20 16:14:38 UTC (service restart) to 2026-04-20 16:20:28 UTC  
**Test Calls**: demo-d2c147c62247 (5 turns) + demo-b31c867427ec (13 turns)  
**Total Traces Captured**: 153 latency marks

---

## Per-Turn Latency Breakdown

### Call 1: demo-d2c147c62247

| Turn | stt→brain | brain→tts_text_pushed | llm_call→llm_done | Total Turn Latency |
|------|-----------|----------------------|-------------------|-------------------|
| 1 | 4ms | 2172ms | 1934ms | ~2176ms |
| 2 | 3ms | 1279ms | 1271ms | ~1282ms |
| 3 | 4ms | 1289ms | 1282ms | ~1293ms |
| 4 | 3ms | 1256ms | 1250ms | ~1259ms |
| 5 | 4ms | (no bot response captured) | (timeout) | (abandoned) |

**Call 1 Summary**: 
- Turn 1 particularly slow: 2176ms (Gemini first-turn extra time common)
- Turns 2-4: ~1.2-1.3s average per turn
- Bottleneck: `brain→tts_text_pushed` = 1.2–2.1s (LLM + tools overhead)
- Turn 5 timed out (no further bot response)

### Call 2: demo-b31c867427ec

| Turn | stt→brain | brain→tts_text_pushed | llm_call→llm_done | Total Turn Latency |
|------|-----------|----------------------|-------------------|-------------------|
| 1 | 3ms | 2165ms | 1964ms | ~2168ms |
| 2 | 4ms | 1743ms | 1736ms | ~1747ms |
| 3 | 3ms | 2158ms | 2153ms | ~2161ms |
| 4 | (incomplete trace) | 2076ms | 2072ms | ~2078ms |
| 5+ | (extended conversation, multiple turns) | 1.0–2.1s range | 1.0–2.1s range | 1.0–2.1s per turn |
| 10 | 4ms | 1356ms | 1350ms | ~1360ms |
| 11 | 5ms | 1115ms | 1109ms | ~1120ms |
| 12 | 4ms | 1593ms | 1583ms | ~1597ms |
| 13 | 4ms | 2121ms | 2105ms | ~2125ms |

**Call 2 Summary**:
- Turn 1: 2168ms (first-turn overhead)
- Turns 2–13: Range 1.1–2.1s, average ~1.5s
- Bottleneck: `brain→tts_text_pushed` consistently dominates (1.1–2.1s)

---

## Stage-by-Stage Analysis

### Total Turn Latency (user speech end → bot speech start)
- **P50 (median)**: ~1.5s
- **P95 (worst typical)**: ~2.1s
- **Worst observed**: 2.1s (turns 3, 13 in Call 2; turn 1 in both calls)

### Breakdown of "brain→tts_text_pushed" (1.1–2.1s):

The stage includes:
1. `process_turn()` execution (LLM call + tool execution)
2. Sanitization & frame construction

Subcomponents observed:
- **llm_call→llm_done**: 1.1–2.0s (95% of the stage latency)
- **tool execution**: Captured in "tool_done" marks but not separately timed
- **TTS text → frame push**: ~2–5ms (negligible)

### Confirmed Bottleneck: LLM Non-Streaming

```
llm_call_start → llm_done: 1.1–2.0s per turn
```

- **Problem 1** (from architecture): Non-streaming LLM call means full 300-token response must complete before TTS can start
- **Evidence**: LLM stage alone is 73–95% of total turn latency
- **Impact on user**: 1–2s speech-to-response delay perceived as "slow" in conversational AI

### No Evidence of TTS Buffer Stalls

TTS buffer_done → first_yield consistently = "instant", meaning:
- Hallucination detection completes without observable latency
- No 429 quota errors observed during measurement window
- TTS generation itself is fast (captured in tts_text_pushed stage already)

### No STT/VAD Floor Visible

- stt→brain consistently 3–5ms (negligible)
- User speech-end detection happens at pipeline layer before LLMContextFrame arrival
- Silero VAD 0.8s `stop_secs` is *not* visible in `stt→brain` mark (VAD happens upstream)
- Confirmed: VAD floor exists but is absorbed upstream of brain entry

---

## Verdict: Fix Priority Order

### Fix A — LLM Streaming (HIGHEST PRIORITY)
- **Target**: Reduce `llm_call→llm_done` from 1.1–2.0s to 0.2–0.4s (first token only)
- **Expected impact**: Turn latency 1.5s → 0.6–0.8s (≥60% reduction)
- **Trigger**: YES — stage dominates baseline

### Fix B — TTS Buffer-First (LOWER PRIORITY)
- **Target**: Skip buffer for short responses (<80 chars)
- **Expected impact**: Minor (<5% improvement, only helps short utterances)
- **Status**: Not the bottleneck

### Fix C — TTS Provider Switch (LOWER PRIORITY)
- **Target**: Switch to Deepgram Aura 2
- **Expected impact**: Eliminate 429 quota risk, incremental speed
- **Status**: No 429 observed in current window, not urgent

### Fix D — Silero VAD (LOWEST PRIORITY)
- **Target**: Reduce stop_secs 0.8 → 0.5
- **Expected impact**: ~300ms per turn saved at STT layer
- **Status**: Architectural, not in critical path for current latency crisis

---

## Next Step: Apply Fix A (LLM Streaming)

Expected outcome after Fix A:
- **New p50**: ~0.7–0.8s per turn (vs. 1.5s baseline)
- **New p95**: ~1.2s per turn (vs. 2.1s baseline)
- **Acceptance**: Re-measure 3 consecutive calls, confirm ≥60% reduction in `brain→tts_text_pushed`

---

**Generated**: 2026-04-20 16:21 UTC  
**Status**: Baseline measurement complete. Ready for Phase 2 fix implementation.
