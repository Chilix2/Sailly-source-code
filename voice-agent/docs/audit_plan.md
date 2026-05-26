# Codex Audit State

Use this file as a durable scratchpad for long Codex audits. Keep it updated so
a fresh context can resume without trusting chat memory.

## Current Objective

Audit the Sailly validation system end-to-end across phases A-I. Verify the
verifier, runtime contract, Postgres evidence, result artifacts, known-issues
memory, and product behavior before making any fixes.

## Runtime Contract

- Canonical health endpoint: `/health`
- Sailly service: port `8080`
- Headless websocket: `ws://127.0.0.1:8080/ws/headless`
- Postgres: port `5432`, authoritative raw transcript/call evidence
- Redis: port `6379`
- Result artifacts: `/tmp/scenario_validation/`, derived evidence only

## Files Read

Record each file read end-to-end:

- [ ] `AGENTS.md`
- [ ] `CODEX_RUNBOOK.md`
- [ ] `VALIDATION_RUN_CONFIG.md`
- [ ] `docs/phase_architecture.md`
- [ ] `docs/codex_evidence_pack.md`
- [ ] `server/validation/AGENTS.md`
- [ ] `server/brain/AGENTS.md`
- [ ] `server/validation/scenario_based_loop.py`
- [ ] `server/validation/phase_runner.py`
- [ ] `server/validation/grok_auditor_integration.py`
- [ ] `server/validation/haiku_fix_generator.py`
- [ ] `server/validation/fix_applier.py`
- [ ] `server/validation/known_issues_advisor.py`
- [ ] `server/validation/known_issues.json`
- [ ] `server/brain/v4_pipeline.py`
- [ ] `server/brain/conversation_state.py`
- [ ] `server/main.py`

## Evidence Reviewed

Record exact artifacts and call SIDs:

- Latest scenario report:
- Batch result files:
- Duplicate/stale result files:
- Postgres call SIDs:
- Raw transcripts checked:
- Known-issues matches:

## Findings

Use this format:

```text
ID:
Severity: block | warn | low
Type: harness | product | infrastructure | evidence
Claim:
Evidence:
Contradiction:
Impact:
Recommended action:
Validation to run:
```

## Current Hypotheses

- 

## Commands Run

Record command, purpose, and result summary:

```text
Command:
Purpose:
Result:
```

## Fix Plan Queue

Only add items after read-only audit:

```text
Root cause:
Files to edit:
Phase affected:
Upstream invariants at risk:
Validation to run after edit:
Approval status:
```

## Final Verdict

```text
Verifier verdict:
Product verdict:
Confidence:
Remaining risks:
```

