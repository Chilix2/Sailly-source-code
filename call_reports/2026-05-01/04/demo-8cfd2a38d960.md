# Sailly — Full Call Analysis Report
## Call ID: `demo-8cfd2a38d960`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-8cfd2a38d960` |
| **Caller / channel** | `[validation:A1_greeting_wuetend]` |
| **Started** | 2026-05-01 04:47:16 UTC |
| **Ended** | 2026-05-01 04:48:14 UTC |
| **Duration** | **57 seconds (0:57 min)** |
| **Total DB turns** | 6 |
| **Outcome / reason** | `client_hangup` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1577 ms |
| **p95 latency (stored)** | 2356 ms |
| **Max latency (stored)** | 2456 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 82.8985 ¢ |

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
| Latency p50 / p95 / max (total) | 1372 / 2456 / 2456 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1467 / 1797 ms | From `llm_latency_ms` column |
| STT p50 | 13 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1467 / 1798 ms (6 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    259
llm_latency_ms:    1797 ✅
tts_latency_ms:    1798
total_latency_ms:  2057 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     greeting_first
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

**User:** Guten Tag, ich wollte nur kurz schauen, ob ihr aufhabt.

**Bot:** Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?

---

### Turn 2

```
stt_latency_ms:    878
llm_latency_ms:    1577 ✅
tts_latency_ms:    1578
total_latency_ms:  2456 ✅
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

**User:** Ich bin gespannt, ob jemand rangeht.

**Bot:** Ja, sehr gerne – wir haben heute Freitag für Sie geöffnet! Darf ich Ihnen unsere genauen Öffnungszeiten durchgeben?

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    1467 ✅
tts_latency_ms:    1467
total_latency_ms:  1471 ✅
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

**User:** Guten Tag, schönen Dank.

**Bot:** Sehr gerne – wir haben heute Freitag von 11:30 bis 22:00 Uhr für Sie geöffnet. Kann ich Ihnen noch bei etwas anderem helfen?

---

### Turn 4

```
stt_latency_ms:    13
llm_latency_ms:    1007 ✅
tts_latency_ms:    1007
total_latency_ms:  1020 ✅
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

**User:** Danke, ich warte.

**Bot:** Gerne – wie kann ich Ihnen heute weiterhelfen?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    1367 ✅
tts_latency_ms:    1368
total_latency_ms:  1372 ✅
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

**User:** Alles klar, ich bleibe dran.

**Bot:** Sehr gerne – ich bin Sailly von DOBOO Korean Soulfood in Bonn. Was kann ich für Sie heute tun?

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1084 ✅
tts_latency_ms:    1084
total_latency_ms:  1087 ✅
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

**User:** Ich habe Zeit.

**Bot:** Gerne helfe ich Ihnen weiter – möchten Sie eine Bestellung aufgeben oder haben Sie eine Frage zu DOBOO Korean Soulfood?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 2057 | 1797 | 259 | None | — | 200 | greeting_first | neutral | None | ai_greeting,get_date_info |  |
| 2 | 2456 | 1577 | 878 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1471 | 1467 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1020 | 1007 | 13 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1372 | 1367 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1087 | 1084 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Guten Tag, ich wollte nur kurz schauen, ob ihr aufhabt.
- **assistant** (turn 1): Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?
- **user** (turn 2): Ich bin gespannt, ob jemand rangeht.
- **user** (turn 3): Guten Tag, schönen Dank.
- **user** (turn 4): Danke, ich warte.
- **user** (turn 5): Alles klar, ich bleibe dran.
- **user** (turn 6): Ich habe Zeit.
- **assistant** (turn 7): Gerne helfe ich Ihnen weiter – möchten Sie eine Bestellung aufgeben oder haben Sie eine Frage zu DOBOO Korean Soulfood?

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
        "phone_number": null,
        "shared_slots": {},
        "abuse_strikes": 0,
        "customer_name": "Guten Tag",
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": null,
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
          "Ja, sehr gerne – wir haben heute Freitag für Sie geöffnet! Darf ich Ihnen unsere genauen Öffnungszeiten durchgeben?",
          "Sehr gerne – wir haben heute Freitag von 11:30 bis 22:00 Uhr für Sie geöffnet. Kann ich Ihnen noch bei etwas anderem helfen?",
          "Gerne – wie kann ich Ihnen heute weiterhelfen?",
          "Sehr gerne – ich bin Sailly von DOBOO Korean Soulfood in Bonn. Was kann ich für Sie heute tun?"
        ],
        "reservation_date": null,
        "reservation_time": null,
        "delivery_intended": false,
        "ai_greeting_called": false,
        "current_intent_idx": null,
        "customer_confirmed": false,
        "get_weather_called": false,
        "reservation_intent": false,
        "validation_entries": {},
        "cached_menu_at_turn": null,
        "caller_id_confirmed": false,
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
            "customer": "Guten Tag, ich wollte nur kurz schauen, ob ihr aufhabt."
          },
          {
            "bot": "Ja, sehr gerne – wir haben heute Freitag für Sie geöffnet! Darf ich Ihnen unsere genauen Öffnungszeiten durchgeben?",
            "node": "greeting",
            "customer": "Ich bin gespannt, ob jemand rangeht."
          },
          {
            "bot": "Sehr gerne – wir haben heute Freitag von 11:30 bis 22:00 Uhr für Sie geöffnet. Kann ich Ihnen noch bei etwas anderem helfen?",
            "node": "greeting",
            "customer": "Guten Tag, schönen Dank."
          },
          {
            "bot": "Gerne – wie kann ich Ihnen heute weiterhelfen?",
            "node": "greeting",
            "customer": "Danke, ich warte."
          },
          {
            "bot": "Sehr gerne – ich bin Sailly von DOBOO Korean Soulfood in Bonn. Was kann ich für Sie heute tun?",
            "node": "greeting",
            "customer": "Alles klar, ich bleibe dran."
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
        "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
        "Ja, sehr gerne – wir haben heute Freitag für Sie geöffnet! Darf ich Ihnen unsere genauen Öffnungszeiten durchgeben?",
        "Sehr gerne – wir haben heute Freitag von 11:30 bis 22:00 Uhr für Sie geöffnet. Kann ich Ihnen noch bei etwas anderem helfen?",
        "Gerne – wie kann ich Ihnen heute weiterhelfen?",
        "Sehr gerne – ich bin Sailly von DOBOO Korean Soulfood in Bonn. Was kann ich für Sie heute tun?"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-8cfd2a38d960",
  "ended_at": "2026-05-01T06:48:14.484711+02:00",
  "started_at": "2026-05-01T06:47:16.780656+02:00",
  "started_ts": 1777610836.780667,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Guten Tag, ich wollte nur kurz schauen, ob ihr aufhabt.",
      "timestamp": "2026-05-01T06:47:20.265430+02:00"
    },
    {
      "role": "assistant",
      "text": "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
      "timestamp": "2026-05-01T06:47:22.339962+02:00"
    },
    {
      "role": "user",
      "text": "Ich bin gespannt, ob jemand rangeht.",
      "timestamp": "2026-05-01T06:47:22.447870+02:00"
    },
    {
      "role": "user",
      "text": "Guten Tag, schönen Dank.",
      "timestamp": "2026-05-01T06:47:31.406367+02:00"
    },
    {
      "role": "user",
      "text": "Danke, ich warte.",
      "timestamp": "2026-05-01T06:47:40.069074+02:00"
    },
    {
      "role": "user",
      "text": "Alles klar, ich bleibe dran.",
      "timestamp": "2026-05-01T06:47:48.131705+02:00"
    },
    {
      "role": "user",
      "text": "Ich habe Zeit.",
      "timestamp": "2026-05-01T06:47:51.506931+02:00"
    },
    {
      "role": "assistant",
      "text": "Gerne helfe ich Ihnen weiter – möchten Sie eine Bestellung aufgeben oder haben Sie eine Frage zu DOBOO Korean Soulfood?",
      "timestamp": "2026-05-01T06:47:52.599378+02:00"
    }
  ],
  "duration_secs": 57.7,
  "emergency_events": [],
  "
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=False (conf=0.00) profile=greeting reroute=False
Turn 2: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 3: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 4: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 5: intent=unknown turn_type=confirm locked=True (conf=0.95) profile=greeting reroute=False
Turn 6: intent=unknown turn_type=unclear locked=True (conf=0.95) profile=greeting reroute=False
Turn 7: intent=unknown turn_type=confirm locked=True (conf=0.95) profile=greeting reroute=False
Turn 8: intent=unknown turn_type=unclear locked=True (conf=0.95) profile=greeting reroute=False
Turn 9: intent=unknown turn_type=unclear locked=True (conf=0.95) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
