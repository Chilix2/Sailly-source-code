# Sailly Codex Audit Instructions

These instructions are for Codex or any external senior-dev agent auditing this
repository. They apply to the entire repository unless a nested `AGENTS.md`
overrides them.

## Primary Mission

Audit and improve the Sailly restaurant voice-agent validation system without
trusting prior AI summaries, generated reports, or saved pass/fail artifacts.
The validation loop is evidence under audit, not the source of truth.

Before editing, verify the full evidence chain:

1. Runtime contract and environment.
2. Validation harness and scorer code.
3. Postgres raw call/transcript evidence.
4. `/tmp/scenario_validation/` result artifacts.
5. Product behavior code.
6. Known-issues memory and previous fix history.

## Required Working Mode

- Start in read-only review mode.
- Read relevant files end-to-end before judging or editing them.
- Produce a plan before any edit.
- Make one scoped root-cause patch at a time.
- After each patch, run syntax/import checks, targeted tests, the affected
  validation batch, and a self-review of the final diff.
- Never use destructive git operations.
- Never edit locked validation configuration unless explicitly asked.

## Runtime Contract

The runtime contract must be checked before accepting validation results:

- Service command: `venv/bin/python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8080`
- Canonical health endpoint: `http://localhost:8080/health`
- Headless validation websocket: `ws://127.0.0.1:8080/ws/headless`
- Demo websocket endpoints: `/ws/demo`, `/ws/demo_text`
- Postgres: localhost port `5432`; authoritative raw call/transcript source
- Redis: localhost port `6379`; dashboard/session/transfer state
- Result artifacts: `/tmp/scenario_validation/`; useful cache/index, not authority
- Caller model: `grok-3-mini`
- Auditor model: `grok-4-1-fast-non-reasoning`
- Fixer model: `claude-haiku-4-5`

Important drift to audit: some current code/docs may still reference `/healthz`.
The canonical endpoint for future validation runtime is `/health`.

## Validation Scope

Testing scope is phases A-I. Treat them as a dependency ladder, not a flat list.
A fix that helps a late edge case but breaks an earlier invariant is invalid.

- Layer 0: tenant config, menu whitelist, validation runner, scorer regexes,
  result timestamps, transcript retrieval, service health, Postgres, Redis.
- Phase A: foundation reservation and FAQ invariants.
- Phase B: ordering, delivery, prices, address/name/order commit.
- Phase C: multi-intent composition.
- Phase D: stress and edge robustness.
- Phase F: late, urgent, hours, next-day, time-sensitive calls.
- Phase G: advanced multi-intent chains and state transitions.
- Phase H: negative, safety, complaint, discount, manager, competitor cases.
- Phase I: complex voice-agent edge cases such as rambling callers, connection
  issues, dietary questions, billing disputes, and long silence.

For every edit, state:

- affected phase(s)
- upstream invariants that might regress
- downstream scenarios to recheck
- exact validation command to run afterward

## Evidence Rules

Postgres is authoritative for raw call and transcript evidence. Files in
`/tmp/scenario_validation/` are derived artifacts and must be cross-checked for
staleness, duplicate batch results, force-advanced results, and scorer bugs.

Do not accept a saved score until you have checked:

- latest batch result by timestamp
- duplicate or stale result files
- pass rate semantics
- whether the run force-advanced
- whether the scorer emitted false positives or false negatives
- raw transcript(s) for weak or suspicious batches
- whether server code was fresh during the run

## Known Issues Memory

Read these before generating any fix:

- `server/validation/known_issues_advisor.py`
- `server/validation/known_issues.json`

Use them as institutional memory, not truth. Confirm every matched issue against
current code, current transcripts, and latest validation behavior. Do not repeat
documented failed fixes. Do not promote stale advice without evidence.

## Locked Configuration

Treat these as locked unless the user explicitly requests a config change:

- `--workers 5`
- `--stagger-s 3`
- `--max-attempts 8`
- `--output-dir /tmp/scenario_validation`
- `--resume` for interrupted/resumed runs
- phases A-I for full audit scope; canonical current foreground loop is F-G-H-I
  when continuing the May 2026 validation track
- fixer model `claude-haiku-4-5`
- caller `grok-3-mini`
- auditor `grok-4-1-fast-non-reasoning`

## Forbidden Fix Patterns

- Hardcoded scenario-specific hacks.
- Hardcoded menu items or prices outside tenant config.
- Broad fallback logic that masks missing state.
- Bare `except` around critical state mutation.
- Moving readback/commit logic into the wrong intent branch.
- Treating force-advance as proof of correctness.
- Trusting LLM-generated fixes without syntax, behavior, and regression checks.
- Changing validation thresholds to make failures pass.
- Restarting duplicate validation loops.

## Required Verification Before Claiming Done

For code changes:

1. `python -m py_compile` or equivalent import/syntax check for touched Python.
2. Targeted unit/smoke test if available.
3. Affected validation batch rerun.
4. At least one upstream regression batch when touching shared core state,
   intent routing, menu resolution, date/time parsing, or tool execution.
5. Diff self-review focused on AI mess: scope creep, misplaced blocks,
   stale config, broad fallbacks, hallucinated data, and missing tests.

For audit-only work:

1. Separate verifier bugs from product behavior bugs.
2. Return verdicts as `block`, `warn`, or `pass`.
3. Cite file paths, result files, batch IDs, call SIDs, or transcripts.
4. Mark each claim as `verified`, `unverified`, or `contradicted`.

