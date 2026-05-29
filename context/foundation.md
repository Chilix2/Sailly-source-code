# Foundation — Sailly Project Identity & Startup

## Project Identity

**Name**: Sailly  
**Type**: Voice-driven scheduling & ordering for restaurants/services  
**Stack**: Python 3.13 + FastAPI + LiveKit (RTC) + Deepgram (ASR) + Gemini (LLM) + Google Cloud TTS  
**Multi-Tenant**: doboo (test), pizzeria_napoli (prod), builder_lab_doboo (sandbox)  
**Deployment**: Google Cloud Run (stateless) + Redis (session state) + Cloud Storage (logs)  
**SLA**: Emergency routing ≥ 95% (human transfer on FSM failure)

---

## Startup Sequence

**Every session, execute this checklist:**

1. **Load CLAUDE.md** (2 min read)
   - Understand FSM architecture
   - Review non-negotiable rules
   - Check current phase

2. **Load RUNBOOK.md** (1 min read)
   - Check last action
   - Verify blockers
   - See test list

3. **Verify Redis connectivity**
   ```bash
   redis-cli PING
   redis-cli KEYS "*:conversation:*" | head -5
   ```

4. **Load active tenant config**
   ```python
   from server.core.tenant_config import load_tenant_config
   ctx = load_tenant_config("doboo")  # or pizzeria_napoli
   print(f"Tenant: {ctx.tenant_id}, Menu items: {len(ctx.menu_items)}")
   ```

5. **Check FSM module**
   ```python
   from server.brain.conversation_fsm import ConversationFSM
   fsm = ConversationFSM()
   print(f"FSM phases: {fsm.phases}")  # Should be 6
   ```

6. **Initialize billing logger**
   ```python
   from server.training.billing_logger import init_billing_logger
   logger = init_billing_logger(run_id="dev_session_20260530")
   ```

7. **Ready to trace/debug** — use RUNBOOK.md for context

---

## Tenant Configurations

| Tenant | Type | Menu Items | Timezone | Locale | Features |
|--------|------|-----------|----------|--------|----------|
| doboo | Test | 12 | Europe/Berlin | de_DE | Order + Reservation |
| pizzeria_napoli | Prod | 18 | Europe/Rome | it_IT | Order only |
| builder_lab_doboo | Sandbox | 8 | Europe/Berlin | de_DE | All features |

**Load any tenant**:
```python
from server.core.tenant_config import TenantConfig
cfg = TenantConfig.from_yaml("configs/tenants/doboo.yaml")
print(cfg.confirmation_token, cfg.menu_items, cfg.business_hours)
```

---

## FSM Phases (6 Total)

| Phase | Purpose | Entry | Exit |
|-------|---------|-------|------|
| GREETING | Intro + intent detect | Call starts | Intent captured |
| INFO | FAQ, menu, hours | User asks Q | User ready for transaction |
| ORDER | Slot collection | User wants to order | All slots filled |
| RESERVE | Slot collection (date/time/party) | User wants reservation | Confirmation ready |
| READBACK | Confirmation + 2-pass guard | Slots complete | Token exact match + LLM >0.85 |
| COMMITTED | Execute Category B tools | Readback OK | Call end |

**Each phase is deterministic** — FSM.step(slots, executor, ctx) returns next_phase + actions.

---

## Key Files

| File | Lines | Purpose |
|------|-------|---------|
| server/brain/conversation_fsm.py | ~800 | FSM state machine, all 6 phases |
| server/brain/conversation_state.py | ~600 | ConversationState dataclass + persistence |
| server/brain/slot_extractors.py | ~400 | German NLP: phone, date, address, items |
| server/brain/v4_pipeline_clean.py | ~250 | Clean v4 pipeline (TTS, FSM, tools) |
| server/core/tenant_config.py | ~400 | TenantConfig dataclass + YAML factory |
| server/tools/handlers/ | ~200 | Category A + B tool implementations |
| configs/tenants/{id}.yaml | ~100 ea | Tenant definitions |

---

## Non-Negotiable Architecture Constraints

### 1. LLM for Language, Code for State
- FSM drives conversation flow
- LLM generates natural responses
- All transitions in conversation_fsm.py (not LLM decision)

### 2. Zero Tenant Hardcodes
- No `if tenant == "doboo"` in code
- All config from YAML + TenantConfig factory
- Feature flags in TenantConfig fields

### 3. Category B Tools are Code-Driven
- `create_order`, `send_sms`, `transfer_to_human` emitted by FSM
- Never LLM → tool directly
- Two-pass confirmation guard: exact token + LLM scorer >0.85

### 4. Slots.to_dict() / from_dict() Required
- ConversationState persists to Redis
- Schema v7 migration required
- All slot changes must round-trip

### 5. Multi-Tenant Isolation
- Keys: `tenant_id:user_id:conversation_id`
- No cross-tenant data leaks
- Per-tenant rate limits (prevent noisy-neighbor)

### 6. Call_id for 4-Stack Tracing
- Every FSM transition logs call_id
- Every tool call includes call_id
- Stack 1-4 tracing enabled (Telephony, Audio, Intelligence, Output)

---

## Debugging Checklist

**Silent failure? Check these:**
1. Did FSM.step() return error result?
   ```python
   from server.brain.conversation_fsm import FunctionCallResult
   result.is_error, result.error_message
   ```
2. Is call_id logged in billing_logger?
   ```bash
   grep "call_id" /var/log/sailly/billing/billing_2026-05-30.jsonl | tail -5
   ```
3. Is tenant_id isolated (Redis key check)?
   ```bash
   redis-cli KEYS "doboo:*" | wc -l
   redis-cli KEYS "pizzeria_napoli:*" | wc -l
   ```

**Token waste? Check these:**
1. Are all 6 FSM phases used, or are we in loops?
2. Is conversation_state reloaded unnecessarily?
3. Are all tenant configs parsed fresh each session?
4. Are tool schemas pre-loaded for unused phases?

---

## Progress (May 2026)

| Date | Milestone |
|------|-----------|
| Mar 1-15 | Phase 0: Legacy cleanup |
| Mar 16-31 | Phase 1-2: FSM refactor |
| Apr 1-15 | Phase 3-4: Multi-tenant hardcodes |
| Apr 16-30 | Phase 4a: Golden dataset |
| May 1-15 | Phase 4b: Regression gate |
| May 16-29 | Phase 0B: Observability (call_id, 4-stack tracing) |
| May 30+ | Week 1: File structure optimization (CLAUDE.md, RUNBOOK.md) |

**Next**: Multi-tenant isolation enforcement (Week 2), token optimization (Week 3).

---

**Remember**: Every session, trace the path through CLAUDE.md → RUNBOOK.md → conversation_fsm.py. This saves 5-10K tokens.
