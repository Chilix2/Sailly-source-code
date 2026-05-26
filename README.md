# Sailly Voice Agent

Production browser-based Sailly voice agent for restaurant calls and demos.
The live host runs this flat tree from `/home/charles2/sailly-browser-demo`.
GitHub stores the same source under `voice-agent/`.

## Production Path

The live service runs `uvicorn server.main:app` on port 8080 and the voice
pipeline is:

```text
Browser / phone audio
  -> server/main.py (/ws/demo)
  -> BrowserBrainService
  -> V4TurnProcessor
  -> v4_pipeline.process_turn_v4
  -> tools/executor.py + server/tools/handlers
  -> SaillyGeminiTTSService
```

The old ADK/node-manager stack has been removed from the production runtime.
Validation and training code that remains in the repository is tooling, not the
live turn processor.

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

Visit `http://localhost:8080` in your browser.

## Architecture

Production runtime:

- `server/main.py` — FastAPI app, WebSocket endpoint, Pipecat pipeline wiring
- `server/brain_service.py` — Pipecat brain processor and call finalization
- `server/brain/v4_turn_processor.py` — live turn-processor adapter
- `server/brain/v4_pipeline.py` — deterministic v4 turn flow
- `server/brain/conversation_state.py` — live state model
- `server/brain/workers/` — deterministic workers used by v4
- `tools/executor.py` and `server/tools/handlers/` — tool execution
- `configs/tenants/` and `configs/providers/` — runtime configuration

## Files

- `server/brain/` — live v4 brain and support modules
- `server/brain_service.py` — Pipecat wrapper and persistence/finalization
- `tools/executor.py` — production tool dispatcher
- `server/main.py` — FastAPI app + WebSocket endpoint
- `frontend/` — vanilla JS, mic capture, audio playback, chat UI
- `configs/tenants/doboo.yaml` — restaurant config
- `docs/PRODUCTION_LEGACY_MANIFEST.md` — production/tooling/legacy classification

## Testing

Run validation scenarios:
```bash
./run_validation.sh
```

## GitHub Layout

GitHub repo layout:

```text
Sailly-source-code/
  .github/
  README.md
  voice-agent/
    server/
    configs/
    tools/
    frontend/
```

Do not push a duplicate root-level `server/`, `configs/`, or `tools/` tree to
GitHub. The production app belongs under `voice-agent/` in the GitHub snapshot.

## Isolation

- **Port:** 8080 (production voice agent on 3003, dashboard on 3000)
- **Service:** Separate systemd service
- **Database:** PostgreSQL `google_*` call tables
- **Redis:** session state and metrics
- **Secrets:** environment or Google Secret Manager

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
