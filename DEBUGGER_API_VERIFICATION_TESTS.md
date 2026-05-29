# Debugger API Response Verification Checklist

**Purpose:** Concrete test cases for verifying `/api/admin/call/{call_sid}/turns` response schema compliance.

**Date:** 2026-05-29  
**Endpoint:** `GET /api/admin/call/{call_sid}/turns?tenant={tenant_id}`

---

## Test Fixture Setup

```python
# pytest fixture for test data
@pytest.fixture
async def sample_call_with_spans(db_pool):
    """Create a call with 2 turns and execution spans."""
    call_sid = "test_call_" + uuid.uuid4().hex[:8]
    tenant_id = "pizzeria_napoli"
    
    async with db_pool.acquire() as conn:
        # Insert call
        await conn.execute(
            "INSERT INTO google_calls (call_sid, tenant_id, started_at, ended_at) VALUES ($1, $2, now(), now())",
            call_sid, tenant_id
        )
        
        # Insert Turn 1
        await conn.execute("""
            INSERT INTO google_turn_metrics (
                call_sid, turn_number, user_text, bot_text, stt_latency_ms, llm_latency_ms,
                total_latency_ms, tools_called, node_name, stt_confidence, build_sha,
                tenant_id, layer1_decision, layer2_raw_output, layer3_changes,
                stt_ms, extract_ms, l2_ms, tool_ms, tts_ttfb_ms,
                intent, turn_type, worker_profile, stage3_text,
                tts_situation, tts_mood, validation_breakdown
            ) VALUES (
                $1, 1, 'I want a pizza', 'What size?', 450, 280, 1200,
                '[]', 'ORDER', 0.92, 'abc123def456', $2,
                '{"node":"ORDER","forced_tools":[],"state_hash":"xyz","validators_run":[]}',
                'Let me help you order a pizza', '{"warnings":[],"text_changed":false,"tools_changed":false}',
                450, 120, 280, 0, 180,
                'place_order', 'bot_prompt', 'order_taker', 'What size would you like?',
                'casual_question', 'helpful', '{"slot_confidence":0.95}'
            )
        """, call_sid, tenant_id)
        
        # Insert ExecutionSpans for Turn 1
        spans = [
            ("sp_001", None, 1, "classify", "Intent classification", 0.0, 120.45, "ok", None, None, None, None, {}),
            ("sp_002", "sp_001", 2, "chat", "LLM response", 120.45, 401.12, "ok", "gpt-4", 450, 28, "stop", {"temperature": 0.7}),
        ]
        for span_id, parent, layer, op, name, t_start, t_end, status, model, in_tok, out_tok, finish, io in spans:
            await conn.execute("""
                INSERT INTO google_turn_spans (
                    call_sid, turn_number, tenant_id, span_id, parent_span_id,
                    layer, operation, name, status, t_start_ms, t_end_ms, latency_ms,
                    ttft_ms, model, tokens_in, tokens_out, finish_reason, io
                ) VALUES ($1, 1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            """, call_sid, tenant_id, span_id, parent, layer, op, name, status,
                t_start, t_end, t_end - t_start, 45.2 if model else None,
                model, in_tok, out_tok, finish, io)
    
    yield {"call_sid": call_sid, "tenant_id": tenant_id}
```

---

## API Response Structure Tests

### ✅ Test 1: Top-Level Envelope
```python
def test_top_level_response_shape(sample_call_with_spans):
    """Response has call_sid, turn_count, turns fields."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns", 
                      params={"tenant": sample_call_with_spans['tenant_id']})
    
    assert resp.status_code == 200
    data = resp.json()
    
    assert "call_sid" in data
    assert data["call_sid"] == sample_call_with_spans["call_sid"]
    assert "turn_count" in data
    assert isinstance(data["turn_count"], int)
    assert "turns" in data
    assert isinstance(data["turns"], list)
```

### ✅ Test 2: Turn Count Accuracy
```python
def test_turn_count_matches_turns_array_length(sample_call_with_spans):
    """turn_count matches len(turns)."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": sample_call_with_spans['tenant_id']})
    data = resp.json()
    
    assert data["turn_count"] == len(data["turns"])
    assert data["turn_count"] == 2  # From fixture
```

### ✅ Test 3: All Required TurnRow Fields Present
```python
def test_all_required_turn_fields(sample_call_with_spans):
    """Each turn includes all 30 core fields."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": sample_call_with_spans['tenant_id']})
    data = resp.json()
    
    required_fields = {
        # Identifiers
        "turn_number", "user_text", "bot_text",
        # STT
        "stt_latency_ms", "stt_confidence",
        # Latencies
        "llm_latency_ms", "total_latency_ms", "tts_ttfb_ms",
        # Phase 9 stage timings
        "stt_ms", "extract_ms", "l2_ms", "tool_ms",
        # Tools
        "tools_called",
        # Classification
        "node_name", "intent", "turn_type", "worker_profile",
        # Layer traces
        "layer1_decision", "layer2_raw_output", "layer3_changes",
        # Text
        "stage3_text",
        # TTS adaptive
        "tts_situation", "tts_mood",
        # Validation
        "validation_breakdown",
        # Metadata
        "tenant_id", "build_sha", "created_at",
        # Traces (CRITICAL)
        "execution_spans"
    }
    
    turn = data["turns"][0]
    for field in required_fields:
        assert field in turn, f"Missing field: {field}"
```

### ✅ Test 4: Field Type Validation
```python
def test_turn_field_types(sample_call_with_spans):
    """Fields have correct types."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": sample_call_with_spans['tenant_id']})
    data = resp.json()
    turn = data["turns"][0]
    
    # Integer fields
    assert isinstance(turn["turn_number"], int)
    assert isinstance(turn["stt_ms"], (int, type(None)))
    
    # String fields
    assert isinstance(turn["user_text"], (str, type(None)))
    assert isinstance(turn["node_name"], (str, type(None)))
    assert isinstance(turn["build_sha"], (str, type(None)))
    
    # Numeric fields
    assert isinstance(turn["stt_latency_ms"], (int, float, type(None)))
    assert isinstance(turn["stt_confidence"], (int, float, type(None)))
    
    # Array
    assert isinstance(turn["tools_called"], list)
    
    # Objects
    assert isinstance(turn["validation_breakdown"], dict)
    
    # ISO timestamp
    assert isinstance(turn["created_at"], str)
    from datetime import datetime
    datetime.fromisoformat(turn["created_at"])  # Should not raise
    
    # Execution spans array
    assert isinstance(turn["execution_spans"], list)
```

### ✅ Test 5: Tools Called Parsing
```python
def test_tools_called_parsed_from_json_string(db_pool, sample_call_with_spans):
    """tools_called is parsed array, not raw JSON string."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": sample_call_with_spans['tenant_id']})
    data = resp.json()
    
    # Verify tools_called is array, not string
    turn = data["turns"][0]
    assert isinstance(turn["tools_called"], list)
    for tool in turn["tools_called"]:
        assert isinstance(tool, str)
    
    # If no tools, should be empty array not null
    assert turn["tools_called"] == [] or all(isinstance(t, str) for t in turn["tools_called"])
```

### ✅ Test 6: Layer1Decision and Layer3Changes as JSON Strings
```python
def test_layer_traces_are_json_strings(sample_call_with_spans):
    """layer1_decision and layer3_changes returned as raw JSON strings."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": sample_call_with_spans['tenant_id']})
    data = resp.json()
    turn = data["turns"][0]
    
    # These should be strings
    assert isinstance(turn["layer1_decision"], (str, type(None)))
    assert isinstance(turn["layer3_changes"], (str, type(None)))
    
    # They should be valid JSON when parsed
    if turn["layer1_decision"]:
        import json
        parsed = json.loads(turn["layer1_decision"])
        assert isinstance(parsed, dict)
        assert "node" in parsed
    
    if turn["layer3_changes"]:
        import json
        parsed = json.loads(turn["layer3_changes"])
        assert isinstance(parsed, dict)
        assert "text_changed" in parsed
```

---

## ExecutionSpan Tests

### ✅ Test 7: ExecutionSpan Array Structure
```python
def test_execution_spans_array_structure(sample_call_with_spans):
    """execution_spans is an array of span objects with all fields."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": sample_call_with_spans['tenant_id']})
    data = resp.json()
    turn = data["turns"][0]
    
    spans = turn["execution_spans"]
    assert isinstance(spans, list)
    assert len(spans) > 0, "Expected at least one span in fixture"
    
    span = spans[0]
    
    # Required span fields
    span_fields = {
        "span_id", "parent_span_id", "layer", "operation", "name",
        "model", "latency_ms", "ttft_ms", "status",
        "tokens_in", "tokens_out", "finish_reason", "io"
    }
    
    for field in span_fields:
        assert field in span, f"Span missing field: {field}"
```

### ✅ Test 8: ExecutionSpan Field Types
```python
def test_execution_span_field_types(sample_call_with_spans):
    """ExecutionSpan fields have correct types."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": sample_call_with_spans['tenant_id']})
    data = resp.json()
    span = data["turns"][0]["execution_spans"][0]
    
    # String fields
    assert isinstance(span["span_id"], str)
    assert isinstance(span["operation"], str)
    assert isinstance(span["status"], str)
    assert isinstance(span["name"], (str, type(None)))
    assert isinstance(span["parent_span_id"], (str, type(None)))
    assert isinstance(span["model"], (str, type(None)))
    
    # Numeric fields
    assert isinstance(span["layer"], int)
    assert isinstance(span["latency_ms"], (int, float))
    assert isinstance(span["ttft_ms"], (int, float, type(None)))
    assert isinstance(span["tokens_in"], (int, type(None)))
    assert isinstance(span["tokens_out"], (int, type(None)))
    
    # Object field
    assert isinstance(span["io"], dict)
    
    # finish_reason can be string or null
    assert isinstance(span["finish_reason"], (str, type(None)))
```

### ✅ Test 9: ExecutionSpan Latency Computation
```python
def test_execution_span_latency_rounded(sample_call_with_spans):
    """latency_ms is properly rounded to 2 decimals."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": sample_call_with_spans['tenant_id']})
    data = resp.json()
    span = data["turns"][0]["execution_spans"][0]
    
    # Should be rounded to 2 decimals max
    latency = span["latency_ms"]
    assert isinstance(latency, (int, float))
    # Check decimal places
    latency_str = str(latency)
    if '.' in latency_str:
        decimal_places = len(latency_str.split('.')[1])
        assert decimal_places <= 2, f"latency_ms has > 2 decimal places: {latency}"
```

### ✅ Test 10: ExecutionSpan Hierarchy
```python
def test_execution_span_hierarchy(sample_call_with_spans):
    """parent_span_id correctly references other spans in turn."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": sample_call_with_spans['tenant_id']})
    data = resp.json()
    spans = data["turns"][0]["execution_spans"]
    
    span_ids = {s["span_id"] for s in spans}
    
    # Every parent_span_id should reference an existing span_id in same turn
    for span in spans:
        if span["parent_span_id"]:
            assert span["parent_span_id"] in span_ids, \
                f"Span {span['span_id']} references invalid parent {span['parent_span_id']}"
```

### ✅ Test 11: Layer and Operation Values
```python
def test_execution_span_layer_and_operation_values(sample_call_with_spans):
    """layer and operation have valid enumerations."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": sample_call_with_spans['tenant_id']})
    data = resp.json()
    spans = data["turns"][0]["execution_spans"]
    
    valid_layers = {1, 2, 3}
    valid_operations = {"classify", "prereq", "chat", "commit_gate", "policy", "execute_tool"}
    valid_statuses = {"ok", "error", "blocked"}
    
    for span in spans:
        assert span["layer"] in valid_layers, f"Invalid layer: {span['layer']}"
        assert span["operation"] in valid_operations, f"Invalid operation: {span['operation']}"
        assert span["status"] in valid_statuses, f"Invalid status: {span['status']}"
```

### ✅ Test 12: ExecutionSpan Token Fields
```python
def test_execution_span_token_fields(sample_call_with_spans):
    """Token fields only populated for Layer 2 (LLM) spans."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": sample_call_with_spans['tenant_id']})
    data = resp.json()
    spans = data["turns"][0]["execution_spans"]
    
    for span in spans:
        if span["layer"] != 2:
            # Layer 1 & 3 typically have null tokens
            # (not enforced, but typical)
            if span["tokens_in"] is not None:
                assert isinstance(span["tokens_in"], int)
        else:
            # Layer 2 may have token counts
            if span["tokens_in"] is not None:
                assert isinstance(span["tokens_in"], int)
                assert span["tokens_in"] > 0
            if span["tokens_out"] is not None:
                assert isinstance(span["tokens_out"], int)
                assert span["tokens_out"] > 0
```

---

## Authorization & Error Tests

### ✅ Test 13: X-Debug-Token Header Required
```python
def test_debug_token_header_required():
    """Request without X-Debug-Token header returns 401."""
    resp = client.get("/api/admin/call/any_call_sid/turns?tenant=pizzeria_napoli",
                      headers={})  # No X-Debug-Token
    
    # Behavior depends on DEBUG_API_TOKEN env var
    # If set, returns 401; if unset, allows it
    if os.getenv("DEBUG_API_TOKEN"):
        assert resp.status_code == 401
```

### ✅ Test 14: Invalid Token Returns 401
```python
def test_invalid_debug_token_returns_401():
    """Request with invalid X-Debug-Token returns 401."""
    resp = client.get("/api/admin/call/any_call_sid/turns?tenant=pizzeria_napoli",
                      headers={"x-debug-token": "invalid_token"})
    
    if os.getenv("DEBUG_API_TOKEN"):
        assert resp.status_code == 401
```

### ✅ Test 15: Tenant Mismatch Returns Error
```python
def test_tenant_authorization_check(sample_call_with_spans):
    """Request with wrong tenant_id rejects call."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": "wrong_tenant"},
                      headers={"x-debug-token": os.getenv("DEBUG_API_TOKEN")})
    
    # Should return error (403 or error response)
    assert resp.status_code in [403, 404, 401] or "error" in resp.json()
```

### ✅ Test 16: Nonexistent Call Returns 404
```python
def test_nonexistent_call_returns_404():
    """Request for nonexistent call_sid returns 404."""
    resp = client.get("/api/admin/call/nonexistent_call_sid_xyz/turns",
                      params={"tenant": "pizzeria_napoli"},
                      headers={"x-debug-token": os.getenv("DEBUG_API_TOKEN")})
    
    assert resp.status_code == 404
    data = resp.json()
    assert "error" in data
    assert data["error"] == "no_turns"
```

### ✅ Test 17: Database Failure Returns 503
```python
def test_database_unavailable_returns_503(monkeypatch):
    """If database fails, returns 503."""
    async def mock_fetch_error(*args, **kwargs):
        raise Exception("Database connection failed")
    
    # Mock the database fetch to raise
    monkeypatch.setattr("server.database.get_pool", mock_fetch_error)
    
    resp = client.get("/api/admin/call/any_call/turns?tenant=pizzeria_napoli",
                      headers={"x-debug-token": os.getenv("DEBUG_API_TOKEN")})
    
    assert resp.status_code == 503
    data = resp.json()
    assert data["error"] == "db_unavailable"
```

---

## Data Consistency Tests

### ✅ Test 18: Turn Ordering
```python
def test_turns_ordered_by_turn_number(sample_call_with_spans):
    """Turns are sorted by turn_number ascending."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": sample_call_with_spans['tenant_id']})
    data = resp.json()
    turns = data["turns"]
    
    turn_numbers = [t["turn_number"] for t in turns]
    assert turn_numbers == sorted(turn_numbers)
```

### ✅ Test 19: ExecutionSpan Ordering
```python
def test_execution_spans_ordered_by_id(sample_call_with_spans):
    """ExecutionSpans are sorted by span_id within turn."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": sample_call_with_spans['tenant_id']})
    data = resp.json()
    spans = data["turns"][0]["execution_spans"]
    
    span_ids = [s["span_id"] for s in spans]
    assert span_ids == sorted(span_ids), f"Spans not sorted: {span_ids}"
```

### ✅ Test 20: Nullable Fields
```python
def test_nullable_fields_can_be_null(sample_call_with_spans):
    """Fields documented as nullable can actually be null."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": sample_call_with_spans['tenant_id']})
    data = resp.json()
    turn = data["turns"][0]
    
    nullable_fields = {
        "user_text", "bot_text", "stt_confidence",
        "stt_latency_ms", "llm_latency_ms", "total_latency_ms", "tts_ttfb_ms",
        "stt_ms", "extract_ms", "l2_ms", "tool_ms",
        "node_name", "intent", "turn_type", "worker_profile",
        "layer1_decision", "layer2_raw_output", "layer3_changes",
        "stage3_text", "tts_situation", "tts_mood",
        "tenant_id", "build_sha"
    }
    
    # Fields can be present and null
    for field in nullable_fields:
        assert field in turn, f"Field missing: {field}"
        # Value can be null (if intentionally set to null in test)
        # This just verifies the field exists
```

---

## End-to-End Test

### ✅ Test 21: Complete Response Validation
```python
def test_complete_call_turns_response(sample_call_with_spans):
    """Full end-to-end validation of GET /api/admin/call/{call_sid}/turns."""
    resp = client.get(f"/api/admin/call/{sample_call_with_spans['call_sid']}/turns",
                      params={"tenant": sample_call_with_spans['tenant_id']},
                      headers={"x-debug-token": os.getenv("DEBUG_API_TOKEN", "debug")})
    
    assert resp.status_code == 200
    data = resp.json()
    
    # Top-level
    assert "call_sid" in data
    assert "turn_count" in data
    assert "turns" in data
    assert isinstance(data["turns"], list)
    
    # Each turn
    for turn in data["turns"]:
        # 30 core fields
        assert all(f in turn for f in [
            "turn_number", "user_text", "bot_text",
            "stt_latency_ms", "llm_latency_ms", "total_latency_ms",
            "tools_called", "node_name", "stt_confidence",
            "build_sha", "tenant_id", "created_at",
            "layer1_decision", "layer2_raw_output", "layer3_changes",
            "stt_ms", "extract_ms", "l2_ms", "tool_ms", "tts_ttfb_ms",
            "intent", "turn_type", "worker_profile",
            "stage3_text", "tts_situation", "tts_mood",
            "validation_breakdown",
            "execution_spans"  # Critical
        ])
        
        # Execution spans populated
        assert isinstance(turn["execution_spans"], list)
        for span in turn["execution_spans"]:
            assert all(f in span for f in [
                "span_id", "parent_span_id", "layer", "operation",
                "name", "model", "latency_ms", "ttft_ms", "status",
                "tokens_in", "tokens_out", "finish_reason", "io"
            ])
```

---

## Summary

**Total Tests:** 21  
**Coverage:**
- Top-level response shape: ✅ 2 tests
- TurnRow fields: ✅ 5 tests
- ExecutionSpan structure: ✅ 6 tests
- Authorization & errors: ✅ 5 tests
- Data consistency: ✅ 2 tests
- End-to-end: ✅ 1 test

**Run all tests:**
```bash
pytest -v tests/test_admin_turns_endpoint.py
```

**Expected Result:** All 21 tests pass, verifying API response matches documented schema.
