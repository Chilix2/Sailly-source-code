# Sailly Browser Demo

A completely isolated browser-based demo of the Sailly voice agent. Test, onboard clients, and conduct sales demos without Twilio costs.

## Key Principle

**The brain files (`server/brain/`) are exact copies of the validated pipeline.** They are never modified, only copied. If a bug is found, it is fixed in the validated source (`sailly-google-fork/server/training/`) and re-copied here.

This guarantee ensures: **demo = validated = production**

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

```
Browser (mic + speaker)
    ↓ PCM16 16kHz + 4-byte chunk ID
WebSocket (/ws/demo)
    ↓
Deepgram STT (nova-3, de)
    ↓
LLMUserResponseAggregator + VAD (SileroVAD)
    ↓
BrowserBrainService (Pipecat wrapper)
    ↓ delegates to
server/brain/adk_runner.py (EXACT COPY of validated)
    ↓
Tools (mock responses from server/tools/executor.py)
    ↓
LLMAssistantResponseAggregator
    ↓
Google Gemini 2.5 Flash TTS
    ↓
PCM16 24kHz
    ↓
WebSocket
    ↓
Browser (plays audio)
```

## Files

- `server/brain/` — validated pipeline copied from `sailly-google-fork/server/training/`
- `server/brain_service.py` — thin Pipecat wrapper around `adk_runner.py` per-turn logic
- `server/tools/executor.py` — mock tool responses (no database)
- `server/main.py` — FastAPI app + WebSocket endpoint
- `frontend/` — vanilla JS, mic capture, audio playback, chat UI
- `configs/tenants/doboo.yaml` — restaurant config

## Testing

Run validation scenarios:
```bash
python3 scripts/test_brain.py
```

## Bug Fixes

When a bug is found in the browser demo:

1. Fix it in `/home/charles2/sailly-google-fork/server/training/` (validated source)
2. Re-run the validation loop to confirm
3. Copy the fixed file to `server/brain/`
4. Both demo and production get the fix

## Isolation

- **Port:** 8080 (production voice agent on 3003, dashboard on 3000)
- **Service:** Separate systemd service
- **Database:** None (stateless demo)
- **Twilio:** Not used
- **Redis:** Not used

## Verification

Prove brain files are identical to validated source:
```bash
diff <(sed 's/server\.brain\./server.training./g' server/brain/adk_runner.py) \
     ../sailly-google-fork/server/training/adk_runner.py
```

Should show only import-path differences.
