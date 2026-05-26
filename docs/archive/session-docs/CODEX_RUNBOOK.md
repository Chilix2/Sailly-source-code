# Codex Audit Runbook

This runbook explains how to run GPT-5.5 Codex as an independent senior-dev
auditor and, only after approval, as a scoped fixer for the Sailly validation
system.

## 1. Authentication

Codex CLI is installed on this machine as `codex`. If it asks for login, run:

```bash
codex login
```

Choose ChatGPT login. API-key auth is not required for foreground use.

## 2. Profiles

User-level config is at:

```text
/home/charles2_hotmail_de/.codex/config.toml
```

Profiles:

- `review`: read-only audit mode. Use first.
- `fix`: workspace-write mode. Use only after the audit plan is approved.

Default model is `gpt-5.5` with high reasoning.

## 3. Start A Read-Only Audit

From the repository root:

```bash
cd /home/charles2/sailly-browser-demo
codex --profile review
```

Initial prompt:

```text
/plan
Goal: Independently audit the Sailly validation system. Do not trust saved
validation results blindly. Verify the verifier, the runtime contract, Postgres
transcripts, /tmp/scenario_validation artifacts, known issues memory, and bot
behavior code. Scope is phases A-I.

Context: Read AGENTS.md, server/validation/AGENTS.md, server/brain/AGENTS.md,
VALIDATION_RUN_CONFIG.md, docs/phase_architecture.md, and
docs/codex_evidence_pack.md. Postgres is authoritative for raw call/transcript
evidence. /tmp/scenario_validation is an artifact cache/index. Canonical health
endpoint is /health. Headless websocket is ws://127.0.0.1:8080/ws/headless.

Constraints: Read-only. Do not edit files. Do not change config. Separate
harness bugs from product behavior bugs. Classify findings as block, warn, or
pass. Cite exact files, batch IDs, result files, call SIDs, and transcript
evidence.

Done when: You produce two verdicts: verifier verdict and product verdict, plus
a prioritized fix list if anything blocks confidence.
```

## 4. Verify The Evidence Chain

Codex should check at least:

```bash
git status --short
git diff -- server/brain server/validation configs/tenants/doboo.yaml
ls -lt /tmp/scenario_validation/scenario_loop_report_*.json
ls -lt /tmp/scenario_validation/batch_result_*.json
```

For runtime:

```bash
ss -tlnp | grep 8080
curl -sf http://localhost:8080/health
/home/charles2/postgres/usr/bin/pg_isready -h localhost -p 5432
pgrep -x redis-server
```

For validation-loop process safety:

```bash
pgrep -af "scenario_based_loop|phase_runner" | grep python
```

If a loop is already active, do not start another one.

## 5. Evidence Pack To Build Or Refresh

The audit should refresh or verify:

- latest result per batch by timestamp
- duplicate/stale batch files
- force-advanced batches
- weak batches: `H2.1_D2`, `H2.2_D3`, `I1.2_D4`
- latest scenario reports
- raw transcript call SIDs for suspicious runs
- known-issues matches from `known_issues_advisor.py`
- runtime-contract status

Postgres transcript data is authoritative. Result files are evidence, not truth.

## 6. Switch To Fix Mode Only After Approval

Use:

```bash
cd /home/charles2/sailly-browser-demo
codex --profile fix
```

Fix prompt template:

```text
/plan
Goal: Fix exactly one root cause from the approved audit findings.

Context: Read the relevant files end-to-end before editing. Use known_issues.json
only as advisory memory, not as truth. Preserve earlier phase invariants.

Constraints: One scoped patch. No locked config changes. No hardcoded scenario
hacks. No broad refactor. No destructive git operations. No secret exposure.

Done when: Syntax/import checks pass, a targeted test or smoke check passes,
the affected batch rerun is green or improved with evidence, at least one
upstream regression check passes if shared core logic changed, and Codex
self-reviews its diff.
```

## 7. Validation Commands

Canonical continuation command:

```bash
cd /home/charles2/sailly-browser-demo
set -a; source .env; set +a
PYTHONPATH=/home/charles2/sailly-browser-demo \
GOOGLE_APPLICATION_CREDENTIALS=/home/charles2/.ssh/sailly-voice-agent-key.json \
venv/bin/python3 -m server.validation.scenario_based_loop \
  --phases f,g,h,i \
  --workers 5 \
  --stagger-s 3 \
  --max-attempts 8 \
  --output-dir /tmp/scenario_validation \
  --resume
```

For targeted reruns, remove only the specific stale `batch_result_<BATCH>_*.json`
files after human approval, then use `--resume`.

## 8. Final Report Format

Codex should report:

```text
Verifier verdict: pass | warn | block
Product verdict: pass | warn | block

Findings:
- Severity:
- Type: harness | product | infrastructure | evidence
- Evidence:
- Impact:
- Proposed fix:
- Validation to run:
```

If Codex edits code, it must also report:

```text
Files changed:
Tests/checks run:
Affected phases:
Upstream regression checks:
Remaining risk:
```

