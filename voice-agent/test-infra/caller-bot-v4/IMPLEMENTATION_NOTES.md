# v4 Caller-Bot v4 Training Loop — Implementation Complete

**Date**: Apr 30, 2026  
**Status**: ✓ Ready for smoke run  
**Location**: `/home/charles2/sailly-browser-demo/test-infra/caller-bot-v4/`

## What Was Built

A complete LLM-driven German caller simulator for comprehensive testing of the Sailly v4 deterministic pipeline. This is a rebuild of the deleted `test-infra/caller-bot/` against the new v4-only architecture.

### Key Components

#### 1. Transport Layer (`src/transport.py`)
- **HeadlessClient**: JSON WebSocket client for `/ws/headless` endpoint
- **Protocol**: Mirrors harness.py semantics (`user_text`, `bot_text`, `tool_event`, `session_end`)
- **No server-side changes required**

#### 2. Caller LLM (`src/persona.py`)
- **Model**: OpenAI GPT-4o (JSON-mode)
- **Response format**: `{speech, end_politely, abandon, internal_note}`
- **System prompt**: Verbatim from v4 audio test spec + scenario injection
- **API key validation**: Precheck ensures `OPENAI_API_KEY` is set

#### 3. Test Scenarios (`scenarios/phase{0..10}/`)
- **Coverage**: 11 YAML scenarios across all phases
- **Smoke suite**: 4 critical scenarios (0.1 + 1.1 + 2.1 + 7.1)
- **Core suite**: All phases 0–7
- **Full suite**: All phases including safety (phase 9) and messy text (phase 10)
- **Format**: YAML with caller goal, identity, patience, confirmation phrases, expectations, thresholds

#### 4. Verification Engine (`src/verifier.py`)
Implements all 10 global pass/fail rules from the v4 audio test script:
1. ✓ No false success claims (before commit fires)
2. ✓ No commits without confirmation
3. ✓ No placeholder text ("Ihrem Namen", `{name}`, etc.)
4. ✓ No legacy paths ([TOOL:] tags, deprecated tools, stuck nodes)
5. ✓ No premature end_call
6. ✓ No hallucinated data
7. ✓ Corrections respected
8. ✓ No duplicate tools
9. ✓ State-speech consistency
10. ✓ No raw tool tags

#### 5. Metrics & Signals (`src/metrics.py`)
- **Source**: `google_turn_metrics` table via asyncpg
- **Fields**: `node_name`, `tools_called`, `intent_classify_ms`, `worker_p50_ms`, `worker_p95_ms`, `generator_total_ms`
- **Derived signals**: `one_llm_per_turn`, `has_readback`, `commit_gate_timing_ok`, `latency_acceptable`

#### 6. Orchestrator (`src/runner.py`)
- **ScenarioRunner**: Per-scenario caller ↔ bot loop
- **Async**: Full async/await throughout
- **Timeout**: 15s per turn (2s extra for safety)
- **End conditions**: `end_politely`, `abandon`, patience budget, latency timeout
- **Result format**: Includes bot_responses, user_utterances, tools_fired, verification, signals

#### 7. Report Generation (`src/scoring.py`)
- **Per-call**: Final Scoring Sheet (Markdown)
- **Aggregate**: Summary report + JSON export
- **Release thresholds**:
  - Internal Alpha: smoke 10/10, false_commits=0, legacy_hits=0
  - Supervised Beta: core ≥90%, false_commits=0, false_success=0, readback ≥95%, end_call ≥95%
  - Production: full ≥95%, critical safety 100%, messy ≥90%, 0 legacy/dup/commit-without-confirmation

#### 8. CLI (`src/main.py`)
- **Commands**: `--suite smoke|core|all`, `--only SCENARIO`, `--phase N`, `--runs K`
- **Output**: `--json-out`, `--md-out` (default: stdout)
- **Config**: `--url`, `--dsn`, or environment variables
- **Async orchestration**: Runs scenarios sequentially, collects results, generates reports

#### 9. Unit Tests (`tests/`)
- **15 tests** covering verifier rules, scenario loading, confirmation detection, placeholder/legacy detection
- **All passing** ✓
- **No server required**

## Architecture Flow

```
User CLI
  ↓
Config (env + args)
  ↓
Scenario Loader (YAML)
  ↓
ScenarioRunner (per-scenario)
  ├─ CallerPersona (GPT-4o)
  ├─ HeadlessClient (WS)
  ├─ Conversation Loop (turn-by-turn)
  ├─ DB Metrics Fetch (google_turn_metrics)
  ├─ Verifier (10 rules)
  └─ Result Dict
  ↓
Scorer
  ├─ Per-call Report (MD)
  ├─ Aggregate Summary (MD + JSON)
  └─ Threshold Check
  ↓
Output (stdout / out/)
```

## File Structure

```
test-infra/caller-bot-v4/
├── src/
│   ├── __init__.py
│   ├── __main__.py
│   ├── main.py              # CLI entry point
│   ├── config.py            # Env + args parsing
│   ├── transport.py         # HeadlessClient WS
│   ├── persona.py           # GPT-4o caller
│   ├── runner.py            # Scenario orchestrator
│   ├── verifier.py          # 10 rules
│   ├── metrics.py           # DB metrics
│   ├── scoring.py           # Report generation
│   └── scenario_loader.py   # YAML parser
├── scenarios/
│   ├── phase0/ (greeting, business_info)
│   ├── phase1/ (reservation commit gate)
│   ├── phase2/ (order start)
│   ├── phase3/ (greeting turn-0)
│   ├── phase4/ (no placeholder)
│   ├── phase5/ (no legacy tags)
│   ├── phase6/ (observability)
│   ├── phase7/ (E2E clean)
│   ├── phase8/ (multi-intent)
│   ├── phase9/ (safety)
│   └── phase10/ (messy text)
├── prompts/
│   └── caller_system.de.txt # System prompt (v4 spec)
├── tests/
│   ├── test_verifier_rules.py (15 tests)
│   └── test_scenario_load.py
├── out/                     # Reports (gitignored)
├── README.md
├── QUICKSTART.md
├── IMPLEMENTATION_NOTES.md  # This file
├── requirements.txt
├── pyproject.toml
└── .gitignore
```

## Test Coverage

### Unit Tests (15/15 passing)
- Confirmation detection: 3 tests
- Placeholder detection: 3 tests
- Legacy detection: 3 tests
- Verifier rules: 4 tests
- Scenario loading: 2 tests

### Scenario Coverage
- **Smoke suite**: 4 scenarios (internal alpha gate)
- **Core suite**: Phases 0–7 (supervised beta)
- **Full suite**: Phases 0–10 + Phase 10 messy text (production)

## How to Run

### Quick Start

```bash
cd test-infra/caller-bot-v4
export OPENAI_API_KEY=sk-...
python3 -m src.main --suite smoke --runs 1 --verbose
```

### Detailed Commands

```bash
# Unit tests (no server required)
python3 -m unittest discover tests -v

# Smoke suite (4 scenarios, must all pass for Internal Alpha)
python3 -m src.main --suite smoke --runs 1 --json-out out/smoke.json

# Core suite (Phase 0-7, ≥90% pass for Supervised Beta)
python3 -m src.main --suite core --runs 1 --md-out out/core_report.md

# Full suite (all phases, ≥95% pass for Production)
python3 -m src.main --suite all --runs 3 --json-out out/full_results.json

# Single scenario (debug)
python3 -m src.main --only phase1_test_1_1_clean_reservation --verbose
```

## Key Design Decisions

1. **Text-only transport**: No audio resurrected. `/ws/headless` is pure text JSON protocol. Phase 10 is text-mode adaptation (messy speech as messy text input).

2. **GPT-4o JSON-mode**: Deterministic JSON output (`{speech, end_politely, abandon, internal_note}`). No parsing required.

3. **V4-native verification**: Rules directly check v4 concepts:
   - `end_call_stage` state machine
   - `node_name` (= profile) from DB
   - `commit_gate_correct` via confirmation detection + commitment timing
   - `readback_present` pattern matching

4. **No server changes**: All verification is observation-only via WS + Postgres. v4 server unmodified.

5. **Async throughout**: `asyncio`-based orchestration. Scales to multi-run easily.

6. **Scenario YAML format**: Richer than old JSONL. Supports:
   - Caller goal + identity
   - Confirmation/denial phrases
   - Expectations block (must/forbid)
   - Release thresholds (internal_alpha / supervised_beta / production)

## Known Limitations

- **Phase 10 (audio realism)**: Text-only. No STT confidence, barge-in, or acoustic realism. Requires audio transport adapter for full testing.
- **OPENAI_API_KEY**: Must be set externally. Precheck validates it.
- **Postgres required**: Metrics pull requires `google_turn_metrics` table. Best-effort fallback if DB unavailable.

## Next Steps for User

1. ✓ Scaffold complete (you are here)
2. ✓ All unit tests passing
3. → Start v4 server on ws://127.0.0.1:8080/ws/headless
4. → Set `OPENAI_API_KEY` environment variable
5. → Run smoke suite: `python3 -m src.main --suite smoke --runs 1 --verbose`
6. → Check `out/` directory for reports
7. → Target: All 4 smoke scenarios PASS → Internal Alpha Ready
8. → Iterate: Add more scenarios, tune confirmation detection, refine persona prompt if needed

## Success Metrics

- **Internal Alpha (current)**: Smoke suite 10/10 pass, 0 false_commits, 0 legacy_hits
- **Supervised Beta**: Core ≥90% pass, 0 false_commits, 0 false_success_claims, readback ≥95%, end_call ≥95%
- **Production**: Full ≥95% pass, critical safety 100%, messy ≥90%, 0 legacy/dup/commit-without-confirmation

## Files Modified (v4 server)

**None.** All caller-bot code is new under `test-infra/caller-bot-v4/`. No changes to v4 server required.

---

**Ready to run.** Execute `python3 -m src.main --suite smoke --runs 1 --verbose` after setting `OPENAI_API_KEY` and starting the v4 server.
