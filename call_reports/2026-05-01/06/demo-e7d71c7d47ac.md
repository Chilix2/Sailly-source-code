# Sailly — Full Call Analysis Report
## Call ID: `demo-e7d71c7d47ac`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-e7d71c7d47ac` |
| **Caller / channel** | `[validation:A2_tool_tag_aeltere_person]` |
| **Started** | 2026-05-01 06:31:59 UTC |
| **Ended** | 2026-05-01 06:33:21 UTC |
| **Duration** | **81 seconds (1:21 min)** |
| **Total DB turns** | 11 |
| **Outcome / reason** | `v4_goodbye` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1757 ms |
| **p95 latency (stored)** | 2983 ms |
| **Max latency (stored)** | 3685 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 120.1065 ¢ |

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
| Latency p50 / p95 / max (total) | 1551 / 3685 / 3685 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1546 / 3682 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1546 / 3682 ms (11 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1420 ✅
tts_latency_ms:    1423
total_latency_ms:  1424 ✅
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

**User:** Hallo, Guten Tag.

**Bot:** Guten Tag! Möchten Sie heute einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage zu DOBOO?

---

### Turn 2

```
stt_latency_ms:    5
llm_latency_ms:    1546 ✅
tts_latency_ms:    1546
total_latency_ms:  1551 ✅
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

**User:** Ich bin ein bisschen vergesslich und hab die Adresse nicht mehr im Kopf.

**Bot:** Guten Tag, Herr Ein Bisschen! Wie kann ich Sie heute bei DOBOO unterstützen?

---

### Turn 3

```
stt_latency_ms:    5
llm_latency_ms:    1359 ✅
tts_latency_ms:    1359
total_latency_ms:  1365 ✅
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

**User:** Ach, das ist ja ärgerlich.

**Bot:** Sehr gerne! Sie finden uns unter der Adresse: DOBOO Korean Soulfood, Bonn. Kann ich Sie noch mit weiteren Informationen unterstützen?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1602 ✅
tts_latency_ms:    1605
total_latency_ms:  1605 ✅
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

**User:** Können Sie mir dann jetzt sagen, wo sich das Restaurant genau befindet?

**Bot:** Ich verstehe, dass das ärgerlich ist – gerne helfe ich Ihnen weiter, um die Situation zu klären. Womit kann ich Sie noch unterstützen?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    1336 ✅
tts_latency_ms:    1336
total_latency_ms:  1340 ✅
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

**User:** Ich finde es nicht mehr so gut.

**Bot:** Selbstverständlich – DOBOO Korean Soulfood befindet sich in Bonn. Kann ich Ihnen noch weitere Informationen zur genauen Adresse oder den Öffnungszeiten geben?

---

### Turn 6

```
stt_latency_ms:    7
llm_latency_ms:    1810 ✅
tts_latency_ms:    1811
total_latency_ms:  1818 ✅
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

**User:** Moment, ich versteh nicht ganz.

**Bot:** Es tut mir leid zu hören, dass Sie unzufrieden sind – könnten Sie mir sagen, wobei ich Ihnen heute helfen kann? Ich bin gerne für Ihre Anliegen da!

---

### Turn 7

```
stt_latency_ms:    3
llm_latency_ms:    1727 ✅
tts_latency_ms:    1728
total_latency_ms:  1730 ✅
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

**User:** Ich hatte doch gefragt, wo euer Restaurant genau ist. Können Sie mir die Adresse sagen?

**Bot:** Gerne helfe ich Ihnen weiter – könnten Sie mir konkret sagen, welcher Punkt unklar ist? Ich bin hier, um Ihre Fragen zu beantworten!

---

### Turn 8

```
stt_latency_ms:    3
llm_latency_ms:    2277 ✅
tts_latency_ms:    2277
total_latency_ms:  2281 ✅
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

**User:** Ich möchte nur die genaue Adresse von eurem Restaurant wissen. Haben Sie die Adresse nicht parat?

**Bot:** Entschuldigung für das Missverständnis – unsere genaue Adresse habe ich leider nicht in meinen Informationen verfügbar. Bitte rufen Sie uns direkt an oder besuchen Sie unsere Website, um die aktuelle Adresse von DOBOO Korean Soulfood in Bonn zu erhalten!

---

### Turn 9

```
stt_latency_ms:    3
llm_latency_ms:    3682 ⚠️
tts_latency_ms:    3682
total_latency_ms:  3685 ⚠️
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

**User:** Ach, das ist aber schade.

**Bot:** Sehr gerne helfe ich Ihnen weiter – kontaktieren Sie uns bitte telefonisch oder schauen Sie auf unserer Website vorbei, dort finden Sie die vollständige Adresse. Kann ich Ihnen noch bei etwas anderem behilflich sein?

---

### Turn 10

```
stt_latency_ms:    7
llm_latency_ms:    1242 ✅
tts_latency_ms:    1242
total_latency_ms:  1250 ✅
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

**User:** dann muss ich wohl woanders nachschauen. Vielen Dank trotzdem.

**Bot:** Ich stehe Ihnen gerne zur Verfügung – gibt es noch etwas, das ich für Sie klären kann? Ansonsten wünsche ich Ihnen einen schönen Freitag!

---

### Turn 11

```
stt_latency_ms:    5
llm_latency_ms:    1274 ✅
tts_latency_ms:    1275
total_latency_ms:  1280 ✅
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

**User:** Nein, das war's schon. Danke schön.

**Bot:** Gerne – viel Erfolg bei Ihrer Suche! Auf Wiedersehen und einen schönen Freitag noch!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1424 | 1420 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1551 | 1546 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1365 | 1359 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1605 | 1602 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1340 | 1336 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1818 | 1810 | 7 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1730 | 1727 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 8 | 2281 | 2277 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 9 | 3685 | 3682 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 10 | 1250 | 1242 | 7 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 11 | 1280 | 1274 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo, Guten Tag.
- **user** (turn 1): Wo befindet sich euer Restaurant genau?
- **user** (turn 2): Ich bin ein bisschen vergesslich und hab die Adresse nicht mehr im Kopf.
- **user** (turn 3): Ach, das ist ja ärgerlich.
- **user** (turn 4): Können Sie mir dann jetzt sagen, wo sich das Restaurant genau befindet?
- **user** (turn 5): Ich finde es nicht mehr so gut.
- **user** (turn 6): Moment, ich versteh nicht ganz.
- **user** (turn 7): Ich hatte doch gefragt, wo euer Restaurant genau ist. Können Sie mir die Adresse sagen?
- **user** (turn 8): Ich möchte nur die genaue Adresse von eurem Restaurant wissen. Haben Sie die Adresse nicht parat?
- **user** (turn 9): Ach, das ist aber schade.
- **user** (turn 10): dann muss ich wohl woanders nachschauen. Vielen Dank trotzdem.
- **user** (turn 11): Nein, das war's schon. Danke schön.

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
        "customer_name": "Guten Tag",
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
          "Guten Tag! Möchten Sie heute einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage zu DOBOO?",
          "Guten Tag, Herr Ein Bisschen! Wie kann ich Sie heute bei DOBOO unterstützen?",
          "Sehr gerne! Sie finden uns unter der Adresse: DOBOO Korean Soulfood, Bonn. Kann ich Sie noch mit weiteren Informationen unterstützen?",
          "Ich verstehe, dass das ärgerlich ist – gerne helfe ich Ihnen weiter, um die Situation zu klären. Womit kann ich Sie noch unterstützen?",
          "Selbstverständlich – DOBOO Korean Soulfood befindet sich in Bonn. Kann ich Ihnen noch weitere Informationen zur genauen Adresse oder den Öffnungszeiten geben?",
          "Es tut mir leid zu hören, dass Sie unzufrieden sind – könnten Sie mir sagen, wobei ich Ihnen heute helfen kann? Ich bin gerne für Ihre Anliegen da!",
          "Gerne helfe ich Ihnen weiter – könnten Sie mir konkret sagen, welcher Punkt unklar ist? Ich bin hier, um Ihre Fragen zu beantworten!",
          "Entschuldigung für das Missverständnis – unsere genaue Adresse habe ich leider nicht in meinen Informationen verfügbar. Bitte rufen Sie uns direkt an oder besuchen Sie unsere Website, um die aktuelle Adresse von DOBOO Korean Soulfood in Bonn zu erhalten!",
          "Sehr gerne helfe ich Ihnen weiter – kontaktieren Sie uns bitte telefonisch oder schauen Sie auf unserer Website vorbei, dort finden Sie die vollständige Adresse. Kann ich Ihnen noch bei etwas anderem behilflich sein?",
          "Ich stehe Ihnen gerne zur Verfügung – gibt es noch etwas, das ich für Sie klären kann? Ansonsten wünsche ich Ihnen einen schönen Freitag!",
          "Gerne – viel Erfolg bei Ihrer Suche! Auf Wiedersehen und einen schönen Freitag noch!"
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
            "bot": "Gerne helfe ich Ihnen weiter – könnten Sie mir konkret sagen, welcher Punkt unklar ist? Ich bin hier, um Ihre Fragen zu beantworten!",
            "node": "greeting",
            "customer": "Ich hatte doch gefragt, wo euer Restaurant genau ist. Können Sie mir die Adresse sagen?"
          },
          {
            "bot": "Entschuldigung für das Missverständnis – unsere genaue Adresse habe ich leider nicht in meinen Informationen verfügbar. Bitte rufen Sie uns direkt an oder besuchen Sie unsere Website, um die aktuelle Adresse von DOBOO Korean Soulfood in Bonn zu erhalten!",
            "node": "greeting",
            "customer": "Ich möchte nur die genaue Adresse von eurem Restaurant wissen. Haben Sie die Adresse nicht parat?"
          },
          {
            "bot": "Sehr gerne helfe ich Ihnen weiter – kontaktieren Sie uns bitte telefonisch oder schauen Sie auf unserer Website vorbei, dort finden Sie die vollständige Adresse. Kann ich Ihnen noch bei etwas anderem behilflich sein?",
            "node": "greeting",
            "customer": "Ach, das ist aber schade."
          },
          {
            "bot": "Ich stehe Ihnen gerne zur Verfügung – gibt es noch etwas, das ich für Sie klären kann? Ansonsten wünsche ich Ihnen einen schönen Freitag!",
            "node": "greeting",
            "customer": "dann muss ich wohl woanders nachschauen. Vielen Dank trotzdem."
          },
          {
            "bot": "Gerne – viel Erfolg bei Ihrer Suche! Auf Wiedersehen und einen schönen Freitag noch!",
            "node": "greeting",
            "customer": "Nein, das war's schon. Danke schön."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Hallo, Guten Tag....' [greeting] Kunde: 'Ich bin ein bisschen vergesslich und hab die Adresse nicht mehr im Kopf....' [greeting] Kunde: 'Ach, das ist ja ärgerlich....' [greeting] Kunde: 'Können Sie mir dann jetzt sagen, wo sich das Restaurant genau befindet?...' [greeting] Kunde: 'Ich finde es nicht mehr so gut....' [greeting] Kunde: 'Moment, ich versteh nicht ganz....'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 12,
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
          
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 4: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 5: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 6: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 7: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 8: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 9: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 10: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 11: intent=greeting turn_type=finalize locked=True (conf=0.90) profile=greeting reroute=False
Turn 12: intent=greeting turn_type=finalize locked=True (conf=0.90) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
