# Sailly — Full Call Analysis Report
## Call ID: `demo-bfe50eaddd5b`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-bfe50eaddd5b` |
| **Caller / channel** | `[validation:A2_tool_tag_aeltere_person]` |
| **Started** | 2026-05-01 07:17:39 UTC |
| **Ended** | 2026-05-01 07:18:49 UTC |
| **Duration** | **70 seconds (1:10 min)** |
| **Total DB turns** | 4 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1234 ms |
| **p95 latency (stored)** | 1384 ms |
| **Max latency (stored)** | 1401 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 101.2703 ¢ |

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
| Latency p50 / p95 / max (total) | 1286 / 1401 / 1401 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1283 / 1397 ms | From `llm_latency_ms` column |
| STT p50 | 7 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1284 / 1397 ms (4 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1283 ✅
tts_latency_ms:    1284
total_latency_ms:  1286 ✅
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

**User:** Hallo, guten Tag.

**Bot:** Guten Tag! Womit kann ich Sie heute helfen – möchten Sie eine Reservation machen oder haben Sie eine Frage zu unserem Restaurant?

---

### Turn 2

```
stt_latency_ms:    32
llm_latency_ms:    959 ✅
tts_latency_ms:    959
total_latency_ms:  991 ✅
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

**User:** Ja, ich hab eine Frage. Wo befindet sich Ihr Restaurant genau?

**Bot:** Guten Tag! Womit kann ich Sie heute helfen – möchten Sie eine Reservation machen oder haben Sie eine Frage zu unserem Restaurant?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1397 ✅
tts_latency_ms:    1397
total_latency_ms:  1401 ✅
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

**User:** Ich finde die Adresse nicht so leicht.

**Bot:** Wir befinden uns in Bonn – gerne gebe ich Ihnen unsere genaue Adresse durch, damit Sie uns leicht finden. Darf ich Ihnen noch weitere Informationen geben?

---

### Turn 4

```
stt_latency_ms:    7
llm_latency_ms:    1250 ✅
tts_latency_ms:    1251
total_latency_ms:  1257 ✅
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

**User:** Moment, ich versteh nicht ganz. Ich möchte nur wissen, wo Ihr Restaurant genau ist. Können Sie mir bitte die genaue Adresse sagen?

**Bot:** DOBOO Korean Soulfood finden Sie in Bonn unter: [Adresse eingeben]. Kann ich Ihnen noch bei etwas anderem behilflich sein?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1286 | 1283 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 991 | 959 | 32 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1401 | 1397 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1257 | 1250 | 7 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo, guten Tag.
- **user** (turn 1): Moment, ich möchte wissen, wo Sie genau sind. Können Sie mir die Adresse sagen?
- **user** (turn 2): Ja, ich hab eine Frage. Wo befindet sich Ihr Restaurant genau?
- **user** (turn 3): Ich finde die Adresse nicht so leicht.
- **user** (turn 4): Moment, ich versteh nicht ganz. Ich möchte nur wissen, wo Ihr Restaurant genau ist. Können Sie mir bitte die genaue Adresse sagen?

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
          "Guten Tag! Womit kann ich Sie heute helfen – möchten Sie eine Reservation machen oder haben Sie eine Frage zu unserem Restaurant?",
          "Guten Tag! Womit kann ich Sie heute helfen – möchten Sie eine Reservation machen oder haben Sie eine Frage zu unserem Restaurant?",
          "Wir befinden uns in Bonn – gerne gebe ich Ihnen unsere genaue Adresse durch, damit Sie uns leicht finden. Darf ich Ihnen noch weitere Informationen geben?",
          "DOBOO Korean Soulfood finden Sie in Bonn unter: [Adresse eingeben]. Kann ich Ihnen noch bei etwas anderem behilflich sein?"
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
        "delivery_address_mentioned": true,
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
            "bot": "Guten Tag! Womit kann ich Sie heute helfen – möchten Sie eine Reservation machen oder haben Sie eine Frage zu unserem Restaurant?",
            "node": "greeting",
            "customer": "Hallo, guten Tag."
          },
          {
            "bot": "Guten Tag! Womit kann ich Sie heute helfen – möchten Sie eine Reservation machen oder haben Sie eine Frage zu unserem Restaurant?",
            "node": "greeting",
            "customer": "Ja, ich hab eine Frage. Wo befindet sich Ihr Restaurant genau?"
          },
          {
            "bot": "Wir befinden uns in Bonn – gerne gebe ich Ihnen unsere genaue Adresse durch, damit Sie uns leicht finden. Darf ich Ihnen noch weitere Informationen geben?",
            "node": "greeting",
            "customer": "Ich finde die Adresse nicht so leicht."
          },
          {
            "bot": "DOBOO Korean Soulfood finden Sie in Bonn unter: [Adresse eingeben]. Kann ich Ihnen noch bei etwas anderem behilflich sein?",
            "node": "greeting",
            "customer": "Moment, ich versteh nicht ganz. Ich möchte nur wissen, wo Ihr Restaurant genau ist. Können Sie mir bitte die genaue Adresse sagen?"
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
      "turn_idx": 5,
      "all_tools": [
        "ai_greeting",
        "get_date_info",
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
        "Guten Tag! Womit kann ich Sie heute helfen – möchten Sie eine Reservation machen oder haben Sie eine Frage zu unserem Restaurant?",
        "Guten Tag! Womit kann ich Sie heute helfen – möchten Sie eine Reservation machen oder haben Sie eine Frage zu unserem Restaurant?",
        "Wir befinden uns in Bonn – gerne gebe ich Ihnen unsere genaue Adresse durch, damit Sie uns leicht finden. Darf ich Ihnen noch weitere Informationen geben?",
        "DOBOO Korean Soulfood finden Sie in Bonn unter: [Adresse eingeben]. Kann ich Ihnen noch bei etwas anderem behilflich sein?"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-bfe50eaddd5b",
  "ended_at": "2026-05-01T09:18:49.994610+02:00",
  "started_at": "2026-05-01T09:17:39.082866+02:00",
  "started_ts": 1777619859.0828998,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Hallo, guten Tag.",
      "timestamp": "2026-05-01T09:17:47.717556+02:00"
    },
    {
      "role": "user",
      "text": "Moment, ich möchte wissen, wo Sie genau sind. Können Sie mir die Adresse sagen?",
      "timestamp": "2026-05-01T09:17:49.637858+02:00"
    },
    {
      "role": "user",
      "text": "Ja, ich hab eine Frage. Wo befindet sich Ihr Restaurant genau?",
      "timestamp": "2026-05-01T09:18:15.216049+02:00"
    },
    {
      "role": "user",
      "text": "Ich finde die Adresse nicht so leicht.",
      "timestamp": "2026-05-01T09:18:16.333420+02:00"
    },
    {
      "role": "user",
      "t
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 4: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
