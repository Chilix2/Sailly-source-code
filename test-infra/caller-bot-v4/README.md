# Sailly v4 Caller-Bot Training Loop

LLM-driven German caller simulator for comprehensive testing of the v4 deterministic pipeline.

## Purpose

Rebuild the deleted `test-infra/caller-bot/` against the v4-only architecture:
- **Transport**: text-only over `/ws/headless` (no audio).
- **Caller LLM**: OpenAI GPT-4o (JSON-mode).
- **Scenarios**: 35+ YAML-based flows covering Phase 0–10 from the v4 audio test script.
- **Verifier**: V4-native metrics adoption (profile, end_call_stage, commit gate, tools_called, readback) with per-call scoring and aggregate thresholds.

## Quick start

### 1. Setup

```bash
cd test-infra/caller-bot-v4
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

Ensure these environment variables are set:

```bash
export OPENAI_API_KEY=sk-...
export SAILLY_WS_URL=ws://127.0.0.1:8080/ws/headless
export SAILLY_PG_DSN=postgresql://sailly:sailly@localhost:5432/sailly
```

### 3. Run

```bash
# Smoke test (Phase 0 + 1.1 + 2.1 + 7.1) — fast, must hit 10/10
python -m src.main --suite smoke --runs 1

# Full matrix
python -m src.main --suite all --runs 3 --md-out out/run-$(date +%s).md

# Single scenario
python -m src.main --only phase1_test_1_1_clean_reservation --verbose
```

## Architecture

```
caller-bot-v4
├── src/
│   ├── main.py              # CLI entry point
│   ├── config.py            # Env + CLI args parsing
│   ├── transport.py         # HeadlessClient (WS protocol)
│   ├── persona.py           # GPT-4o caller simulator
│   ├── runner.py            # Per-scenario orchestrator
│   ├── verifier.py          # V4-native rule verification
│   ├── metrics.py           # Postgres metrics pull
│   ├── scoring.py           # Per-call + aggregate scoring
│   └── scenario_loader.py   # YAML scenario parser
├── scenarios/
│   ├── phase0/              # Greeting, business_info, goodbye
│   ├── phase1/              # Reservation commit gate
│   ├── phase2/              # Profile coverage
│   ├── phase3/              # Greeting + barge-in
│   ├── phase4/              # Placeholder/dup-tool regressions
│   ├── phase5/              # Legacy traps
│   ├── phase6/              # Observability
│   ├── phase7/              # Full E2E flows
│   ├── phase8/              # Multi-intent
│   ├── phase9/              # Safety/negative
│   └── phase10/             # Messy text (text-mode adaptation)
├── prompts/
│   └── caller_system.de.txt # System prompt (v4 spec)
├── tests/
│   ├── test_verifier_rules.py
│   └── test_scenario_load.py
├── out/                     # Reports (gitignored)
└── requirements.txt         # Dependencies
```

## Release Thresholds

Scenarios are tagged with thresholds: `internal_alpha`, `supervised_beta`, `production`.

Aggregate results:

- **Internal alpha**: smoke 10/10, false_commits=0, legacy_hits=0
- **Supervised beta**: core ≥90%, false_commits=0, false_success=0, readback ≥95%, end_call ≥95%
- **Production**: full ≥95%, critical safety 100%, messy ≥90%, legacy_hits=0, dup_tools=0, commit_without_confirmation=0

## Outputs

- Per-call MD scoring sheet (Final Scoring Sheet format from v4 spec).
- Aggregate JSON + MD summary.

## Limitations

- Phase 10 (audio realism) is text-mode-best-effort. Barge-in / STT confidence not exercised.
- No server-side modifications. All verification via WS + Postgres observability.
