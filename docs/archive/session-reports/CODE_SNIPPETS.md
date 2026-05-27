# Code Snippets - Key Changes

## 1. Initialize TurnTimings (v4_turn_processor.py)

```python
async def process_turn(
    self,
    user_text: str,
    tts_callback: Optional[Callable[[str], Awaitable[None]]] = None,
) -> TurnResult:
    from server.brain.conversation_state import update_state_from_utterance
    from server.brain.context_doc_builder import _persist_resolved_entities_to_state
    from server.brain.v4_pipeline import process_turn_v4
    from server.brain.contracts.turn_timings import TurnTimings  # NEW
    import time  # NEW

    # Initialize _turn_timings at the start of each turn for TTS TTFB instrumentation.
    # This must happen at the top of process_turn before any async work begins.
    # _turn_timings is used by the TTS timing processor to stamp tts_first_byte_at
    # and by brain_service.py to accumulate per-stage latencies.
    self.state._turn_timings = TurnTimings()  # NEW

    self._semantic_tools_called_this_turn = []
    # ... rest of method
```

**Why**: Ensures each turn starts with a fresh timing accumulator, and TTS processor can stamp first audio byte.

---

## 2. Compute TTFB (turn_timings.py)

```python
def tts_ttfb_ms(self) -> int:
    """Time-to-first-audio (TTFB) from brain start to first audio byte.
    
    This measures end-to-end latency from when the brain starts processing
    (after STT final) to when the first audio chunk is sent to the client.
    Includes: LLM processing + TTS synthesis + network delay.
    """
    if not self.tts_first_byte_at or not self.stt_done_at:
        return 0
    return max(0, int((self.tts_first_byte_at - self.stt_done_at) * 1000))
```

**Why**: Measures perceived latency = time user waits to hear first audio.

---

## 3. Metrics Dictionary Export (turn_timings.py)

```python
def to_metrics_dict(self) -> dict:
    """Return a dict ready for insertion into google_turn_metrics."""
    return {
        "stt_ms": self.stt_ms() or None,
        "extract_ms": self.extract_ms() or None,
        "l2_ms": self.l2_ms() or None,
        "tool_ms": self.tool_ms() or None,
        "tts_first_byte_ms": self.tts_first_byte_ms() or None,
        "tts_ttfb_ms": self.tts_ttfb_ms() or None,  # NEW: Brain start to first audio
        "total_ms": self.total_ms() or None,
        "tool_durations": self.tool_durations or None,
        "prompt_tokens_in": self.prompt_tokens_in or None,
        "prompt_tokens_out": self.prompt_tokens_out or None,
        "extract_tokens_in": self.extract_tokens_in or None,
        "extract_tokens_out": self.extract_tokens_out or None,
    }
```

**Why**: Makes tts_ttfb_ms available to database layer.

---

## 4. Metrics Dictionary Merge (brain_service.py)

```python
# Build the base metrics dict
_metrics_dict = {
    "turn_number": self._turn_counter,
    "user_text": user_text,
    "bot_text": result.clean_text,
    # ... all other base fields ...
    "tts_ttfb_ms": getattr(self, "_last_tts_ttfb_ms", None),  # FALLBACK
    # ... more fields ...
}

# Phase 9 A1 — per-stage latency, token counts, and cost_eur from TurnTimings.
# Merge TurnTimings metrics (which include tts_ttfb_ms computed from timestamps).
# These authoritative values override any fallback values set above.
if _tp and getattr(getattr(_tp, "state", None), "_turn_timings", None):
    _metrics_dict.update(_build_turn_metrics_extra(_tp.state))

self._turn_metrics.append(_metrics_dict)
```

**Why**: 
- Ensures TurnTimings values (authoritative) override fallback values
- TurnTimings data has priority (computed from actual timestamps)
- Backward compatible (fallback if timings not available)

---

## 5. Database Migration (database.py)

```python
# Additive migrations for pre-existing deployments.
for _col_ddl in (
    "ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS tenant_id TEXT",
    "ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS stt_confidence REAL",
    # ... other migrations ...
    # TTS TTFB instrumentation: time from brain_start to first audio byte
    "ALTER TABLE google_turn_metrics ADD COLUMN IF NOT EXISTS tts_ttfb_ms INTEGER",  # NEW
):
    try:
        await conn.execute(_col_ddl)
    except Exception as _mig_err:
        logger.warning(f"[DB] migration '{_col_ddl}' failed: {_mig_err}")
```

**Why**:
- Safe `IF NOT EXISTS` prevents errors on re-runs
- Runs automatically on service startup
- Non-blocking: old deployments don't break

---

## 6. Call Report Metrics Display (call_report/builder.py)

```python
if turn_num in metrics_by_turn:
    m = metrics_by_turn[turn_num]
    lines.append("**Metrics**:")
    if m.get("total_latency_ms"):
        lines.append(f"- Total Latency: {m['total_latency_ms']}ms")
    if m.get("llm_latency_ms"):
        lines.append(f"- Brain Processing: {m['llm_latency_ms']}ms (STT final → TTS text)")
    if m.get("tts_ttfb_ms"):
        lines.append(f"- TTS TTFB: {m['tts_ttfb_ms']}ms (STT final → first audio)")
    if m.get("stt_confidence"):
        lines.append(f"- STT Confidence: {m['stt_confidence']:.2f}")
    if m.get("intent"):
        lines.append(f"- Intent: {m['intent']} ({m.get('turn_type', '')})")
    if m.get("tools_called"):
        lines.append(f"- Tools: {m['tools_called']}")
    lines.append("")
```

**Before**:
```
- Latency: 3200ms
- LLM: 2388ms
```

**After**:
```
- Total Latency: 3200ms
- Brain Processing: 2388ms (STT final → TTS text)
- TTS TTFB: 3188ms (STT final → first audio)
```

**Why**: Clear separation helps users understand latency breakdown.

---

## 7. Latency Breakdown Documentation (call_report/builder.py)

```python
lines.append("\n## Latency Breakdown\n")
lines.append("- **Brain Processing** (`llm_latency_ms`): Time from STT final to first TTS text generated by LLM")
lines.append("- **TTS TTFB** (`tts_ttfb_ms`): End-to-end time from STT final to first audio byte sent to client")
lines.append("  - Includes: LLM processing + TTS synthesis + network delay")
lines.append("  - Perceived latency by user ≈ TTS TTFB")
lines.append("- **TTS Synthesis** = TTS TTFB - Brain Processing (synthesis + network)")
```

**Why**: Explains what each metric represents and how they relate.

---

## Example SQL Queries

### Check Metrics Are Populated
```sql
SELECT COUNT(*) as populated, COUNT(*) FILTER (WHERE tts_ttfb_ms IS NULL) as null_count
FROM google_turn_metrics
WHERE created_at > NOW() - INTERVAL '1 hour';
```

### Calculate Latency Breakdown
```sql
SELECT 
    turn_number,
    llm_latency_ms as brain_processing,
    (tts_ttfb_ms - llm_latency_ms) as tts_synthesis_network,
    tts_ttfb_ms as perceived_latency
FROM google_turn_metrics
WHERE call_sid = 'demo-xyz'
ORDER BY turn_number;
```

### Find Slow Turns
```sql
SELECT 
    turn_number,
    bot_text,
    tts_ttfb_ms,
    (tts_ttfb_ms - llm_latency_ms) as tts_latency
FROM google_turn_metrics
WHERE call_sid = 'demo-xyz'
  AND (tts_ttfb_ms - llm_latency_ms) > 1000
ORDER BY tts_latency DESC;
```

### Monitor Service Health
```sql
SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY tts_ttfb_ms) as p50,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY tts_ttfb_ms) as p95,
    MAX(tts_ttfb_ms) as max_ms
FROM google_turn_metrics
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour DESC;
```

---

## Testing Examples

### Unit Test: Compute TTFB
```python
from server.brain.contracts.turn_timings import TurnTimings
import time

def test_tts_ttfb_computation():
    timings = TurnTimings()
    
    # Simulate timestamps
    base = timings.turn_started_at
    timings.stt_done_at = base + 0.5  # 500ms
    timings.l2_done_at = base + 2.9   # 2900ms (2400ms after stt)
    timings.tts_first_byte_at = base + 3.7  # 3700ms
    
    # Compute: 3700 - 500 = 3200ms
    assert timings.tts_ttfb_ms() == 3200
    
    # tts_first_byte_ms: 3700 - 2900 = 800ms
    assert timings.tts_first_byte_ms() == 800
```

### Integration Test: End-to-End
```python
async def test_ttfb_captured_in_db():
    # Make a call
    call_sid = "test-call-xyz"
    # ... call execution ...
    
    # Verify metrics in DB
    result = await conn.fetch(
        "SELECT tts_ttfb_ms, llm_latency_ms FROM google_turn_metrics WHERE call_sid = $1",
        call_sid
    )
    
    assert len(result) > 0, "No metrics found"
    row = result[0]
    
    assert row['tts_ttfb_ms'] is not None, "tts_ttfb_ms is NULL!"
    assert row['tts_ttfb_ms'] > 0, "tts_ttfb_ms should be positive"
    assert row['tts_ttfb_ms'] >= row['llm_latency_ms'], \
        "TTFB must be >= brain processing"
```

---

## Summary: What Each Code Change Does

| Component | Change | Result |
|-----------|--------|--------|
| v4_turn_processor | Initialize `_turn_timings` | Enables TTS timestamp capture |
| turn_timings.py | Add `tts_ttfb_ms()` method | Computes perceived latency |
| turn_timings.py | Export in `to_metrics_dict()` | Makes TTFB available to DB |
| brain_service.py | Merge TurnTimings data | Gets TTFB into metrics dict |
| database.py | Add migration | Stores TTFB in DB |
| call_report/builder.py | Display both metrics | Shows latency breakdown |

**Result**: End-to-end latency (TTFB) now measured and visible! ✅
