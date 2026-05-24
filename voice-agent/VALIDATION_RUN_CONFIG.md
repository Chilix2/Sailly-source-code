# Sailly Validation Run — Canonical Configuration

> **Source of truth.** Derived from 10 foreground run logs in `/tmp/scenario_validation/`.
> Never change run parameters without updating this file.

---

## ⚠️ SINGLE-RUN RULE (MANDATORY — read before touching the loop)

> **Only one validation process may run at any time.**  
> Starting a second run wastes the entire XAI token budget in duplicate caller-bot calls.

### Before starting or restarting the loop — always run:

```bash
pgrep -af "scenario_based_loop|phase_runner" | grep python
```

If anything is returned: **stop. Do not start another run.** Kill the existing one first if it is stale or errored:

```bash
pkill -9 -f "scenario_based_loop"
```

### After any fix, error, or crash — always resume, never restart fresh:

```bash
# ✅ CORRECT — picks up from the last completed batch
venv/bin/python3 -m server.validation.scenario_based_loop \
  --phases a,e --workers 5 --stagger-s 3 \
  --output-dir /tmp/scenario_validation \
  --resume \
  2>&1 | tee "/tmp/scenario_validation/foreground_AE_$(date +%s).log"

# ❌ WRONG — restarts all batches from scratch, burns full token budget again
venv/bin/python3 -m server.validation.scenario_based_loop \
  --phases a,e --workers 5 --stagger-s 3 \
  --output-dir /tmp/scenario_validation \
  2>&1 | ...
```

> `--resume` skips only batch results that are verifier-passing (`threshold_met=true`) and are not marked `force_advanced` or `audit_failed`.  
> A fresh run (no `--resume`) is **only** correct when intentionally re-running ALL batches from zero.

---

## 💸 TOKEN / COST CONTROL RULE (MANDATORY)

> Validation runs can burn Cursor/API budget very quickly because each batch can
> involve 7 caller-bot conversations, Grok audits, Haiku fixer prompts with large
> code context, transcript reads, and service restarts. The operator must protect
> budget first.

### Hard stop conditions

Stop paid validation/fixer loops immediately when any of these occur:

- The same batch fails twice with the same category of issue.
- A rerun starts with infrastructure noise (`ConnectionRefusedError`, stale
  uvicorn, missing bot turns, port conflicts, duplicated services).
- Haiku/Grok generates malformed JSON or exact-match fixes fail.
- The failure appears semantic or architectural rather than a simple localized
  typo.
- A batch has already consumed two full 7-persona attempts during debugging.

After a hard stop, do **not** run another full batch until root cause is proven
with local evidence.

### Required root-cause workflow before another full batch

1. Inspect the latest `batch_result_<KEY>_*.json`, Postgres transcripts, raw
   `google_tool_calls`, and server logs for the failing call SIDs.
2. Separate the problem type:
   - **Product bug:** bot state/readback/tool behavior is wrong.
   - **Harness bug:** caller knowledge, metrics fetcher, loop detector, expected
     tools, or audit prompt is wrong.
   - **Infrastructure bug:** stale server, duplicate uvicorn, port conflict,
     connection refused, missing transcript writes.
3. Reproduce with the cheapest deterministic check possible:
   - Prefer unit/inline parser tests (`_extract_all_dishes`, quantity parsing,
     name parsing, readback builder logic).
   - Then run one single-persona smoke scenario.
   - Only after that passes, run the full 7-persona batch.
4. Disable/avoid LLM fixer loops while root-causing. Apply manual surgical fixes
   and verify syntax/lints first.
5. Re-run Grok audit only after the raw transcript/tool evidence is sane.

### Budget approval gate

If Cursor/API spend is suspected to be high, or if more than two full batch
reruns are needed for one issue, stop and ask for explicit approval before
continuing. The approval request must state:

- exact batch(es) to run,
- expected number of caller-bot conversations,
- whether Grok audit will run,
- whether Haiku fixer will run,
- why cheaper local/single-scenario checks are insufficient.

### Forbidden burn patterns

- Do not patch blindly and re-run the same full batch repeatedly.
- Do not let the validation loop auto-fixer consume attempts while the root
  cause is still unknown.
- Do not trust saved scores until verifier semantics are checked.
- Do not run full A-I while an earlier phase/batch is known to be untrusted.
- Do not start a new run to “bring it foreground” if an existing run can be
  monitored by log/artifact inspection.

---

## Light Validation Run Configuration (debug mode)

> **Purpose:** debug code paths cheaply after the heavy A-I build run has already
> produced coverage. Light validation is for root-cause work, not final sign-off.

### Light runner

Use:

```bash
cd /home/charles2/sailly-browser-demo
set -a; source .env; set +a

PYTHONPATH=/home/charles2/sailly-browser-demo \
GOOGLE_APPLICATION_CREDENTIALS=/home/charles2/.ssh/sailly-voice-agent-key.json \
venv/bin/python3 -m server.validation.light_validation_loop \
  --phase b \
  --batch B1.2_D2 \
  --max-attempts 3 \
  --workers 5 \
  --stagger-s 3 \
  --output-dir /tmp/scenario_validation_light \
  --all-personas \
  2>&1 | tee "/tmp/scenario_validation_light/light_B1.2_D2_$(date +%s).log"
```

### What light mode does

- Runs a **single smoke persona first** (`neutral` by default).
- Runs all 7 personas only if the smoke scenario passes.
- Uses the real `run_one_scenario` caller/server path.
- Uses deterministic scoring only:
  - expected tool calls present,
  - no failed tool calls,
  - no `[Achtung Sailly:]` flags,
  - no adjacent assistant loop,
  - transcript exists,
  - commit evidence present where expected.
- Emits `light_result_<BATCH>_<mode>_attempt<N>_<ts>.json`.
- Includes `known_issues_advisor.py` guidance in the artifact for GPT-5.5/Codex review.

### What light mode does NOT do

- Does **not** run Grok audit.
- Does **not** run Haiku fixer.
- Does **not** run Grok web research.
- Does **not** restore `/tmp/v4_pipeline_clean_baseline.py`.
- Does **not** auto-call GPT/Codex. The Cursor foreground agent reads the artifact
  and fixes manually.

### Light mode limits

| Setting | Value |
|---------|-------|
| `--max-attempts` | `3` maximum; higher is rejected |
| Smoke persona | `neutral` by default |
| Full persona run | only after smoke pass |
| Grok audit | off |
| Haiku fixer | off |
| Web research | off |
| Context strategy | artifact + targeted files only |

### GPT-5.5 / Codex role in light mode

Cursor GPT-5.5 acts as the debugger/fixer outside the Python loop:

1. Read the latest `light_result_*.json`.
2. Inspect only the call SIDs/transcripts/tool rows involved.
3. Inspect targeted source files only.
4. Apply small manual patches.
5. Run syntax/lint checks.
6. Re-run smoke before full 7-persona batch.

Do **not** call the heavy Haiku fixer unless explicitly approved.

### When to escalate from light to heavy validation

Only return to `scenario_based_loop.py` when:

- smoke persona passes,
- full 7-persona light batch passes,
- tool calls and transcripts are sane,
- no infrastructure noise occurred,
- the Cursor GPT-5.5 external review agrees the batch is ready.

Then resume the heavy run with `--resume`, never from scratch.

---

## Services Required (must be up before any run)

| Service | Check | Start if down |
|---------|-------|---------------|
| Sailly (port 8080) | `curl -sf http://localhost:8080/health` | `cd ~/sailly-browser-demo && venv/bin/python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8080` |
| Postgres (port 5432) | `/home/charles2/postgres/usr/bin/pg_isready -h localhost -p 5432` | runs as charles2 user, check `pgdata` |
| Redis | `pgrep -x redis-server` | `$HOME/bin/redis-server --daemonize yes --port 6379 --save "" --appendonly no` |

---

## API Keys (loaded from `.env` — always `source .env` before running)

```
ANTHROPIC_API_KEY  → Claude Haiku 4.5 fixer (fix generator)
XAI_API_KEY        → Grok (caller bot: grok-3-mini | auditor: grok-4-1-fast-non-reasoning)
OPENAI_API_KEY     → fallback caller if XAI unavailable
DEEPGRAM_API_KEY   → STT (loaded by Sailly server itself)
GOOGLE_APPLICATION_CREDENTIALS=/home/charles2/.ssh/sailly-voice-agent-key.json

# Optional model overrides (env vars):
CALLER_BOT_MODEL   → default: grok-3-mini       (phase_runner.py)
GROK_AUDIT_MODEL   → default: grok-4-1-fast-non-reasoning  (grok_auditor_integration.py)
```

---

## Fix Model

```
claude-haiku-4-5   (set in server/validation/haiku_fix_generator.py DEFAULT_HAIKU_FIX_MODEL)
```

**Do NOT change to sonnet or any other model without explicit instruction.**

---

## Canonical Run Command

```bash
cd /home/charles2/sailly-browser-demo
set -a; source .env; set +a

# ── PRE-FLIGHT: confirm no other run is active ──────────────────────────────
pgrep -af "scenario_based_loop|phase_runner" | grep python && echo "ERROR: run already active — abort" && exit 1

# ── START or RESUME (always --resume unless explicitly starting from scratch) ─
PYTHONPATH=/home/charles2/sailly-browser-demo \
GOOGLE_APPLICATION_CREDENTIALS=/home/charles2/.ssh/sailly-voice-agent-key.json \
venv/bin/python3 -m server.validation.scenario_based_loop \
  --phases f,g,h,i \
  --workers 5 \
  --stagger-s 3 \
  --max-attempts 8 \
  --threshold 80.0 \
  --output-dir /tmp/scenario_validation \
  --resume \
  2>&1 | tee "/tmp/scenario_validation/foreground_FGHI_$(date +%s).log"
```

> Remove `--resume` **only** when intentionally wiping progress and re-running all batches from zero.

### Parameters (NEVER change without instruction)

| Parameter | Value | Notes |
|-----------|-------|-------|
| `--workers` | `5` | All 10 logs confirm 5 concurrent workers |
| `--stagger-s` | `3` | All 10 logs confirm 3s stagger (NOT the CLI default of 5) |
| `--output-dir` | `/tmp/scenario_validation` | All logs confirm this path |
| `--threshold` | `80.0` | Explicit current FGHI gate for this validation track |
| `--max-attempts` | `8` | Explicit current retry cap for this validation track |
| `--resume` | **always include** unless fresh start | Skips only verifier-passing, non-force-advanced, non-audit-failed batches |

### Phase values for `--phases`

| Run | `--phases` value |
|-----|-----------------|
| Phase A only (fresh/retry) | `a` |
| Phase A → E | `a,e` |
| **Phases F → I (canonical current)** | `f,g,h,i` ← **USE THIS** |
| All active phases | `a,e,f,g,h,i` |
| Phases B+C+D (skip — already passing) | `b,c,d` |

### Phase Execution Order (MANDATORY)
> **Rule (2026-05-19):** A → E → F → G → H → I  
> Skip B, C, D (already passing).  
> Phases F–I: 168 scenarios defined in `scenario_generator.py` (added 2026-05-19).  
> Phase J (end-to-end production) is out of scope.

---

## Python Interpreter

Always use the **project venv**, never system python or /tmp venvs:

```bash
/home/charles2/sailly-browser-demo/venv/bin/python3
```

---

## Output Location

```
/tmp/scenario_validation/
  foreground_phase<X>_<timestamp>.log   ← tee'd stdout/stderr
  batch_result_<BATCH>_<timestamp>.json ← per-batch result
  scenario_loop_report_<timestamp>.json ← phase-level summary
```

---

## Phase Status (as of 2026-05-19 15:45 — XAI CREDIT OUTAGE STOP)

> ⚠️ **XAI API credits exhausted at ~15:40 UTC+2 on 2026-05-19.**  
> Loop was stopped to prevent garbage data. Restart once credits are topped up (see below).  
> `conversation_state.py` reverted to pre-outage state. `v4_pipeline.py` syntax is clean.

| Impl Phase | A–J Concept | Batches | Status |
|-----------|-------------|---------|--------|
| `a` | A Basic Single-Intent (Reservation + FAQ) | 17 | ✅ All resumed — **DONE** |
| `b` | B Ordering / Delivery | 10 | ✅ All pass — **SKIP** |
| `c` | C Complex FAQ + Edge Cases | 5 | ✅ All pass — **SKIP** |
| `d` | D Escalation + Stress | 7 | ✅ All pass — **SKIP** |
| `e` | E Delivery & Address | 8 scripts × 7 personas = 56 | ✅ Complete — **DONE** |
| `f` | F Late & Urgent Calls | 6 batches | ⚠️ **PARTIAL** — 4/6 done: F1.1=84✅ F1.2=80✅ F1.3=83✅ **F2.1=86✅** F2.2=21❌ F2.3=41❌ |
| `g` | G Multi-Intent | 6 batches | 🔴 **BLOCKED (XAI outage)** — 2/6 valid: G1.3=84✅ G2.1=86✅; G1.1/G1.2/G2.2/G2.3 need re-run |
| `h` | H Negative / Safety | 7 batches | 🔴 **BLOCKED (XAI outage)** — 1/7 valid: H1.1=86✅; H1.2–H3.1 not yet run |
| `i` | I Complex Edge Cases | 5 batches | 🔴 **BLOCKED (XAI outage)** — 1/5 valid: I1.1=92✅; I1.2–I2.3 not yet run |

### Batches remaining (14 total — need XAI credits):

| Batch | Status |
|-------|--------|
| G1.1_D2 | needs re-run (invalid 0.0 result from outage, moved to `/tmp/scenario_validation/invalid_xai_outage/`) |
| G1.2_D3 | not yet run |
| G2.2_D4 | not yet run |
| G2.3_D5 | not yet run |
| H1.2_D2 | not yet run |
| H1.3_D3 | not yet run |
| H2.1_D2 | not yet run |
| H2.2_D3 | not yet run |
| H2.3_D4 | not yet run |
| H3.1_D5 | not yet run |
| I1.2_D4 | not yet run |
| I2.1_D3 | not yet run |
| I2.2_D4 | not yet run |
| I2.3_D5 | not yet run |

### Restart command (once XAI credits restored):

```bash
cd /home/charles2/sailly-browser-demo
set -a; source .env; set +a
pgrep -af "scenario_based_loop" | grep python && echo "already running" && exit 1
PYTHONPATH=/home/charles2/sailly-browser-demo \
GOOGLE_APPLICATION_CREDENTIALS=/home/charles2/.ssh/sailly-voice-agent-key.json \
SKIP_VERTEX_PREFLIGHT=1 \
venv/bin/python3 -m server.validation.scenario_based_loop \
  --phases f,g,h,i \
  --workers 5 \
  --stagger-s 3 \
  --max-attempts 8 \
  --threshold 80.0 \
  --output-dir /tmp/scenario_validation \
  --resume \
  2>&1 | tee "/tmp/scenario_validation/foreground_FGHI_retry_$(date +%s).log"
```

### Phase E Final Results (2026-05-19, after 3 runs)

> **Note on batch result files:** The EIR gate saves the score at gate-fire time, which can be a regression attempt score rather than the best or reverted baseline. True bot capability (code state) is often better than the saved file suggests. Use a fresh no-resume run for accurate baselines.

| Batch | Saved Score | Saved Pass | True Capability | Notes |
|-------|-------------|------------|-----------------|-------|
| E1.1_D1 | 57.2 | 1/7 | ~64/2-3 | Stuck — needs deeper fix |
| E1.2_D2 | 67.0 | **6/7 ✓** | ~76-79/4-6 | 6/7 threshold met |
| E1.3_D3 | 57.2 | 4/7 | **75.2/7/7 ★** | Code at attempt 3 = ALL PASS |
| E1.4_D3 | 76.8 | 6/7 ✓ | 76.8/6-7 | Stable plateau |
| E1.5_D2 | 58.8 | 2/7 | **76.8/7/7 ★** | Code reverted = ALL PASS |
| E2.1_D2 | 63.2 | **6/7 ✓** | 63.2/6 | Stable |
| E2.2_D3 | 75.2 | **7/7 ★** | 75.2/7/7 | ALL PASS — stable |
| E2.3_D4 | 69.2 | 1/7 | ~76.8/3 | Hardest — partial improvement |

**By saved batch results:** 4/8 = 50% batches ≥6/7  
**By true code capability:** ~5–6/8 = 62–75% batches ≥6/7  
**Goal:** ≥80% = 7/8 batches

**Key fix applied 2026-05-19:** `_slot_ask_count` AttributeError in `v4_pipeline.py` — fixed by adding `if not hasattr(state, "_slot_ask_count"): state._slot_ask_count = {}` before pre-commit name check (line 932). Impact: E2.3 improved from 28.2→73.8 (+45.6), E1.5 from 60.2→76.8/7/7.

**Composite ceiling at ~76–77:** `tool_accuracy` metric (40% weight) ≈ 40–50/100 because the bot makes partial but not all required tool calls (create_order, create_reservation). Reaching ≥ 95 composite requires fixing tool-calling in delivery/address scenarios.

**Phases F–I Results (2026-05-19 re-run, partial — stopped by XAI outage):**

| Phase | Batches | Grok≥80 | Avg Grok | Notable |
|-------|---------|---------|----------|---------|
| F | 6 total | **4/6 (67%)** | 71.3 | F1.1=84✅ F1.2=80✅ F1.3=83✅ **F2.1=86✅ NEW**; F2.2=21❌ F2.3=41❌ |
| G | 2/6 valid | 2/2 valid passing | — | G1.3=84✅ G2.1=86✅; G1.1/G1.2/G2.2/G2.3 pending |
| H | 1/7 valid | 1/1 valid passing | — | H1.1=86✅; H1.2–H3.1 pending |
| I | 1/5 valid | 1/1 valid passing | — | I1.1=92✅; I1.2–I2.3 pending |

**F2.2 (21.0) and F2.3 (41.2) core failure patterns (6 attempts each):**
- `PERSONEN_FALSCH` — bot reads back wrong guest count (reads 1 when user said 2)
- `BOT_LOOP` — repeated utterances on phone-number slot during pickup flow
- `NAME_FALSCH` — reads back "Hallo" as the guest name instead of extracted name
- Composite ceiling hit at 62.0 (attempt 5 for F2.3); attempt 6 regressed to 41.2 → EIR gate forced advance

**Root causes still unresolved for F2.2/F2.3:**
- `reservation.py` slot confirmation reads the *slot value at booking time* (often 1-person default) instead of *extracted user utterance*
- Name extraction in `conversation_state._extract_name_from_utterance` passes but the confirmation context still uses wrong slot

**Root causes of low Grok scores:**
- `flow` metric consistently 25–40 (expected conversation flow not met)
- `deterministic` metric 25–45 (name/phone readback errors)
- Haiku fixes often regressed scores; EIR gate reverted ~10 times
- Complaint/billing handling (H1.3, I2.2) bot lacks resolution escalation
- Phone-number loop for pickup orders fixed manually in `context_doc_builder.py` + `v4_pipeline.py`

**Fix applied 2026-05-19:** Removed `phone_number` from `create_order` required slots in `context_doc_builder.py` (pickup orders don't require phone). Added pickup detection in `v4_pipeline.py` dup-utterance handler.

**Execution order: A → E → F → G → H → I.** B/C/D skipped (passing).
Phase J (End-to-End Production) is out of scope.

---

## Resuming an Interrupted Run

After any crash, fix, restart, or interruption — this is the correct command:

```bash
cd /home/charles2/sailly-browser-demo
set -a; source .env; set +a

# Step 1: confirm no stale process
pgrep -af "scenario_based_loop|phase_runner" | grep python && echo "already running" && exit 1

# Step 2: resume
PYTHONPATH=/home/charles2/sailly-browser-demo \
GOOGLE_APPLICATION_CREDENTIALS=/home/charles2/.ssh/sailly-voice-agent-key.json \
venv/bin/python3 -m server.validation.scenario_based_loop \
  --phases f,g,h,i \
  --workers 5 \
  --stagger-s 3 \
  --max-attempts 8 \
  --threshold 80.0 \
  --output-dir /tmp/scenario_validation \
  --resume \
  2>&1 | tee "/tmp/scenario_validation/foreground_FGHI_$(date +%s).log"
```

**How `--resume` works:** skips only batches whose latest/available `batch_result_<KEY>_*.json` is a verifier pass: `threshold_met=true`, `force_advanced=false`, and `audit_failed=false`. Low-score, audit-failed, or force-advanced artifacts are intentionally re-run.

### Post-phase GPT-5.5 external review (mandatory before trusting a phase)

After each phase completes in the validation output dir, generate an evidence pack and record an external verdict **before** treating the phase as product-validated:

```bash
cd /home/charles2/sailly-browser-demo
set -a; source .env; set +a

OUT="$(cat /tmp/current_truth_validation_dir.txt)"   # or explicit path
PYTHONPATH=. GOOGLE_APPLICATION_CREDENTIALS=/home/charles2/.ssh/sailly-voice-agent-key.json \
venv/bin/python3 -m server.validation.post_phase_reviewer \
  --output-dir "$OUT" \
  --phase a \
  --sample-count 6
```

This writes `post_phase_review_<PHASE>_<ts>.json` (batch summaries + Postgres transcript spot-checks).

The Cursor master monitor (GPT-5.5) then reads that pack plus `batch_result_*.json`, produces `post_phase_verdict_<PHASE>_<ts>.json` with:

- **verifier_verdict** — harness/scorer truthfulness (`pass | warn | block`)
- **product_verdict** — bot behavior (`pass | warn | block`)
- **phase_trusted** — whether to treat the phase as done (`true | false`)

**Rule:** Loop may force-advance batches; external review decides whether the phase is actually validated. A phase with mostly `force_advanced` batches must **not** be trusted as product-pass without re-run.

> To intentionally re-run a specific failing batch: delete its `batch_result_*.json` file, then run with `--resume` — the loop will re-process only that batch.

---

## Caller Bot

- Model: **`grok-3-mini`** (lighter — simulates users; override with `CALLER_BOT_MODEL` env var)
- 7 personas per batch: `busy`, `elderly`, `impatient`, `indecisive`, `neutral`, `rude`, `skeptical`
- Connects to Sailly at `ws://localhost:8080/ws/headless`
- File: `server/validation/phase_runner.py`

---

## Auditor

- Model: **`grok-4-1-fast-non-reasoning`** (heavier — complex quality reasoning; override with `GROK_AUDIT_MODEL`)
- Grok composite = tool_accuracy(40%) + flow(30%) + linguistic(15%) + deterministic(15%)
- Current advance gate: effective Grok composite score ≥ configured `--threshold` (80.0 for the current FGHI validation track). Persona pass rate is reported separately and is not a clean verifier pass by itself.
- Max 8 fix attempts per batch before force-advance
- File: `server/validation/grok_auditor_integration.py`

> **Model logic (2026-05-18):** Caller bot uses lighter model (saves tokens on user simulation).
> Auditor uses heavier model (needs strong reasoning to accurately score tool accuracy, flow, loops).

---

## Fix Loop (Haiku 4.5)

Each failed attempt triggers:
1. Grok audit → scores + flags
2. Postgres → full call reports (9-section per call_sid)
3. **XAI Grok web search** → live internet research on the flagged issues (injected as `INTERNET RESEARCH CONTEXT`)
4. Haiku 4.5 → reads audit + call reports + web research + **known issues library** + **sequential fix history** (all prior attempts)
5. Applies code patch → **restarts Sailly on port 8080** → re-runs same batch

### Port 8080 Restart Rule (MANDATORY)
> After EVERY fix application, the Sailly service MUST be fully restarted on port 8080.  
> `fix_applier._restart_service()` handles this automatically:  
> - Kills `uvicorn.*server.main` + `uvicorn.*8080`  
> - Starts fresh: `sudo -u charles2 venv/bin/python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8080`  
> - Waits up to 60s for `http://localhost:8080/health` to respond 200  
> - Reverts all modified files and re-restarts if health check fails  

### Internet Research Rule (added 2026-05-18)
> Before each Haiku fix call, a targeted XAI Grok search runs (`grok-3-mini` with `search: true`).  
> The query is built from: `batch_key`, `achtung_flags`, `failing_metrics`, `grok_summary`.  
> Results are injected as `INTERNET RESEARCH CONTEXT` block in the dynamic prompt.  
> This gives Haiku live documentation, best practices, and similar bug patterns from the web.  
> Implemented in: `haiku_fix_generator._web_research()`

The **sequential context** (added 2026-05-18) means Haiku sees every previous fix it tried for this batch and the resulting score, so it doesn't repeat failed approaches.

---

---

# Optimization Research

> Researched 2026-05-18. Scope: token-efficient and pass-rate-efficient improvements to the fix loop.

## Implementation Status

| # | Change | Status |
|---|--------|--------|
| 1 | Prompt-cache system prompt + call-report context (`cache_control` breakpoints) | ✅ **DONE** — `haiku_fix_generator.py` (2026-05-18) |
| 1b | Internet research via XAI Grok web search before each Haiku call | ✅ **DONE** — `haiku_fix_generator._web_research()` (2026-05-18) |
| 2 | Deterministic pre-filter before Grok auditor | ⬜ Pending |
| 3 | Route attempts 1–3 to Anthropic Batch API | ⬜ Pending |
| 4 | Failure-mode clustering before Haiku | ✅ **DONE** — `known_issues.json` + `known_issues_advisor.py` (rebuilt 2026-05-18, **53 issues, 5 sources**) |
| 5 | EIR gate — stop when fixes plateau / regress | ✅ **DONE** — `scenario_based_loop.py` (2026-05-18) — window=3, min_delta=2 pts |
| 6 | Context stripping for Haiku | ⬜ Pending |
| 7 | Two-stage auditing | ⬜ Pending |
| 8 | Cache Sailly turn LLM prefix | ⬜ Pending |
| 9 | No-improvement early-stop gate | ✅ **DONE** (merged into EIR gate) |
| 10 | Observability / token logging | ✅ **DONE** — cache hit/miss logged per call (`[haiku] tokens:`) |

> Next run will log `[haiku] tokens: input=X cache_write=Y cache_read=Z (saved ~N%)` per fix attempt.
> EIR gate: if score improves < 2 pts over last 3 attempts, stop calling Haiku for that batch.

## Known Issues Library (2026-05-18)

Files:
- `server/validation/known_issues.json` — **53 issues**, schema v2.0 (added 2026-05-18: NAME_SINGLE_LASTONLY, PHONE_EXTRACT_MISSING_ALIAS)
- `server/validation/known_issues_advisor.py` — matching engine + advice injector

Sources used to build the library:
- 60 batch result JSONs (May 13 + May 18 runs)
- 8 large agent transcripts (fc4c5bbc, 5d2ac383, a06197b0, d6c51a74, 16688416, 4c6bfd09, 263f6dac, 90ed704f)
- 9 git fix commits (d30bb11 → ced5a9a, May 7–8 sprint)
- FIX_VALIDATION_IMPLEMENTATION_GUIDE.md

Each run now automatically matches the current batch's achtung flags / metric scores / Grok text against the library and injects:
- Root cause (what is ACTUALLY broken)
- Failed fixes (do NOT repeat these)
- Confirmed working fixes (start here)
- Code quality rules (Python 3.12+ scoping, indentation)

**Phase summary from library:**

| Phase | Status | Primary issues |
|-------|--------|---------------|
| A1.x | FAILING | DATUM_FALSCH, BOT_LOOP, COMMIT_GATE, PHONE_LOOP, CONFIRM_ADVANCE |
| A2.x | FAILING | BOT_LOOP (regression), INTENT_MISDETECT |
| B1.x | PASSING | — |
| B2.x | MOSTLY PASSING | ADRESSE_FALSCH occasional |
| C | PASSING | — |
| D | MOSTLY PASSING | BOT_LOOP occasional regression |

## TL;DR — Top 10 Recommendations by ROI

| # | Change | Effort | Expected impact |
|---|--------|--------|-----------------|
| 1 | **Prompt-cache the Haiku fixer's system prompt + call-report context** with `cache_control` breakpoints | Half a day | **70–90% token cost cut on fix attempts 2–8**, plus ~85 ms lower TTFT |
| 2 | **Deterministic pre-filter before the Grok auditor** — tool-coverage, forbidden-phrase, dish-whitelist, "du" violations | 1 day | **Skip auditor on ~30–50% of clean batches** |
| 3 | **Route fix attempts 1–3 to Anthropic Batch API** (50% off) when running overnight; real-time only for attempts 4–8 | 1 day | **~25–30% total fixer cost cut** on unattended phases |
| 4 | **Failure-mode clustering before invoking Haiku** — group failing batches by root cause, fix the cluster not the batch | 1 day | **3–5× fewer wall-clock attempts** on current Phase A backlog |
| 5 | **EIR-gate the fix loop** — measure error introduction rate; revert + stop if a batch regresses | Half a day | Prevents "fix made it worse" failure mode (hits ~50% of attempts at high attempt counts) |
| 6 | **Strip tool results from Haiku's context** — keep only audit summary + flagged-turn excerpts + fix diffs | Half a day | **~30–60% per-attempt input token cut** |
| 7 | **Two-stage auditor cascade**: Haiku 4.5 JSON judge on every batch; escalate to Grok only on scores 50–94 | 1–2 days | **~60% auditor cost cut** with no quality loss on clear batches |
| 8 | **Cache the Sailly turn LLM's menu/policy prefix** (Gemini implicit context caching) | 1 day | Cuts cost of every actual call run |
| 9 | **Replace "force-advance after 8" with "force-advance after no-improvement streak"** — bail if last 2 attempts moved composite < 2 pts | 2 hours | **30–50% fewer attempts** on stuck batches |
| 10 | **Adopt `pass^k` not `pass@1`** as the gate metric — run each batch 2–3× at advance time, require all-pass | 1 day | Prevents "fixed once, broken forever after" failure; aligns with τ-bench methodology |

**If you do only one thing: do #1.** The fix loop is structurally a multi-turn conversation against a stable prefix — that is the textbook prompt-cache use case. Break-even is 1 cache read (5-min TTL) or 2 reads (1-hr TTL).

---

## 1. Prompt Caching (Highest ROI)

| Cache mechanic | Cost |
|---|---|
| Cache read | 0.1× base input price (90% discount) |
| Cache write (5-min TTL) | 1.25× base input price |
| Cache write (1-hr TTL) | 2.0× base input price |
| Haiku 4.5 minimum cache prefix | 4,096 tokens |
| Break-even (5-min) | 0.28 reads — pays off after **1 read** |
| Break-even (1-hr) | 1.11 reads — pays off after **2 reads** |
| Latency reduction | up to 85% on cached prefix |

**What to cache in `haiku_fix_generator.py`:**

```python
system = [
    {
        "type": "text",
        "text": HAIKU_FIX_SYSTEM_PROMPT,          # static — cache 1 hr
        "cache_control": {"type": "ephemeral", "ttl": "1h"},
    },
    {
        "type": "text",
        "text": render_call_auditor_rubric(),       # static per audit version
        "cache_control": {"type": "ephemeral", "ttl": "1h"},
    },
]

messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": f"Scenario spec:\n{scenario_yaml}"},   # same for all 8 attempts — cache 5 min
            {"type": "text", "text": f"Full call reports:\n{reports}"},      # cache 5 min
            {
                "type": "text",
                "text": f"Audit (attempt {n}):\n{audit_json}",
                "cache_control": {"type": "ephemeral"},  # auto-moves per turn
            },
        ],
    }
]
```

Verify cache is hitting: check `response.usage.cache_read_input_tokens` — if it's 0 on attempt ≥ 2, the breakpoints are misplaced. Stacks with Batch API for a ~95% discount on the cached portion.

References: [Anthropic Prompt Caching docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) · [Anthropic cookbook](https://github.com/anthropics/anthropic-cookbook/blob/main/misc/prompt_caching.ipynb)

---

## 2. Deterministic Pre-Filter

Three of the six Grok audit dimensions are pure deterministic checks that don't need an LLM:

- Tool completeness (set membership: did `create_order` / `create_reservation` fire?)
- Forbidden-phrase scan (regex: "du/dir/dein", hallucinated dishes outside whitelist, "kassensystem")
- Sie violations (already partially implemented)
- Stuck-loop detection (already implemented as `_is_stuck_loop`)

**Three-level cascade:**

```
Level 1: Deterministic triage (regex, set membership, schema — milliseconds)
   → hard-fail trigger fires → FAIL, send synthetic audit to fix loop (no Grok call)
   → all clean AND component scores ≥ 95 → PASS (no Grok call)
   → else → continue

Level 2: Haiku 4.5 JSON judge (~3K tokens, structured-output schema)
   → composite ≥ 95 → PASS
   → composite < 50 → FAIL (no Grok call)
   → 50–95 → escalate to Grok

Level 3: Grok composite — full rubric, only on ~30–50% of batches
```

This layering routinely cuts judge cost 60% with better reliability (format/schema failures don't get masked by LLM "this looks fine" hallucination).

Reference: [Sogeti Labs — Token Economics in LLM Testing](https://labs.sogeti.com/part-1-token-economics-in-llm-testing/)

---

## 3. Batch API for Overnight Runs

For unattended overnight runs, route fix attempts 1–3 through the [Anthropic Batch API](https://platform.claude.com/docs/en/build-with-claude/message-batches) (50% discount, ~24h turnaround). Switch to real-time only for attempts 4–8 where speed matters for iteration.

Stacks with prompt caching: cached + batch gives ~95% discount on the stable prefix.

---

## 4. Failure-Mode Clustering

When you have 13 failing batches you probably have 2–3 root causes, not 13.

**Process:**
1. Pull all failing audit JSONs from `/tmp/scenario_validation/`.
2. Extract the top failure reason + `prompt_fixes[].file/node` per batch.
3. Cluster manually (13 is small enough) — likely clusters for Phase A:
   - `DATUM_FALSCH` — date parsing (fixed 2026-05-18 in `reservation_workers._parse_date` and `v4_pipeline.py`)
   - BOT_LOOP post-commit — end_call not firing after farewell
   - Tool not called — `check_availability`/`create_reservation` missing
   - SMS confirmed without parent success
4. Fix the cluster root cause once → re-run all batches in the cluster.

A real-world example (Future AGI 2026): 41% of failures were a single wrong parameter in one tool call — one fix resolved half the backlog in one PR.

Reference: [Future AGI error analysis guide](https://futureagi.com/blog/what-is-error-analysis-llm-2026)

---

## 5. EIR Gate — Stop When Fixes Make It Worse

From the self-correction literature: most gains concentrate in attempts 1–2; past attempt ~3, error introduction rate (EIR) rises sharply and the LLM starts breaking previously-working code.

**Dirt-simple gate (add to `scenario_based_loop._run_scenario_batch_loop`):**

```python
def _should_continue_fixing(fix_history: list) -> bool:
    if len(fix_history) < 2:
        return True
    last = fix_history[-1]["composite_score"]
    prev = fix_history[-2]["composite_score"]
    # Stop if score regressed by ≥ 5 pts — revert happens separately
    if last < prev - 5:
        return False
    # Stop if last 2 attempts moved composite by < 2 pts (plateau)
    if abs(last - prev) < 2:
        return False
    return True
```

The revert-on-regression mechanism is already implemented (2026-05-18). This gate adds a plateau-stop. Together they typically cap real attempts at 3–4 instead of 8, saving ~40% of tokens and wall-clock.

References: [When Can LLMs Correct Their Own Mistakes (TACL 2024)](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00713/125177/) · [How Many Tries Does It Take? (arxiv 2604.10508)](https://arxiv.org/html/2604.10508)

---

## 6. Strip Tool Results from Haiku's Context

The Grok auditor already digests raw transcripts into structured findings. Haiku doesn't need the raw call reports on top — it just adds noise.

**Replace:**
```python
reports = fetch_full_call_reports(batch_id)   # 9 sections × 7 calls = 63 sections
```

**With:**
```python
reports = extract_flagged_turns(audit, full_reports)  # only the turns the audit flagged
fix_context = git_diff_of_prior_patches(fix_history)  # diffs, not full files
```

Expected: 30–60% per-attempt input token cut, and better fix quality (less noise). Anthropic's own context-engineering team recommends "just-in-time" context over "dump everything up-front."

Reference: [Effective Context Engineering (Anthropic engineering blog)](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

---

## 7. Two-Stage Auditor Cascade

A panel of small models outperforms a single large judge at a fraction of the cost (PoLL paper). Stage 1 Haiku → Stage 2 Grok only on ambiguous scores (50–94) cuts Grok calls by ~60% with no quality loss on clear pass/fail batches.

Reference: [Replacing Judges with Juries — PoLL](https://eugeneyan.com/writing/llm-evaluators/) · [Tuning LLM Judge Design Decisions (arxiv 2501.17178)](https://arxiv.org/pdf/2501.17178)

---

## 9. No-Improvement Streak Early Stop

Current: force-advance after exactly 8 attempts regardless of trajectory.
Better: force-advance when the last 2 consecutive attempts both improved composite by < 2 pts.

```python
# In scenario_based_loop.py — replace the attempt >= max_attempts check with:
_no_improvement = (
    len(fix_history) >= 2
    and abs(fix_history[-1]["composite_score"] - fix_history[-2]["composite_score"]) < 2
)
if attempt >= self.max_attempts or _no_improvement:
    logger.warning("[batch_loop] %s: stopping (attempts=%d, no_improvement=%s)",
                   batch_key, attempt, _no_improvement)
    break
```

Saves ~40% of attempts on stuck batches with no meaningful pass-rate loss.

---

## 10. `pass^k` Reliability Gate

`pass@1` (advance if the batch passes once) is optimistic — fixes that pass once and then regress in later batches are common. τ-bench shows GPT-4o pass@1 of ~50% drops to pass^8 < 25% on retail tasks.

**Practical version:** before marking a batch VALIDATED, re-run it once more. Require both runs to pass. Cost: one extra run per passing batch (~10–15% overhead). Benefit: catches flaky fixes before they compound.

Reference: [τ-bench paper](https://arxiv.org/abs/2406.12045) · [τ-voice (arxiv 2603.13686)](https://arxiv.org/pdf/2603.13686)

---

## Optimized Per-Batch Flow

```
[Caller bot — 7 personas in parallel]
        ↓
[Sailly run — Gemini Flash w/ cached menu/policy prefix]
        ↓
[Level 1 — Deterministic triage (ms)]
   ├─ hard-fail → FAIL + synthetic audit → fix loop (no Grok)
   ├─ all-clean + components ≥ 95 → PASS (no Grok)
   └─ else → Level 2
        ↓
[Level 2 — Haiku 4.5 JSON judge (~3K tokens)]
   ├─ ≥ 95 → PASS
   ├─ < 50 → FAIL → fix loop (no Grok)
   └─ 50–94 → Level 3
        ↓
[Level 3 — Grok composite — only on ambiguous batches]
        ↓
[Cluster check — is this failure shared with 2+ other batches?]
   ├─ yes → hold for cluster fix
   └─ no → Haiku fixer
        ↓
[Haiku 4.5 fixer — prompt-cached system + rubric + scenario]
   ├─ Fresh per-attempt: audit JSON + flagged-turn excerpts + prior fix diffs
   ├─ EIR gate: stop on regression ≥ 5 pts or plateau < 2 pts
   └─ Hard cap: 4–5 attempts (8 as safety)
        ↓
[Restart Sailly → re-run batch]
        ↓
[pass^2: re-run once more, require both runs to pass before VALIDATED]
```

**Expected impact vs. current baseline:**

| Metric | Change |
|--------|--------|
| Haiku input tokens | ↓ ~70% (caching + context strip + attempt cap) |
| Grok auditor tokens | ↓ ~60% (cascade + deterministic pre-filter) |
| Wall-clock per failing batch | ↓ ~50% (fewer attempts + shorter context) |
| Pass-rate on stuck batches | ↑ ~10–25 pp (cluster fixes hit multiple batches per change) |
| Net cost per Phase A run | ↓ ~60–75% |

---

## Implementation Order (1-week plan)

| Day | Task | Yields |
|-----|------|--------|
| Mon | Add `cache_control` to Haiku fixer system + rubric + scenario blocks; log `cache_read_input_tokens` | 70–90% cost cut on attempts ≥ 2 |
| Tue | Build Level 1 deterministic pre-filter; auto-FAIL on tool/forbidden-phrase hits; auto-PASS on clean scores | ~30–50% of Grok calls skipped |
| Wed | Cluster the failing Phase A batches by root cause; write one fix per cluster; re-run | Phase A backlog drops 30–60% in one PR |
| Thu | EIR / no-improvement gates; cap real attempts at 4–5 with 8 as hard safety | ~40% fewer attempts |
| Fri | Trim Haiku context to flagged turns + diffs only (not full reports) | ~30–60% additional per-attempt cost cut |

Optional follow-ons:
- Batch API path for overnight runs (50% off on first 3 attempts)
- Two-stage Haiku → Grok cascade for the auditor
- `pass^2` gate at advance time
- GEPA / DSPy on node prompts where Haiku keeps failing (see [gepa-ai/gepa](https://github.com/gepa-ai/gepa))

---

## Notable Repos and References

**Voice-agent testing frameworks:**
- [ServiceNow/eva](https://github.com/ServiceNow/eva) — bot-to-bot voice eval; scores accuracy + experience separately
- [sierra-research/tau-bench](https://github.com/sierra-research/tau-bench) — `pass^k` reliability metric, simulated-user benchmark
- [saharmor/voice-lab](https://github.com/saharmor/voice-lab) — text-side LLM/prompt testing
- [KhalilMrini/Agent-Testing-Agent](https://github.com/KhalilMrini/Agent-Testing-Agent) — meta-agent that adapts difficulty

**Key findings from recent benchmarks:**
- **τ-voice (March 2026):** voice agents (GPT-5, Gemini, xAI) hit only 31–51% pass@1 on clean audio; 79–90% of failures stem from agent behavior, not audio quality — validates Sailly's text-first approach.
- **τ-bench retail leaderboard (mid-2026):** Claude Sonnet 4.5 at 0.862, Opus 4.1 at 0.824. Your DOBOO numbers are competitive if Phase A clears 90%+.
- **Hamming 4-Layer Quality Framework:** targets P95 latency < 800ms, tool-call success > 99%, reprompt rate < 10%.

**Research papers:**
- [When Can LLMs Correct Their Own Mistakes (TACL 2024)](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00713/125177/)
- [How Many Tries Does It Take? (arxiv 2604.10508)](https://arxiv.org/html/2604.10508)
- [τ-voice (arxiv 2603.13686)](https://arxiv.org/pdf/2603.13686)
- [LLM-Rubric: multidimensional calibrated evaluation (arxiv 2501.00274)](https://arxiv.org/pdf/2501.00274)
- [Effective Context Engineering (Anthropic engineering blog)](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Replacing Judges with Juries — PoLL](https://eugeneyan.com/writing/llm-evaluators/)

**Anthropic levers (all applicable to Haiku 4.5):**
- [Prompt Caching docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [Context editing beta (`clear_tool_uses_20250919`)](https://docs.anthropic.com/en/docs/build-with-claude/context-editing)
- [Batch API (50% off)](https://platform.claude.com/docs/en/build-with-claude/message-batches)
- [Memory tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool) — persist "what we learned from fix attempts 1..N" across batches
