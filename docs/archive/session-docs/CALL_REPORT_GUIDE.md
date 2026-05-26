# Call Analysis Report — Data Collection Guide

## Overview

The comprehensive call analysis report (`CALL_ANALYSIS_FULL_REPORT_demo-*.md`) captures all metrics and checkpoints implemented across PRs 1-15. This guide explains where to find each metric.

---

## Data Sources

### 1. **Call Metadata** (Part 1)
- **Source:** Browser demo UI / WebSocket session
- **Timing:** Captured in browser console when call connects
- **Items to collect:**
  - Call start time: `new Date().toISOString()`
  - Call end time: When disconnect happens
  - Caller phone: From Twilio if available

### 2. **Layer 1 State Management** (Part 2)
- **Source:** `server/brain/layer1/` logs
- **Key variables:** `server.brain.adk_turn_processor.py`
  ```python
  # In _check_stuck_loop():
  is_stuck = server.brain.layer1.turn_control.is_stuck_loop(...)
  
  # Validation registry:
  registry = self.state._validation_registry
  ```
- **To collect per turn:**
  - `state.node_name`
  - `state.turn_idx`
  - Slots validated (count)
  - Gated tools checked (count)

### 3. **Layer 2 LLM & Tokens** (Part 3)
- **Source:** `server/brain/tier2_runner.py` + `server/brain/adk_turn_processor.py`
- **Token capture points:**
  ```python
  # In adk_turn_processor._exec_turn():
  usage = self._gemini_runner._last_stream_usage_metadata
  prompt_tokens_in = usage.prompt_token_count
  prompt_tokens_out = usage.candidates[0].token_count
  
  # Slot extraction:
  extract_usage = self._slot_extractor._last_usage_metadata
  extract_tokens_in = extract_usage.prompt_token_count
  extract_tokens_out = extract_usage.candidates[0].token_count
  ```

### 4. **Layer 3 Policy** (Part 4)
- **Source:** `server/brain/layer3/policy.py`
- **Logs:** Look for `[POLICY]` lines in debug logs
- **Items:**
  ```python
  # From policy.check():
  blocked_tools = ...
  hallucination_hits = ...
  safety_violations = ...
  ```

### 5. **Tool Execution & Audit Trail** (Part 5)
- **Source:** PostgreSQL `bot_tool_audit_log` table
- **Query:**
  ```sql
  SELECT tool_name, executed_at, result_status, error_code 
  FROM bot_tool_audit_log 
  WHERE call_id = 'demo-7bba699665ed'
  ORDER BY executed_at;
  ```
- **Tool latencies:** Captured in each audit log entry
- **State mutations:** Tracked in `result` field

### 6. **Observability Metrics** (Part 6) — **MOST IMPORTANT**
- **Source:** `server/brain/adk_turn_processor.py` + `server/brain_service.py`

#### Cost Tracking
- **Gemini cost:** Calculate from token count
  ```python
  # In _build_turn_metrics_extra():
  cost = calculate_gemini_cost(
    prompt_tokens_in,
    prompt_tokens_out,
    model="gemini-2.5-flash"
  )
  ```
- **STT cost:** Deepgram pricing per minute
- **TTS cost:** Gemini Cloud TTS per character

#### Turn Metrics Data
- **Source:** `google_turn_metrics` PostgreSQL table
- **Query:**
  ```sql
  SELECT 
    turn_idx,
    cost_eur,
    prompt_tokens_in,
    prompt_tokens_out,
    extract_tokens_in,
    extract_tokens_out,
    error_codes,
    tts_first_byte_at,
    tool_durations,
    turn_duration_ms
  FROM google_turn_metrics
  WHERE call_id = 'demo-7bba699665ed'
  ORDER BY turn_idx;
  ```

#### Error Codes (PR-4)
- **Source:** `_turn_error_codes` set in `adk_turn_processor`
- **Logged as:** `error_codes` JSONB column in `google_turn_metrics`
- **Possible codes:**
  ```python
  "ERR_VALIDATION_FAILED"
  "ERR_CIRCUIT_BREAKER_OPEN"
  "ERR_TOOL_EXECUTION_FAILED"
  "ERR_RATE_LIMITED"
  "ERR_DEPRECATED_TOOL"
  "ERR_POLICY_BLOCKED"
  ```

### 7. **TTS Conditioning & Speech** (Part 7) — **NEWLY UPDATED**
- **Source:** `server/brain/tts_conditioning.py`
- **Speaking rates applied:**
  - Base greeting: 2.0x (GREETING_FIRST.rate)
  - Global multiplier: 2.0x (GLOBAL_SPEED_MULTIPLIER)
  - Per-turn rate: Logged as `[TTS-COND]` in brain logs
  ```
  [TTS-COND] situation=greeting_first mood=neutral rate=200% tag=[warm] global_mul=2.0
  ```
- **TTS anomalies:**
  ```python
  # In sailly_gemini_tts.py:
  ratio = audio_bytes / expected_bytes
  if ratio < 0.30 or ratio > 3.00:
    # Anomaly detected
  ```

### 8. **Circuit Breaker** (Part 8)
- **Source:** `server/core/resilience/breakers.py`
- **Track:**
  - Maps API calls and breaker state
  - SMS API calls and breaker state
  - 429 retries and backoff attempts
- **Log pattern:** `[BREAKER]` lines

### 9. **Tenant Configuration** (Part 9)
- **Source:** `configs/tenants/doboo.yaml` + CI guard verification
- **Items:**
  - Greeting line text
  - Farewell text
  - Hardcoded string detection result

### 10. **Rate Limiting** (Part 10)
- **Source:** `server/brain/rate_limit.py` + `configs/rate_limit_overrides.txt`
- **Logs:** Look for `rate_limit_*` log entries
- **Check:** Caller phone in override list (yes/no)

### 11. **Health Endpoints** (Part 11)
- **Source:** `/health` and `/ready` responses captured during call
- **Query during call:**
  ```bash
  curl http://localhost:8080/health
  curl http://localhost:8080/ready
  ```

### 12. **Callback Queue** (Part 12)
- **Source:** PostgreSQL `callback_queue` table
- **Query:**
  ```sql
  SELECT * FROM callback_queue 
  WHERE call_id = 'demo-7bba699665ed';
  ```

### 13. **Test Results** (Part 13)
- **Source:** Run regression tests
  ```bash
  pytest server/tests/audit/test_finding_regressions.py -v
  ```
- **All 33 findings should PASS**

---

## How to Generate a Full Report

### Quick Way (Manual Data Entry)
1. Open the template: `CALL_ANALYSIS_FULL_REPORT_demo-*.md`
2. During/after the live demo, fill in `[...]` placeholders
3. Pull data from logs, database queries, and API responses

### Automated Way (Query Script)
```python
# Example: Query google_turn_metrics for a call
import asyncpg
import asyncio

async def get_call_metrics(call_id):
    conn = await asyncpg.connect("postgresql://localhost/sailly")
    rows = await conn.fetch(
        "SELECT * FROM google_turn_metrics WHERE call_id = $1 ORDER BY turn_idx",
        call_id
    )
    await conn.close()
    return rows
```

### Browser Console Way
The browser demo UI can be enhanced to log metrics:
```javascript
// In browser during call
console.log({
  callId: window.callId,
  startTime: window.callStart,
  currentTurn: window.currentTurn,
  metrics: window.turnMetrics
});
```

---

## Key Metrics to Always Capture

### Per-Turn Minimum
- Turn index
- Turn start/end time
- LLM response time
- Tokens in/out
- Tool calls made
- Error codes

### Per-Call Minimum
- Total turns
- Total cost (€)
- Total tokens
- Success rate (%)
- Notable events

### Production Checkpoints
- Circuit breaker activations
- Rate limit hits
- Anomalies detected
- Policy blocks
- Health status

---

## Example: Filled Report Structure

```markdown
## Part 2: Layer 1 (Turn Control & State Management)

### Per-Turn Decisions

#### Turn 0 (Greeting)
- Turn Index: 0
- Node Name: greeting
- Conversation State: fresh_call=true, slots_validated=0
- Decision Made: continue to turn 1
- Stuck Loop Detection: false

#### Turn 1 (Order Intent)
- Turn Index: 1
- Node Name: order_disambiguation
- Conversation State: slots_validated=1 (dish_name)
- Decision Made: continue to turn 2
- Stuck Loop Detection: false

### Validation Registry State
- Total slots validated: 3 (dish_name, quantity, delivery_address)
- Gated tools checked: 2 (create_order, create_reservation)
- Required slots met: create_order (3/3), create_reservation (2/3)
```

---

## File Naming Convention

Use this pattern for call reports:
- `CALL_ANALYSIS_FULL_REPORT_demo-{call_id}.md` — Comprehensive
- `CALL_ANALYSIS_SUMMARY_demo-{call_id}.md` — Quick summary
- `CALL_TRACE_DETAILED_demo-{call_id}.md` — Raw trace logs

---

## Next Steps

1. **For current demo session:** Fill in the template with live data
2. **For future calls:** Automate metric collection via logging hooks
3. **For production:** Set up daily call analysis reports

