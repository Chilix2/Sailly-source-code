# Caller-Bot v4 Quick Start

## Installation

```bash
cd test-infra/caller-bot-v4
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Set environment variables:

```bash
export OPENAI_API_KEY=sk-...         # Your OpenAI API key
export SAILLY_WS_URL=ws://127.0.0.1:8080/ws/headless
export SAILLY_PG_DSN=postgresql://sailly:sailly@localhost:5432/sailly
```

Or provide as CLI args:

```bash
python3 -m src.main --url ws://... --dsn postgresql://...
```

## Running Tests

Unit tests (no server required):

```bash
python3 -m unittest discover tests -v
```

## Running Scenarios

**Smoke suite** (required for internal alpha):

```bash
python3 -m src.main --suite smoke --runs 1 --verbose
```

**Core suite** (Phase 0–7):

```bash
python3 -m src.main --suite core --runs 1 --json-out out/core_results.json
```

**Full suite** (all phases):

```bash
python3 -m src.main --suite all --runs 1 --md-out out/full_report.md
```

**Single scenario** (debug):

```bash
python3 -m src.main --only phase1_test_1_1_clean_reservation --verbose
```

## Expected Output

- **Smoke suite pass**: all 4 scenarios pass → INTERNAL ALPHA READY
- **Core suite pass**: ≥90% of Phase 0–7 scenarios pass → SUPERVISED BETA READY
- **Full suite pass**: ≥95% overall, 100% critical safety, 0 legacy hits → PRODUCTION READY

Reports saved to `out/` directory as JSON + Markdown.

## Troubleshooting

### OPENAI_API_KEY not set

```
ValueError: OPENAI_API_KEY not set in environment. Please set: export OPENAI_API_KEY=sk-...
```

Solution: Set your OpenAI API key:

```bash
export OPENAI_API_KEY=sk-your-key-here
```

### Connection refused

```
ConnectionRefusedError: [Errno 111] Connection refused
```

Solution: Ensure v4 server is running on ws://127.0.0.1:8080/ws/headless

```bash
cd /home/charles2/sailly-browser-demo
python3 -m server.main  # Or however you normally start the server
```

### DB connection failed

```
psycopg.OperationalError: connection failed
```

Solution: Ensure Postgres is running and SAILLY_PG_DSN is correct:

```bash
export SAILLY_PG_DSN=postgresql://sailly:sailly@localhost:5432/sailly
```

## Architecture

- **Transport**: Headless JSON WS protocol (`/ws/headless`)
- **Caller LLM**: OpenAI GPT-4o (JSON-mode)
- **Verification**: V4-native rules (10 global + scenario-specific)
- **Metrics**: From `google_turn_metrics` table + per-turn WS telemetry
- **Scoring**: Per-call + aggregate against Internal-Alpha / Supervised-Beta / Production thresholds

## Files

- `src/main.py` — CLI entry point
- `src/config.py` — Config loading
- `src/transport.py` — WS client
- `src/persona.py` — GPT-4o caller simulator
- `src/runner.py` — Scenario orchestrator
- `src/verifier.py` — Rule verification (10 global rules)
- `src/metrics.py` — DB metrics collection
- `src/scoring.py` — Report generation
- `src/scenario_loader.py` — YAML scenario parsing
- `scenarios/phase{0..10}/` — 10+ test scenarios per phase
- `tests/` — Unit tests (no server required)

## Next Steps

1. ✓ Scaffold complete (you are here)
2. ✓ Transport implemented
3. ✓ Persona LLM implemented
4. ✓ Scenarios authored (smoke/core coverage)
5. ✓ Verifier + metrics implemented
6. ✓ Unit tests passing
7. → Start v4 server and run smoke suite
8. → Iterate on scenarios/rules based on results
9. → Target: Internal Alpha (smoke 10/10) in first run
