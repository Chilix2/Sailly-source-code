# Debugger API Schema Analysis — Executive Summary

**Analysis Date:** 2026-05-29  
**Endpoint:** `GET /api/admin/call/{call_sid}/turns`  
**Status:** ⚠️ **Critical Type Mismatch Identified**

---

## Quick Facts

| Metric | Value |
|--------|-------|
| **TurnRow fields returned by API** | 30 |
| **ExecutionSpan fields per span** | 13 |
| **Fields in TypeScript TurnRow** | 39 |
| **Mismatch: Extra in TS** | 9 fields |
| **Mismatch: Missing in TS** | 1 major field (execution_spans) |
| **Type mismatches** | 2 fields (layer1_decision, layer3_changes returned as JSON strings, not objects) |

---

## Key Findings

### 1. ✅ API is Well-Structured
- Returns comprehensive per-turn metrics
- Includes observability data (execution spans, layer traces, stage timings)
- Proper tenant authorization and error handling

### 2. ⚠️ TypeScript Types are Outdated
The `TurnRow` interface in `apps/dashboard/types/sailly-debugger.ts` does not match actual API response:

#### Missing Fields (Frontend Cannot Access)
- ❌ `execution_spans` — **Critical**, this array is always returned
- ❌ `stt_ms`, `extract_ms`, `l2_ms`, `tool_ms` — Phase 9 stage timings
- ❌ `intent`, `turn_type`, `worker_profile` — Classification context

#### Extra Fields (Not in API Response)
- ❌ `id`, `call_id`, `call_sid` (at turn level)
- ❌ `vad_start_ms`, `vad_stop_ms` (VAD timings)
- ❌ `tts_latency_ms`, `acoustic_gap_ms`
- ❌ `stage1_clean_text`, `stage2_clean_text`
- ❌ `has_markdown`, `has_greeting`, `tts_suppressed_reason`

#### Type Mismatches
- ⚠️ `layer1_decision` — API returns **raw JSON string**, TypeScript expects `Layer1Decision` object
- ⚠️ `layer3_changes` — API returns **raw JSON string**, TypeScript expects `Layer3Changes` object

### 3. 🔍 ExecutionSpan Structure (Complete)

**13 Fields per span:**

```typescript
{
  span_id: string;              // 12-char UUID
  parent_span_id: string | null; // Hierarchy
  layer: number;                // 1, 2, or 3
  operation: string;            // classify, chat, policy, etc.
  name: string | null;          // Human label
  model: string | null;         // LLM identifier
  latency_ms: number;           // Wall time (computed)
  ttft_ms: number | null;       // Time-to-first-token
  status: string;               // ok, error, blocked
  tokens_in: number | null;     // Input tokens
  tokens_out: number | null;    // Output tokens
  finish_reason: string | null; // LLM stop reason
  io: Record<string, unknown>;  // Variable payload
}
```

**Database Source:** `google_turn_spans` table (9 migrations in)

---

## Impact Assessment

### 🔴 High Priority
1. **Missing `execution_spans` field** — App cannot display observability traces
2. **JSON string parsing not automated** — Frontend must manually parse layer1_decision and layer3_changes

### 🟡 Medium Priority
1. Phase 9 stage timings not accessible (stt_ms, extract_ms, etc.)
2. Classification context not accessible (intent, turn_type, worker_profile)
3. Extra TypeScript fields create confusion and type safety issues

### 🟢 Low Priority
1. VAD timings (vad_start_ms, vad_stop_ms) — not in API, unlikely to be added

---

## Files Analyzed

| File | Lines | Key Content |
|------|-------|------------|
| `server/main.py` | 1667–1798 | API endpoint implementation |
| `server/brain/contracts/trace.py` | 24–67 | ExecutionSpan dataclass |
| `apps/dashboard/types/sailly-debugger.ts` | 33–78 | TurnRow interface (outdated) |
| `apps/dashboard/lib/api/debugger-client.ts` | 143–156 | useCallTurns hook |
| `migrations/0009_turn_spans_table.sql` | Full | Database schema for spans |
| `migrations/0002_full_observability_schema.sql` | Full | Phase 9 observability columns |

---

## Deliverables Created

### 1. **DEBUGGER_API_RESPONSE_SCHEMAS.md**
- **Purpose:** Authoritative documentation of exact API response structure
- **Content:**
  - Top-level envelope shape
  - All 30 TurnRow fields with types
  - All 13 ExecutionSpan fields with types
  - Detailed mapping table showing gaps
  - Example JSON response for one turn with spans
  - Verification checklist for tests

### 2. **DEBUGGER_API_CORRECTED_TYPES.ts**
- **Purpose:** Corrected TypeScript types matching actual API response
- **Content:**
  - ExecutionSpan interface (newly defined)
  - TurnRowCorrected interface (with all 30 fields + execution_spans)
  - CallTurnsResponseCorrected envelope
  - Helper functions for parsing JSON strings (parseLayer1Decision, parseLayer3Changes)
  - Usage documentation

### 3. **DEBUGGER_API_VERIFICATION_TESTS.md**
- **Purpose:** Concrete test cases verifying response schema compliance
- **Content:**
  - 21 test cases covering:
    - Top-level response shape
    - All TurnRow fields
    - ExecutionSpan structure
    - Authorization & error handling
    - Data consistency
  - Pytest fixtures and code examples
  - Test running instructions

### 4. **DEBUGGER_API_ANALYSIS_SUMMARY.md** (this file)
- **Purpose:** Executive summary with key findings and action items

---

## Recommended Actions

### For Frontend Team
1. **Update TypeScript types**
   - Use corrected types from `DEBUGGER_API_CORRECTED_TYPES.ts`
   - Remove extra fields (id, call_id, vad_*, etc.)
   - Add missing fields (execution_spans, stt_ms, extract_ms, etc.)
   - Handle JSON string parsing for layer traces

2. **Update useCallTurns hook** (lines 143–156)
   - Remove type assertion or update the type target
   - Add parsing logic for layer1_decision and layer3_changes

3. **Add ExecutionSpan visualization**
   - Components need to be built for rendering trace spans
   - Use the 13-field structure from corrected types

### For Backend Team
1. **Document Phase 9 stage timings** in API comments (stt_ms, extract_ms, etc.)
2. **Consider parsing layer traces at API level** if frontend needs them as objects (currently returns raw strings)
3. **Add optional t_start_ms/t_end_ms to ExecutionSpan response** if relative timing is needed (currently only latency_ms is sent from DB)

### For QA/Testing
1. **Run verification tests** from `DEBUGGER_API_VERIFICATION_TESTS.md`
2. **Verify against corrected types** before frontend deployment
3. **Test error cases** (missing token, wrong tenant, db failure)
4. **Test edge cases** (empty spans array, null fields, very large calls)

---

## Database Query Reference

### Fetch Turn Metrics (Main Query)
```sql
SELECT
    turn_number, user_text, bot_text,
    stt_latency_ms, llm_latency_ms, total_latency_ms,
    tools_called, node_name, stage3_text,
    stt_confidence, build_sha, tenant_id, created_at,
    layer1_decision, layer2_raw_output, layer3_changes,
    stt_ms, extract_ms, l2_ms, tool_ms, tts_ttfb_ms,
    intent, turn_type, worker_profile,
    tts_situation, tts_mood, validation_breakdown
FROM google_turn_metrics
WHERE call_sid = $1
ORDER BY turn_number ASC
```

### Fetch Execution Spans (Secondary Query)
```sql
SELECT
    turn_number, span_id, parent_span_id, layer, operation, name, model,
    latency_ms, ttft_ms, status, tokens_in, tokens_out, finish_reason, io
FROM google_turn_spans
WHERE call_sid = $1
ORDER BY turn_number ASC, span_id ASC
```

---

## Testing Verification Command

```bash
# Run all verification tests
pytest -v tests/test_admin_turns_endpoint.py

# Run specific test class
pytest -v tests/test_admin_turns_endpoint.py::TestTurnRowStructure

# Run with coverage
pytest --cov=server.main --cov-report=html tests/test_admin_turns_endpoint.py
```

---

## Type Safety Checklist

When updating TypeScript types, verify:

- [ ] ExecutionSpan interface added to sailly-debugger.ts
- [ ] TurnRow now includes execution_spans field (ExecutionSpan[])
- [ ] All 30 fields documented with JSDoc comments
- [ ] layer1_decision typed as `string | null` (not Layer1Decision)
- [ ] layer3_changes typed as `string | null` (not Layer3Changes)
- [ ] Extra fields removed (id, call_id, vad_*, stage1_clean_text, etc.)
- [ ] Phase 9 fields added (stt_ms, extract_ms, l2_ms, tool_ms)
- [ ] Classification fields added (intent, turn_type, worker_profile)
- [ ] Helper functions added for JSON parsing (parseLayer1Decision, parseLayer3Changes)
- [ ] useCallTurns hook updated to return corrected types
- [ ] No type assertions needed (all fields explicitly typed)

---

## Quick Reference: JSON Example

```json
{
  "call_sid": "call_abc123",
  "turn_count": 1,
  "turns": [
    {
      "turn_number": 1,
      "user_text": "I want a large pizza",
      "bot_text": "Great! Would you like extra cheese?",
      "stt_latency_ms": 450,
      "llm_latency_ms": 280,
      "total_latency_ms": 1200,
      "tools_called": [],
      "node_name": "ORDER",
      "stt_confidence": 0.92,
      "build_sha": "abc123def456",
      "tenant_id": "pizzeria_napoli",
      "created_at": "2026-05-29T19:30:15.123456+00:00",
      "layer1_decision": "{\"node\":\"ORDER\",\"forced_tools\":[],\"state_hash\":\"xyz\"}",
      "layer2_raw_output": "Let me confirm the order...",
      "layer3_changes": "{\"warnings\":[],\"text_changed\":false,\"tools_changed\":false}",
      "stt_ms": 450,
      "extract_ms": 120,
      "l2_ms": 280,
      "tool_ms": 0,
      "tts_ttfb_ms": 180,
      "intent": "place_order",
      "turn_type": "bot_prompt",
      "worker_profile": "order_taker",
      "stage3_text": "Great! Would you like extra cheese?",
      "tts_situation": "casual_question",
      "tts_mood": "helpful",
      "validation_breakdown": {"slot_confidence": 0.95},
      "execution_spans": [
        {
          "span_id": "sp_001a",
          "parent_span_id": null,
          "layer": 1,
          "operation": "classify",
          "name": "Intent classification",
          "model": null,
          "latency_ms": 120.45,
          "ttft_ms": null,
          "status": "ok",
          "tokens_in": null,
          "tokens_out": null,
          "finish_reason": null,
          "io": {}
        },
        {
          "span_id": "sp_002b",
          "parent_span_id": "sp_001a",
          "layer": 2,
          "operation": "chat",
          "name": "LLM response generation",
          "model": "gpt-4",
          "latency_ms": 280.67,
          "ttft_ms": 45.2,
          "status": "ok",
          "tokens_in": 450,
          "tokens_out": 28,
          "finish_reason": "stop",
          "io": {"temperature": 0.7}
        }
      ]
    }
  ]
}
```

---

## Questions?

Refer to:
- **Detailed schema:** `DEBUGGER_API_RESPONSE_SCHEMAS.md`
- **Corrected types:** `DEBUGGER_API_CORRECTED_TYPES.ts`
- **Test cases:** `DEBUGGER_API_VERIFICATION_TESTS.md`
- **Source code:** `/server/main.py` lines 1667–1798

---

**Analysis completed:** 2026-05-29 19:44 UTC+2
