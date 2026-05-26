# Sound Validation — STS Caller Test Harness

**Status:** ✓ Phase A Infrastructure PASSED (May 1, 2026, 01:25 UTC+2)

Sound Validation is a fully automated STS (Speech-to-Speech) test harness for Sailly. Unlike text-only testing, Sound Validation uses real voice calls with 5 realistic caller personas over a programmatic audio bridge to catch real-world failure modes: barge-in timing, STT confidence on accented speech, TTS latency spikes, and natural German hesitation.

## Why STS?

Text-mode testing (`/ws/headless`) cannot catch:
- **Barge-in timing** — caller interrupts mid-response
- **STT confidence** — accented speech misrecognized
- **TTS latency** — speed variations impact turn rhythm
- **Turn detection** — VAD misfires or early cutoff
- **Natural speech** — hesitation ("äh", "also"), pacing, emotion

Sound Validation uses **Grok Voice Agent** (OpenAI-Realtime-compatible) as the synthetic caller, connected via a programmatic PCM16 audio bridge to Sailly's `/ws/demo` WebSocket.

## Architecture

```
┌─────────────────────────────────────────────┐
│  Sound Validation Loop (loop_runner.py)     │
│  • Phase A–G orchestrator                   │
│  • Fix loop (Claude → patches → restart)    │
│  • 3 attempts per phase                     │
└─────────────┬───────────────────────────────┘
              │
      ┌───────▼────────┐
      │ Phase Runner   │
      │ (asyncio.gather│
      │  all calls)    │
      └───────┬────────┘
              │
      ┌───────▼──────────────────────────┐
      │ Grok Caller Bridge (per scenario) │
      │ • Grok Realtime (STS caller)     │
      │ • Audio resampling (24k↔16k)     │
      │ • Transcript capture             │
      │ • 120s max per call              │
      └───────┬──────────────────────────┘
              │
       ┌──────┴──────┐
       │             │
   ┌───▼──┐    ┌────▼────────┐
   │ Grok │    │ Sailly /ws/ │
   │Voice │◄──►│    demo      │
   │Agent │    │  (PCM16 24k) │
   └──────┘    └─────────────┘
```

## Quick Start

### 1. Prerequisites

```bash
# Install dependencies
pip install websockets aiohttp anthropic --break-system-packages

# Verify Sailly is running on port 8080
curl http://localhost:8080/healthz
# Expected: {"status":"ok","service":"sailly-browser-demo",...}
```

### 2. Set API Keys

Choose one:

```bash
# Grok (xAI, $0.05/min, faster startup)
export XAI_API_KEY="your-grok-key"

# OR OpenAI (GPT-4o Realtime, $0.10/min, fallback)
export OPENAI_API_KEY="your-openai-key"

# Claude (for auto-fix generation)
export ANTHROPIC_API_KEY="your-claude-key"
```

### 3. Run Phase A Smoke Test

```bash
cd /home/charles2/sailly-browser-demo

# Check infrastructure (no API keys needed)
python3 server/validation/phase_a_smoke_test.py

# Run full Phase A with real STS (needs API keys)
python3 -m server.validation.loop_runner
```

### Expected Output (Phase A Smoke Test)

```
======================================================================
SOUND VALIDATION — PHASE A SMOKE TEST
Integration Test (Infra Verification)
======================================================================

[Test 1] Health endpoint check...
  ✓ Sailly service is healthy: ok
    Port: 8080
    Active connections: 0

[Test 2] WebSocket /ws/demo availability...
  ✓ /ws/demo endpoint is accepting connections
  ✓ /ws/demo endpoint exists and is accessible

[Test 3] Service manager health polling...
  ✓ Service manager successfully polled health endpoint

[Test 4] Phase and scenario definitions...
  ✓ Phase A loaded: 0_phase_a_smoke
    Base scenarios: 4
    With 5 personas: 20 total test cases
    Pass threshold: 100%

[Test 5] Report infrastructure...
  ✓ Report generator initialized
    Reports dir: /home/charles2/sailly-browser-demo/reports

======================================================================
PHASE A SMOKE TEST: 5/5 infrastructure checks passed

✓ PHASE A PASSED
  Sound Validation infrastructure is ready for STS testing
  Next step: Provide XAI_API_KEY or OPENAI_API_KEY for real audio calls
```

## Phase Definitions

### Phase A: Smoke Test (Blocker)

4 base scenarios × 5 personas = **20 calls**

| Scenario | Goal | Expected Tools |
|----------|------|---|
| A1_greeting | Verify greeting works | - |
| A2_faq_hours | Ask opening hours | get_restaurant_info |
| A3_reservation | Book table for 2 tomorrow 19:00 (Mueller, 0228 123456) | create_reservation |
| A4_order | Order 2x Bulgogi takeaway (Schmidt, 0179 345 6789) | create_order |

**Personas (5 × each scenario):**
- `neutral` — standard polite German
- `eilig` — impatient, cuts bot off
- `aeltere_person` — slow, confused
- `froehlich` — chatty, friendly
- `wuetend` — frustrated, escalates

**Pass Threshold:** 100% (20/20 calls must pass)

**Blocker:** If Phase A fails 3×, entire loop stops.

### Phases B–G

*(To be implemented)*

- **Phase B**: FAQ (6 clusters, 30 calls)
- **Phase C**: Smalltalk (4 scenarios, 20 calls)
- **Phase D**: Reservation variations (6 scenarios, 30 calls)
- **Phase E**: Order variations (12 scripts, 60 calls)
- **Phase F**: Multi-intent (36 calls)
- **Phase G**: Chaos (10+ scenarios, 50 calls)

## File Structure

```
server/validation/
├── __init__.py
├── __main__.py                     # CLI entry point
├── loop_runner.py                  # Main orchestrator
├── phase_runner.py                 # asyncio.gather batch runner
├── grok_caller_bridge.py           # Audio bridge (Grok ↔ Sailly)
├── scenario_matrix.py              # Persona variants
├── service_manager.py              # Restart + health checks
├── report_generator.py             # Per-phase + final reports
├── phase_a_smoke_test.py           # Phase A infra test
├── data_structures.py              # PhaseConfig, ScenarioConfig, etc.
├── phases/
│   ├── __init__.py
│   └── definitions.py              # PHASE_A, PHASE_B, etc.
└── reports/                        # Generated markdown + JSON reports
    ├── phase_a_smoke_attempt1.json
    ├── phase_a_smoke_attempt1.md
    ├── phase_a_smoke_attempt2.json
    └── final_summary.md
```

## Environment Variables

```bash
# STS Caller (required for real audio calls)
XAI_API_KEY=...                    # Grok (primary)
OPENAI_API_KEY=...                # OpenAI Realtime (fallback)

# Auto-fix generation
ANTHROPIC_API_KEY=...             # Claude

# Service endpoints
SAILLY_WS_URL=ws://localhost:8080/ws/demo    # Default
SAILLY_HEALTH_URL=http://localhost:8080/healthz  # Default
DATABASE_URL=postgresql://sailly:sailly@localhost:5432/sailly

# Reports output
REPORTS_DIR=./reports
```

## Key Design Decisions

### Personas (5, not 8)

Covers realistic caller spectrum without combinatorial explosion:
- **neutral** — baseline
- **eilig** — detects barge-in and turn-detection issues
- **aeltere_person** — detects speech clarity issues
- **froehlich** — detects chit-chat loop
- **wuetend** — detects escalation handling

### Audio Bridge

- **Grok → Sailly:** Caller audio (24 kHz PCM16 from Grok) → resampled to 16 kHz → forwarded to Sailly `/ws/demo`
- **Sailly → Grok:** Bot audio (24 kHz PCM16 from Sailly) → base64 encoded → `input_audio_buffer.append` → Grok VAD processes
- **Resampling:** `soxr` with `numpy` fallback
- **Max duration:** 120s per call

### Phase Loop

```
for attempt in 1..max_fix_attempts:
  1. Run all scenarios in parallel (asyncio.gather)
  2. Wait for ALL audio to complete (critical!)
  3. Evaluate pass rate vs. threshold
  4. If passed: move to next phase
  5. If failed & attempt < max:
     - Generate fixes via Claude API
     - Apply patches atomically
     - Restart service
     - Health-check until ready
     - Loop back to step 1
  6. If failed after 3 attempts:
     - Report as FAILED phase
     - Continue (Phase A is blocker only)
```

## Reports

After each phase attempt:

**Markdown Report** (`phase_a_smoke_attempt1.md`)
```markdown
# phase_a_smoke — Attempt 1

**Status:** ✓ PASSED

- **Passed:** 20/20 (100%)
- **Threshold:** 100%
- **Duration:** 87.3s

## Failures

None — all scenarios passed!
```

**JSON Report** (`phase_a_smoke_attempt1.json`)
```json
{
  "phase": "phase_a_smoke",
  "attempt": 1,
  "total": 20,
  "passed": 20,
  "failed": 0,
  "pass_rate": 1.0,
  "threshold": 1.0,
  "met_threshold": true,
  "duration_s": 87.3,
  "timestamp": "2026-05-01T01:25:57.314Z"
}
```

**Final Summary** (`final_summary.md`)
```markdown
# Sound Validation — Final Summary

**Report Generated:** 2026-05-01T01:25:57.314Z

## Overall

- **Total Scenarios:** 20
- **Passed:** 20
- **Pass Rate:** 100.0%

## Per-Phase Results

- **phase_a_smoke**: 20/20 (100%) — ✓ PASS
```

## Monitoring

During a run:

```bash
# In another terminal
tail -f reports/*.md
# or
watch 'curl -s http://localhost:8080/healthz | jq'
```

## Troubleshooting

### No API keys set

```
ValueError: Neither XAI_API_KEY nor OPENAI_API_KEY set. Cannot proceed.
```

**Solution:** Set `XAI_API_KEY` or `OPENAI_API_KEY` environment variable.

### Service not healthy

```
[Service] Did not become healthy within 60s
```

**Solution:** Ensure Sailly is running on port 8080:
```bash
curl http://localhost:8080/healthz
```

### Connection refused

```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Solution:** Start Sailly server:
```bash
cd /home/charles2/sailly-browser-demo
python3 -m server.main
```

## Next Steps

1. ✓ **Phase A infrastructure verified** (May 1, 2026)
2. → Set `XAI_API_KEY` or `OPENAI_API_KEY`
3. → Run `python3 -m server.validation.loop_runner`
4. → Monitor `reports/phase_a_smoke_attempt*.md`
5. → Target: Phase A 20/20 pass rate

---

**Built:** May 1, 2026, 01:25 UTC+2  
**Status:** Ready for real STS testing (awaiting API keys)
