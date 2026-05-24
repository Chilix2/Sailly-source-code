# Sailly — Full Call Analysis Report
## Call ID: `demo-8cf1870adbd5`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-8cf1870adbd5` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-04-28 22:15:52 UTC |
| **Ended** | 2026-04-28 22:16:47 UTC |
| **Duration** | **55 seconds (0:55 min)** |
| **Total DB turns** | 2 |
| **Outcome / reason** | `farewell_text` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1077 ms |
| **p95 latency (stored)** | 1404 ms |
| **Max latency (stored)** | 1440 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 78.8716 ¢ |

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
| Latency p50 / p95 / max (total) | 713 / 1440 / 1440 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1437 / 1437 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
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
stt_latency_ms:    3
llm_latency_ms:    1437 ✅
tts_latency_ms:    0
total_latency_ms:  1440 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1339 / None / 95 / None
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
tools_called:      ['get_nearby_parking', 'get_date_info', 'ai_greeting', 'check_availability']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Hallo, Sally. Gibt's bei euch Parkplätze?

**Bot:** Gerne — wir haben direkt vor dem Restaurant Parkplätze, und in der Umgebung gibt's auch noch weitere Möglichkeiten in der Friedrich-Ebert-Allee.

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    710 ✅
tts_latency_ms:    0
total_latency_ms:  713 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1011 / None / 271 / None
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

**User:** Ja, danke. Das war's. Cheese.

**Bot:** Sehr gerne — bis bald bei uns!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1440 | 1437 | 3 | None | — | 200 | greeting_first | neutral | None | get_nearby_parking,get_date_info,ai_greeting,check_availability |  |
| 2 | 713 | 710 | 3 | None | — | 200 | info_neutral | neutral | None | end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?
- **user** (turn 1): Hallo, Sally. Gibt's bei euch Parkplätze?
- **user** (turn 2): Ja, danke. Das war's. Cheese.

---

## 7. Tool calls (`google_tool_calls`)

- `get_date_info` @ turn 0 — success=None — {'success': True, 'date': '2026-04-29', 'weekday': 'Mittwoch', 'relative': 'heute', 'message': '29.04.2026 ist ein Mittwoch (heute).'}

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
          "[TOOL:get_nearby_parking] [TOOL:get_date_info] [TOOL:ai_greeting] [TOOL:check_availability]\n\nGerne — wir haben direkt vor dem Restaurant Parkplätze, und in der Umgebung gibt's auch noch weitere Möglichkeiten in der Friedrich-Ebert-Allee.",
          "Sehr gerne — bis bald bei uns!"
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
            "bot": "[TOOL:get_nearby_parking] [TOOL:get_date_info] [TOOL:ai_greeting] [TOOL:check_availability]\n\nGerne — wir haben direkt vor dem Restaurant Parkplätze, und in der Umgebung gibt's auch noch weitere Möglichkeiten in der Friedrich-Ebert-Allee.",
            "node": "greeting",
            "customer": "Hallo, Sally. Gibt's bei euch Parkplätze?"
          },
          {
            "bot": "Sehr gerne — bis bald bei uns!",
            "node": "greeting",
            "customer": "Ja, danke. Das war's. Cheese."
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
      "turn_idx": 2,
      "all_tools": [
        "get_nearby_parking",
        "get_date_info",
        "ai_greeting",
        "check_availability",
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
        "[TOOL:get_nearby_parking] [TOOL:get_date_info] [TOOL:ai_greeting] [TOOL:check_availability]\n\nGerne — wir haben direkt vor dem Restaurant Parkplätze, und in der Umgebung gibt's auch noch weitere Möglichkeiten in der Friedrich-Ebert-Allee.",
        "Sehr gerne — bis bald bei uns!"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-8cf1870adbd5",
  "ended_at": "2026-04-29T00:16:47.849429+02:00",
  "started_at": "2026-04-29T00:15:52.516554+02:00",
  "started_ts": 1777414552.516588,
  "tool_calls": [
    {
      "args": {
        "date": "heute"
      },
      "tool": "get_date_info",
      "timestamp": "2026-04-29T00:16:15.361425+02:00",
      "duration_ms": 0,
      "result_summary": "{'success': True, 'date': '2026-04-29', 'weekday': 'Mittwoch', 'relative': 'heute', 'message': '29.04.2026 ist ein Mittwoch (heute).'}"
    }
  ],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "assistant",
      "text": "Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?",
      "timestamp": "2026-04-29T00:15:52.521954+02:00"
    },
    {
      "role": "user",
      "text": "Hallo, Sally. Gibt's bei euch Parkplätze?",
      "timestamp": "2026-04-29T00:16:14.006704+02:00"
    },
    {
      "role": "user",
      "text": "Ja, danke. Das war's. Cheese.",
      "timestamp": "2026-04-29T00:16:37.643743+02:00"
    }
  ],
  "duration_secs": 55.3,
  "emergency_events": [],
  "emergency_detected": false,
  "recording_consent_at": "2026-04-29T00:15:52.516554+02:00",
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
