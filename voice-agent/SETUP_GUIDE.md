# Sailly Browser Demo — Setup & Deployment Guide

## What Was Built

A completely isolated, standalone browser-based demo of the Sailly voice agent.

### Key Files

#### Brain (Exact Copies from Validated Source)
- `server/brain/adk_runner.py` — The reference orchestrator (11,043 lines)
- `server/brain/node_manager.py` — Node selection + forced commits
- `server/brain/conversation_state.py` — State tracking
- `server/brain/conversation_nodes.py` — Per-node prompts and tool definitions
- `server/brain/tier2_runner.py` — Gemini 2.5 Flash LLM + TTS
- `server/brain/memory_manager.py` — Context compression
- `server/brain/response_variations.py` — Anti-repetition logic
- `server/brain/conversation_loop.py` — ConvTurn, ConvResult dataclasses
- `server/brain/audio_injector.py` — Training audio pipeline (not used at runtime)
- `server/brain/call_auditor_de.py` — Conversation scoring

**Verification**: All files are byte-identical to originals (diff shows only import-path changes).

#### New Code (Thin Wrappers)
- `server/brain_service.py` — Pipecat wrapper around adk_runner per-turn logic
- `server/main.py` — FastAPI app + /ws/demo endpoint
- `server/tools/executor.py` — Mock tool responses (stateless)
- `server/browser_serializer.py` (copied) — WebSocket frame serializer
- `server/sailly_gemini_tts.py` (copied) — Gemini TTS with cascade support

#### Frontend (Vanilla JS, No Build Step)
- `frontend/index.html` — UI with phone mockup
- `frontend/app.js` — WebSocket client + microphone capture
- `frontend/worklet.js` — AudioWorklet processor (PCM16 16kHz)
- `frontend/style.css` — Sailly brand styling

#### Configuration
- `.env.example` — Template for API keys
- `requirements.txt` — Python dependencies (exact versions)
- `README.md` — Project overview
- `configs/tenants/doboo.yaml` — Restaurant config (copied)

---

## Initial Setup (First Time)

```bash
cd /home/charles2/sailly-browser-demo

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys:
#   DEEPGRAM_API_KEY=your_key
#   GOOGLE_APPLICATION_CREDENTIALS=/path/to/creds.json
#   GOOGLE_CLOUD_PROJECT=sailly-voice-agent-eu

# Run the server
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8080 --reload
```

**Output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8080
Press CTRL+C to quit
```

Visit `http://localhost:8080` in your browser.

---

## Running the Demo

1. Click the green button **"Anruf starten"** (Start Call)
2. Grant microphone permission when prompted
3. Speak naturally: "Hallo", "Ich möchte Bibimbap bestellen", etc.
4. Listen to the agent respond
5. Click the red button **"Anruf beenden"** (End Call) when done

**Chat bubbles** show:
- **Purple/pink**: Your voice (user)
- **Gray**: Agent response (bot)

---

## Systemd Service (Optional)

Create `/etc/systemd/system/sailly-browser-demo.service`:

```ini
[Unit]
Description=Sailly Browser Demo
After=network.target

[Service]
Type=simple
User=charles2
WorkingDirectory=/home/charles2/sailly-browser-demo
Environment="PATH=/home/charles2/sailly-browser-demo/venv/bin"
Environment="DEEPGRAM_API_KEY=your_key"
Environment="GOOGLE_APPLICATION_CREDENTIALS=/home/charles2/.ssh/sailly-voice-agent-key.json"
Environment="GOOGLE_CLOUD_PROJECT=sailly-voice-agent-eu"
Environment="DEMO_PORT=8080"
ExecStart=/home/charles2/sailly-browser-demo/venv/bin/python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8080
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable sailly-browser-demo.service
sudo systemctl start sailly-browser-demo.service
sudo systemctl status sailly-browser-demo.service
```

---

## Audio Pipeline

### Capture (Browser → Server)

```
Microphone
    ↓ MediaStream
AudioContext (16kHz)
    ↓
AudioWorklet
    ↓ 320-sample chunks
PCM16 Encoder
    ↓ 4-byte chunk ID + PCM data
WebSocket
    ↓
BrowserFrameSerializer
```

### Processing (Server)

```
WebSocket
    ↓
BrowserFrameSerializer
    ↓ Extract PCM16 16kHz
FastAPIWebsocketTransport
    ↓
DeepgramSTT (nova-3, de)
    ↓ User text
LLMUserResponseAggregator (with SileroVAD at aggregator layer)
    ↓
BrowserBrainService
    ↓ Delegates to adk_runner.py logic
Tier2AudioRunner (Gemini 2.5 Flash)
    ↓
LLMAssistantResponseAggregator
    ↓
SaillyGeminiTTSService
    ↓ PCM16 24kHz
WebSocket
    ↓
Browser (plays audio)
```

---

## Configuration Notes

### Brain Settings (Validated)
- **Gemini**: `gemini-2.5-flash`, `temperature=0.0` (NOT 0.6 — that was a bug)
- **VAD**: `min_volume=0.2`, `start_secs=0.4`, `stop_secs=0.8` (at aggregator layer, NOT transport)
- **STT**: Deepgram `nova-3`, German, `endpointing=350`
- **TTS**: Gemini `gemini-2.5-flash-tts`, German

### Audio Format
- **In**: PCM16 LE mono 16kHz + 4-byte chunk ID prefix
- **Out**: PCM16 LE mono 24kHz (raw, no header)
- **Chunk size**: 320 samples (~20ms @ 16kHz)

### Tools (Mock)
All tools return realistic fake data:
- `get_menu` → menu list
- `create_order` → `{"success": true, "order_id": "DEMO-..."}`
- `create_reservation` → `{"success": true, "reservation_id": "RES-..."}`
- `check_availability` → time slots
- `verify_address` → validation result
- etc.

---

## Debugging

### Check Logs
```bash
tail -f /tmp/demo.log  # If running with logging
# OR check the console output
```

### Test WebSocket Handshake
```bash
# Terminal 1: Start server
python3 -m uvicorn server.main:app --host 0.0.0.0 --port 8080

# Terminal 2: Send WebSocket message
python3 << 'EOF'
import websocket
import json

ws = websocket.create_connection("ws://localhost:8080/ws/demo")
ws.send(json.dumps({"tenant": "doboo", "voice": "Kore"}))
print("Handshake sent, waiting for response...")
# Browser should handle this
ws.close()
EOF
```

### Verify Brain Imports
```bash
cd /home/charles2/sailly-browser-demo
python3 << 'EOF'
from server.brain.adk_runner import ADKRunner
from server.brain.node_manager import NodeManager
from server.brain.conversation_state import ConversationState
print("✓ All brain imports OK")
EOF
```

### Check File Integrity
```bash
cd /home/charles2
for f in adk_runner.py node_manager.py conversation_state.py; do
  if diff <(sed 's/server\.brain\./server.training./g' sailly-browser-demo/server/brain/$f) \
          sailly-google-fork/server/training/$f > /dev/null; then
    echo "✓ $f is identical"
  else
    echo "✗ $f HAS DIFFERENCES"
  fi
done
```

---

## Bug Fix Workflow

If you find a bug in the demo:

1. **Fix the validated source** (where the bug really is):
   ```bash
   # Edit /home/charles2/sailly-google-fork/server/training/adk_runner.py
   # or any brain file
   ```

2. **Re-run validation loop** to confirm the fix works

3. **Copy the fixed file**:
   ```bash
   cp /home/charles2/sailly-google-fork/server/training/BUGGY_FILE.py \
      /home/charles2/sailly-browser-demo/server/brain/BUGGY_FILE.py
   ```

4. **Update imports** (if needed):
   ```bash
   sed -i 's/from server\.training\./from server.brain./g' \
      /home/charles2/sailly-browser-demo/server/brain/BUGGY_FILE.py
   ```

5. **Test in demo** — the fix is now active

6. **Redeploy production** — it gets the same fix

---

## Isolation Guarantees

- **Port**: 8080 (production on 3003)
- **Database**: None (stateless)
- **Redis**: Not used
- **Twilio**: Not used
- **Cost**: Only Deepgram + Google API (no call minutes)

The demo can run while production is down, and vice versa.

---

## Next Steps

1. **First run**: Navigate to `http://localhost:8080` and test
2. **Verify greeting**: Say "Hallo" — agent should respond
3. **Test ordering flow**: "Ich möchte Bibimbap" → full order flow
4. **Check transcripts**: Verify user/bot messages appear correctly
5. **Monitor logs**: Watch for any errors
6. **Deploy to production**: When confident, redeploy to `sailly-google-fork`
