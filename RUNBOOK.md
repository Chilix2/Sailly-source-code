# RUNBOOK — Session Heartbeat

**Last Update**: 2026-05-30 02:15 UTC  
**Status**: 🟢 ACTIVE (Week 1 Complete: File Structure Optimization)

## Current State

| Field | Value |
|-------|-------|
| **Phase** | Week 2: Multi-Tenant Isolation + call_id Logging |
| **Last Action** | Created CLAUDE.md, RUNBOOK.md, foundation.md, FSM-phases.md, enhanced billing_logger.py |
| **Next Action** | Implement tenant_id namespacing in node_manager.py + Redis isolation |
| **Blockers** | None (Week 1 priorities completed) |
| **Call Count (Month)** | 4,780 calls (May 1-29, $1,592.75 spent) |
| **Token Budget Used** | 73% (4.3B of 6.21B tokens/quarter) |

## Week 1 Completed ✅

- [x] CLAUDE.md — Root guidance (identity, startup, permissions)
- [x] RUNBOOK.md — Session heartbeat (phase tracking)
- [x] .cursor/settings.json — Safety layer (deny .env, ask bash)
- [x] context/foundation.md — Tenant ID, startup, constraints
- [x] context/specs/FSM-phases.md — 6 phases detailed spec
- [x] billing_logger.py — Added call_id, tenant_id, fsm_phase fields

## Recent Decisions

1. **Skip subagents** — Use Composer agent only (token efficiency)
2. **Obsidian MCP as Tier 0** — All transcripts indexed, semantic search active
3. **Week 1 focus** — File structure DONE (saves 5-10K tokens/session)
4. **Gap priority** — call_id logging DONE (enables 4-stack tracing)

## Known Issues

| Issue | Status | Assigned | Effort |
|-------|--------|----------|--------|
| Multi-tenant isolation gaps (Redis namespacing) | OPEN | Week 2 | 2h |
| Context bloat (9-10M tokens/session) | IN PROGRESS | Week 1-3 | 3h |
| Tool definition bloat (30+ schemas loaded) | OPEN | Week 3 | 2h |
| Progressive tool disclosure (phase-based) | PENDING | Week 3 | 3h |

## Tests to Run

- [ ] `pytest server/tests/test_conversation_fsm.py` (24 tests × 2 tenants)
- [ ] `python server/training/billing_logger.py` (verify call_id logging)
- [ ] `pytest server/tests/test_tenant_config.py` (tenant isolation)
- [ ] Check Redis keys: `redis-cli KEYS "doboo:*"` (should be isolated)

## Week 2 Priorities

1. **Implement tenant_id namespacing** (node_manager.py)
   - Composite keys: `{tenant_id}:{object_type}:{id}`
   - Add `_extract_tenant_id()` function
   - Update Redis operations

2. **Add per-tenant rate limits**
   - Track calls per tenant
   - Prevent noisy-neighbor (one tenant consuming budget)

3. **Verify call_id propagation**
   - FSM transitions log call_id
   - Tool calls include call_id
   - BillingLogger captures it

## Next Session Checklist

- [ ] Read CLAUDE.md (this doc)
- [ ] Read context/foundation.md (tenant startup)
- [ ] Check Redis for active conversations (`redis-cli KEYS "*:conversation:*"`)
- [ ] Load tenant config for active tenant
- [ ] Initialize FSM to GREETING phase (or recover if in_progress)
- [ ] Run Week 1 tests to verify structure is solid

---

**Remember**: Every session, check this file first. It saves 2-3K tokens by avoiding re-explaining.

