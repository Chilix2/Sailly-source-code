# Sailly — Full Call Analysis Report
## Call ID: `demo-120a1ffc2e10`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-120a1ffc2e10` |
| **Caller / channel** | `[validation:A4_basic_order_aeltere_person]` |
| **Started** | 2026-05-01 04:59:38 UTC |
| **Ended** | 2026-05-01 05:00:40 UTC |
| **Duration** | **61 seconds (1:01 min)** |
| **Total DB turns** | 7 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1462 ms |
| **p95 latency (stored)** | 1924 ms |
| **Max latency (stored)** | 1992 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 89.2268 ¢ |

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
| Latency p50 / p95 / max (total) | 1491 / 1992 / 1992 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1482 / 1985 ms | From `llm_latency_ms` column |
| STT p50 | 6 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1483 / 1986 ms (7 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    6
llm_latency_ms:    1985 ✅
tts_latency_ms:    1986
total_latency_ms:  1992 ✅
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

**User:** Guten Tag, hier ist das Restaurant Dobu. Wie kann ich Ihnen helfen?

**Bot:** Guten Tag! Womit kann ich Sie bei DOBOO Korean Soulfood unterstützen?

---

### Turn 2

```
stt_latency_ms:    9
llm_latency_ms:    1064 ✅
tts_latency_ms:    1064
total_latency_ms:  1073 ✅
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

**User:** Kein Problem, ich höre.

**Bot:** Guten Tag! Ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn – womit kann ich Sie heute unterstützen?

---

### Turn 3

```
stt_latency_ms:    6
llm_latency_ms:    1066 ✅
tts_latency_ms:    1067
total_latency_ms:  1073 ✅
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

**User:** Was möchten Sie bestellen?

**Bot:** Gerne helfe ich Ihnen weiter – möchten Sie heute bei uns bestellen oder einen Tisch reservieren?

---

### Turn 4

```
stt_latency_ms:    4
llm_latency_ms:    1320 ✅
tts_latency_ms:    1320
total_latency_ms:  1324 ✅
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

**User:** Natürlich, lassen Sie sich Zeit. Ich bin hier, wenn Sie bereit sind.

**Bot:** Haben Sie Interesse an einer Bestellung zum Mitnehmen oder Liefern, oder möchten Sie einen Tisch für heute Freitag bei uns reservieren?

---

### Turn 5

```
stt_latency_ms:    19
llm_latency_ms:    1746 ✅
tts_latency_ms:    1746
total_latency_ms:  1765 ✅
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

**User:** Ja, zum Mitnehmen.

**Bot:** Gerne! Können Sie mir sagen, ob Sie heute lieber abholen oder liefern lassen möchten, oder interessiert Sie eher ein Tisch bei uns im Restaurant?

---

### Turn 6

```
stt_latency_ms:    8
llm_latency_ms:    1482 ✅
tts_latency_ms:    1483
total_latency_ms:  1491 ✅
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

**User:** bitte.

**Bot:** Perfekt, zum Mitnehmen verstanden! Möchten Sie die Speisen abholen oder sollen wir Sie mit Ihrer Bestellung beliefern?

---

### Turn 7

```
stt_latency_ms:    4
llm_latency_ms:    1510 ✅
tts_latency_ms:    1510
total_latency_ms:  1514 ✅
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

**User:** Ich möchte gerne zwei Portionen Bulgogi bestellen. Moment.

**Bot:** Gerne, ich helfe Ihnen weiter! Möchten Sie Ihre Bestellung abholen oder liefern wir sie zu Ihnen nach Hause?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1992 | 1985 | 6 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1073 | 1064 | 9 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1073 | 1066 | 6 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1324 | 1320 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1765 | 1746 | 19 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1491 | 1482 | 8 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1514 | 1510 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Guten Tag, hier ist das Restaurant Dobu. Wie kann ich Ihnen helfen?
- **user** (turn 1): Kein Problem, ich höre.
- **user** (turn 2): Was möchten Sie bestellen?
- **user** (turn 3): Natürlich, lassen Sie sich Zeit. Ich bin hier, wenn Sie bereit sind.
- **user** (turn 4): Ja, zum Mitnehmen.
- **user** (turn 5): bitte.
- **user** (turn 6): Ich möchte gerne zwei Portionen Bulgogi bestellen. Moment.

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
        "first_name": "Hier",
        "party_size": null,
        "cached_menu": null,
        "menu_fetched": false,
        "order_intent": true,
        "phone_number": null,
        "shared_slots": {},
        "abuse_strikes": 0,
        "customer_name": null,
        "order_created": false,
        "selected_dish": "Bulgogi",
        "end_call_stage": "idle",
        "order_quantity": 2,
        "schema_version": 5,
        "caller_id_phone": null,
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute behilflich sein?",
          "Guten Tag! Womit kann ich Sie bei DOBOO Korean Soulfood unterstützen?",
          "Guten Tag! Ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn – womit kann ich Sie heute unterstützen?",
          "Gerne helfe ich Ihnen weiter – möchten Sie heute bei uns bestellen oder einen Tisch reservieren?",
          "Haben Sie Interesse an einer Bestellung zum Mitnehmen oder Liefern, oder möchten Sie einen Tisch für heute Freitag bei uns reservieren?",
          "Gerne! Können Sie mir sagen, ob Sie heute lieber abholen oder liefern lassen möchten, oder interessiert Sie eher ein Tisch bei uns im Restaurant?",
          "Perfekt, zum Mitnehmen verstanden! Möchten Sie die Speisen abholen oder sollen wir Sie mit Ihrer Bestellung beliefern?",
          "Gerne, ich helfe Ihnen weiter! Möchten Sie Ihre Bestellung abholen oder liefern wir sie zu Ihnen nach Hause?"
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
            "bot": "Gerne helfe ich Ihnen weiter – möchten Sie heute bei uns bestellen oder einen Tisch reservieren?",
            "node": "greeting",
            "customer": "Was möchten Sie bestellen?"
          },
          {
            "bot": "Haben Sie Interesse an einer Bestellung zum Mitnehmen oder Liefern, oder möchten Sie einen Tisch für heute Freitag bei uns reservieren?",
            "node": "greeting",
            "customer": "Natürlich, lassen Sie sich Zeit. Ich bin hier, wenn Sie bereit sind."
          },
          {
            "bot": "Gerne! Können Sie mir sagen, ob Sie heute lieber abholen oder liefern lassen möchten, oder interessiert Sie eher ein Tisch bei uns im Restaurant?",
            "node": "greeting",
            "customer": "Ja, zum Mitnehmen."
          },
          {
            "bot": "Perfekt, zum Mitnehmen verstanden! Möchten Sie die Speisen abholen oder sollen wir Sie mit Ihrer Bestellung beliefern?",
            "node": "greeting",
            "customer": "bitte."
          },
          {
            "bot": "Gerne, ich helfe Ihnen weiter! Möchten Sie Ihre Bestellung abholen oder liefern wir sie zu Ihnen nach Hause?",
            "node": "greeting",
            "customer": "Ich möchte gerne zwei Portionen Bulgogi bestellen. Moment."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Guten Tag, hier ist das Restaurant Dobu. Wie kann ich Ihnen helfen?...' [greeting] Kunde: 'Kein Problem, ich höre....'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 8,
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
        "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute behilflich sein?",
        "Guten Tag! Womit kann ich Sie bei DOBOO Korean Soulfood unterstützen?",
        "Guten Tag! Ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn – womit kann ich Sie heute unterstützen?",
        "Gerne helfe ich Ihnen weiter – möchten Sie heute bei uns bestellen oder einen Tisch reservieren?",
        "Haben Sie Interesse an einer Bestellung zum Mitnehmen oder Liefern, oder möchten Sie einen Tisch für heute Freitag bei uns reservieren?",
        "Gerne! Können Sie mir sagen, ob Sie heute lieber abholen oder liefern lassen möchten, oder interessiert Sie eher ein Tisch bei uns im Restaurant?",
        "Perfekt, zum Mitnehmen verstanden! Möchten Sie die Speisen abholen oder sollen wir Sie mit Ihrer Bestellung beliefern?",
        "Gerne, ich helfe Ihnen weiter! Möchten Sie Ihre Bestellung abholen oder liefern wir sie zu Ihnen nach Hause?"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-120a1ffc2e10",
  "ended_at": "2026-05-01T07:00:40.099706+02:00",
  "started_at": "2026-05-01T06:59:38.177496+02:00",
  "started_ts": 1777
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 4: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 5: intent=greeting turn_type=confirm locked=True (conf=0.90) profile=greeting reroute=False
Turn 6: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 7: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
