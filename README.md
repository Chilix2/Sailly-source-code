# Sailly Voice Agent — Vertical Platform

A production **vertical voice-agent platform** for German businesses (restaurants, medical practices, automotive shops, etc.). Multi-tenant architecture with configurable agent behavior, menu items, business logic, and conversational flows per tenant.

## Platform Overview

Sailly is a German-language conversational AI system that handles phone/browser calls, captures orders/reservations, and integrates with business tools. The platform is **tenant-driven**: DOBOO (Korean restaurant) is one reference tenant; the system supports unlimited additional tenants through YAML configuration.

**Key principle:** *LLM for language, code for state.* All business logic, menu data, thresholds, and agent personality are externalized to tenant YAML files. The brain code contains zero tenant-specific hardcodes.

## Production Path

The live service runs `uvicorn server.main:app` on port 8080 and the voice pipeline is:

```text
Browser / phone audio
  -> server/main.py (/ws/demo or /ws/headless)
  -> BrowserBrainService
  -> V4TurnProcessor
  -> v4_pipeline.process_turn_v4  [FSM-driven conversation state machine]
  -> conversation_fsm.py           [Finite State Machine: 6 phases]
  -> slot_extractors.py            [Robust German NLP extraction]
  -> tools/executor.py + handlers  [Category A/B tool execution]
  -> SaillyGeminiTTSService
```

The old ADK/node-manager stack has been removed. Validation and training code that remains is tooling, not the live turn processor.

## Business Context

**Target Market:** German businesses (restaurants, medical practices, etc.)
**Language:** German (de-DE), all prompts configurable per tenant
**Phone Format:** German-specific (+49 country code, spoken format "null neun zwei acht...")
**Address Format:** German addresses; postal codes vary by tenant delivery zones
**Timezone:** Europe/Berlin (per tenant, configurable)
**Formality:** Sie-form (formal German "you") as default, configurable per tenant

## Setup

```bash
cd sailly-browser-demo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

## Run

```bash
source venv/bin/activate
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8080 --reload
```

Visit `http://localhost:8080` in your browser or run headless tests via `ws://localhost:8080/ws/headless`.

## Architecture

**Production Runtime:**

- `server/main.py` — FastAPI app, WebSocket endpoints (`/ws/demo`, `/ws/headless`)
- `server/brain_service.py` — Pipecat brain processor, call finalization
- `server/brain/v4_turn_processor.py` — live turn-processor adapter
- `server/brain/v4_pipeline_clean.py` — FSM-driven v4 turn flow (refactored)
- `server/brain/conversation_fsm.py` — Finite State Machine: GREETING → INFO → ORDER/RESERVE → READBACK → COMMITTED
- `server/brain/conversation_state.py` — state model, slot persistence (Redis schema v7)
- `server/brain/slot_extractors.py` — German NLP: phone, date, address, menu items
- `server/brain/workers/` — deterministic workers (phone, name, date extraction)
- `server/core/tenant_config.py` — TenantConfig model (~65 fields, from YAML)
- `configs/tenants/doboo.yaml` — reference tenant configuration
- `configs/tenants/pizzeria_napoli.yaml` — second tenant example
- `configs/tenants/default.yaml` — neutral defaults for all fields
- `tools/executor.py` and `server/tools/handlers/` — tool execution (Category A/B)

**Multi-Tenant Model:**

Every tenant is defined by a YAML file at `configs/tenants/<tenant_id>.yaml`. The file contains:
- Business identity: name, city, phone, timezone
- Operational: menu items, order thresholds, delivery zones, opening hours
- Conversational: German slot prompts, confirmation tokens, formality level
- LLM: temperature, fallback model, extraction timeouts
- TTS/STT: pronunciation hints, language-specific keywords, audio thresholds
- Thresholds: all magic numbers (collection_max_attempts, confirmation_cycle_max, etc.)

**No hardcoded tenant values exist in Python code.**

## Files

- `server/brain/` — live FSM-driven brain and support modules
- `server/brain_service.py` — Pipecat wrapper, persistence, finalization
- `tools/executor.py` — multi-tenant tool dispatcher
- `server/main.py` — FastAPI app + WebSocket endpoints
- `frontend/` — vanilla JS, mic capture, audio playback, chat UI
- `configs/tenants/` — all tenant configurations (YAML)
- `docs/PRODUCTION_LEGACY_MANIFEST.md` — classification of production vs. tooling code

## Testing

Run FSM tests for multi-tenant validation:
```bash
pytest server/tests/test_conversation_fsm.py -v
```

Run full regression suite (both tenants):
```bash
pytest server/tests/regression/ -v
```

Run headless E2E tests:
```bash
python scripts/load_test.py --tenant doboo --count 3
python scripts/load_test.py --tenant pizzeria_napoli --count 3
```

## GitHub Layout

```text
sailly-browser-demo/
  .github/workflows/      — CI/CD (pytest, hardcode guard, tenant schema validation)
  README.md               — this file
  AGENTS.md               — developer guide
  server/                 — live runtime code
  configs/tenants/        — tenant YAML configurations
  tools/                  — tool executors
  frontend/               — browser UI
  docs/                   — architecture docs
  scripts/                — deployment and testing scripts
  server/tests/           — pytest suite (unit, integration, E2E)
```

There is no second copy of the app tree in the repository.

## Isolation & Deployment

- **Port:** 8080 (production voice agent; dashboard on 3000, headless on 3003 via nginx)
- **Service:** `sailly-browser-demo.service` (systemd)
- **Database:** PostgreSQL `call_reports` table (per-call logs)
- **Redis:** session state (`{tenant_id}:session:{call_id}`) and metrics
- **Secrets:** `.env` (local dev) or Google Secret Manager (prod)
- **Tenant Resolution:** JWT session token (`tenant` claim) or query parameter

## German Language Specifics

- **Phone numbers:** `+49 228 1234567` spoken as "null neun zwei acht eins zwei drei vier fünf sechs sieben"
- **Dates:** Supports "nächsten Samstag" (next Saturday), "achtzehnten Mai" (18th of May), with guards for year-bumping and past-date rejection
- **Address:** German Umlaute (ä, ö, ü) and common variants (e.g., "Bonner Bogen" → "Am Bonner Bogen") mapped in tenant config
- **Confirmation:** Two-pass gate — exact German tokens ("ja", "nein", "passt so") + optional LLM scorer for ambiguous cases
- **Backchannel:** German "ja" and "genau" are configured NOT to interrupt bot (configurable per tenant)

## Key Refactoring: FSM Architecture

**Old Problem:** 7 different confirmation detectors, 99 writes to `end_call_stage`, 53 references to commit gates → constant desync, readback loops.

**New Solution:** Single `Slots.confirmed` boolean field, driven by 6-phase FSM:
1. **GREETING** — agent intro, intent detection
2. **INFO** — FAQ, menu queries, business info
3. **ORDER** / **RESERVE** — slot collection (items/date/party_size/address/phone/name)
4. **READBACK** — confirmation with two-pass guard (keyword gate + optional LLM)
5. **COMMITTED** — Category B tool execution (create_order, send_sms, etc.)

FSM is **tenant-aware**: transitions, tools, and thresholds all driven by TenantConfig, not hardcoded.

## Development & Contribution

See `AGENTS.md` for developer guide and project workspace rules.

For multi-tenant testing, use `pytest --co` to see fixtures, or pass `-k doboo` / `-k pizzeria` to filter by tenant.

## References

- `docs/PRODUCTION_LEGACY_MANIFEST.md` — what is production vs. training vs. archive
- `.cursor/rules/` — Cursor IDE rules for this workspace
- `AGENTS.md` — developer guide

## Verification

Check syntax for core production files:

```bash
python3 - <<'PY'
from pathlib import Path
for rel in [
    "server/main.py",
    "server/brain_service.py",
    "server/brain/v4_turn_processor.py",
    "server/brain/v4_pipeline.py",
    "tools/executor.py",
]:
    compile(Path(rel).read_text(), rel, "exec")
print("ok")
PY
```
