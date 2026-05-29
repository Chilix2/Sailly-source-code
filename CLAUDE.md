# Sailly Voice Agent — Live FSM Brain

## Identity

**Project**: Sailly — Production voice-agent for restaurant/service scheduling  
**Architecture**: FSM-driven multi-tenant system (not LLM-delegated flow)  
**Tech Stack**: Python 3.13, FastAPI, LiveKit, Deepgram (ASR), Gemini (LLM), Google Cloud TTS  
**Multi-Tenant Model**: doboo, pizzeria_napoli (isolated via tenant_id:user_id:conversation_id keys)  
**Compliance**: GDPR, C5 Testat (medical scheduling), emergency routing 95%+  
**Schema Version**: ConversationState v7 (Redis persistence)

---

## Startup Sequence (Session Init)

1. **Load this file** — understand architecture, constraints, permissions
2. **Read RUNBOOK.md** — what phase are we in, what was last action
3. **Load context/foundation.md** — tenant identity, startup hooks
4. **Check Redis** — recover conversation state if in_progress
5. **Initialize FSM** — set phase = GREETING (or resumed phase if call active)
6. **Verify tenant config** — load from `configs/tenants/{tenant_id}.yaml` via `TenantConfig.from_yaml()`
7. **Ready to process** — LLM calls FSM, FSM emits tools (never LLM → tools directly)

---

## Autonomous Permissions

**WITHOUT asking:**
- Read any file under `server/brain/`, `server/core/`, `configs/`, `server/tests/`
- Read Redis state for conversation recovery
- Trace FSM transitions and inspect tool calls
- Write to RUNBOOK.md (session tracking)
- Write to `/tmp/` (debug logs)

**MUST ask before:**
- Modifying conversation_fsm.py, conversation_state.py, slot_extractors.py
- Changing tenant configs (YAML files)
- Executing tools (send_sms, create_order, transfer_to_human) — only emit via FSM
- Writing to server/, tools/, configs/

**NEVER do:**
- Read `.env`, `sailly-voice-agent-key.json`, SSH keys
- Execute `rm -rf`, `curl`, unvetted Bash
- Hardcode tenant values or thresholds
- Bypass tenant_id isolation (use composite keys always)

---

## Non-Negotiable Rules

1. **LLM for language, code for state**
   - FSM drives conversation flow (not LLM text)
   - All state transitions in conversation_fsm.py
   - LLM generates natural responses, FSM decides next phase

2. **Zero tenant hardcodes**
   - All thresholds, menus, confirmations from TenantConfig YAML
   - No `if tenant == "doboo"` in code
   - If feature needed, add to TenantConfig, load via factory

3. **Category B tools are code-driven**
   - `create_order`, `send_sms`, `transfer_to_human` emitted by FSM transitions
   - Never called by LLM directly
   - Protected by two-pass confirmation guard (exact token match + LLM scorer >0.85)

4. **Slots.to_dict() / from_dict() required**
   - ConversationState persists to Redis via schema_version 7
   - All slot changes must round-trip cleanly
   - Never skip serialization — breaks recovery

5. **Multi-tenant isolation**
   - Every query uses composite key: `tenant_id:user_id:conversation_id`
   - Every tool call includes tenant context
   - Redis namespacing enforced at node_manager layer
   - Per-tenant rate limits prevent noisy-neighbor

---

## Key Architectural Decisions

| Decision | Why | Location |
|----------|-----|----------|
| FSM-first not LLM-first | Predictable, auditable, compliant | `conversation_fsm.py` phases |
| Slots as typed dataclass | Type safety + schema migration | `conversation_state.py` |
| TenantConfig factory pattern | Single source of truth, no hardcodes | `tenant_config.py` + YAML |
| Category A vs B tool split | State-safe execution, LLM cannot leak PII | `tools/executor.py` |
| Two-pass confirmation | Guards against slot injection attacks | `node_manager.check_forced_commits()` |
| German NLP with ASCII fallback | Customer base (EU), backwards compat | `slot_extractors.py` |

---

## Current State

**Phase**: Active development (Phase 0B observability → production Phase 1 hardening)  
**Last Milestone**: May 29 — Phase 4b regression gate complete, observability dashboard deployed  
**Next Action**: Implement token optimization via Obsidian MCP + context window management  
**Blockers**: Silent failure handling in v4_pipeline_clean.py (LiveKit issue #4933 pattern)

---

## Context Layers

- **RUNBOOK.md** — Session-specific state (phase, last action, next action)  
- **context/foundation.md** — Tenant identity, startup, constraints  
- **context/specs/FSM-phases.md** — 6 phases, transitions, exit conditions  
- **context/design/State-schema.md** — ConversationState v7 lifecycle  
- **server/brain/conversation_fsm.py** — Live FSM (source of truth)  
- **configs/tenants/{tenant_id}.yaml** — Tenant config (override rules)

---

## Success Metrics

- ✅ All FSM transitions use state machine (no LLM shortcuts)
- ✅ Zero tenant data leaks (composite keys enforced)
- ✅ Two-pass confirmation on all Category B tools
- ✅ Emergency routing ≥ 95% (SLA)
- ✅ Token budget < $1,600/month (MCP optimization active)
- ✅ Silent failures logged with call_id for tracing

---

## Commands

- `RUNBOOK.md` — Check this if confused about where we are
- `context/foundation.md` — Understand tenant, startup rules
- `server/brain/conversation_fsm.py` — Trace phase transitions
- `conversation_state.py` → `to_dict()` / `from_dict()` — Understand persistence

---

**Last Updated**: 2026-05-30 | **Schema**: v7 | **Tenants**: doboo, pizzeria_napoli | **Compliance**: GDPR, C5
