# Sailly — Full Call Analysis Report

## Call ID: `demo-7bba699665ed` (Example: How a Filled Report Looks)
_Generated: 2026-04-25 | Analyst: Cursor Agent | Source: DB + journalctl logs_

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-7bba699665ed` |
| **Channel** | browser_demo |
| **Started** | 2026-04-25 20:30:15 UTC |
| **Ended** | 2026-04-25 20:33:42 UTC |
| **Duration** | **207 seconds (3:27 min)** |
| **Total DB Turns** | 6 |
| **Outcome** | `order_completed` |
| **Quality Score** | 8.5 / 10 |
| **Avg Latency** | 1847ms |
| **Was Escalated** | No |
| **Order Completed** | ✓ Yes |

### Pipeline Configuration (from service startup logs)

```
STT:  DeepgramSTTService (Nova-3, de keywords: Bibimbap, Bulgogi, Kimchi Jjigae, Tteokbokki, Japchae, Mandu, Tofu Jjigae, Mochi-Eis …)
VAD:  Silero VAD → SmartTurn v3.2 (local ONNX)
LLM:  gemini-2.5-flash (max_output_tokens: 20000)
TTS:  SaillyGeminiTTSService (Kore, cascade_speaking_rate=2.0 AFTER PR-15 FIX)
SlotExtractor: gemini-2.5-flash, budget T0=1.6s (2× greeting), T1+=0.4s
ValidationRegistry: enabled (background)
TTS Conditioning: enabled (Phase 2, adaptive mood detection, 2.0x global multiplier)
BargeIn: enabled after greeting completes
Circuit Breaker: Maps & SMS with exponential backoff
Rate Limiting: [DOBOO] - 3 calls/hour, overrides from configs/rate_limit_overrides.txt
Pipeline order: Input → STT → STTWatchdog → STTConfidenceTracker → SilenceReprompt → BargeInHandler → BrainService → ToolsBroadcaster → TTS → TTSStreamWatchdog → Output
```

---

## 2. Per-Turn Breakdown (DB + Logs)

### T0 — Greeting (bot-initiated, before caller speaks)
```
Time:     20:30:15 → 20:30:19
TTS-COND: situation=greeting_first mood=neutral rate=200% tag=[warm] ← NEW: 2.0x from PR-15
Bot:      "Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. 
           Wie kann ich Ihnen heute helfen?"
Duration: ~4s
BARGE_IN: enabled after greeting complete at 20:30:19
Cost:     Gemini: €0.002 | TTS: €0.001 | Total: €0.003
Tokens:   prompt_in=156 prompt_out=28 total=184
```

**Observability Metrics (PR-15 Deployment):**
- ✓ Speaking rate: 2.0x (max per Gemini spec, from 1.5x)
- ✓ Global multiplier: 2.0x (from 1.5x)
- ✓ Cost tracked: €0.003 in google_turn_metrics
- ✓ TTS first byte latency: 180ms

---

### T1 (DB turn_number=1) — Order Intent + Delivery Address
```
Time:         20:30:19 → 20:30:52
STT→Brain:    985ms
Brain→TTS:    1230ms
TTS chunk:    150ms
DB latency:   total=2365ms, llm=1230ms
Node:         order_disambiguation
TTS-COND:     situation=info_neutral mood=relaxed rate=150% tag=[friendly]
Tools called: [get_menu]
Validation:   {dish_name: validated, delivery_address: validated}
Error codes:  (none)
```

**Caller utterance (full):**
```
"Ja, ich möchte einen Bulgogi zur Lieferung auf die Friedrichstraße 20 in Bonn bestellen."
```
> 2 slots given: dish_name (Bulgogi), delivery_address (Friedrichstraße 20, Bonn)

**What happened internally (from logs):**
```
[SLOT_EXTRACT]  dish_name='Bulgogi' (confidence: 0.98)
                delivery_address='Friedrichstraße 20, Bonn' (confidence: 0.96)
[VALIDATION]    dish_name → PASS (in menu), delivery_address → PASS (valid format)
[TOOLS_CALLED]  get_menu (price fetch)
[POLICY_CHECK]  Layer 3 policy pass ✓ (no hallucination, no blocked tools)
[AUDIT_LOG]     Tool: get_menu | Status: ok | Latency: 45ms | Result: 99 menu items retrieved
[GATED_TOOLS]   create_order check: required_slots={dish_name, quantity, delivery_address}
                → dish_name=✓, quantity=❌, delivery_address=✓ → CANNOT EXECUTE YET
```

**Bot response (DB):**
```
"Gerne! Ein Bulgogi zur Lieferung auf die Friedrichstraße 20 in Bonn. 
Wie viele möchten Sie denn?"
```

**Latency Breakdown (PR-5):**
| Component | Latency | Notes |
|-----------|---------|-------|
| STT (Deepgram) | 985ms | p50 ~1000ms |
| LLM (Gemini) | 1230ms | p50 ~540ms, long due to menu lookup |
| Tools | 45ms | get_menu latency captured |
| TTS (Gemini) | 150ms | cache miss on new phrase |
| **Total Turn** | **2365ms** | Above average but acceptable |

**Cost Breakdown (PR-4):**
| Component | Tokens | Cost |
|-----------|--------|------|
| Gemini LLM | 287 in / 34 out | €0.009 |
| Deepgram STT | 12.3s duration | €0.003 |
| TTS Synthesis | 156 chars | €0.002 |
| **Turn Total** | | **€0.014** |

**✅ ISSUES FOUND:**
None ✓ — Perfect turn execution

---

### T2 (DB turn_number=2) — Quantity Specified
```
Time:         20:30:52 → 20:31:03
STT→Brain:    1012ms
Brain→TTS:    890ms
TTS chunk:    95ms
DB latency:   total=1997ms, llm=890ms
Node:         order_confirmation
TTS-COND:     situation=confirm_success mood=neutral rate=150% tag=[cheerful]
Tools called: [create_order, send_sms]
Validation:   {quantity: validated}
Error codes:  (none)
```

**Caller:** `"Zwei bitte."`

**What happened internally (from logs):**
```
[SLOT_EXTRACT]  quantity='2' (confidence: 0.99)
[VALIDATION]    quantity → PASS (valid range 1-10)
[GATED_TOOLS]   create_order check: ALL REQUIRED SLOTS MET ✓
                → Can execute create_order
[TOOLS_CALLED]  create_order (order committed), send_sms (confirmation sent)
[AUDIT_LOG]     Tool: create_order | Status: ok | Latency: 234ms 
                Params: {dish: "Bulgogi", qty: 2, addr: "Friedrichstraße 20, Bonn", phone: "..."}
[AUDIT_LOG]     Tool: send_sms | Status: ok | Latency: 189ms
```

**Bot response:**
```
"Perfekt! Ich habe Ihre Bestellung für 2× Bulgogi zur Lieferung auf die 
Friedrichstraße 20 in Bonn aufgenommen. Sie erhalten gleich eine SMS-Bestätigung."
```

**Latency Breakdown (PR-5):**
| Component | Latency | Notes |
|-----------|---------|-------|
| STT (Deepgram) | 1012ms | Short phrase, normal latency |
| LLM (Gemini) | 890ms | Tool execution latency included |
| Tools | 423ms | create_order (234ms) + send_sms (189ms) |
| TTS (Gemini) | 95ms | Cache hit on similar phrasing |
| **Total Turn** | **2420ms** | Tool execution dominant |

**Cost Breakdown (PR-4):**
| Component | Tokens | Cost |
|-----------|--------|------|
| Gemini LLM | 156 in / 42 out | €0.006 |
| Deepgram STT | 5.2s duration | €0.001 |
| TTS Synthesis | 89 chars | €0.001 |
| **Turn Total** | | **€0.008** |

**✅ ISSUES FOUND:**
None ✓ — Successful order committed

---

## 3. Pipeline Stage Evaluation

### Per-Turn Stage Health

| Turn | VAD | STT | Brain Ctx | LLM | Tools | Guardian | Tool Exec | Response | TTS | Audio | DB | Status |
|------|-----|-----|-----------|-----|-------|----------|-----------|----------|-----|-------|-----|--------|
| 0 | ok | ok | ok | ok | ok | ok | N/A | ok | ok | ok | ok | ✓ |
| 1 | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ✓ |
| 2 | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ✓ |
| 3 | ok | ok | ok | ⚠️ | ok | ok | ok | ok | ok | ok | ok | ⚠️ |
| 4 | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ✓ |
| 5 | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ok | ✓ |

**Legend:** ok = normal | ⚠️ = degraded (>3x normal latency or confidence <0.7) | ✗ = fail (error or timeout)

### Overall Pipeline Health
- **Stages: ok / degraded / fail** = 71 / 1 / 0
- **Calls with ≥1 FAIL stage:** 0
- **Calls with ≥1 DEGRADED stage:** 1 (Turn 3 LLM spike)

---

## 4. Tool Execution & Audit Trail (PR-3)

### Tools Called Per Turn

| Turn | Tool Name | Latency | Result | Error Code | Params |
|------|-----------|---------|--------|-----------|--------|
| 0 | (none) | 0ms | N/A | N/A | N/A |
| 1 | get_menu | 45ms | ok | N/A | {search: "*"} |
| 2 | create_order | 234ms | ok | N/A | {dish: "Bulgogi", qty: 2, addr: "..."}|
| 2 | send_sms | 189ms | ok | N/A | {phone: "+49...", msg: "..."} |

### bot_tool_audit_log Summary (PR-3 Implementation)

```sql
SELECT tool_name, COUNT(*) as count, SUM(latency_ms) as total_latency
FROM bot_tool_audit_log
WHERE call_id = 'demo-7bba699665ed'
GROUP BY tool_name
ORDER BY total_latency DESC;
```

**Results:**
- **create_order:** 1 call, 234ms total latency, ✓ success
- **send_sms:** 1 call, 189ms total latency, ✓ success
- **get_menu:** 1 call, 45ms total latency, ✓ success
- **Total tool execution:** 468ms across 3 tools

---

## 5. Observability Metrics (PR-4, PR-5)

### Token Economy & Cost (PR-4)

**Call-Level Summary:**
| Metric | Value |
|--------|-------|
| **Total Gemini Tokens In** | 1245 |
| **Total Gemini Tokens Out** | 312 |
| **Total Extract Tokens In** | 156 |
| **Total Extract Tokens Out** | 28 |
| **Total Tokens** | 1741 |
| **Gemini Cost** | €0.045 |
| **Deepgram Cost** | €0.008 |
| **TTS Cost** | €0.006 |
| **Total Call Cost** | €0.059 |
| **Cost per turn (avg)** | €0.010 |

### Latency Instrumentation (PR-5)

**Turn Latencies (ms):**

| Turn | STT | LLM | Tool | TTS | Total |
|------|-----|-----|------|-----|-------|
| 0 | — | 450 | 0 | 180 | 630 |
| 1 | 985 | 1230 | 45 | 150 | 2410 |
| 2 | 1012 | 890 | 423 | 95 | 2420 |
| 3 | 1045 | 3890 | 0 | 120 | 5055 ← degraded |
| 4 | 998 | 545 | 0 | 110 | 1653 |
| 5 | 987 | 530 | 0 | 95 | 1612 |

**Statistics:**
- **STT p50:** ~1000ms ± 15ms (stable)
- **LLM p50:** ~890ms (higher due to tool execution)
- **TTS p50:** ~127ms (mix of cache hits/misses)
- **Worst turn:** 5055ms (Turn 3 LLM spike)

### Error Codes (PR-4)

From `_turn_error_codes` set in adk_turn_processor:

| Error Code | Count | Turns |
|-----------|-------|-------|
| (none) | 0 | — |

---

## 6. TTS Conditioning & Speech Synthesis (PR-15 Update)

### Speaking Rates Applied (NEW in PR-15)

**Configuration:**
- **GREETING_FIRST rate:** 2.00 (was 1.00)
- **GLOBAL_SPEED_MULTIPLIER:** 2.0 (was 1.5)
- **Final greeting rate:** 2.0x (clamped to Gemini max)

**Per-Turn Rates:**

| Turn | Situation | Mood | Situation Rate | Mood Mul | Final Rate | Comments |
|------|-----------|------|---|---|---|---|
| 0 | greeting_first | neutral | 2.0x | 1.0x | **2.0x** | Fast, energetic greeting |
| 1 | info_neutral | relaxed | 1.0x | 1.0x | **1.0x** | Natural tempo, caller calm |
| 2 | confirm_success | neutral | 1.0x | 1.0x | **1.0x** | Cheerful tone, normal speed |
| 3 | info_neutral | neutral | 1.0x | 1.0x | **1.0x** | Informational |
| 4 | farewell_warm | relaxed | 0.98x | 1.0x | **0.98x** | Warm goodbye, slightly slower |

### TTS Anomaly Detection

- **Low threshold:** 0.30 (too silent)
- **High threshold:** 3.00 (runaway)
- **Anomalies detected:** 0
- **Fallback to silence:** 0

---

## 7–12. [Additional Sections...]

[Abbreviated for this example]

---

## 13. Summary & Conclusion

### Call Metrics

| Metric | Value | Status |
|--------|-------|--------|
| **Total Turns** | 6 | |
| **Successful Turns** | 6 (100%) | ✓ |
| **Failed Turns** | 0 | |
| **Total Cost** | €0.059 | |
| **Avg Latency** | 1847ms | Good |
| **Worst Turn** | 5055ms (T3) | Acceptable |

### Quality Assessment

| Dimension | Grade | Notes |
|-----------|-------|-------|
| **Latency** | B+ | One spike in T3, otherwise consistent |
| **Accuracy** | A | 100% accuracy in slot extraction |
| **Reliability** | A | Zero errors, all tools succeeded |
| **Cost Efficiency** | A | €0.010 per turn is excellent |

### Notable Events

- **Circuit breaker activations:** 0
- **Rate limit hits:** 0
- **TTS anomalies:** 0
- **Policy blocks:** 0
- **Validation failures:** 0

### Recommendations

1. Investigate T3 LLM spike (5.5s) — possibly hitting upstream timeout or backoff
2. Consider increasing LLM timeout budget for complex utterances
3. Monitor STT latency — consistently ~1000ms but could be optimized

---

**Report End**

Generated: 2026-04-25 | System: sailly-browser-demo (Post-Audit PR-15)
Audit Status: All 33 findings ✓ PASS

