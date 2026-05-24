# Sailly — Full Call Analysis Report
## Call ID: `demo-7d88e4dc1aa8`
_Generated: 2026-04-30 17:57 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-7d88e4dc1aa8` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-04-30 17:53:41 UTC |
| **Ended** | 2026-04-30 17:55:19 UTC |
| **Duration** | **98 seconds (1:38 min)** |
| **Total DB turns** | 9 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 391 ms |
| **p95 latency (stored)** | 879 ms |
| **Max latency (stored)** | 1032 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 140.6626 ¢ |

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
| Latency p50 / p95 / max (total) | 225 / 1032 / 1032 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 220 / 1029 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | ['ERR_TOOL_VALIDATION_FAILED'] | `error_codes` |
| Call-level observability (stored on `google_calls`) | validation_registry_invocations=0, loop_incidents=0 | From `persist_call_aggregates` |

---

## 3. Caller-flag insights (`Achtung Sailly: …` / `Attention Sailly: …`)

_Test harness, caller-bot, or human reviewer: phrases like **Achtung Sailly:** (also **Attention Sailly:** / **Warnung Sailly:**) mark what Sailly did **wrong** — use this for qualitative issues that **latency and tool metrics may not show**._

_No matching caller markers in `google_transcripts` (non-assistant roles), `session_data.transcripts`, or `user_text` in turn metrics._
## 4. Per-turn breakdown (DB)

### Turn 1

```
stt_latency_ms:    4
llm_latency_ms:    338 ✅
tts_latency_ms:    0
total_latency_ms:  342 ✅
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

**Bot:** Was darf ich für Sie tun?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    650 ✅
tts_latency_ms:    0
total_latency_ms:  650 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 642 / 4 / None
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
tools_called:      ['check_availability']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Und habt ihr heute Abend noch einen Tisch für zwei

**Bot:** (empty)

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    198 ✅
tts_latency_ms:    0
total_latency_ms:  202 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 642 / 4 / 612
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

**User:** Mon travail.

**Bot:** Was darf ich für Sie tun?

---

### Turn 4

```
stt_latency_ms:    4
llm_latency_ms:    220 ✅
tts_latency_ms:    0
total_latency_ms:  225 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 642 / 4 / 612
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

**User:** Sag mir das.

**Bot:** Was darf ich für Sie tun?

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    446 ✅
tts_latency_ms:    0
total_latency_ms:  449 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 642 / 4 / 612
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

**User:** Sally, Achtung, Du hast

**Bot:** Was darf ich für Sie tun?

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    204 ✅
tts_latency_ms:    0
total_latency_ms:  207 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 642 / 4 / 612
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

**User:** Du hast nur einen gesagt, das war wieder nur ein Bruchstück.

**Bot:** Was darf ich für Sie tun?

---

### Turn 7

```
stt_latency_ms:    3
llm_latency_ms:    1029 ✅
tts_latency_ms:    0
total_latency_ms:  1032 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 1060 / 5 / None
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
tools_called:      ['get_weather', 'check_availability', 'create_reservation']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       ['ERR_TOOL_VALIDATION_FAILED']
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Ich möchte gerne wissen, wie das Wetter heute bei euch ist und ob ihr heute Abend um neunzehn Uhr noch einen Tisch für zwei Personen frei habt.

**Bot:** In Bonn ist es gerade 18.7°C, Überwiegend klar. Entschuldigung — Ihre Reservierung konnte ich noch nicht abschließen. Mir fehlen noch ein paar Angaben.

---

### Turn 8

```
stt_latency_ms:    3
llm_latency_ms:    201 ✅
tts_latency_ms:    0
total_latency_ms:  205 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 1060 / 5 / 662
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
error_codes:       ['ERR_TOOL_VALIDATION_FAILED']
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Danke, ich wart.

**Bot:** Was darf ich für Sie tun?

---

### Turn 9

```
stt_latency_ms:    3
llm_latency_ms:    199 ✅
tts_latency_ms:    0
total_latency_ms:  203 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / 1060 / 5 / 662
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
error_codes:       ['ERR_TOOL_VALIDATION_FAILED']
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Sally, Achtung, Du hast schon wieder, was darf ich für Sie tun gefragt, obwohl ich dir das gerade erst gesagt habe.

**Bot:** Was darf ich für Sie tun?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-------|-------|
| 1 | 342 | 338 | 4 | None | — | 200 | greeting_first | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 2 | 650 | 650 | 3 | None | — | 200 | info_neutral | neutral | check_availability |  |
| 3 | 202 | 198 | 3 | None | — | 200 | info_neutral | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 4 | 225 | 220 | 4 | None | — | 200 | info_neutral | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 5 | 449 | 446 | 3 | None | — | 200 | info_neutral | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 6 | 207 | 204 | 3 | None | — | 200 | info_neutral | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 7 | 1032 | 1029 | 3 | None | — | 200 | info_neutral | neutral | get_weather,check_availability,create_reservation |  |
| 8 | 205 | 201 | 3 | None | — | 200 | confirm_success | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 9 | 203 | 199 | 3 | None | — | 200 | confirm_success | neutral | ai_greeting,get_date_info,ai_greeting |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?
- **user** (turn 1): Hallo, Sally. Wie ist das Wetter heute bei euch?
- **assistant** (turn 2): Was darf ich für Sie tun?
- **user** (turn 3): Und habt ihr heute Abend noch einen Tisch für zwei
- **user** (turn 4): Mon travail.
- **user** (turn 5): Sag mir das.
- **user** (turn 6): Sally, Achtung, Du hast
- **user** (turn 7): Du hast nur einen gesagt, das war wieder nur ein Bruchstück.
- **user** (turn 8): Ich möchte gerne wissen, wie das Wetter heute bei euch ist und ob ihr heute Abend um neunzehn Uhr noch einen Tisch für zwei Personen frei habt.
- **user** (turn 9): Danke, ich wart.
- **user** (turn 10): Sally, Achtung, Du hast schon wieder, was darf ich für Sie tun gefragt, obwohl ich dir das gerade erst gesagt habe.

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
        "customer_name": "Sally Achtung",
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": null,
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "",
          "In Bonn ist es gerade 18.7°C, Überwiegend klar. Entschuldigung — Ihre Reservierung konnte ich noch nicht abschließen. Mir fehlen noch ein paar Angaben."
        ],
        "reservation_date": "Heute",
        "reservation_time": "19:00",
        "delivery_intended": false,
        "ai_greeting_called": false,
        "current_intent_idx": null,
        "customer_confirmed": true,
        "get_weather_called": true,
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
            "bot": "Was darf ich für Sie tun?",
            "node": "greeting",
            "customer": "Sally, Achtung, Du hast"
          },
          {
            "bot": "Was darf ich für Sie tun?",
            "node": "greeting",
            "customer": "Du hast nur einen gesagt, das war wieder nur ein Bruchstück."
          },
          {
            "bot": "[TOOL:get_weather] [TOOL:check_availability]\n[TOOL:create_reservation]\n\nIhre Reservierung für 2 Personen am Heute um 19:00 Uhr ist bestätigt. Sie erhalten eine Bestätigung per SMS.",
            "node": "greeting",
            "customer": "Ich möchte gerne wissen, wie das Wetter heute bei euch ist und ob ihr heute Abend um neunzehn Uhr noch einen Tisch für zwei Personen frei habt."
          },
          {
            "bot": "Was darf ich für Sie tun?",
            "node": "greeting",
            "customer": "Danke, ich wart."
          },
          {
            "bot": "Was darf ich für Sie tun?",
            "node": "greeting",
            "customer": "Sally, Achtung, Du hast schon wieder, was darf ich für Sie tun gefragt, obwohl ich dir das gerade erst gesagt habe."
          }
        ],
        "context_summary": " [greeting] Kunde: 'Hallo, Sally. Wie ist das Wetter heute bei euch?...' [greeting] Kunde: 'Und habt ihr heute Abend noch einen Tisch für zwei...' [greeting] Kunde: 'Mon travail....' [greeting] Kunde: 'Sag mir das....'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 9,
      "all_tools": [
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
        "ai_greeting",
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "get_weather",
        "check_availability",
        "create_reservation",
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
        "",
        "In Bonn ist es gerade 18.7°C, Überwiegend klar. Entschuldigung — Ihre Reservierung konnte ich noch nicht abschließen. Mir fehlen noch ein paar Angaben."
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-7d88e4dc1aa8",
  "ended_at": "2026-04-30T19:55:19.753508+02:00",
  "started_at": "2026-04-30T19:53:41.438416+02:00",
  "started_ts": 1777571621.438448,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "assistant",
      "text": "Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?",
      "timestamp": "2026-04-30T19:53:41.442770+02:00"
    },
    {
      "role": "user",
      "text": "Hallo, Sally. Wie ist das Wetter heute bei euch?",
      "timestamp": "2026-04-30T19:54:01.514521+02:00"
    },
    {
      "role": "assistant",
      "text": "Was darf ich für Sie tun?",
      "timestamp": "2026-04-30T19:54:01.859989+02:00"
    },
    {
      "role": "user",
      "text": "Und habt ihr heute Abend noch einen Tisch für zwei",
      "timestamp": "2026-04-30T19:54:04.615256+02:00"
    },
    {
      "role": "user",
      "text": "Mon travail.",
      "timestamp": "2026-04-30T19:54:07.375960+02:00"
    },
    {
      "role": "user",
      "text": "Sag mir das.",
      "timestamp": "2026-04-30T19:54:10.111878+02:00"
    },
    {
      "role": "user",
      "text": "Sally, Achtung, Du hast",
      "timestamp": "2026-04-30T19:54:13.203787+02:00"
    },
    {
      "role": "user",
      "text": "Du hast nur einen gesagt, das war wieder nur ein Bruchstück.",
      "timestamp": "2026-04-30T19:54:19.022041+02:00"
    },
    {
      "role": "user",
      "text": "Ich möchte gerne wissen, wie das Wetter heute bei euch ist und ob ihr heute Abend um neunzehn Uhr noch einen Tisch für zwei Personen frei ha
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
Turn 7: intent=reservation turn_type=add_information locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 8: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 9: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
```

---

## 9. Auto-generated observations

- **Error codes present**: ['ERR_TOOL_VALIDATION_FAILED'].

---

_Report end._
