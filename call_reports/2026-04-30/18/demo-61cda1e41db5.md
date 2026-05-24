# Sailly — Full Call Analysis Report
## Call ID: `demo-61cda1e41db5`
_Generated: 2026-04-30 18:45 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-61cda1e41db5` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-04-30 18:44:44 UTC |
| **Ended** | 2026-04-30 18:45:12 UTC |
| **Duration** | **28 seconds (0:28 min)** |
| **Total DB turns** | 7 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1964 ms |
| **p95 latency (stored)** | 5304 ms |
| **Max latency (stored)** | 7060 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 42.379 ¢ |

### Pipeline configuration (runtime snapshot)

```
STT:  DeepgramFluxSTTService (flux-general-multi, EU endpoint, eot_threshold=0.6, eot_timeout_ms=3000 ms, mip_opt_out=True)
VAD:  None — Deepgram Flux semantic EOT (eot_threshold=0.6, eot_timeout_ms=3000)
LLM:  claude-haiku-4-5 (Vertex region env: us-east5)
Worker pipeline: IntentSessionManager (shadow) → WorkerRouter (15 profiles) → WorkerExecutor (Required≤280ms / Optional≤350ms / Background)
TTS:  SaillyGeminiTTSService — voice=Kore, engine=chirp3hd
      GLOBAL_SPEED_MULTIPLIER=2.25 (env override possible)
Filler: pre-baked PCM 12-phrase pool, 400ms trigger (ENABLE_PRE_LLM_FILLER=true) | Backchannel: 6-phrase pool, 200-500ms hesitation window (ENABLE_BACKCHANNEL=true)
MULTI-INTENT / ADK: Enabled per brain configuration for browser demo
ValidationRegistry: async validation when configured
TTS Conditioning: Phase 2 — situation + mood → prosody_rate_pct → Gemini speaking_rate
Barge-in: enabled post-greeting when BargeInHandler is in pipeline
Monitoring thresholds (env): MONITOR_LATENCY_P95_MS=3000 ms, MONITOR_SUCCESS_THRESHOLD=80, Redis monitor=1
```

---

## 2. Aggregate health (from `google_turn_metrics`)

| Check | Value | Notes |
|-------|-------|-------|
| Latency p50 / p95 / max (total) | 1142 / 7060 / 7060 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1137 / 7056 ms | From `llm_latency_ms` column |
| STT p50 | 5 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| Call-level observability (stored on `google_calls`) | validation_registry_invocations=0, loop_incidents=0 | From `persist_call_aggregates` |

---

## 3. Caller-flag insights (`Achtung Sailly: …` / `Attention Sailly: …`)

_Test harness, caller-bot, or human reviewer: phrases like **Achtung Sailly:** (also **Attention Sailly:** / **Warnung Sailly:**) mark what Sailly did **wrong** — use this for qualitative issues that **latency and tool metrics may not show**._

_No matching caller markers in `google_transcripts` (non-assistant roles), `session_data.transcripts`, or `user_text` in turn metrics._
## 4. Per-turn breakdown (DB)

### Turn 1

```
stt_latency_ms:    5
llm_latency_ms:    1202 ✅
tts_latency_ms:    0
total_latency_ms:  1208 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     greeting_first
tts_mood:          neutral
tts_rate_pct:      200
node_name:         greeting
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['ai_greeting', 'get_date_info', 'ai_greeting']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** fine.

**Bot:** Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?

---

### Turn 2

```
stt_latency_ms:    5
llm_latency_ms:    1137 ✅
tts_latency_ms:    0
total_latency_ms:  1142 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_rate_pct:      200
node_name:         greeting
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['ai_greeting', 'get_date_info', 'ai_greeting']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Begrüßung okay

**Bot:** Vielen Dank für Ihr Interesse an DOBOO Korean Soulfood! Möchten Sie gerne etwas bestellen oder haben Sie Fragen zu unserem Angebot?

---

### Turn 3

```
stt_latency_ms:    5
llm_latency_ms:    1103 ✅
tts_latency_ms:    0
total_latency_ms:  1108 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_rate_pct:      200
node_name:         greeting
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['ai_greeting', 'get_date_info', 'ai_greeting']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Turn zwei, ich habe beide intens.

**Bot:** Wie kann ich Ihnen heute helfen – möchten Sie bestellen oder haben Sie Fragen zu unserem koreanischen Angebot? Gerne unterstütze ich Sie!

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1016 ✅
tts_latency_ms:    0
total_latency_ms:  1020 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 1049 / 6 / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_rate_pct:      200
node_name:         reservation
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['check_availability']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Reservierung gestellt.

**Bot:** Ah, verstanden — Sie möchten eine Reservierung vornehmen! Für welches Datum hätten Sie denn gerne einen Tisch?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    7056 ⚠️
tts_latency_ms:    0
total_latency_ms:  7060 ⚠️
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 1049 / 6 / 596
tts_situation:     info_neutral
tts_mood:          neutral
tts_rate_pct:      200
node_name:         greeting
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['ai_greeting', 'get_date_info', 'ai_greeting']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Turns good.

**Bot:** Sehr gerne helfe ich Ihnen weiter! Für welches Datum und wie viele Personen möchten Sie denn einen Tisch reservieren?

---

### Turn 6

```
stt_latency_ms:    7
llm_latency_ms:    1152 ✅
tts_latency_ms:    0
total_latency_ms:  1159 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 1049 / 6 / 596
tts_situation:     info_neutral
tts_mood:          neutral
tts_rate_pct:      200
node_name:         greeting
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['ai_greeting', 'get_date_info', 'ai_greeting']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Verstanden. Willst Du den nächsten Call starten?

**Bot:** Sehr gerne helfe ich Ihnen weiter! Für welches Datum und wie viele Personen möchten Sie denn einen Tisch reservieren?

---

### Turn 7

```
stt_latency_ms:    3
llm_latency_ms:    1050 ✅
tts_latency_ms:    0
total_latency_ms:  1053 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 1049 / 6 / 596
tts_situation:     info_neutral
tts_mood:          neutral
tts_rate_pct:      200
node_name:         greeting
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['ai_greeting', 'get_date_info', 'ai_greeting']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Verstanden. Willst Du den nächsten Call starten?

**Bot:** Sehr gerne helfe ich Ihnen weiter! Für welches Datum und wie viele Personen möchten Sie denn einen Tisch reservieren?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-------|-------|
| 1 | 1208 | 1202 | 5 | None | — | 200 | greeting_first | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 2 | 1142 | 1137 | 5 | None | — | 200 | info_neutral | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 3 | 1108 | 1103 | 5 | None | — | 200 | info_neutral | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 4 | 1020 | 1016 | 3 | None | — | 200 | info_neutral | neutral | check_availability |  |
| 5 | 7060 | 7056 | 4 | None | — | 200 | info_neutral | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 6 | 1159 | 1152 | 7 | None | — | 200 | info_neutral | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 7 | 1053 | 1050 | 3 | None | — | 200 | info_neutral | neutral | ai_greeting,get_date_info,ai_greeting |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?
- **user** (turn 1): fine.
- **user** (turn 2): Begrüßung okay
- **user** (turn 3): Turn zwei, ich habe beide intens.
- **user** (turn 4): Reservierung gestellt.
- **user** (turn 5): Achtung, Sally. Eins noch, bitte hinzu --
- **bot** (turn 6): Verstanden, ich habe das notiert.
- **user** (turn 7): Turns good.
- **user** (turn 8): Verstanden. Willst Du den nächsten Call starten?
- **user** (turn 9): Verstanden. Willst Du den nächsten Call starten?

---

## 7. Tool calls (`google_tool_calls`)

- `check_availability` @ turn 0 — success=None — {'status': 'wait_time_info', 'estimated_wait_minutes': 25, 'message': 'Aktuelle geschätzte Wartezeit: ca. 25 Minuten.', 'note': 'Für genaue Verfügbarkeit bitte Datum und Uhrzeit angeben.'}

---

## 8. Session blob excerpt (`google_calls.session_data`)

```json
{
  "state": {
    "adk_brain": {
      "state": {
        "call_sid": "",
        "call_ended": false,
        "first_name": null,
        "party_size": null,
        "cached_menu": null,
        "menu_fetched": false,
        "order_intent": false,
        "phone_number": null,
        "shared_slots": {},
        "abuse_strikes": 0,
        "customer_name": null,
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": null,
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Ah, verstanden — Sie möchten eine Reservierung vornehmen! Für welches Datum hätten Sie denn gerne einen Tisch?"
        ],
        "reservation_date": null,
        "reservation_time": null,
        "delivery_intended": false,
        "ai_greeting_called": false,
        "current_intent_idx": null,
        "customer_confirmed": true,
        "get_weather_called": false,
        "reservation_intent": true,
        "validation_entries": {},
        "cached_menu_at_turn": null,
        "caller_id_confirmed": false,
        "caller_said_goodbye": false,
        "reservation_created": false,
        "bulk_order_confirmed": false,
        "cached_menu_metadata": {},
        "escalation_requested": false,
        "get_date_info_called": true,
        "verify_address_called": false,
        "verify_address_failed": false,
        "multi_intent_completed": false,
        "failed_intent_summaries": [],
        "request_callback_called": false,
        "transfer_to_tier2_called": false,
        "check_availability_called": true,
        "pending_bulk_confirmation": false,
        "delivery_address_mentioned": false,
        "last_caller_confirmation_turn": null
      },
      "memory": {
        "recent_turns": [
          {
            "bot": "Wie kann ich Ihnen heute helfen – möchten Sie bestellen oder haben Sie Fragen zu unserem koreanischen Angebot? Gerne unterstütze ich Sie!",
            "node": "greeting",
            "customer": "Turn zwei, ich habe beide intens."
          },
          {
            "bot": "[TOOL:check_availability] Ah, verstanden — Sie möchten eine Reservierung vornehmen! Für welches Datum hätten Sie denn gerne einen Tisch?",
            "node": "reservation",
            "customer": "Reservierung gestellt."
          },
          {
            "bot": "Sehr gerne helfe ich Ihnen weiter! Für welches Datum und wie viele Personen möchten Sie denn einen Tisch reservieren?",
            "node": "greeting",
            "customer": "Turns good."
          },
          {
            "bot": "Sehr gerne helfe ich Ihnen weiter! Für welches Datum und wie viele Personen möchten Sie denn einen Tisch reservieren?",
            "node": "greeting",
            "customer": "Verstanden. Willst Du den nächsten Call starten?"
          },
          {
            "bot": "Sehr gerne helfe ich Ihnen weiter! Für welches Datum und wie viele Personen möchten Sie denn einen Tisch reservieren?",
            "node": "greeting",
            "customer": "Verstanden. Willst Du den nächsten Call starten?"
          }
        ],
        "context_summary": " [greeting] Kunde: 'fine....' [greeting] Kunde: 'Begrüßung okay...'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "reservation",
        "turns_in_node": 0
      },
      "turn_idx": 7,
      "all_tools": [
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "check_availability",
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "ai_greeting",
        "get_date_info",
        "ai_greeting"
      ],
      "order_slots": {
        "name": {
          "value": null,
          "status": "missing",
          "confidence": "low",
          "source_turn": null,
          "raw_mentions": []
        },
        "items": {
          "value": null,
          "status": "missing",
          "confidence": "low",
          "source_turn": null,
          "raw_mentions": []
        },
        "phone": {
          "value": null,
          "status": "missing",
          "confidence": "low",
          "source_turn": null,
          "raw_mentions": []
        },
        "intent": null,
        "party_size": {
          "value": null,
          "status": "missing",
          "confidence": "low",
          "source_turn": null,
          "raw_mentions": []
        },
        "address_city": {
          "value": null,
          "status": "missing",
          "confidence": "low",
          "source_turn": null,
          "raw_mentions": []
        },
        "delivery_type": {
          "value": null,
          "status": "missing",
          "confidence": "low",
          "source_turn": null,
          "raw_mentions": []
        },
        "address_number": {
          "value": null,
          "status": "missing",
          "confidence": "low",
          "source_turn": null,
          "raw_mentions": []
        },
        "address_street": {
          "value": null,
          "status": "missing",
          "confidence": "low",
          "source_turn": null,
          "raw_mentions": []
        },
        "reservation_date": {
          "value": null,
          "status": "missing",
          "confidence": "low",
          "source_turn": null,
          "raw_mentions": []
        },
        "reservation_time": {
          "value": null,
          "status": "missing",
          "confidence": "low",
          "source_turn": null,
          "raw_mentions": []
        }
      },
      "recent_responses": [
        "Ah, verstanden — Sie möchten eine Reservierung vornehmen! Für welches Datum hätten Sie denn gerne einen Tisch?"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-61cda1e41db5",
  "ended_at": "2026-04-30T20:45:12.542395+02:00",
  "started_at": "2026-04-30T20:44:44.229127+02:00",
  "started_ts": 1777574684.2291598,
  "tool_calls": [
    {
      "args": {
        "date": "",
        "time": "",
        "party_size": 2
      },
      "tool": "check_availability",
      "timestamp": "2026-04-30T20:44:54.407396+02:00",
      "duration_ms": 0,
      "result_summary": "{'status': 'wait_time_info', 'estimated_wait_minutes': 25, 'message': 'Aktuelle geschätzte Wartezeit: ca. 25 Minuten.', 'note': 'Für genaue Verfügbarkeit bitte Datum und Uhrzeit angeben.'}"
    }
  ],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "assistant",
      "text": "Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?",
      "timestamp": "2026-04-30T20:44:44.233851+02:00"
    },
    {
      "role": "user",
      "text": "fine.",
      "timestamp": "2026-04-30T20:44:46.184303+02:00"
    },
    {
      "role": "user",
      "text": "Begrüßung okay",
      "timestamp": "2026-04-30T20:44:47.403844+02:00"
    },
    {
      "role": "user",
      "text": "Turn zwei, ich habe beide intens.",
      "timestamp": "2026-04-30T20:44:50.915854+02:00"
    },
    {
      "role": "user",
      "text": "Reservierung gestellt.",
      "timestamp": "2026-04-30T20:44:53.339346+02:00"
    },
    {
      "role": "user",
      "text": "Achtung, Sally. Eins noch, bitte hinzu --",
      "timestamp": "2026-04-30T20:44:56.987880+02:00"
    },
    {
      "role": "bot",
      "text": "Verstanden, ich habe das notiert.",
      "timestamp": "2026-04-30T20:44:56.991274+02:00"
    },
    {
      "role": "user",
      "text": "Turns good.",
      "timestamp": "2026-04-30T20:45:00.204532+02:00"
    },
    {
      "role": "user",
      "text": "Verstanden. Willst Du den nächsten Call starten?",
    
```

---

## 8.5 Intent Session (shadow — `google_context_documents`)

```python
# Phase 3 shadow data — intent classification running alongside legacy pipeline.
# MIGRATED_PROFILES is currently empty; these are observations only, not driving responses.
Turn 1: intent=greeting turn_type=start_intent locked=False (conf=0.00) profile=greeting reroute=False
Turn 2: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 3: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 4: intent=reservation turn_type=start_intent locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 5: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 6: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 7: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
