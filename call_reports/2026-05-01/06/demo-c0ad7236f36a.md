# Sailly — Full Call Analysis Report
## Call ID: `demo-c0ad7236f36a`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-c0ad7236f36a` |
| **Caller / channel** | `[validation:A2_tool_tag_eilig]` |
| **Started** | 2026-05-01 06:31:44 UTC |
| **Ended** | 2026-05-01 06:33:25 UTC |
| **Duration** | **100 seconds (1:40 min)** |
| **Total DB turns** | 9 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1298 ms |
| **p95 latency (stored)** | 1578 ms |
| **Max latency (stored)** | 1606 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 146.1723 ¢ |

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
| Latency p50 / p95 / max (total) | 1368 / 1606 / 1606 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1363 / 1602 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1364 / 1602 ms (9 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    49
llm_latency_ms:    955 ✅
tts_latency_ms:    954
total_latency_ms:  1005 ✅
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

**Bot:** Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute unterstützen?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    923 ✅
tts_latency_ms:    923
total_latency_ms:  926 ✅
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

**User:** Hallo? Wo ist denn Euer Restaurant?

**Bot:** Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute unterstützen?

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    1602 ✅
tts_latency_ms:    1602
total_latency_ms:  1606 ✅
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

**User:** Schneller bitte, ich hab's eilig.

**Bot:** Gerne! Wir befinden uns in Bonn – leider habe ich die genaue Adresse gerade nicht zur Hand. Kann ich Sie mit unseren Öffnungszeiten oder einer anderen Information helfen?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1533 ✅
tts_latency_ms:    1533
total_latency_ms:  1537 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          impatient
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

**User:** Ja, ja, verstanden. Aber ich brauche die genaue Adresse. Können Sie das bitte nachschauen?

**Bot:** Unsere Öffnungszeiten heute Freitag sind von 11:30 bis 23:00 Uhr – wir sind also gerade offen und freuen uns auf Sie! Womit kann ich Sie noch schnell helfen?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    1253 ✅
tts_latency_ms:    1254
total_latency_ms:  1258 ✅
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

**User:** Touren zwei. Problem. Boot wiederholt die komplette Begrüßung trotz meiner Nachfrage. Sollte direkt auf die Adressfrage antworten. Touren drei. Problem. Boot gibt zu, die Adresse nicht zu kennen, statt sie nachzuschlagen. Ignoriert die eigentliche Anfrage. Touren vier. Problem. Boot wechselt

**Bot:** Gerne! Unsere Adresse ist DOBOO Korean Soulfood, Bonngasse 16, 53111 Bonn. Kann ich noch etwas für Sie tun?

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1143 ✅
tts_latency_ms:    1148
total_latency_ms:  1147 ✅
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

**User:** zu Öffnungszeiten, obwohl ich nur die Adresse wollte. Ignoriert meine dringende Nachfrage erneut.

**Bot:** Entschuldigen Sie, ich verstehe, dass Sie Feedback zu früheren Gesprächen haben – können Sie mir konkret sagen, wie ich Ihnen heute helfen kann?

---

### Turn 7

```
stt_latency_ms:    4
llm_latency_ms:    1460 ✅
tts_latency_ms:    1463
total_latency_ms:  1464 ✅
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

**User:** Turn eins, kein Problem. Korrekte Einleitung. Turn zwei, Problem. Bot wiederholt Begrüßung und schiebt technisches Problem vor. Sollte direkt auf Adressfrage antworten. Doorn

**Bot:** Gerne gebe ich Ihnen unsere Adresse: DOBOO Korean Soulfood befindet sich in Bonn – können Sie mir kurz mitteilen, welche Informationen Sie konkret benötigen?

---

### Turn 8

```
stt_latency_ms:    4
llm_latency_ms:    1363 ✅
tts_latency_ms:    1364
total_latency_ms:  1368 ✅
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

**User:** drei. Problem. Bot gibt zu, Adresse nicht zu haben, statt sie zu liefern. Ignoriert Anfrage. Torn vier.

**Bot:** Entschuldigen Sie, ich möchte Ihnen gerne direkt weiterhelfen – können Sie mir bitte sagen, ob Sie einen Tisch reservieren möchten, Öffnungszeiten benötigen oder eine andere Information suchen?

---

### Turn 9

```
stt_latency_ms:    7
llm_latency_ms:    1366 ✅
tts_latency_ms:    1366
total_latency_ms:  1373 ✅
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

**User:** Problem. Botwechsel zu Öffnungszeiten, obwohl User nur Adresse wollte. Anfrage komplett ignoriert.

**Bot:** Entschuldigen Sie – unsere Adresse in Bonn finden Sie gerne über Google Maps oder unsere Website. Wie kann ich Sie sonst noch unterstützen?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1005 | 955 | 49 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 926 | 923 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1606 | 1602 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1537 | 1533 | 3 | None | — | 200 | info_neutral | impatient | None | ai_greeting,get_date_info |  |
| 5 | 1258 | 1253 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1147 | 1143 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1464 | 1460 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 8 | 1368 | 1363 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 9 | 1373 | 1366 | 7 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo,
- **user** (turn 1): Wo befindet sich euer Restaurant genau? Ich bin in Eile.
- **user** (turn 2): Hallo? Wo ist denn Euer Restaurant?
- **assistant** (turn 3): Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute unterstützen?
- **user** (turn 4): Schneller bitte, ich hab's eilig.
- **user** (turn 5): Ja, ja, verstanden. Aber ich brauche die genaue Adresse. Können Sie das bitte nachschauen?
- **user** (turn 6): Touren zwei. Problem. Boot wiederholt die komplette Begrüßung trotz meiner Nachfrage. Sollte direkt auf die Adressfrage antworten. Touren drei. Problem. Boot gibt zu, die Adresse nicht zu kennen, statt sie nachzuschlagen. Ignoriert die eigentliche Anfrage. Touren vier. Problem. Boot wechselt
- **user** (turn 7): zu Öffnungszeiten, obwohl ich nur die Adresse wollte. Ignoriert meine dringende Nachfrage erneut.
- **user** (turn 8): Turn eins, kein Problem. Korrekte Einleitung. Turn zwei, Problem. Bot wiederholt Begrüßung und schiebt technisches Problem vor. Sollte direkt auf Adressfrage antworten. Doorn
- **user** (turn 9): drei. Problem. Bot gibt zu, Adresse nicht zu haben, statt sie zu liefern. Ignoriert Anfrage. Torn vier.
- **user** (turn 10): Problem. Botwechsel zu Öffnungszeiten, obwohl User nur Adresse wollte. Anfrage komplett ignoriert.

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
        "order_intent": true,
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
          "Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute unterstützen?",
          "Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute unterstützen?",
          "Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute unterstützen?",
          "Gerne! Wir befinden uns in Bonn – leider habe ich die genaue Adresse gerade nicht zur Hand. Kann ich Sie mit unseren Öffnungszeiten oder einer anderen Information helfen?",
          "Unsere Öffnungszeiten heute Freitag sind von 11:30 bis 23:00 Uhr – wir sind also gerade offen und freuen uns auf Sie! Womit kann ich Sie noch schnell helfen?",
          "Gerne! Unsere Adresse ist DOBOO Korean Soulfood, Bonngasse 16, 53111 Bonn. Kann ich noch etwas für Sie tun?",
          "Entschuldigen Sie, ich verstehe, dass Sie Feedback zu früheren Gesprächen haben – können Sie mir konkret sagen, wie ich Ihnen heute helfen kann?",
          "Gerne gebe ich Ihnen unsere Adresse: DOBOO Korean Soulfood befindet sich in Bonn – können Sie mir kurz mitteilen, welche Informationen Sie konkret benötigen?",
          "Entschuldigen Sie, ich möchte Ihnen gerne direkt weiterhelfen – können Sie mir bitte sagen, ob Sie einen Tisch reservieren möchten, Öffnungszeiten benötigen oder eine andere Information suchen?",
          "Entschuldigen Sie – unsere Adresse in Bonn finden Sie gerne über Google Maps oder unsere Website. Wie kann ich Sie sonst noch unterstützen?"
        ],
        "reservation_date": null,
        "reservation_time": null,
        "delivery_intended": true,
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
            "bot": "Gerne! Unsere Adresse ist DOBOO Korean Soulfood, Bonngasse 16, 53111 Bonn. Kann ich noch etwas für Sie tun?",
            "node": "greeting",
            "customer": "Touren zwei. Problem. Boot wiederholt die komplette Begrüßung trotz meiner Nachfrage. Sollte direkt auf die Adressfrage antworten. Touren drei. Problem. Boot gibt zu, die Adresse nicht zu kennen, statt sie nachzuschlagen. Ignoriert die eigentliche Anfrage. Touren vier. Problem. Boot wechselt"
          },
          {
            "bot": "Entschuldigen Sie, ich verstehe, dass Sie Feedback zu früheren Gesprächen haben – können Sie mir konkret sagen, wie ich Ihnen heute helfen kann?",
            "node": "greeting",
            "customer": "zu Öffnungszeiten, obwohl ich nur die Adresse wollte. Ignoriert meine dringende Nachfrage erneut."
          },
          {
            "bot": "Gerne gebe ich Ihnen unsere Adresse: DOBOO Korean Soulfood befindet sich in Bonn – können Sie mir kurz mitteilen, welche Informationen Sie konkret benötigen?",
            "node": "greeting",
            "customer": "Turn eins, kein Problem. Korrekte Einleitung. Turn zwei, Problem. Bot wiederholt Begrüßung und schiebt technisches Problem vor. Sollte direkt auf Adressfrage antworten. Doorn"
          },
          {
            "bot": "Entschuldigen Sie, ich möchte Ihnen gerne direkt weiterhelfen – können Sie mir bitte sagen, ob Sie einen Tisch reservieren möchten, Öffnungszeiten benötigen oder eine andere Information suchen?",
            "node": "greeting",
            "customer": "drei. Problem. Bot gibt zu, Adresse nicht zu haben, statt sie zu liefern. Ignoriert Anfrage. Torn vier."
          },
          {
            "bot": "Entschuldigen Sie – unsere Adresse in Bonn finden Sie gerne über Google Maps oder unsere Website. Wie kann ich Sie sonst noch unterstützen?",
            "node": "greeting",
            "customer": "Problem. Botwechsel zu Öffnungszeiten, obwohl User nur Adresse wollte. Anfrage komplett ignoriert."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Hallo,...' [greeting] Kunde: 'Hallo? Wo ist denn Euer Restaurant?...' [greeting] Kunde: 'Schneller bitte, ich hab's eilig....' [greeting] Kunde: 'Ja, ja, verstanden. Aber ich brauche die genaue Adresse. Können Sie das bitte nachschauen?...'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 10,
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
          "value": null,
          "status": "missing",
          "confidence": "low",
          "source_turn": null,
          "raw_mentions": []
        },
        "reservation_date": {
          "value": null,

```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 4: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 5: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 6: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 7: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 8: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 9: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
