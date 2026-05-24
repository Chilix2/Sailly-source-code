# Codex Evidence Pack

Generated setup context for a fresh Codex audit. This is an index of evidence,
not a verdict. Codex must verify each item before relying on it.

## Audit Contract

- Scope: phases A-I
- Runtime health endpoint: `/health` is canonical
- Service port: `8080`
- Headless websocket: `ws://127.0.0.1:8080/ws/headless`
- Postgres: port `5432`; authoritative raw call/transcript evidence
- Redis: port `6379`
- Result artifacts: `/tmp/scenario_validation/`; derived evidence/cache only
- Caller model: `grok-3-mini`
- Auditor model: `grok-4-1-fast-non-reasoning`
- Fixer model: `claude-haiku-4-5`

## Files Codex Must Inspect

### Core Contract

- `VALIDATION_RUN_CONFIG.md`
- `AGENTS.md`
- `CODEX_RUNBOOK.md`
- `docs/phase_architecture.md`
- `docs/audit_plan.md`

### Validation Harness

- `server/validation/AGENTS.md`
- `server/validation/scenario_based_loop.py`
- `server/validation/phase_runner.py`
- `server/validation/scenario_generator.py`
- `server/validation/grok_auditor_integration.py`
- `server/validation/haiku_fix_generator.py`
- `server/validation/fix_applier.py`
- `server/validation/postgres_metrics_fetcher.py`
- `server/validation/known_issues_advisor.py`
- `server/validation/known_issues.json`

### Product Behavior

- `server/brain/AGENTS.md`
- `server/brain/v4_pipeline.py`
- `server/brain/conversation_state.py`
- `server/brain/context_doc_builder.py`
- `server/brain/v4_turn_processor.py`
- `server/brain/layer1/text_mode_runner.py`
- `tools/executor.py`
- `configs/tenants/doboo.yaml`
- `server/main.py`

## Current Claims To Verify

These are claims from the previous validation summary. They must be checked
against Postgres and latest result artifacts.

| Claim | Evidence Pointer | Status |
| --- | --- | --- |
| 62/63 batches meet pass criteria | `/tmp/scenario_validation/batch_result_*.json` | unverified |
| H2.1_D2 is the only failing batch | latest H2.1 result plus Postgres transcripts | unverified |
| H2.2_D3 advanced by pass rate despite low composite | latest H2.2 result and transcripts | unverified |
| I1.2_D4 has 100 percent scenario pass rate but low composite | latest I1.2 result and transcripts | unverified |
| KEIN_READBACK false positives were caused by Euro-vs-symbol regex mismatch | `phase_runner.py` and flagged transcripts | unverified |
| Runtime health endpoint should be `/health` | user confirmation plus `fix_applier.py` default | verified by user, code drift unverified |
| Postgres is authoritative for raw transcripts | user confirmation | verified by user |

## Known Suspicious Areas

### Runtime Contract Drift

Observed during setup:

- `server/main.py` exposes `/healthz`.
- `VALIDATION_RUN_CONFIG.md` references `/healthz`.
- `fix_applier.py` defaults to `http://localhost:8080/health`.

Canonical target is `/health`. Codex should classify current mismatch as a
runtime-contract finding before judging validation quality.

### Result Artifact Semantics

Known risks:

- duplicate batch result files
- stale files skipped by `--resume`
- force-advance saved as a completed batch
- pass rate and Grok composite disagreeing
- saved artifact reflecting a reverted or stale code state

### Known-Issues Memory

`known_issues.json` currently reports schema `2.0`, 87 issues, and sources from
batch JSONs, agent transcripts, git commits, run config, and a May 20 agent
session. Codex must audit whether this memory is still accurate before using it
as advice.

## Commands For Codex To Run In Review Mode

Repository state:

```bash
git status --short
git diff -- server/brain server/validation configs/tenants/doboo.yaml server/main.py
git log -5 --oneline
```

Runtime state:

```bash
ss -tlnp | grep 8080
curl -sf http://localhost:8080/health
/home/charles2/postgres/usr/bin/pg_isready -h localhost -p 5432
pgrep -x redis-server
pgrep -af "scenario_based_loop|phase_runner" | grep python
```

Result artifacts:

```bash
ls -lt /tmp/scenario_validation/scenario_loop_report_*.json
ls -lt /tmp/scenario_validation/batch_result_*.json
```

Latest-result computation should be done by timestamp per batch. Do not trust
alphabetical order.

## Required First Audit Questions

Codex must answer these before proposing edits:

1. Is the runtime contract internally consistent?
2. Is the current service on port 8080 running fresh code?
3. Do saved result artifacts match Postgres transcripts?
4. Which batches are truly failing versus force-advanced or stale?
5. Are `known_issues_advisor.py` and `known_issues.json` helping or repeating
   stale failed fixes?
6. Are observed failures product bugs, harness bugs, caller-bot drift, or scorer
   bugs?
7. What is the smallest root-cause fix with the broadest safe improvement?

