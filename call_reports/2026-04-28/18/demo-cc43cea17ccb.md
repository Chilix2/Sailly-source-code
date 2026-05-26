# Sailly — Full Call Analysis Report
## Call ID: `demo-cc43cea17ccb`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-cc43cea17ccb` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-04-28 18:47:20 UTC |
| **Ended** | 2026-04-28 18:48:30 UTC |
| **Duration** | **70 seconds (1:10 min)** |
| **Total DB turns** | 3 |
| **Outcome / reason** | `farewell_text` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1285 ms |
| **p95 latency (stored)** | 2168 ms |
| **Max latency (stored)** | 2311 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 100.7801 ¢ |

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
| Latency p50 / p95 / max (total) | 885 / 2311 / 2311 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 881 / 2306 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | None / None ms (0 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    2306 ✅
tts_latency_ms:    0
total_latency_ms:  2311 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 2056 / None / 248 / None
tts_situation:     greeting_first
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_nearby_parking', 'get_date_info', 'check_availability', 'ai_greeting']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Hallo Sally. Gibt's bei euch Parkplätze?

**Bot:** Gute Frage — wir haben leider keine eigenen Parkplätze direkt beim Restaurant, aber in der Friedrich-Ebert-Allee und den Nebenstraßen drumherum finden Sie normalerweise welche, und die Bushaltestelle ist auch gleich um die Ecke.

---

### Turn 2

```
stt_latency_ms:    4
llm_latency_ms:    881 ✅
tts_latency_ms:    0
total_latency_ms:  885 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1012 / None / 117 / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      []
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Ja, danke.

**Bot:** Gerne — womit kann ich Ihnen sonst noch helfen, oder möchten Sie schon bestellen?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    655 ✅
tts_latency_ms:    0
total_latency_ms:  659 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1011 / None / 345 / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['end_call']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Das war's schon. Tschüs.

**Bot:** Alles Gute für Sie — bis bald beim DOBOO!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 2311 | 2306 | 4 | None | — | 200 | greeting_first | neutral | None | get_nearby_parking,get_date_info,check_availability,ai_greeting |  |
| 2 | 885 | 881 | 4 | None | — | 200 | info_neutral | neutral | None | — |  |
| 3 | 659 | 655 | 3 | None | — | 200 | info_neutral | neutral | None | end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?
- **user** (turn 1): Hallo Sally. Gibt's bei euch Parkplätze?
- **user** (turn 2): Ja, danke.
- **user** (turn 3): Das war's schon. Tschüs.

---

## 7. Tool calls (`google_tool_calls`)

- `get_date_info` @ turn 0 — success=None — {'success': True, 'date': '2026-04-28', 'weekday': 'Dienstag', 'relative': 'heute', 'message': '28.04.2026 ist ein Dienstag (heute).'}

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
          "[TOOL:get_nearby_parking] [TOOL:get_date_info] [TOOL:check_availability] [TOOL:ai_greeting]\n\nGute Frage — wir haben leider keine eigenen Parkplätze direkt beim Restaurant, aber in der Friedrich-Ebert-Allee und den Nebenstraßen drumherum finden Sie normalerweise welche, und die Bushaltestelle ist auch gleich um die Ecke.",
          "Gerne — womit kann ich Ihnen sonst noch helfen, oder möchten Sie schon bestellen?",
          "Alles Gute für Sie — bis bald beim DOBOO!"
        ],
        "reservation_date": null,
        "reservation_time": null,
        "delivery_intended": false,
        "ai_greeting_called": true,
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
            "bot": "[TOOL:get_nearby_parking] [TOOL:get_date_info] [TOOL:check_availability] [TOOL:ai_greeting]\n\nGute Frage — wir haben leider keine eigenen Parkplätze direkt beim Restaurant, aber in der Friedrich-Ebert-Allee und den Nebenstraßen drumherum finden Sie normalerweise welche, und die Bushaltestelle ist auch gleich um die Ecke.",
            "node": "greeting",
            "customer": "Hallo Sally. Gibt's bei euch Parkplätze?"
          },
          {
            "bot": "Gerne — womit kann ich Ihnen sonst noch helfen, oder möchten Sie schon bestellen?",
            "node": "greeting",
            "customer": "Ja, danke."
          },
          {
            "bot": "Alles Gute für Sie — bis bald beim DOBOO!",
            "node": "greeting",
            "customer": "Das war's schon. Tschüs."
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
      "turn_idx": 3,
      "all_tools": [
        "get_nearby_parking",
        "get_date_info",
        "check_availability",
        "ai_greeting",
        "end_call"
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
        "[TOOL:get_nearby_parking] [TOOL:get_date_info] [TOOL:check_availability] [TOOL:ai_greeting]\n\nGute Frage — wir haben leider keine eigenen Parkplätze direkt beim Restaurant, aber in der Friedrich-Ebert-Allee und den Nebenstraßen drumherum finden Sie normalerweise welche, und die Bushaltestelle ist auch gleich um die Ecke.",
        "Gerne — womit kann ich Ihnen sonst noch helfen, oder möchten Sie schon bestellen?",
        "Alles Gute für Sie — bis bald beim DOBOO!"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-cc43cea17ccb",
  "ended_at": "2026-04-28T20:48:30.635605+02:00",
  "started_at": "2026-04-28T20:47:20.580408+02:00",
  "started_ts": 1777402040.5804439,
  "tool_calls": [
    {
      "args": {
        "date": "heute"
      },
      "tool": "get_date_info",
      "timestamp": "2026-04-28T20:47:47.830163+02:00",
      "duration_ms": 0,
      "result_summary": "{'success': True, 'date': '2026-04-28', 'weekday': 'Dienstag', 'relative': 'heute', 'message': '28.04.2026 ist ein Dienstag (heute).'}"
    }
  ],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "assistant",
      "text": "Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?",
      "timestamp": "2026-04-28T20:47:20.585257+02:00"
    },
    {
      "role": "user",
      "text": "Hallo Sally. Gibt's bei euch Parkplätze?",
      "timestamp": "2026-04-28T20:47:45.757460+02:00"
    },
    {
      "role": "user",
      "text": "Ja, danke.",
      "timestamp": "2026-04-28T20:48:17.128175+02:00"
    },
    {
      "role": "user",
      "text": "Das war's schon. Tschüs.",
      "timestamp": "2026-04-28T20:48:19.901972+02:00"
    }
  ],
  "duration_secs": 70.1,
  "emergency_events": [],
  "emergency_detected": false,
  "recording_consent_at": "2026-04-28T20:47:20.580408+02:00",
  "insurance_data_collected": false
}
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
# (no context documents for this call — predates v4 migration)
```

_(no context documents for this call — predates v4 migration)_

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
