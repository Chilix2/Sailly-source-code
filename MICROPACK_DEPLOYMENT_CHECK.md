# Micro-Pack Deployment Verification — Bug D Follow-up

## Deployment Location
**Codebase**: `/home/charles2/sailly-browser-demo` (port 8080, live demo)  
**Status**: All fixes correctly deployed ✓

## Fix 1: Bug D Cross-Turn Phone Digit Buffer

### Location
- **File**: `server/brain/conversation_state.py`
- **Field added** (line 419): `phone_digits_buffer: str = ""`
- **Logic added** (lines 929–961): Cross-turn accumulation with threshold checking

### Verification
```bash
✓ phone_digits_buffer field declared in ConversationState
✓ Buffer initialization: line 419
✓ Single-turn extraction: lines 915–928 (unchanged from Step 2)
✓ Buffer fallback path: lines 929–961 (NEW)
  - Lines 932–938: Extract digit tokens from utterance, accumulate in buffer
  - Lines 941–950: Check if buffer ≥ 10 digits, validate mobile prefix, extract
  - Lines 955–958: Overflow protection (> 13 digits)
  - Lines 959–961: Logging of accumulation progress
✓ Buffer cleared on success: line 924, 949, 954
✓ Buffer cleared on overflow: line 958
✓ Log tags: [PHONE_EXTRACT] with detailed progress
```

### Test Results
```
✓ D1a: T10 buffers 0151
✓ D1b: phone_number stays None after T10
✓ D2a: phone_number extracted from buffer on T11
✓ D2b: phone confirmed as mobile
✓ D2c: buffer cleared after use
✓ D3a: partial buffer accumulated
✓ D4a: buffer landline detected and rejected
✓ D4b: phone_number stays None on landline
```

---

## Fix 2: LLM Pre-Commit Sanitizer

### Location
- **File**: `server/brain/conversation_state.py`
- **Function added** (line 1101–1146): `sanitize_bot_text_pre_commit()`
- **Wired in**: `server/brain/node_manager.py` (lines 796–797)

### Function Details
```python
sanitize_bot_text_pre_commit(bot_text, state, escalating=True/False)
```

**Behavior**:
- If `escalating=False`: return bot_text unchanged
- If `escalating=True` and name invalid: rewrite "Herr Schmidt" → "Sie", strip name-related claims
- If `escalating=True` and phone invalid: replace "Es fehlt nichts mehr" → "Es fehlt noch Ihre Telefonnummer"
- If `escalating=True` and address invalid (with delivery): rewrite address-related claims
- Log: `[PreCommitSanitize] rewrote due to escalation`

### Integration Point (node_manager.py)
```python
# Line 791–798: F-A gate escalation path
elif state.should_escalate():
    logger.warning("[TRACE-2026-04-20] F-A gate ESCALATION...")
    state.escalation_requested = True
    from server.brain.conversation_state import sanitize_bot_text_pre_commit
    bot_response = sanitize_bot_text_pre_commit(bot_response, state, escalating=True)
    return bot_response
```

### Test Results
```
✓ D5a: rewrite triggers on escalation
✓ D5b: correctly rewrites to "Es fehlt noch Ihre Telefonnummer"
✓ D6a: no rewrite when escalating=False
✓ D7: no rewrite when all fields valid
```

---

## Instrumentation Status
All `[TRACE-2026-04-20]` tags are still in place from Phase 1:

```bash
$ grep -c "TRACE-2026-04-20" server/brain/*.py tools/executor.py
  server/brain/adk_turn_processor.py: 6
  server/brain/node_manager.py: 8
  server/brain/conversation_state.py: 4
  server/brain/conversation_nodes.py: 0
  tools/executor.py: 4
  Total: 22 trace points
```

These are preserved per ground rules — they will be removed after final verification.

---

## Service Status
```
● sailly-browser-demo.service - Sailly Browser Demo Server
  Active: active (running) since Mon 2026-04-20 15:16:37 UTC
  PID: 1206706
  Memory: 81.6M
  Port: 8080 (localhost)
```

**Last restart**: 2026-04-20 15:16:37 UTC (post-micro-pack deployment)  
**Syntax check**: PASS (both conversation_state.py and node_manager.py)

---

## Deployment Checklist

| Item | Status | Evidence |
|------|--------|----------|
| Bug D cross-turn buffer field | ✓ | `conversation_state.py:419` |
| Bug D buffer accumulation logic | ✓ | `conversation_state.py:929–961` |
| Bug D buffer extraction | ✓ | `conversation_state.py:941–950` |
| LLM pre-commit sanitizer function | ✓ | `conversation_state.py:1101–1146` |
| Sanitizer wired in F-A gate | ✓ | `node_manager.py:796–797` |
| All 8 unit tests pass | ✓ | `tests/test_micro_pack_bugD.py` |
| Service restarts cleanly | ✓ | Systemd active + running |
| Syntax valid (no parse errors) | ✓ | `python3 -c "import ast; ast.parse(...)"` |
| Instrumentation preserved | ✓ | 22 `[TRACE-2026-04-20]` tags intact |

---

## Ready for End-to-End Verification

**Timestamp**: 2026-04-20 15:16:42 UTC  
**Deployment complete**: YES ✓  
**Service running**: YES ✓  
**Next step**: Execute the live call scenario to verify both fixes work end-to-end
