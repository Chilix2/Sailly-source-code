# Validation Harness Audit Instructions

These instructions apply to `server/validation/` and override the repository
root guidance for validation-harness work.

## Audit Posture

Treat every validator, scorer, report, and run artifact as suspect until proven
against raw evidence. The harness can be wrong even when the bot is right.

Primary files to read for validation work:

- `loop_runner_v2.py` (Phase 4b: deterministic regression gate, replaces scenario_based_loop)
- `phase_runner.py`
- `scenario_generator.py`
- `postgres_metrics_fetcher.py`
- `known_issues_advisor.py`
- `known_issues.json`

Deprecated/archived:
- `scenario_based_loop.py` (Phase 4c: deleted; whack-a-mole anti-pattern replaced by loop_runner_v2)

## Runtime Contract

Validation must use:

- Sailly server on port `8080`
- Headless websocket `ws://127.0.0.1:8080/ws/headless`
- Canonical health endpoint `/health`
- Postgres on `5432` as authoritative raw transcript/call evidence
- Redis on `6379` for runtime state where applicable
- Output artifacts under `/tmp/scenario_validation/`

If code or docs still refer only to `/healthz`, flag that as runtime-contract
drift. Do not silently accept health-check mismatches.

## Result Artifact Rules

Before using any batch result:

- Pick the latest file by timestamp.
- Identify duplicate result files for the same batch.
- Check whether the batch was force-advanced.
- Check whether pass rate and composite score disagree.
- Cross-check suspicious results against Postgres transcripts.
- Sample raw transcripts for weak batches, flaky batches, and any claimed
  improvement from an automated fix.

Postgres is authoritative. `/tmp/scenario_validation/` is a derived artifact
store and can be stale or misleading.

## Known Issues Rules

`known_issues_advisor.py` and `known_issues.json` are institutional memory.
Use them to avoid repeating failed fixes, but audit them for staleness.

When using known issues:

- Confirm issue match against current Grok report and raw transcripts.
- Check whether `confirmed_working_fixes` still apply to current code.
- Check whether `fix_attempts` document a failed approach that Codex is about
  to repeat.
- Treat `unmatched_fix_log` as candidate evidence, not as guidance.
- Never allow the library to self-reinforce a bad pattern without fresh proof.

## Scorer Audit Rules

For every scorer or caller-bot finding, ask:

- Is this a real bot behavior issue?
- Is this caller-bot drift or simulator corruption?
- Is this a regex or deterministic checker false positive?
- Is this a Grok judge consistency issue?
- Does the transcript show the claimed problem?

Known failure class: readback checks previously matched `EUR` symbol only while
the bot said `Euro`, causing false `KEIN_READBACK` flags. Similar symbol/word
mismatches must be audited before fixing product code.

## Fix-Applier Rules

`fix_applier.py` can restart the service and revert modified files. Audit:

- process ownership and stale server behavior
- health endpoint consistency
- whether the server restarts with fresh code
- whether automatic reverts restore the right baseline
- whether generated patches introduce syntax errors or misplaced code blocks

Do not let an automated fixer change locked run parameters to improve scores.

