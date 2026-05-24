# Sailly — Full Call Analysis Report
## Call ID: `demo-f53a3cc24e55`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-f53a3cc24e55` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-05-01 05:27:26 UTC |
| **Ended** | 2026-05-01 05:29:11 UTC |
| **Duration** | **104 seconds (1:44 min)** |
| **Total DB turns** | 10 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1539 ms |
| **p95 latency (stored)** | 1840 ms |
| **Max latency (stored)** | 1910 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 153.3437 ¢ |

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
| Latency p50 / p95 / max (total) | 1482 / 1910 / 1910 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1545 / 1906 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1546 / 1907 ms (10 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    301
llm_latency_ms:    1141 ✅
tts_latency_ms:    1141
total_latency_ms:  1442 ✅
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

**User:** Hallo,

**Bot:** Guten Tag! Möchten Sie gerne einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage zu DOBOO?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    1075 ✅
tts_latency_ms:    1076
total_latency_ms:  1079 ✅
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

**User:** Hallo, ich möchte wissen, wann ihr heute geöffnet habt.

**Bot:** Guten Tag und willkommen bei DOBOO Korean Soulfood! Wie kann ich Sie heute unterstützen?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1710 ✅
tts_latency_ms:    1711
total_latency_ms:  1714 ✅
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

**User:** Moment, ich verstehe nicht.

**Bot:** Gerne helfe ich Ihnen mit unseren Öffnungszeiten – könnten Sie mir kurz mitteilen, ob Sie die heutigen Zeiten für Freitag oder generell unsere Öffnungszeiten wissen möchten?

---

### Turn 4

```
stt_latency_ms:    4
llm_latency_ms:    1545 ✅
tts_latency_ms:    1546
total_latency_ms:  1549 ✅
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

**User:** Können Sie mir bitte sagen, wann Sie heute geöffnet haben?

**Bot:** Sehr gerne – heute ist Freitag, den 1. Mai 2026. Möchten Sie die Öffnungszeiten speziell für heute oder unsere regulären Öffnungszeiten erfahren?

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    1712 ✅
tts_latency_ms:    1712
total_latency_ms:  1715 ✅
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

**User:** Können Sie mir die Öffnungszeiten für heute sagen?

**Bot:** Da heute Freitag, der 1. Mai ist (ein Feiertag in Deutschland), können unsere Öffnungszeiten abweichen – können Sie mir sagen, ob Sie die heutigen Zeiten oder unsere normalen Öffnungszeiten wissen möchten?

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1478 ✅
tts_latency_ms:    1479
total_latency_ms:  1482 ✅
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

**User:** Moment, ich verstehe nicht.

**Bot:** Da heute Freitag, der 1. Mai ist (ein Feiertag in Deutschland), können unsere Öffnungszeiten abweichen – können Sie mir sagen, ob Sie die heutigen Zeiten oder unsere normalen Öffnungszeiten wissen möchten?

---

### Turn 7

```
stt_latency_ms:    3
llm_latency_ms:    1751 ✅
tts_latency_ms:    1751
total_latency_ms:  1755 ✅
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

**User:** Heute ist Feiertag, sagen Sie. Dann möchte ich gerne wissen, ob Sie heute geöffnet haben und wann genau.

**Bot:** Gerne helfe ich Ihnen weiter! Möchten Sie unsere heutigen Öffnungszeiten für diesen Feiertag oder unsere regulären Öffnungszeiten erfahren?

---

### Turn 8

```
stt_latency_ms:    3
llm_latency_ms:    1411 ✅
tts_latency_ms:    1412
total_latency_ms:  1415 ✅
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

**User:** Moment, ich verstehe nicht ganz.

**Bot:** Heute ist Freitag, der 1. Mai – ein Feiertag in Deutschland. Leider habe ich keine Informationen zu unseren speziellen Öffnungszeiten heute, aber ich empfehle Ihnen, uns direkt anzurufen oder unsere Website zu besuchen, um sicherzustellen, dass wir geöffnet haben!

---

### Turn 9

```
stt_latency_ms:    3
llm_latency_ms:    1330 ✅
tts_latency_ms:    1330
total_latency_ms:  1333 ✅
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

**User:** Können Sie mir bitte einfach sagen, ob Sie heute geöffnet haben und von wann bis wann?

**Bot:** Gerne helfe ich Ihnen weiter – können Sie mir konkret sagen, was Sie noch wissen möchten, damit ich Sie bestmöglich unterstützen kann?

---

### Turn 10

```
stt_latency_ms:    3
llm_latency_ms:    1906 ✅
tts_latency_ms:    1907
total_latency_ms:  1910 ✅
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

**User:** Moment, ich bin etwas verwirrt. Können Sie mir bitte sagen, ob Sie heute geöffnet haben und von wann bis wann? Heute ist doch Feiertag, oder?

**Bot:** Entschuldigung, ich verstehe – Sie möchten gerne wissen, ob wir heute Freitag geöffnet haben und zu welchen Zeiten. Leider habe ich diese Informationen gerade nicht verfügbar, aber ich verbinde Sie gerne direkt mit unserem Restaurant, damit Sie die genauen Öffnungszeiten erhalten.

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1442 | 1141 | 301 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1079 | 1075 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1714 | 1710 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1549 | 1545 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1715 | 1712 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1482 | 1478 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1755 | 1751 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 8 | 1415 | 1411 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 9 | 1333 | 1330 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 10 | 1910 | 1906 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo,
- **user** (turn 1): Moment, ich bin mir nicht sicher, ob ich das richtig verstanden habe.
- **user** (turn 2): Hallo, ich möchte wissen, wann ihr heute geöffnet habt.
- **user** (turn 3): Achtung, Saley. Du bist vom Thema abgekommen. Bitte beantworte nur die Öffnungszeiten.
- **bot** (turn 4): Verstanden, ich habe das notiert.
- **user** (turn 5): Moment, ich verstehe nicht.
- **user** (turn 6): Können Sie mir bitte sagen, wann Sie heute geöffnet haben?
- **user** (turn 7): Können Sie mir die Öffnungszeiten für heute sagen?
- **user** (turn 8): Moment, ich verstehe nicht.
- **user** (turn 9): Heute ist Feiertag, sagen Sie. Dann möchte ich gerne wissen, ob Sie heute geöffnet haben und wann genau.
- **user** (turn 10): Moment, ich verstehe nicht ganz.
- **user** (turn 11): Können Sie mir bitte einfach sagen, ob Sie heute geöffnet haben und von wann bis wann?
- **user** (turn 12): Moment, ich bin etwas verwirrt. Können Sie mir bitte sagen, ob Sie heute geöffnet haben und von wann bis wann? Heute ist doch Feiertag, oder?

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
        "phone_number": "+4915900000003",
        "shared_slots": {},
        "abuse_strikes": 0,
        "customer_name": "Etwas Verwirrt",
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": "+4915900000003",
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
          "Guten Tag! Möchten Sie gerne einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage zu DOBOO?",
          "Guten Tag und willkommen bei DOBOO Korean Soulfood! Wie kann ich Sie heute unterstützen?",
          "Gerne helfe ich Ihnen mit unseren Öffnungszeiten – könnten Sie mir kurz mitteilen, ob Sie die heutigen Zeiten für Freitag oder generell unsere Öffnungszeiten wissen möchten?",
          "Sehr gerne – heute ist Freitag, den 1. Mai 2026. Möchten Sie die Öffnungszeiten speziell für heute oder unsere regulären Öffnungszeiten erfahren?",
          "Da heute Freitag, der 1. Mai ist (ein Feiertag in Deutschland), können unsere Öffnungszeiten abweichen – können Sie mir sagen, ob Sie die heutigen Zeiten oder unsere normalen Öffnungszeiten wissen möchten?",
          "Da heute Freitag, der 1. Mai ist (ein Feiertag in Deutschland), können unsere Öffnungszeiten abweichen – können Sie mir sagen, ob Sie die heutigen Zeiten oder unsere normalen Öffnungszeiten wissen möchten?",
          "Gerne helfe ich Ihnen weiter! Möchten Sie unsere heutigen Öffnungszeiten für diesen Feiertag oder unsere regulären Öffnungszeiten erfahren?",
          "Heute ist Freitag, der 1. Mai – ein Feiertag in Deutschland. Leider habe ich keine Informationen zu unseren speziellen Öffnungszeiten heute, aber ich empfehle Ihnen, uns direkt anzurufen oder unsere Website zu besuchen, um sicherzustellen, dass wir geöffnet haben!",
          "Gerne helfe ich Ihnen weiter – können Sie mir konkret sagen, was Sie noch wissen möchten, damit ich Sie bestmöglich unterstützen kann?",
          "Entschuldigung, ich verstehe – Sie möchten gerne wissen, ob wir heute Freitag geöffnet haben und zu welchen Zeiten. Leider habe ich diese Informationen gerade nicht verfügbar, aber ich verbinde Sie gerne direkt mit unserem Restaurant, damit Sie die genauen Öffnungszeiten erhalten."
        ],
        "reservation_date": "2026-05-01",
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
        "delivery_address_mentioned": false,
        "last_caller_confirmation_turn": null
      },
      "memory": {
        "recent_turns": [
          {
            "bot": "Da heute Freitag, der 1. Mai ist (ein Feiertag in Deutschland), können unsere Öffnungszeiten abweichen – können Sie mir sagen, ob Sie die heutigen Zeiten oder unsere normalen Öffnungszeiten wissen möchten?",
            "node": "greeting",
            "customer": "Moment, ich verstehe nicht."
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter! Möchten Sie unsere heutigen Öffnungszeiten für diesen Feiertag oder unsere regulären Öffnungszeiten erfahren?",
            "node": "greeting",
            "customer": "Heute ist Feiertag, sagen Sie. Dann möchte ich gerne wissen, ob Sie heute geöffnet haben und wann genau."
          },
          {
            "bot": "Heute ist Freitag, der 1. Mai – ein Feiertag in Deutschland. Leider habe ich keine Informationen zu unseren speziellen Öffnungszeiten heute, aber ich empfehle Ihnen, uns direkt anzurufen oder unsere Website zu besuchen, um sicherzustellen, dass wir geöffnet haben!",
            "node": "greeting",
            "customer": "Moment, ich verstehe nicht ganz."
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter – können Sie mir konkret sagen, was Sie noch wissen möchten, damit ich Sie bestmöglich unterstützen kann?",
            "node": "greeting",
            "customer": "Können Sie mir bitte einfach sagen, ob Sie heute geöffnet haben und von wann bis wann?"
          },
          {
            "bot": "Entschuldigung, ich verstehe – Sie möchten gerne wissen, ob wir heute Freitag geöffnet haben und zu welchen Zeiten. Leider habe ich diese Informationen gerade nicht verfügbar, aber ich verbinde Sie gerne direkt mit unserem Restaurant, damit Sie die genauen Öffnungszeiten erhalten.",
            "node": "greeting",
            "customer": "Moment, ich bin etwas verwirrt. Können Sie mir bitte sagen, ob Sie heute geöffnet haben und von wann bis wann? Heute ist doch Feiertag, oder?"
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Hallo,...' [greeting] Kunde: 'Hallo, ich möchte wissen, wann ihr heute geöffnet habt....' [greeting] Kunde: 'Moment, ich verstehe nicht....' [greeting] Kunde: 'Können Sie mir bitte sagen, wann Sie heute geöffnet haben?...' [greeting] Kunde: 'Können Sie mir die Öffnungszeiten für heute sagen?...'",
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
          "value": "+4915900000003",
          "status": "partial",
          "confidence": "high",
          "source_turn": 0,
          "raw_mentions": [
            "caller_id:+4915900000003"
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
   
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 4: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 5: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 6: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 7: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 8: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 9: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 10: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
