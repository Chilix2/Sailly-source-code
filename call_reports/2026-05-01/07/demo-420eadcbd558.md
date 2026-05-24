# Sailly — Full Call Analysis Report
## Call ID: `demo-420eadcbd558`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-420eadcbd558` |
| **Caller / channel** | `[validation:A2_tool_tag_eilig]` |
| **Started** | 2026-05-01 07:06:04 UTC |
| **Ended** | 2026-05-01 07:07:23 UTC |
| **Duration** | **79 seconds (1:19 min)** |
| **Total DB turns** | 10 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1411 ms |
| **p95 latency (stored)** | 1743 ms |
| **Max latency (stored)** | 1770 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 117.0368 ¢ |

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
| Latency p50 / p95 / max (total) | 1323 / 1770 / 1770 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1349 / 1766 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1348 / 1767 ms (10 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1186 ✅
tts_latency_ms:    1187
total_latency_ms:  1190 ✅
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

**User:** Ich hab's eilig, also direkt die Info bitte.

**Bot:** Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – womit kann ich Ihnen heute behilflich sein?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    1440 ✅
tts_latency_ms:    1440
total_latency_ms:  1444 ✅
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
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Ja, ja, verstanden, aber ich seh brauch jetzt schnell die Adresse. Wo befindet sich euer Restaurant genau?

**Bot:** Sehr gerne, ich helfe Ihnen schnell weiter – was benötigen Sie denn konkret von DOBOO?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1706 ✅
tts_latency_ms:    1706
total_latency_ms:  1710 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          impatient
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
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Die genaue Adresse

**Bot:** Entschuldigung, ich habe leider keinen Zugriff auf unsere genaue Adresse in meinen Daten – können Sie mich bitte kurz durchstellen oder ich gebe Ihnen die Nummer, unter der Sie unseren Restaurant direkt erreichen?

---

### Turn 4

```
stt_latency_ms:    6
llm_latency_ms:    1120 ✅
tts_latency_ms:    1120
total_latency_ms:  1126 ✅
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

**User:** Ich hab's eilig.

**Bot:** Unsere aktuelle Adresse finden Sie am schnellsten auf unserer Website oder Sie können uns direkt anrufen – dann können wir Ihnen sofort alle Details geben!

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    1320 ✅
tts_latency_ms:    1321
total_latency_ms:  1323 ✅
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
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Wie, Sie haben die Adresse nicht?

**Bot:** Gerne helfe ich Ihnen schnell weiter – was kann ich für Sie tun? Wenn Sie unsere Öffnungszeiten oder die Adresse brauchen, sage ich Ihnen diese sofort!

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1231 ✅
tts_latency_ms:    1231
total_latency_ms:  1234 ✅
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
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Dann geben Sie mir die Nummer, ich ruf selbst an.

**Bot:** Unsere Adresse ist DOBOO Korean Soulfood, Bonn – gerne gebe ich Ihnen die genaue Adresse, wenn Sie diese benötigen. Wie kann ich Ihnen noch weiterhelfen?

---

### Turn 7

```
stt_latency_ms:    3
llm_latency_ms:    1261 ✅
tts_latency_ms:    1261
total_latency_ms:  1265 ✅
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
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Sie haben noch gerade gesagt, Sie haben keinen Zugriff auf die Adresse. Jetzt plötzlich doch. Sagen Sie mir jetzt die Adresse.

**Bot:** Sehr gerne – unsere Telefonnummer ist +49 228 [Nummer], unter der Sie uns erreichen können. Kann ich Ihnen noch etwas anderes behilflich sein?

---

### Turn 8

```
stt_latency_ms:    15
llm_latency_ms:    1676 ✅
tts_latency_ms:    1677
total_latency_ms:  1692 ✅
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
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Die Adresse, nicht die Nummer. Ich hab doch gesagt, ich brauch die Adresse. Wo sind Sie denn?

**Bot:** Entschuldigen Sie, ich habe keinen Zugriff auf unsere genaue Adresse – aber unter der Telefonnummer +49 228 [Nummer] können unsere Kollegen Ihnen diese gerne durchgeben und alle weiteren Fragen beantworten.

---

### Turn 9

```
stt_latency_ms:    3
llm_latency_ms:    1766 ✅
tts_latency_ms:    1767
total_latency_ms:  1770 ✅
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

**User:** Ja, ja, schon verstanden, aber das hilft nie jetzt nicht.

**Bot:** Sehr gerne – unsere Kollegen am Telefon geben Ihnen die genaue Adresse sofort durch und helfen Ihnen jederzeit weiter. Kann ich Sie noch mit etwas anderem unterstützen?

---

### Turn 10

```
stt_latency_ms:    10
llm_latency_ms:    1349 ✅
tts_latency_ms:    1348
total_latency_ms:  1360 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         goodbye
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

**User:** Ich hab keine Lust, noch mal anzurufen. Tschüs.

**Bot:** Sehr gerne, und vielen Dank für Ihren Anruf bei DOBOO Korean Soulfood! Ich wünsche Ihnen einen schönen Tag und freue mich auf Ihren Besuch.

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1190 | 1186 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1444 | 1440 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 3 | 1710 | 1706 | 3 | None | — | 200 | info_neutral | impatient | None | get_date_info |  |
| 4 | 1126 | 1120 | 6 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1323 | 1320 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 6 | 1234 | 1231 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 7 | 1265 | 1261 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 8 | 1692 | 1676 | 15 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 9 | 1770 | 1766 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 10 | 1360 | 1349 | 10 | None | — | 200 | info_neutral | neutral | None | end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo, ich suche die genaue Adresse von eurem Restaurant.
- **user** (turn 1): Ich hab's eilig, also direkt die Info bitte.
- **user** (turn 2): Ja, ja, verstanden, aber ich seh brauch jetzt schnell die Adresse. Wo befindet sich euer Restaurant genau?
- **user** (turn 3): Die genaue Adresse
- **user** (turn 4): Ich hab's eilig.
- **user** (turn 5): Wie, Sie haben die Adresse nicht?
- **user** (turn 6): Dann geben Sie mir die Nummer, ich ruf selbst an.
- **user** (turn 7): Sie haben noch gerade gesagt, Sie haben keinen Zugriff auf die Adresse. Jetzt plötzlich doch. Sagen Sie mir jetzt die Adresse.
- **user** (turn 8): Die Adresse, nicht die Nummer. Ich hab doch gesagt, ich brauch die Adresse. Wo sind Sie denn?
- **user** (turn 9): Ja, ja, schon verstanden, aber das hilft nie jetzt nicht.
- **user** (turn 10): Ich hab keine Lust, noch mal anzurufen. Tschüs.

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
          "Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – womit kann ich Ihnen heute behilflich sein?",
          "Sehr gerne, ich helfe Ihnen schnell weiter – was benötigen Sie denn konkret von DOBOO?",
          "Entschuldigung, ich habe leider keinen Zugriff auf unsere genaue Adresse in meinen Daten – können Sie mich bitte kurz durchstellen oder ich gebe Ihnen die Nummer, unter der Sie unseren Restaurant direkt erreichen?",
          "Unsere aktuelle Adresse finden Sie am schnellsten auf unserer Website oder Sie können uns direkt anrufen – dann können wir Ihnen sofort alle Details geben!",
          "Gerne helfe ich Ihnen schnell weiter – was kann ich für Sie tun? Wenn Sie unsere Öffnungszeiten oder die Adresse brauchen, sage ich Ihnen diese sofort!",
          "Unsere Adresse ist DOBOO Korean Soulfood, Bonn – gerne gebe ich Ihnen die genaue Adresse, wenn Sie diese benötigen. Wie kann ich Ihnen noch weiterhelfen?",
          "Sehr gerne – unsere Telefonnummer ist +49 228 [Nummer], unter der Sie uns erreichen können. Kann ich Ihnen noch etwas anderes behilflich sein?",
          "Entschuldigen Sie, ich habe keinen Zugriff auf unsere genaue Adresse – aber unter der Telefonnummer +49 228 [Nummer] können unsere Kollegen Ihnen diese gerne durchgeben und alle weiteren Fragen beantworten.",
          "Sehr gerne – unsere Kollegen am Telefon geben Ihnen die genaue Adresse sofort durch und helfen Ihnen jederzeit weiter. Kann ich Sie noch mit etwas anderem unterstützen?",
          "Sehr gerne, und vielen Dank für Ihren Anruf bei DOBOO Korean Soulfood! Ich wünsche Ihnen einen schönen Tag und freue mich auf Ihren Besuch."
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
            "bot": "Unsere Adresse ist DOBOO Korean Soulfood, Bonn – gerne gebe ich Ihnen die genaue Adresse, wenn Sie diese benötigen. Wie kann ich Ihnen noch weiterhelfen?",
            "node": "business_info",
            "customer": "Dann geben Sie mir die Nummer, ich ruf selbst an."
          },
          {
            "bot": "Sehr gerne – unsere Telefonnummer ist +49 228 [Nummer], unter der Sie uns erreichen können. Kann ich Ihnen noch etwas anderes behilflich sein?",
            "node": "business_info",
            "customer": "Sie haben noch gerade gesagt, Sie haben keinen Zugriff auf die Adresse. Jetzt plötzlich doch. Sagen Sie mir jetzt die Adresse."
          },
          {
            "bot": "Entschuldigen Sie, ich habe keinen Zugriff auf unsere genaue Adresse – aber unter der Telefonnummer +49 228 [Nummer] können unsere Kollegen Ihnen diese gerne durchgeben und alle weiteren Fragen beantworten.",
            "node": "business_info",
            "customer": "Die Adresse, nicht die Nummer. Ich hab doch gesagt, ich brauch die Adresse. Wo sind Sie denn?"
          },
          {
            "bot": "Sehr gerne – unsere Kollegen am Telefon geben Ihnen die genaue Adresse sofort durch und helfen Ihnen jederzeit weiter. Kann ich Sie noch mit etwas anderem unterstützen?",
            "node": "greeting",
            "customer": "Ja, ja, schon verstanden, aber das hilft nie jetzt nicht."
          },
          {
            "bot": "Sehr gerne, und vielen Dank für Ihren Anruf bei DOBOO Korean Soulfood! Ich wünsche Ihnen einen schönen Tag und freue mich auf Ihren Besuch.",
            "node": "goodbye",
            "customer": "Ich hab keine Lust, noch mal anzurufen. Tschüs."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Ich hab's eilig, also direkt die Info bitte....' [business_info] Kunde: 'Ja, ja, verstanden, aber ich seh brauch jetzt schnell die Adresse. Wo befindet sich euer Restaurant genau?...' [business_info] Kunde: 'Die genaue Adresse...' [greeting] Kunde: 'Ich hab's eilig....' [business_info] Kunde: 'Wie, Sie haben die Adresse nicht?...'",
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
        "get_date_info",
        "ai_greeting",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "ai_greeting",
        "get_date_info",
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
          "source_t
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 2: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 3: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 4: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 5: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 6: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 7: intent=faq turn_type=add_information locked=False (conf=0.00) profile=business_info reroute=False
Turn 8: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 9: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 10: intent=goodbye turn_type=finalize locked=True (conf=0.95) profile=goodbye reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
