# Sailly — Full Call Analysis Report
## Call ID: `demo-1aeff0d4ce84`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-1aeff0d4ce84` |
| **Caller / channel** | `[validation:A1_meta_feedback_froehlich]` |
| **Started** | 2026-05-01 06:32:01 UTC |
| **Ended** | 2026-05-01 06:33:17 UTC |
| **Duration** | **75 seconds (1:15 min)** |
| **Total DB turns** | 10 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1153 ms |
| **p95 latency (stored)** | 3376 ms |
| **Max latency (stored)** | 4487 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 109.8715 ¢ |

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
| Latency p50 / p95 / max (total) | 9 / 4487 / 4487 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1131 / 4440 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1132 / 4440 ms (10 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1131 ✅
tts_latency_ms:    1132
total_latency_ms:  1134 ✅
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

**User:** Hello,

**Bot:** Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Ihnen heute weiterhelfen?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    2015 ✅
tts_latency_ms:    2015
total_latency_ms:  2018 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         business_info
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info', 'get_weather']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Wir haben ja herrlich Wetter heute. Da würde ein gemütliches Abendessen superpassen. Haben Sie noch was frei?

**Bot:** Das Wetter heute ist Klar mit 12.4°C. Willkommen bei DOBOO Korean Soulfood! Wie kann ich Sie heute unterstützen – möchten Sie eine Reservierung vornehmen oder haben Sie Fragen zu unseren Angeboten?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1912 ✅
tts_latency_ms:    1912
total_latency_ms:  1915 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          relaxed
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

**User:** Ach, das klingt erfrisch draußen.

**Bot:** Sehr gerne helfe ich Ihnen weiter – für heute Freitag können Sie uns gerne anrufen, um die aktuelle Verfügbarkeit zu prüfen, oder Sie teilen mir Ihre Wunschzeit mit und ich prüfe das für Sie!

---

### Turn 4

```
stt_latency_ms:    47
llm_latency_ms:    4440 ⚠️
tts_latency_ms:    4440
total_latency_ms:  4487 ⚠️
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

**User:** Ich würde gerne für heute Abend reservieren, für zwei Personen so gegen neunzehn Uhr. Wär das möglich?

**Bot:** Das freut mich, dass Sie Interesse an DOBOO haben! Wie kann ich Ihnen heute weiterhelfen – möchten Sie einen Tisch reservieren oder haben Sie eine andere Frage?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    1936 ✅
tts_latency_ms:    1937
total_latency_ms:  1941 ✅
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

**User:** Ach, heute ist der schon Freitag, das hatte ich gar nicht im Kopf.

**Bot:** Ja, sehr gerne! Ich reserviere Ihnen gerne einen Tisch für zwei Personen heute Freitag um 19:00 Uhr – könnten Sie mir noch Ihren Namen und eine Telefonnummer für die Reservierung geben?

---

### Turn 6

```
stt_latency_ms:    4
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  7 ✅
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

**User:** Dann würde ich gerne für heute Abend um neunzehn Uhr einen Tisch für zwei Personen reservieren. Passt das bei euch?

**Bot:** Auf welchen Namen darf ich reservieren?

---

### Turn 7

```
stt_latency_ms:    3
llm_latency_ms:    5 ✅
tts_latency_ms:    5
total_latency_ms:  9 ✅
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

**User:** Auf den Namen Müller bitte.

**Bot:** Auf welchen Namen darf ich reservieren?

---

### Turn 8

```
stt_latency_ms:    5
llm_latency_ms:    4 ✅
tts_latency_ms:    4
total_latency_ms:  9 ✅
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

**User:** Könnten Sie schauen, ob das klappt?

**Bot:** Auf welchen Namen darf ich reservieren?

---

### Turn 9

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

**User:** Ich hatte doch gerade Miller gesagt. Ist das nicht angekommen?

**Bot:** Auf welchen Namen darf ich reservieren?

---

### Turn 10

```
stt_latency_ms:    3
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  6 ✅
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

**User:** Müller, genau.

**Bot:** Auf welchen Namen darf ich reservieren?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1134 | 1131 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 2018 | 2015 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info,get_weather |  |
| 3 | 1915 | 1912 | 3 | None | — | 200 | info_neutral | relaxed | None | ai_greeting,get_date_info |  |
| 4 | 4487 | 4440 | 47 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1941 | 1936 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 7 | 3 | 4 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 7 | 9 | 5 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 8 | 9 | 4 | 5 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 9 | 8 | 4 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 10 | 6 | 3 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hello,
- **user** (turn 1): ja, ich wollte mal schauen, ob ihr heute Abend noch einen Tisch für zwei Personen frei habt.
- **user** (turn 2): Wir haben ja herrlich Wetter heute. Da würde ein gemütliches Abendessen superpassen. Haben Sie noch was frei?
- **user** (turn 3): Ach, das klingt erfrisch draußen.
- **user** (turn 4): Ich würde gerne für heute Abend reservieren, für zwei Personen so gegen neunzehn Uhr. Wär das möglich?
- **user** (turn 5): Ach, heute ist der schon Freitag, das hatte ich gar nicht im Kopf.
- **user** (turn 6): Dann würde ich gerne für heute Abend um neunzehn Uhr einen Tisch für zwei Personen reservieren. Passt das bei euch?
- **user** (turn 7): Auf den Namen Müller bitte.
- **user** (turn 8): Könnten Sie schauen, ob das klappt?
- **user** (turn 9): Ich hatte doch gerade Miller gesagt. Ist das nicht angekommen?
- **user** (turn 10): Müller, genau.

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
        "phone_number": "+4915900000001",
        "shared_slots": {},
        "abuse_strikes": 0,
        "customer_name": null,
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": "+4915900000001",
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
          "Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Ihnen heute weiterhelfen?",
          "Das Wetter heute ist Klar mit 12.4°C. Willkommen bei DOBOO Korean Soulfood! Wie kann ich Sie heute unterstützen – möchten Sie eine Reservierung vornehmen oder haben Sie Fragen zu unseren Angeboten?",
          "Sehr gerne helfe ich Ihnen weiter – für heute Freitag können Sie uns gerne anrufen, um die aktuelle Verfügbarkeit zu prüfen, oder Sie teilen mir Ihre Wunschzeit mit und ich prüfe das für Sie!",
          "Das freut mich, dass Sie Interesse an DOBOO haben! Wie kann ich Ihnen heute weiterhelfen – möchten Sie einen Tisch reservieren oder haben Sie eine andere Frage?",
          "Ja, sehr gerne! Ich reserviere Ihnen gerne einen Tisch für zwei Personen heute Freitag um 19:00 Uhr – könnten Sie mir noch Ihren Namen und eine Telefonnummer für die Reservierung geben?",
          "Auf welchen Namen darf ich reservieren?",
          "Auf welchen Namen darf ich reservieren?",
          "Auf welchen Namen darf ich reservieren?",
          "Auf welchen Namen darf ich reservieren?",
          "Auf welchen Namen darf ich reservieren?"
        ],
        "reservation_date": "2026-05-01",
        "reservation_time": "19:00",
        "delivery_intended": false,
        "ai_greeting_called": false,
        "current_intent_idx": null,
        "customer_confirmed": true,
        "get_weather_called": false,
        "reservation_intent": true,
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
            "bot": "Auf welchen Namen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Dann würde ich gerne für heute Abend um neunzehn Uhr einen Tisch für zwei Personen reservieren. Passt das bei euch?"
          },
          {
            "bot": "Auf welchen Namen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Auf den Namen Müller bitte."
          },
          {
            "bot": "Auf welchen Namen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Könnten Sie schauen, ob das klappt?"
          },
          {
            "bot": "Auf welchen Namen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Ich hatte doch gerade Miller gesagt. Ist das nicht angekommen?"
          },
          {
            "bot": "Auf welchen Namen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Müller, genau."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Hello,...' [business_info] Kunde: 'Wir haben ja herrlich Wetter heute. Da würde ein gemütliches Abendessen superpassen. Haben Sie noch was frei?...' [greeting] Kunde: 'Ach, das klingt erfrisch draußen....' [greeting] Kunde: 'Ich würde gerne für heute Abend reservieren, für zwei Personen so gegen neunzehn Uhr. Wär das möglich?...' [greeting] Kunde: 'Ach, heute ist der schon Freitag, das hatte ich gar nicht im Kopf....'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 11,
      "all_tools": [
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "get_date_info",
        "get_date_info",
        "get_weather",
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
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
          "value": "+4915900000001",
          "status": "partial",
          "confidence": "high",
          "source_turn": 0,
          "raw_mentions": [
            "caller_id:+4915900000001"
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
        "Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Ihnen heute weiterhelfen?",
        "Das Wetter heute ist Klar mit 12.4°C. Willkommen bei DOBOO Korean Soulfood! Wie kann ich Sie heute unterstützen – möchten Sie eine Reservierung vornehmen oder haben Sie Fragen zu unseren Angeboten?",
        "Sehr gerne helfe ich Ihnen weiter – für heute Freitag können Sie uns gerne anrufen, um die aktuelle Verfügbarkeit zu prüfen, oder Sie teilen mir Ihre Wunschzeit mit und ich prüfe das für Sie!",
        "Das freut mich, dass Sie Interesse an DOBOO haben! Wie kann ich Ihnen heute weiterhelfen – möchten Sie einen Tisch reservieren oder haben
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 2: intent=faq turn_type=add_information locked=False (conf=0.00) profile=business_info reroute=False
Turn 3: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 4: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 5: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 6: intent=reservation turn_type=finalize locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 7: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 8: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 9: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 10: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
