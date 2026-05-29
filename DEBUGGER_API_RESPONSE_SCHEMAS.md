# Debugger API Response Schemas — Detailed Analysis

**Endpoint:** `GET /api/admin/call/{call_sid}/turns`  
**File:** `server/main.py` lines 1667–1798  
**Date Analyzed:** 2026-05-29

---

## 1. Top-Level Response Shape

```json
{
  "call_sid": "string",
  "turn_count": number,
  "turns": TurnRow[]
}
```

---

## 2. TurnRow Structure — As Returned by API

**Exact fields returned by API** (lines 1762–1797 in `server/main.py`):

| Field | Type | Source | Notes |
|-------|------|--------|-------|
| `turn_number` | int | DB | Row order, 1-indexed |
| `user_text` | string \| null | DB | User speech (ASR output) |
| `bot_text` | string \| null | DB | Bot response text |
| `stt_latency_ms` | number \| null | DB | STT duration |
| `llm_latency_ms` | number \| null | DB | LLM/Layer2 duration |
| `total_latency_ms` | number \| null | DB | Full turn time |
| `tools_called` | string[] | DB | Parsed JSON array (handles string fallback) |
| `node_name` | string \| null | DB | FSM state name at end of turn |
| `stt_confidence` | number \| null | DB | ASR confidence 0.0–1.0 |
| `build_sha` | string \| null | DB | Git SHA of deployed code |
| `tenant_id` | string \| null | DB | Tenant identifier |
| `created_at` | string | DB | ISO timestamp (`.isoformat()`) |
| `layer1_decision` | string \| null | DB | Raw JSON (not parsed in API) |
| `layer2_raw_output` | string \| null | DB | Raw LLM response text |
| `layer3_changes` | string \| null | DB | Raw JSON (not parsed in API) |
| `stt_ms` | number \| null | DB | Phase 9 stage timing |
| `extract_ms` | number \| null | DB | Phase 9 stage timing |
| `l2_ms` | number \| null | DB | Phase 9 stage timing |
| `tool_ms` | number \| null | DB | Phase 9 stage timing |
| `tts_ttfb_ms` | number \| null | DB | TTS time-to-first-byte |
| `intent` | string \| null | DB | Classification intent |
| `turn_type` | string \| null | DB | Classification turn type |
| `worker_profile` | string \| null | DB | Classification worker context |
| `stage3_text` | string \| null | DB | Final TTS text (after policy layer) |
| `tts_situation` | string \| null | DB | TTS adaptive context |
| `tts_mood` | string \| null | DB | TTS emotional state |
| `validation_breakdown` | JSON object | DB | Validator metrics (not parsed) |
| `execution_spans` | ExecutionSpan[] | In-memory | Built from `google_turn_spans` table |

**Total: 30 fields + 1 computed (execution_spans)**

---

## 3. ExecutionSpan Structure

**Location:** Built in-memory at lines 1726–1741 of `server/main.py`  
**Source Table:** `google_turn_spans` (lines 1708–1718)  
**Python Definition:** `server/brain/contracts/trace.py` lines 24–67

### ExecutionSpan Serialized Fields

```json
{
  "span_id": "string",                 // 12-char UUID hex
  "parent_span_id": "string | null",   // Links to parent operation
  "layer": number,                     // 1=Orchestrator, 2=LLM, 3=Policy
  "operation": "string",               // classify|prereq|chat|commit_gate|policy|execute_tool
  "name": "string | null",             // Human-readable op name
  "model": "string | null",            // LLM model used (e.g., "gpt-4")
  "latency_ms": number,                // Derived: t_end_ms - t_start_ms
  "ttft_ms": "number | null",          // Time-to-first-token (streaming)
  "status": "string",                  // "ok" | "error" | "blocked"
  "tokens_in": "number | null",        // Input token count
  "tokens_out": "number | null",       // Output token count
  "finish_reason": "string | null",    // "stop" | "length" | "error" | etc.
  "io": "JSON object",                 // Variable payload dict (JSONB from DB)
}
```

**Total: 13 fields (latency_ms computed, rest from DB or Python dataclass)**

### Database Columns (google_turn_spans table)

From `migrations/0009_turn_spans_table.sql`:

| DB Column | Type | API Field | Notes |
|-----------|------|-----------|-------|
| `call_sid` | TEXT | (not in span) | Used for filtering only |
| `turn_number` | INTEGER | (not in span) | Used for grouping |
| `tenant_id` | TEXT | (not in span) | Used for filtering |
| `span_id` | TEXT | `span_id` | Unique within call+turn |
| `parent_span_id` | TEXT | `parent_span_id` | Forms tree hierarchy |
| `layer` | SMALLINT | `layer` | 1=Orchestrator, 2=LLM, 3=Policy |
| `operation` | TEXT | `operation` | classify, prereq, chat, etc. |
| `name` | TEXT | `name` | Optional human label |
| `status` | TEXT | `status` | ok, error, blocked |
| `t_start_ms` | DOUBLE | (excluded from response) | Not serialized |
| `t_end_ms` | DOUBLE | (excluded from response) | Not serialized |
| `latency_ms` | DOUBLE | `latency_ms` | Computed: t_end_ms - t_start_ms |
| `ttft_ms` | DOUBLE | `ttft_ms` | Time-to-first-token |
| `model` | TEXT | `model` | LLM identifier |
| `tokens_in` | INTEGER | `tokens_in` | Input tokens |
| `tokens_out` | INTEGER | `tokens_out` | Output tokens |
| `finish_reason` | TEXT | `finish_reason` | LLM stop reason |
| `io` | JSONB | `io` | Variable payload |

---

## 4. Critical Schema Discrepancies: API vs Frontend Types

### TypeScript TurnRow Definition
**File:** `apps/dashboard/types/sailly-debugger.ts` lines 33–78

The TypeScript `TurnRow` interface defines:

```typescript
export interface TurnRow {
  id: number;                                    // ❌ NOT in API response
  call_id: string;                               // ❌ NOT in API response
  call_sid: string;                              // ❌ NOT in API response
  tenant_id: string | null;                      // ✅ In API
  turn_number: number;                           // ✅ In API
  user_text: string | null;                      // ✅ In API
  bot_text: string | null;                       // ✅ In API
  
  // VAD + STT
  vad_start_ms: number | null;                   // ❌ NOT in API
  vad_stop_ms: number | null;                    // ❌ NOT in API
  stt_confidence: number | null;                 // ✅ In API
  
  // Latencies
  stt_latency_ms: number | null;                 // ✅ In API
  llm_latency_ms: number | null;                 // ✅ In API
  tts_latency_ms: number | null;                 // ❌ NOT in API
  tts_ttfb_ms: number | null;                    // ✅ In API
  total_latency_ms: number | null;               // ✅ In API
  acoustic_gap_ms: number | null;                // ❌ NOT in API
  
  // Tools
  tools_called: string[];                        // ✅ In API
  
  // Layer traces
  node_name: string | null;                      // ✅ In API
  layer1_decision: Layer1Decision | null;        // ⚠️  API returns raw string (not parsed)
  layer2_raw_output: string | null;              // ✅ In API
  layer3_changes: Layer3Changes | null;          // ⚠️  API returns raw string (not parsed)
  
  // Text pipeline stages
  stage1_clean_text: string | null;              // ❌ NOT in API
  stage2_clean_text: string | null;              // ❌ NOT in API
  stage3_text: string | null;                    // ✅ In API
  
  // Misc
  has_markdown: boolean;                         // ❌ NOT in API
  has_greeting: boolean;                         // ❌ NOT in API
  tts_situation: string | null;                  // ✅ In API
  tts_mood: string | null;                       // ✅ In API
  tts_suppressed_reason: string | null;          // ❌ NOT in API
  validation_breakdown: Record<string, unknown>; // ✅ In API
  build_sha: string | null;                      // ✅ In API
  created_at: string;                            // ✅ In API
}
```

### Missing ExecutionSpan Type in TypeScript

**Critical Gap:** The TypeScript `TurnRow` interface does **NOT** include an `execution_spans` field, but the API **ALWAYS** returns one (as an array).

The API returns at line 1795:
```python
"execution_spans": spans_by_turn.get(turn_num, []),
```

This array is **never typed** in TypeScript. Frontend code using `useCallTurns` must work around this:

```typescript
// File: apps/dashboard/lib/api/debugger-client.ts lines 143–156
export function useCallTurns(callSid: string, tenantId?: string) {
  return useQuery({
    queryKey: ['call-turns', callSid, tenantId],
    queryFn: async () => {
      const url = buildUrl(`/api/admin/call/${callSid}/turns`, API_BASE);
      if (tenantId) url.searchParams.set('tenant', tenantId);

      const resp = await fetch(url.toString());
      if (!resp.ok) throw new Error(`Failed to fetch turns: ${resp.status}`);
      return resp.json() as Promise<CallTurnsResponse>;  // ← Type assertion
    },
    enabled: !!callSid,
  });
}
```

The `CallTurnsResponse` type only defines `turns: TurnRow[]`, but each TurnRow in the response will have an unmapped `execution_spans` array.

---

## 5. Example: Single Turn with Execution Spans

### API Response (Partial, One Turn)

```json
{
  "call_sid": "call_abc123",
  "turn_count": 3,
  "turns": [
    {
      "turn_number": 1,
      "user_text": "I want to order a pizza",
      "bot_text": "Sure! What size would you like?",
      "stt_latency_ms": 450,
      "llm_latency_ms": 280,
      "total_latency_ms": 1200,
      "tools_called": [],
      "node_name": "ORDER",
      "stt_confidence": 0.92,
      "build_sha": "abc123def456",
      "tenant_id": "pizzeria_napoli",
      "created_at": "2026-05-29T19:30:15.123456+00:00",
      "layer1_decision": "{\"node\":\"ORDER\",\"forced_tools\":[],\"state_hash\":\"xyz789\",\"validators_run\":[]}",
      "layer2_raw_output": "Let me confirm: you want to order a pizza.",
      "layer3_changes": "{\"warnings\":[],\"text_changed\":false,\"tools_changed\":false}",
      "stt_ms": 450,
      "extract_ms": 120,
      "l2_ms": 280,
      "tool_ms": 0,
      "tts_ttfb_ms": 180,
      "intent": "place_order",
      "turn_type": "bot_prompt",
      "worker_profile": "order_taker",
      "stage3_text": "Sure! What size would you like?",
      "tts_situation": "casual_question",
      "tts_mood": "helpful",
      "validation_breakdown": {
        "slot_confidence": 0.95,
        "flow_stage": "item_selection"
      },
      
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
          "io": {
            "prompt_template": "order_prompt_v2",
            "temperature": 0.7
          }
        },
        {
          "span_id": "sp_003c",
          "parent_span_id": "sp_001a",
          "layer": 3,
          "operation": "policy",
          "name": "Policy gate check",
          "model": null,
          "latency_ms": 35.12,
          "ttft_ms": null,
          "status": "ok",
          "tokens_in": null,
          "tokens_out": null,
          "finish_reason": null,
          "io": {
            "policy_rules_checked": ["profanity", "spam"],
            "policy_pass": true
          }
        }
      ]
    }
  ]
}
```

---

## 6. Type Mapping Summary Table

| Field Name | API Returns | TypeScript TurnRow | ExecutionSpan Has | Gap |
|------------|-------------|-------------------|-------------------|-----|
| `turn_number` | ✅ | ✅ | ✅ (via turn grouping) | No |
| `user_text` | ✅ | ✅ | N/A | No |
| `bot_text` | ✅ | ✅ | N/A | No |
| `stt_latency_ms` | ✅ | ✅ | N/A | No |
| `llm_latency_ms` | ✅ | ✅ | N/A | No |
| `total_latency_ms` | ✅ | ✅ | N/A | No |
| `tools_called` | ✅ | ✅ | N/A | No |
| `node_name` | ✅ | ✅ | N/A | No |
| `stt_confidence` | ✅ | ✅ | N/A | No |
| `build_sha` | ✅ | ✅ | N/A | No |
| `tenant_id` | ✅ | ✅ | N/A | No |
| `created_at` | ✅ | ✅ | N/A | No |
| `layer1_decision` | ✅ (raw JSON string) | ⚠️ (typed as object) | N/A | **Type mismatch** |
| `layer2_raw_output` | ✅ | ✅ | N/A | No |
| `layer3_changes` | ✅ (raw JSON string) | ⚠️ (typed as object) | N/A | **Type mismatch** |
| `stt_ms` | ✅ | ❌ | N/A | **Missing in TS** |
| `extract_ms` | ✅ | ❌ | N/A | **Missing in TS** |
| `l2_ms` | ✅ | ❌ | N/A | **Missing in TS** |
| `tool_ms` | ✅ | ❌ | N/A | **Missing in TS** |
| `tts_ttfb_ms` | ✅ | ✅ | N/A | No |
| `intent` | ✅ | ❌ | N/A | **Missing in TS** |
| `turn_type` | ✅ | ❌ | N/A | **Missing in TS** |
| `worker_profile` | ✅ | ❌ | N/A | **Missing in TS** |
| `stage3_text` | ✅ | ✅ | N/A | No |
| `tts_situation` | ✅ | ✅ | N/A | No |
| `tts_mood` | ✅ | ✅ | N/A | No |
| `validation_breakdown` | ✅ | ✅ | N/A | No |
| `execution_spans` | ✅ (array) | ❌ | ✅ (13 fields) | **Missing in TS** |
| `id` | ❌ | ✅ | N/A | **Extra in TS** |
| `call_id` | ❌ | ✅ | N/A | **Extra in TS** |
| `call_sid` | ❌ in turn | ✅ | N/A | **Extra in TS** |
| `vad_start_ms` | ❌ | ✅ | N/A | **Extra in TS** |
| `vad_stop_ms` | ❌ | ✅ | N/A | **Extra in TS** |
| `tts_latency_ms` | ❌ | ✅ | N/A | **Extra in TS** |
| `acoustic_gap_ms` | ❌ | ✅ | N/A | **Extra in TS** |
| `stage1_clean_text` | ❌ | ✅ | N/A | **Extra in TS** |
| `stage2_clean_text` | ❌ | ✅ | N/A | **Extra in TS** |
| `has_markdown` | ❌ | ✅ | N/A | **Extra in TS** |
| `has_greeting` | ❌ | ✅ | N/A | **Extra in TS** |
| `tts_suppressed_reason` | ❌ | ✅ | N/A | **Extra in TS** |

---

## 7. Identified Type Mismatches & Gaps

### Critical Issues

#### 1. **ExecutionSpan Not Typed in TypeScript**
- **Problem:** API returns `execution_spans: ExecutionSpan[]` but TypeScript has no type for this.
- **Impact:** Frontend code accessing span fields will have `any` type.
- **Fix:** Define `ExecutionSpan` interface in `apps/dashboard/types/sailly-debugger.ts`

#### 2. **JSON String vs Parsed Object**
- **Problem:** API returns `layer1_decision` and `layer3_changes` as **raw JSON strings**
- **TypeScript Expects:** Parsed objects (`Layer1Decision | null`, `Layer3Changes | null`)
- **Line in API:** 1776–1778 directly assign the raw DB values
- **Impact:** Type assertion will fail if frontend tries to access `.node` or `.warnings` properties

#### 3. **Missing Phase 9 Stage Timings**
- **Problem:** API returns `stt_ms`, `extract_ms`, `l2_ms`, `tool_ms` but TypeScript TurnRow doesn't include them
- **Impact:** Frontend cannot access per-stage latencies (available in DB)

#### 4. **Missing Classification Fields**
- **Problem:** API returns `intent`, `turn_type`, `worker_profile` but TypeScript doesn't include them
- **Impact:** Frontend loses classification context

#### 5. **Extra Fields in TypeScript (Not in API)**
The TypeScript TurnRow includes fields **never populated by the API**:
- `id`, `call_id`, `call_sid` (at turn level)
- `vad_start_ms`, `vad_stop_ms`
- `tts_latency_ms`, `acoustic_gap_ms`
- `stage1_clean_text`, `stage2_clean_text`
- `has_markdown`, `has_greeting`, `tts_suppressed_reason`

These suggest the TypeScript was designed for a different schema.

---

## 8. ExecutionSpan Python Definition

**File:** `server/brain/contracts/trace.py` lines 24–67

```python
@dataclass
class ExecutionSpan:
    """One operation within a turn, OTel gen_ai-shaped.
    
    Times are milliseconds relative to the start of the turn (t0), so they are
    comparable across calls without absolute clock alignment. ``latency_ms`` is
    the wall time of the operation itself.
    """
    
    layer: int                          # 1=Orchestrator, 2=LLM, 3=Policy
    operation: str                      # classify|prereq|chat|commit_gate|policy|execute_tool
    name: str                           # Human-readable operation name
    t_start_ms: float                   # Relative to turn start (monotonic)
    t_end_ms: float                     # Relative to turn start (monotonic)
    status: str = "ok"                  # ok | error | blocked
    span_id: str = UUID[:12]            # 12-char hex ID
    parent_span_id: Optional[str] = None # Forms tree hierarchy
    model: Optional[str] = None         # LLM identifier if Layer 2
    tokens_in: Optional[int] = None     # Input token count
    tokens_out: Optional[int] = None    # Output token count
    finish_reason: Optional[str] = None # LLM stop reason
    io: Dict[str, Any] = {}             # Variable payload
    
    @property
    def latency_ms(self) -> float:
        """Computed: t_end_ms - t_start_ms (rounded to 2 decimals)"""
        return round(self.t_end_ms - self.t_start_ms, 2)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serializes to JSON (excludes t_start_ms, t_end_ms from response)"""
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "layer": self.layer,
            "operation": self.operation,
            "name": self.name,
            "t_start_ms": round(self.t_start_ms, 2),
            "t_end_ms": round(self.t_end_ms, 2),
            "latency_ms": self.latency_ms,
            "status": self.status,
            "model": self.model,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "finish_reason": self.finish_reason,
            "io": self.io,
        }
```

**Note:** The Python dataclass has `t_start_ms` and `t_end_ms`, but the `to_dict()` method **includes both** in serialization (unlike earlier analysis of lines 1726–1741 which only read from DB columns).

**DB vs. Python Serialization Mismatch:**
- Database stores `t_start_ms`, `t_end_ms`, `latency_ms` (redundantly)
- API reads from DB returns `latency_ms`, `ttft_ms` (lines 1708–1718 query)
- Python `ExecutionSpan.to_dict()` would return `t_start_ms`, `t_end_ms`, `latency_ms`

---

## 9. Verification Checklist for Tests

When writing or updating tests, verify:

- [ ] API response includes all 30 TurnRow fields + execution_spans array
- [ ] `tools_called` array is properly parsed (handles JSON string fallback)
- [ ] `execution_spans` array is populated for each turn
- [ ] Each ExecutionSpan has all 13 required fields (including computed `latency_ms`)
- [ ] `created_at` is ISO format string
- [ ] `layer1_decision` and `layer3_changes` are returned as **raw JSON strings** (not parsed objects)
- [ ] Phase 9 stage timings (`stt_ms`, `extract_ms`, `l2_ms`, `tool_ms`) are present
- [ ] ExecutionSpan `t_start_ms` and `t_end_ms` are included if serialized via `to_dict()`
- [ ] Optional fields (model, tokens_in, tokens_out, etc.) can be null
- [ ] Tenant authorization is checked via X-Debug-Token header
- [ ] 404 returned if call has no turns
- [ ] 503 returned if database query fails

---

## 10. Recommendations

### For Frontend
1. **Add ExecutionSpan type** to `apps/dashboard/types/sailly-debugger.ts`
2. **Add `execution_spans` field** to TurnRow interface
3. **Parse `layer1_decision` and `layer3_changes`** in the query hook or useCallback
4. **Add missing Phase 9 fields** to TurnRow (stt_ms, extract_ms, l2_ms, tool_ms, intent, turn_type, worker_profile)
5. **Remove fields never returned by API** (id, call_id, call_sid at turn level, vad_*, stage1/2_*, has_*, acoustic_gap_ms, tts_latency_ms, tts_suppressed_reason)

### For Backend (main.py)
1. **Verify layer1_decision and layer3_changes JSON parsing** — consider parsing at API level if frontend needs objects
2. **Document Phase 9 stage timings** — currently undocumented in API comments
3. **Consider including t_start_ms/t_end_ms in ExecutionSpan response** — currently only latency_ms is sent, but Python dataclass includes both

### For Database
1. **No changes needed** — schema is comprehensive
2. **Consider indexing on (tenant_id, turn_number)** for faster per-turn lookups (already indexed for call_sid + turn_number)

---

## 11. Response Summary

**What the API Actually Returns:**
- Top-level envelope with call_sid, turn_count, turns array
- 30 TurnRow fields per turn (not 39 as TypeScript claims)
- 1 computed field (execution_spans) containing 0+ ExecutionSpan objects
- ExecutionSpan has 13 fields including 1 computed (latency_ms)
- Raw JSON strings for layer1_decision and layer3_changes (not parsed)

**What Frontend Type Claims:**
- 39 TurnRow fields (9 extra)
- No execution_spans field (missing)
- layer1_decision and layer3_changes as parsed objects (type mismatch)

**Testing Implication:**
A test verifying the response against TypeScript types will fail on:
1. Missing execution_spans field
2. Extra fields in TypeScript (call_id, id, vad_*, stage1/2_*, etc.)
3. JSON string vs. object mismatch for Layer 1/3 fields
