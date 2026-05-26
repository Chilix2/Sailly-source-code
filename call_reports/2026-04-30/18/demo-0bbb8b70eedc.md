# Sailly — Full Call Analysis Report
## Call ID: `demo-0bbb8b70eedc`
_Generated: 2026-04-30 18:48 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-0bbb8b70eedc` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-04-30 18:45:34 UTC |
| **Ended** | 2026-04-30 18:47:36 UTC |
| **Duration** | **122 seconds (2:02 min)** |
| **Total DB turns** | 6 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1304 ms |
| **p95 latency (stored)** | 1671 ms |
| **Max latency (stored)** | 1736 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 175.9145 ¢ |

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
| Latency p50 / p95 / max (total) | 1187 / 1736 / 1736 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1359 / 1729 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
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
stt_latency_ms:    4
llm_latency_ms:    1182 ✅
tts_latency_ms:    0
total_latency_ms:  1187 ✅
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

**User:** Hallo, Sally. Wie ist das Wetter heute bei euch?

**Bot:** Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    968 ✅
tts_latency_ms:    0
total_latency_ms:  972 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 1076 / 6 / None
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
tools_called:      []
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** und hab dir heute Abend noch einen Tisch für zwei Personen um neunzehn Uhr

**Bot:** Ihre Reservierung für 2 Personen am 2026-04-30 um 19:00 Uhr ist bestätigt. Ich habe 2 Personen für heute um 19:00 Uhr auf den Namen Ihrem Namen reserviert. Stimmt das so?

---

### Turn 3

```
stt_latency_ms:    6
llm_latency_ms:    1729 ✅
tts_latency_ms:    0
total_latency_ms:  1736 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 1076 / 6 / None
tts_situation:     confirm_success
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

**User:** Willkommen bei Dob.

**Bot:** Perfekt, Ihre Reservierung für 2 Personen am Donnerstag, den 30. April um 19:00 Uhr ist bestätigt! Auf welchen Namen soll ich die Reservierung eintragen?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1471 ✅
tts_latency_ms:    0
total_latency_ms:  1475 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 1076 / 6 / 6240
tts_situation:     confirm_success
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

**User:** Was kann ich für dich tun?

**Bot:** Gerne helfe ich Ihnen bei der Reservierung! Auf welchen Namen soll ich diese für Sie eintragen?

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    1088 ✅
tts_latency_ms:    0
total_latency_ms:  1091 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 1076 / 6 / 6240
tts_situation:     confirm_success
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

**User:** Auf den Namen Thomas Meyer.

**Bot:** Gerne helfe ich Ihnen bei der Reservierung! Auf welchen Namen soll ich diese für Sie eintragen?

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1359 ✅
tts_latency_ms:    0
total_latency_ms:  1362 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 1076 / 6 / 6240
tts_situation:     confirm_success
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

**User:** Thomas Meyer

**Bot:** Vielen Dank, Herr Meyer! Für welchen Tag und welche Uhrzeit möchten Sie gerne einen Tisch bei uns reservieren?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-------|-------|
| 1 | 1187 | 1182 | 4 | None | — | 200 | greeting_first | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 2 | 972 | 968 | 3 | None | — | 200 | info_neutral | neutral | — |  |
| 3 | 1736 | 1729 | 6 | None | — | 200 | confirm_success | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 4 | 1475 | 1471 | 3 | None | — | 200 | confirm_success | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 5 | 1091 | 1088 | 3 | None | — | 200 | confirm_success | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 6 | 1362 | 1359 | 3 | None | — | 200 | confirm_success | neutral | ai_greeting,get_date_info,ai_greeting |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?
- **user** (turn 1): Hallo, Sally. Wie ist das Wetter heute bei euch?
- **user** (turn 2): und hab dir heute Abend noch einen Tisch für zwei Personen um neunzehn Uhr
- **user** (turn 3): Willkommen bei Dob.
- **user** (turn 4): Was kann ich für dich tun?
- **user** (turn 5): Auf den Namen Thomas Meyer.
- **user** (turn 6): Thomas Meyer
- **user** (turn 7): Achtung, Sally eins noch, bitte hinzufügen zum Transcript. Turn eins, Begrüßung okay. Turn zwei, Wetter plus Reservierung gefragt. Turn drei, Reservierung für falschen Tag gemacht. Dreißigster April ist morgen, nicht heute. Turn vier, Du hast mich zweimal nach dem Namen gefragt, obwohl ich ihn schon genannt hatte. Turn fünf, Du hast mir schon vielen Dank, Herr Meyer gesagt und fragst dann wieder nach Tag und Uhrzeit, die ich dir bereits genannt hatte. Das war's.

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
        "party_size": 2,
        "cached_menu": null,
        "menu_fetched": false,
        "order_intent": false,
        "phone_number": null,
        "shared_slots": {},
        "abuse_strikes": 0,
        "customer_name": "Thomas Meyer",
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "readback_pending",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": null,
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Ihre Reservierung für 2 Personen am 2026-04-30 um 19:00 Uhr ist bestätigt. Ich habe 2 Personen für heute um 19:00 Uhr auf den Namen Ihrem Namen reserviert. Stimmt das so?"
        ],
        "reservation_date": "2026-04-30",
        "reservation_time": "19:00",
        "delivery_intended": false,
        "ai_greeting_called": false,
        "current_intent_idx": null,
        "customer_confirmed": false,
        "get_weather_called": false,
        "reservation_intent": true,
        "validation_entries": {},
        "cached_menu_at_turn": null,
        "caller_id_confirmed": false,
        "caller_said_goodbye": false,
        "reservation_created": true,
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
            "bot": "Ihre Reservierung für 2 Personen am 2026-04-30 um 19:00 Uhr ist bestätigt. Sie erhalten eine Bestätigung per SMS. Ich habe 2 Personen für heute um 19:00 Uhr auf den Namen Ihrem Namen reserviert. Stimmt das so?",
            "node": "reservation",
            "customer": "und hab dir heute Abend noch einen Tisch für zwei Personen um neunzehn Uhr"
          },
          {
            "bot": "Perfekt, Ihre Reservierung für 2 Personen am Donnerstag, den 30. April um 19:00 Uhr ist bestätigt! Auf welchen Namen soll ich die Reservierung eintragen?",
            "node": "greeting",
            "customer": "Willkommen bei Dob."
          },
          {
            "bot": "Gerne helfe ich Ihnen bei der Reservierung! Auf welchen Namen soll ich diese für Sie eintragen?",
            "node": "greeting",
            "customer": "Was kann ich für dich tun?"
          },
          {
            "bot": "Gerne helfe ich Ihnen bei der Reservierung! Auf welchen Namen soll ich diese für Sie eintragen?",
            "node": "greeting",
            "customer": "Auf den Namen Thomas Meyer."
          },
          {
            "bot": "Vielen Dank, Herr Meyer! Für welchen Tag und welche Uhrzeit möchten Sie gerne einen Tisch bei uns reservieren?",
            "node": "greeting",
            "customer": "Thomas Meyer"
          }
        ],
        "context_summary": " [greeting] Kunde: 'Hallo, Sally. Wie ist das Wetter heute bei euch?...'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "reservation",
        "turns_in_node": 0
      },
      "turn_idx": 6,
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
        "Ihre Reservierung für 2 Personen am 2026-04-30 um 19:00 Uhr ist bestätigt. Ich habe 2 Personen für heute um 19:00 Uhr auf den Namen Ihrem Namen reserviert. Stimmt das so?"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-0bbb8b70eedc",
  "ended_at": "2026-04-30T20:47:36.685456+02:00",
  "started_at": "2026-04-30T20:45:34.616067+02:00",
  "started_ts": 1777574734.616109,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "assistant",
      "text": "Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?",
      "timestamp": "2026-04-30T20:45:34.621725+02:00"
    },
    {
      "role": "user",
      "text": "Hallo, Sally. Wie ist das Wetter heute bei euch?",
      "timestamp": "2026-04-30T20:45:52.967232+02:00"
    },
    {
      "role": "user",
      "text": "und hab dir heute Abend noch einen Tisch für zwei Personen um neunzehn Uhr",
      "timestamp": "2026-04-30T20:45:57.049836+02:00"
    },
    {
      "role": "user",
      "text": "Willkommen bei Dob.",
      "timestamp": "2026-04-30T20:46:01.964311+02:00"
    },
    {
      "role": "user",
      "text": "Was kann ich für dich tun?",
      "timestamp": "2026-04-30T20:46:04.312016+02:00"
    },
    {
      "role": "user",
      "text": "Auf den Namen Thomas Meyer.",
      "timestamp": "2026-04-30T20:46:31.442387+02:00"
    },
    {
      "role": "user",
      "text": "Thomas Meyer",
      "timestamp": "2026-04-30T20:46:45.814453+02:00"
    },
    {
      "role": "user",
      "text": "Achtung, Sally eins noch, bitte hinzufügen zum Transcript. Turn eins, Begrüßung okay. Turn zwei, Wetter plus Reservierung gefragt. Turn drei, Reservierung für falschen Tag gemacht. Dreißigster April ist morgen, nicht heute. Turn vier, Du hast mich zweimal nach dem Namen gefragt, obwohl ich ihn schon genannt hatte. Turn fünf, Du hast mir schon vielen Dank, Herr Meyer gesagt und fragst dann wieder nach Tag und Uhrzeit, die ich dir bereits genannt hatte. Das w
```

---

## 8.5 Intent Session (shadow — `google_context_documents`)

```python
# Phase 3 shadow data — intent classification running alongside legacy pipeline.
# MIGRATED_PROFILES is currently empty; these are observations only, not driving responses.
Turn 1: intent=greeting turn_type=start_intent locked=False (conf=0.00) profile=greeting reroute=False
Turn 2: intent=reservation turn_type=add_information locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 3: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 4: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 5: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 6: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
