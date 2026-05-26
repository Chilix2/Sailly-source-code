# Sailly — Full Call Analysis Report
## Call ID: `demo-b7b8c41ee1fc`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-b7b8c41ee1fc` |
| **Caller / channel** | `[validation:A2_tool_tag_neutral]` |
| **Started** | 2026-05-01 07:16:23 UTC |
| **Ended** | 2026-05-01 07:17:31 UTC |
| **Duration** | **67 seconds (1:07 min)** |
| **Total DB turns** | 3 |
| **Outcome / reason** | `client_hangup` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1157 ms |
| **p95 latency (stored)** | 1287 ms |
| **Max latency (stored)** | 1293 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 96.4198 ¢ |

### Pipeline configuration (runtime snapshot)

```
STT:  DeepgramFluxSTTService (flux-general-multi, EU endpoint, eot_threshold=0.6, eot_timeout_ms=3000 ms, mip_opt_out=True)
VAD:  None — Deepgram Flux semantic EOT (eot_threshold=0.6, eot_timeout_ms=3000)
LLM:  claude-haiku-4-5 (Vertex region env: us-east5)
Worker pipeline: IntentSessionManager (shadow) → WorkerRouter (15 profiles) → WorkerExecutor (Required≤280ms / Optional≤350ms / Background)
TTS:  SaillyGeminiTTSService — voice=Kore, engine=gemini-2.5-flash-tts
      GLOBAL_SPEED_MULTIPLIER=2.25 (env override possible)
Filler: pre-baked PCM 12-phrase pool, 400ms trigger (ENABLE_PRE_LLM_FILLER=true) | Backchannel: 6-phrase pool, 200-500ms hesitation window (ENABLE_BACKCHANNEL=true)
MULTI-INTENT / ADK: Enabled per brain configuration for browser demo
ValidationRegistry: async validation when configured
TTS Conditioning: Phase 2 — situation + mood → prosody_rate_pct → Gemini speaking_rate
Barge-in: enabled post-greeting when BargeInHandler is in pipeline
Monitoring thresholds (env): MONITOR_LATENCY_P95_MS=3000 ms, MONITOR_SUCCESS_THRESHOLD=80, Redis monitor=0
```

---

## 2. Aggregate health (from `google_turn_metrics`)

| Check | Value | Notes |
|-------|-------|-------|
| Latency p50 / p95 / max (total) | 1234 / 1293 / 1293 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1231 / 1290 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1231 / 1290 ms (3 turns) | From `tts_latency_ms` |
| **[Phase 2] Validation passes** | 0 turns | From `validation_passes` |
| **[Phase 1] Slot extractions** | 0 turns | From `slot_retention_status` |
| Call-level observability (stored on `google_calls`) | validation_registry_invocations=0, loop_incidents=0 | From `persist_call_aggregates` |

---

## 3. Caller-flag insights (`Achtung Sailly: …` / `Attention Sailly: …`)

_Test harness, caller-bot, or human reviewer: phrases like **Achtung Sailly:** (also **Attention Sailly:** / **Warnung Sailly:**) mark what Sailly did **wrong** — use this for qualitative issues that **latency and tool metrics may not show**._

_No matching caller markers in `google_transcripts` (non-assistant roles), `session_data.transcripts`, or `user_text` in turn metrics._
## 4. Per-turn breakdown (DB)

### Turn 1

```
stt_latency_ms:    4
llm_latency_ms:    940 ✅
tts_latency_ms:    941
total_latency_ms:  945 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         greeting
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['ai_greeting', 'get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Kein Problem. Ich versuche es einfach noch mal.

**Bot:** Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – worauf kann ich Sie heute hinweisen?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    1290 ✅
tts_latency_ms:    1290
total_latency_ms:  1293 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         greeting
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['ai_greeting', 'get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Wo befindet sich euer Restaurant genau?

**Bot:** Sehr gerne – ich bin ganz Ohr! Was kann ich für Sie tun?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1231 ✅
tts_latency_ms:    1231
total_latency_ms:  1234 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         greeting
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['ai_greeting', 'get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Wo befindet sich euer Restaurant genau? Vielen Dank.

**Bot:** Gerne helfe ich Ihnen weiter – unser Restaurant DOBOO Korean Soulfood befindet sich in Bonn. Könnten Sie mir sagen, ob Sie die genaue Adresse benötigen oder haben Sie noch weitere Fragen?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 945 | 940 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1293 | 1290 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1234 | 1231 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo, ich wollte fragen, wo sich euer Restaurant genau befindet. Vielen Dank.
- **user** (turn 1): Kein Problem. Ich versuche es einfach noch mal.
- **user** (turn 2): Wo befindet sich euer Restaurant genau?
- **user** (turn 3): Wo befindet sich euer Restaurant genau? Vielen Dank.

---

## 7. Tool calls (`google_tool_calls`)

_No tool call rows._

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
        "phone_number": "+4915900000002",
        "shared_slots": {},
        "abuse_strikes": 0,
        "customer_name": null,
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": "+4915900000002",
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
          "Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – worauf kann ich Sie heute hinweisen?",
          "Sehr gerne – ich bin ganz Ohr! Was kann ich für Sie tun?",
          "Gerne helfe ich Ihnen weiter – unser Restaurant DOBOO Korean Soulfood befindet sich in Bonn. Könnten Sie mir sagen, ob Sie die genaue Adresse benötigen oder haben Sie noch weitere Fragen?"
        ],
        "reservation_date": null,
        "reservation_time": null,
        "delivery_intended": false,
        "ai_greeting_called": false,
        "current_intent_idx": null,
        "customer_confirmed": true,
        "get_weather_called": false,
        "reservation_intent": false,
        "validation_entries": {},
        "cached_menu_at_turn": null,
        "caller_id_confirmed": true,
        "caller_said_goodbye": false,
        "reservation_created": false,
        "bulk_order_confirmed": false,
        "cached_menu_metadata": {},
        "escalation_requested": false,
        "get_date_info_called": false,
        "verify_address_called": false,
        "verify_address_failed": false,
        "multi_intent_completed": false,
        "failed_intent_summaries": [],
        "request_callback_called": false,
        "transfer_to_tier2_called": false,
        "check_availability_called": false,
        "pending_bulk_confirmation": false,
        "delivery_address_mentioned": false,
        "last_caller_confirmation_turn": null
      },
      "memory": {
        "recent_turns": [
          {
            "bot": "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
            "node": "greeting",
            "customer": "<call_start>"
          },
          {
            "bot": "Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – worauf kann ich Sie heute hinweisen?",
            "node": "greeting",
            "customer": "Kein Problem. Ich versuche es einfach noch mal."
          },
          {
            "bot": "Sehr gerne – ich bin ganz Ohr! Was kann ich für Sie tun?",
            "node": "greeting",
            "customer": "Wo befindet sich euer Restaurant genau?"
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter – unser Restaurant DOBOO Korean Soulfood befindet sich in Bonn. Könnten Sie mir sagen, ob Sie die genaue Adresse benötigen oder haben Sie noch weitere Fragen?",
            "node": "greeting",
            "customer": "Wo befindet sich euer Restaurant genau? Vielen Dank."
          }
        ],
        "context_summary": "",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 4,
      "all_tools": [
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "get_date_info"
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
          "value": "+4915900000002",
          "status": "partial",
          "confidence": "high",
          "source_turn": 0,
          "raw_mentions": [
            "caller_id:+4915900000002"
          ]
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
        "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
        "Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – worauf kann ich Sie heute hinweisen?",
        "Sehr gerne – ich bin ganz Ohr! Was kann ich für Sie tun?",
        "Gerne helfe ich Ihnen weiter – unser Restaurant DOBOO Korean Soulfood befindet sich in Bonn. Könnten Sie mir sagen, ob Sie die genaue Adresse benötigen oder haben Sie noch weitere Fragen?"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-b7b8c41ee1fc",
  "ended_at": "2026-05-01T09:17:31.301620+02:00",
  "started_at": "2026-05-01T09:16:23.838615+02:00",
  "started_ts": 1777619783.8386345,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Hallo, ich wollte fragen, wo sich euer Restaurant genau befindet. Vielen Dank.",
      "timestamp": "2026-05-01T09:16:31.342337+02:00"
    },
    {
      "role": "user",
      "text": "Kein Problem. Ich versuche es einfach noch mal.",
      "timestamp": "2026-05-01T09:16:36.531382+02:00"
    },
    {
      "role": "user",
      "text": "Wo befindet sich euer Restaurant genau?",
      "timestamp": "2026-05-01T09:16:37.741557+02:00"
    },
    {
      "role": "user",
      "text": "Wo befindet sich euer Restaurant genau? Vielen Dank.",
      "timestamp": "2026-05-01T09:16:50.952742+02:00"
    }
  ],
  "duration_secs": 67.5,
  "emergency_events": [],
  "emergency_detected": false,
  "recording_consent_at": "2026-05-01T09:16:23.838615+02:00",
  "insurance_data_collected": false
}
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 2: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 3: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
