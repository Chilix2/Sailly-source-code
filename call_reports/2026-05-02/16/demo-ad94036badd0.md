# Sailly — Full Call Analysis Report
## Call ID: `demo-ad94036badd0`
_Generated: 2026-05-02 18:28 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-ad94036badd0` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-05-02 16:50:09 UTC |
| **Ended** | 2026-05-02 16:51:41 UTC |
| **Duration** | **91 seconds (1:31 min)** |
| **Total DB turns** | 5 |
| **Outcome / reason** | `v4_goodbye` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 241 ms |
| **p95 latency (stored)** | 938 ms |
| **Max latency (stored)** | 1170 ms |
| **Was escalated** | False |
| **Tenant** | `doboo` |
| **Est. cost (stored)** | 130.6398 ¢ |

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
| Latency p50 / p95 / max (total) | 8 / 1170 / 1170 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 5 / 1162 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 5 / 1162 ms (5 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    8
llm_latency_ms:    1162 ✅
tts_latency_ms:    1162
total_latency_ms:  1170 ✅
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
tools_called:      ['ai_greeting', 'get_date_info', 'get_weather']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Hallo Sally. Wie ist das Wetter heute bei euch?

**Bot:** Das Wetter heute ist Bewölkt mit 19.4°C. Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    4 ✅
tts_latency_ms:    4
total_latency_ms:  8 ✅
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

**User:** Und habt ihr heute Abend noch einen Tisch für 2 Personen 19 Uhr frei?

**Bot:** Auf welchen Namen darf ich reservieren?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    5 ✅
tts_latency_ms:    5
total_latency_ms:  8 ✅
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

**User:** Max Müller.

**Bot:** Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?

---

### Turn 4

```
stt_latency_ms:    5
llm_latency_ms:    6 ✅
tts_latency_ms:    8
total_latency_ms:  12 ✅
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
tools_called:      ['get_date_info', 'check_availability', 'create_reservation']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** 7 1 6 2 3 4 6 7 8 9.

**Bot:** Ich habe 2 Personen für heute um 19:00 Uhr auf den Namen Max Müller reserviert. Stimmt das so?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    2 ✅
tts_latency_ms:    2
total_latency_ms:  7 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     confirm_success
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
tools_called:      ['end_call']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Ja, das stimmt. Danke schön.

**Bot:** Vielen Dank und auf Wiederhören!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1170 | 1162 | 8 | None | — | 200 | greeting_first | neutral | None | ai_greeting,get_date_info,get_weather |  |
| 2 | 8 | 4 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 3 | 8 | 5 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 4 | 12 | 6 | 5 | None | — | 200 | info_neutral | neutral | None | get_date_info,check_availability,create_reservation |  |
| 5 | 7 | 2 | 4 | None | — | 200 | confirm_success | neutral | None | end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen behilflich sein?
- **user** (turn 1): Hallo Sally. Wie ist das Wetter heute bei euch?
- **assistant** (turn 2): Das Wetter heute ist Bewölkt mit 19.4°C. Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?
- **user** (turn 3): Und habt ihr heute Abend noch einen Tisch für 2 Personen 19 Uhr frei?
- **assistant** (turn 4): Auf welchen Namen darf ich reservieren?
- **user** (turn 5): Max Müller.
- **assistant** (turn 6): Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?
- **user** (turn 7): 7 1 6 2 3 4 6 7 8 9.
- **assistant** (turn 8): Ich habe 2 Personen für heute um 19:00 Uhr auf den Namen Max Müller reserviert. Stimmt das so?
- **user** (turn 9): Ja, das stimmt. Danke schön.
- **assistant** (turn 10): Vielen Dank und auf Wiederhören!

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
        "phone_number": "7 1 6 2 3 4 6 7 8 9",
        "shared_slots": {},
        "abuse_strikes": 0,
        "customer_name": "Max Müller",
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "confirmed",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": null,
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Das Wetter heute ist Bewölkt mit 19.4°C. Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?",
          "Auf welchen Namen darf ich reservieren?",
          "Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?",
          "Ich habe 2 Personen für heute um 19:00 Uhr auf den Namen Max Müller reserviert. Stimmt das so?",
          "Vielen Dank und auf Wiederhören!"
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
        "reservation_created": true,
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
        "check_availability_called": true,
        "pending_bulk_confirmation": false,
        "delivery_address_mentioned": false,
        "last_caller_confirmation_turn": null
      },
      "memory": {
        "recent_turns": [
          {
            "bot": "Das Wetter heute ist Bewölkt mit 19.4°C. Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?",
            "node": "greeting",
            "customer": "Hallo Sally. Wie ist das Wetter heute bei euch?"
          },
          {
            "bot": "Auf welchen Namen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Und habt ihr heute Abend noch einen Tisch für 2 Personen 19 Uhr frei?"
          },
          {
            "bot": "Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?",
            "node": "reservation_start",
            "customer": "Max Müller."
          },
          {
            "bot": "Ich habe 2 Personen für heute um 19:00 Uhr auf den Namen Max Müller reserviert. Stimmt das so?",
            "node": "reservation_start",
            "customer": "7 1 6 2 3 4 6 7 8 9."
          },
          {
            "bot": "Vielen Dank und auf Wiederhören!",
            "node": "reservation_start",
            "customer": "Ja, das stimmt. Danke schön."
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
        "get_weather",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "check_availability",
        "create_reservation",
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
        "Das Wetter heute ist Bewölkt mit 19.4°C. Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?",
        "Auf welchen Namen darf ich reservieren?",
        "Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?",
        "Ich habe 2 Personen für heute um 19:00 Uhr auf den Namen Max Müller reserviert. Stimmt das so?",
        "Vielen Dank und auf Wiederhören!"
      ]
    }
  },
  "caller": "browser_demo",
  "tenant": "doboo",
  "call_sid": "demo-ad94036badd0",
  "ended_at": "2026-05-02T18:51:41.588678+02:00",
  "tenant_id": "doboo",
  "started_at": "2026-05-02T18:50:09.763146+02:00",
  "started_ts": 1777740609.7631805,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "assistant",
      "text": "Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen behilflich sein?",
      "timestamp": "2026-05-02T18:50:09.768537+02:00"
    },
    {
      "role": "user",
      "text": "Hallo Sally. Wie ist das Wetter heute bei euch?",
      "timestamp": "2026-05-02T18:50:38.510462+02:00"
    },
    {
      "role": "user",
      "text": "Und habt ihr heute Abend noch einen Tisch für 2 Personen 19 Uhr frei?",
      "timestamp": "2026-05-02T18:50:39.690780+02:00"
    },
    {
      "role": "user",
      "text": "Max Müller.",
      "timestamp": "2026-05-02T18:51:04.817892+02:00"
    },
    {
      "role": "user",
      "text": "7 1 6 2 3 4 6 7 8 9.",
      "timestamp": "2026-05-02T18:51:20.568690+02:00"
    },
    {
      "role": "user",
      "text": "Ja, das stimmt. Danke schön.",
      "timestamp": "2026-05-02T18:51:37.425025+02:00"
    }
  ],
  "duration_secs": 91.8,
  "emergency_events": [],
  "emergency_detected": false,
  "recording_consent_at": "2026-05-02T18:50:09.763146+02:00",
  "insurance_data_collected": false
}
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=False (conf=0.00) profile=greeting reroute=False
Turn 2: intent=reservation turn_type=add_information locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 3: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 4: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 5: intent=reservation turn_type=confirm locked=True (conf=0.85) profile=reservation_start reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
