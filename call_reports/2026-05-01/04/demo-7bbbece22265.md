# Sailly — Full Call Analysis Report
## Call ID: `demo-7bbbece22265`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-7bbbece22265` |
| **Caller / channel** | `[validation:A3_simple_reservation_aeltere_person]` |
| **Started** | 2026-05-01 04:47:16 UTC |
| **Ended** | 2026-05-01 04:48:08 UTC |
| **Duration** | **51 seconds (0:51 min)** |
| **Total DB turns** | 8 |
| **Outcome / reason** | `client_hangup` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 104 ms |
| **p95 latency (stored)** | 468 ms |
| **Max latency (stored)** | 687 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 73.5665 ¢ |

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
| Latency p50 / p95 / max (total) | 17 / 687 / 687 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 9 / 641 ms | From `llm_latency_ms` column |
| STT p50 | 5 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 8 / 642 ms (8 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    46
llm_latency_ms:    641 ✅
tts_latency_ms:    642
total_latency_ms:  687 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     greeting_first
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Ich rufe an wegen einer Reservierung.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    19 ✅
tts_latency_ms:    19
total_latency_ms:  23 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Ich bin der Herr Müller und möchte einen Tisch für zwei Personen morgen um neunzehn Uhr reservieren. Meine Telefonnummer ist null zweitausend

**Bot:** Auf welchen Namen darf ich reservieren?

---

### Turn 3

```
stt_latency_ms:    9
llm_latency_ms:    8 ✅
tts_latency_ms:    8
total_latency_ms:  17 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** acht null eins SEP.

**Bot:** Auf welchen Namen darf ich reservieren?

---

### Turn 4

```
stt_latency_ms:    12
llm_latency_ms:    49 ✅
tts_latency_ms:    49
total_latency_ms:  61 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** dreitausendvierhundertvierundsechzigste Haben Sie da noch etwas frei?

**Bot:** Auf welchen Namen darf ich reservieren?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    6 ✅
tts_latency_ms:    6
total_latency_ms:  10 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Moment, ich verstehe nicht.

**Bot:** Auf welchen Namen darf ich reservieren?

---

### Turn 6

```
stt_latency_ms:    5
llm_latency_ms:    5 ✅
tts_latency_ms:    5
total_latency_ms:  11 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Für zwei Personen bitte.

**Bot:** Auf welchen Namen darf ich reservieren?

---

### Turn 7

```
stt_latency_ms:    5
llm_latency_ms:    9 ✅
tts_latency_ms:    8
total_latency_ms:  14 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Morgen um neunzehn Uhr. Mein Name ist Müller.

**Bot:** Auf welchen Namen darf ich reservieren?

---

### Turn 8

```
stt_latency_ms:    4
llm_latency_ms:    6 ✅
tts_latency_ms:    6
total_latency_ms:  11 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Haben Sie das verstanden?

**Bot:** Auf welchen Namen darf ich reservieren?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 687 | 641 | 46 | None | — | 200 | greeting_first | neutral | None | get_date_info |  |
| 2 | 23 | 19 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 3 | 17 | 8 | 9 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 4 | 61 | 49 | 12 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 5 | 10 | 6 | 4 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 6 | 11 | 5 | 5 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 7 | 14 | 9 | 5 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 8 | 11 | 6 | 4 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Ich rufe an wegen einer Reservierung.
- **user** (turn 1): Ich bin der Herr Müller und möchte einen Tisch für zwei Personen morgen um neunzehn Uhr reservieren. Meine Telefonnummer ist null zweitausend
- **user** (turn 2): acht null eins SEP.
- **user** (turn 3): dreitausendvierhundertvierundsechzigste Haben Sie da noch etwas frei?
- **user** (turn 4): Moment, ich verstehe nicht.
- **user** (turn 5): Für zwei Personen bitte.
- **user** (turn 6): Morgen um neunzehn Uhr. Mein Name ist Müller.
- **user** (turn 7): Haben Sie das verstanden?

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
        "first_name": "Müller",
        "party_size": 2,
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
          "Für wie viele Personen darf ich reservieren?",
          "Auf welchen Namen darf ich reservieren?",
          "Auf welchen Namen darf ich reservieren?",
          "Auf welchen Namen darf ich reservieren?",
          "Auf welchen Namen darf ich reservieren?",
          "Auf welchen Namen darf ich reservieren?",
          "Auf welchen Namen darf ich reservieren?",
          "Auf welchen Namen darf ich reservieren?"
        ],
        "reservation_date": "2026-05-02",
        "reservation_time": "19:00",
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
            "bot": "Auf welchen Namen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "dreitausendvierhundertvierundsechzigste Haben Sie da noch etwas frei?"
          },
          {
            "bot": "Auf welchen Namen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Moment, ich verstehe nicht."
          },
          {
            "bot": "Auf welchen Namen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Für zwei Personen bitte."
          },
          {
            "bot": "Auf welchen Namen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Morgen um neunzehn Uhr. Mein Name ist Müller."
          },
          {
            "bot": "Auf welchen Namen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Haben Sie das verstanden?"
          }
        ],
        "context_summary": " [reservation_start] Kunde: 'Ich rufe an wegen einer Reservierung....' [reservation_start] Kunde: 'Ich bin der Herr Müller und möchte einen Tisch für zwei Personen morgen um neunzehn Uhr reservieren. Meine Telefonnummer ist null zweitausend...' [reservation_start] Kunde: 'acht null eins SEP....'",
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
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
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
        "Für wie viele Personen darf ich reservieren?",
        "Auf welchen Namen darf ich reservieren?",
        "Auf welchen Namen darf ich reservieren?",
        "Auf welchen Namen darf ich reservieren?",
        "Auf welchen Namen darf ich reservieren?",
        "Auf welchen Namen darf ich reservieren?",
        "Auf welchen Namen darf ich reservieren?",
        "Auf welchen Namen darf ich reservieren?"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-7bbbece22265",
  "ended_at": "2026-05-01T06:48:08.030922+02:00",
  "started_at": "2026-05-01T06:47:16.778558+02:00",
  "started_ts": 1777610836.7785778,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Ich rufe an wegen einer Reservierung.",
      "timestamp": "2026-05-01T06:47:19.532115+02:00"
    },
    {
      "role": "user",
      "text": "Ich bin der Herr Müller und möchte einen Tisch für zwei Personen morgen um neunzehn Uhr reservieren. Meine Telefonnummer ist null zweitausend",
      "timestamp": "2026-05-01T06:47:25.871699+02:00"
    },
    {
      "role": "user",
      "text": "acht null eins SEP.",
      "timestamp": "2026-05-01T06:47:27.886365+02:00"
    },
    {
      "role": "user",
      "text": "dreitausendvierhundertvierundsechzigste Haben Sie da noch etwas frei?",
      "timestamp": "2026-05-01T06:47:30.716874+02:00"
    },
    {
      "role": "user",
      "text": "Moment, ich verstehe nicht.",
      "timestamp": "2026-05-01T06:47:38.570476+02:00"
    },
    {
      "role": "user",
      "text": "Für zwei Personen bitte.",
      "timestamp": "2026-05-01T06:47:40.560180+02:00"
    },
    {
      "role": "user",
      "text": "Morgen um neunzehn Uhr. Mein Name ist Müller.",
      "timestamp": "2026-05-01T06:47:42.620928+02:00"
    },
    {
      "role": "user",
      "text": "Haben Sie das verstanden?",
      "timestamp": "2026-05-01T06:47:43.744386+02:00"
    }
  ],
  "duration_secs": 51.3,
  "emergency_events": [],
  "emergency_detected": false,
  "recording_consent_at": "2026-05-01T06:47:16.778558+02:00",
  "insurance_data_collected": false
}
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=reservation turn_type=add_information locked=False (conf=0.00) profile=reservation_start reroute=False
Turn 2: intent=reservation turn_type=finalize locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 3: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 4: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 5: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 6: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 7: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 8: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
