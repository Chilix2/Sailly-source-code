# Sailly — Full Call Analysis Report
## Call ID: `demo-cf6ed7b9b74e`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-cf6ed7b9b74e` |
| **Caller / channel** | `[validation:A2_tool_tag_neutral]` |
| **Started** | 2026-05-01 06:23:25 UTC |
| **Ended** | 2026-05-01 06:24:53 UTC |
| **Duration** | **88 seconds (1:28 min)** |
| **Total DB turns** | 7 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1449 ms |
| **p95 latency (stored)** | 1674 ms |
| **Max latency (stored)** | 1741 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 127.9343 ¢ |

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
| Latency p50 / p95 / max (total) | 1415 / 1741 / 1741 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1382 / 1738 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1382 / 1738 ms (7 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1738 ✅
tts_latency_ms:    1738
total_latency_ms:  1741 ✅
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

**User:** Ich bin gerade in der Gegend und würde gern vorbeikommen.

**Bot:** Guten Tag Herr Gerade In, schön, Sie bei uns zu haben! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?

---

### Turn 2

```
stt_latency_ms:    18
llm_latency_ms:    1499 ✅
tts_latency_ms:    1500
total_latency_ms:  1518 ✅
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

**User:** Hallo, ich wollte nur wissen, wo euer Restaurant genau liegt. Könntet ihr mir die Adresse geben?

**Bot:** Das freut uns sehr, dass Sie vorbeikommen möchten! Kann ich Ihnen unsere Öffnungszeiten geben, damit Sie wissen, wann wir für Sie da sind?

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    1382 ✅
tts_latency_ms:    1382
total_latency_ms:  1386 ✅
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

**User:** Nein, danke. Ich brauche erst mal nur die genaue Adresse.

**Bot:** Unsere Adresse ist Maximilianstraße 36, 53111 Bonn – wir freuen uns auf Ihren Besuch! Heute haben wir bis 23:00 Uhr für Sie geöffnet.

---

### Turn 4

```
stt_latency_ms:    4
llm_latency_ms:    1341 ✅
tts_latency_ms:    1342
total_latency_ms:  1346 ✅
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

**User:** Wo befindet sich euer Restaurant genau?

**Bot:** Gerne! Sie finden uns unter Maximilianstraße 36, 53111 Bonn – heute Freitag sind wir noch bis 23:00 Uhr für Sie da.

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    1464 ✅
tts_latency_ms:    1465
total_latency_ms:  1468 ✅
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

**User:** Vielen Dank. Das ist genau, was ich wissen wollte.

**Bot:** Kann ich Sie noch mit weiteren Informationen helfen – etwa zu Reservierungen oder Öffnungszeiten an anderen Tagen?

---

### Turn 6

```
stt_latency_ms:    5
llm_latency_ms:    1261 ✅
tts_latency_ms:    1262
total_latency_ms:  1266 ✅
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

**User:** Dann bis bald.

**Bot:** Sehr gerne! Falls Sie noch Fragen zu unseren Reservierungen, Öffnungszeiten oder anderen Services haben, stehe ich Ihnen jederzeit zur Verfügung.

---

### Turn 7

```
stt_latency_ms:    168
llm_latency_ms:    1246 ✅
tts_latency_ms:    1247
total_latency_ms:  1415 ✅
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

**User:** nach Adresse. Turn zwei, kein Problem. Höfliche Nachfrage trotz technischer Störung. Turn drei, kein Problem. Erneute klare Frage nach Adresse. Turn vier, kein Problem. Höfliche Ablehnung des Angebots und Wiederholung der Frage.

**Bot:** Bis bald und vielen Dank, dass Sie sich für DOBOO Korean Soulfood interessieren! Guten Appetit und auf Wiedersehen!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1741 | 1738 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1518 | 1499 | 18 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 3 | 1386 | 1382 | 4 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 4 | 1346 | 1341 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1468 | 1464 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1266 | 1261 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1415 | 1246 | 168 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Ich wollte fragen, wo euer Restaurant genau liegt. Könntet ihr mir die Adresse sagen?
- **user** (turn 1): Ich bin gerade in der Gegend und würde gern vorbeikommen.
- **user** (turn 2): Hallo, ich wollte nur wissen, wo euer Restaurant genau liegt. Könntet ihr mir die Adresse geben?
- **user** (turn 3): Nein, danke. Ich brauche erst mal nur die genaue Adresse.
- **user** (turn 4): Wo befindet sich euer Restaurant genau?
- **user** (turn 5): Vielen Dank. Das ist genau, was ich wissen wollte.
- **user** (turn 6): Dann bis bald.
- **user** (turn 7): nach Adresse. Turn zwei, kein Problem. Höfliche Nachfrage trotz technischer Störung. Turn drei, kein Problem. Erneute klare Frage nach Adresse. Turn vier, kein Problem. Höfliche Ablehnung des Angebots und Wiederholung der Frage.
- **user** (turn 8): Turn fünf. Kein Problem. Adresse korrekt erhalten und Gespräch beendet. Alle Turns korrekt. Turn zwei, Bot. Falsche Namenserkennung. Guten Tag, Herr geradein. Korrekt wäre eine neutrale Begrüßung ohne falschen Namen. Turn drei, Bot. Ignorierte Frage, Bot Öffnungszeiten statt Adresse an. Korrekt wäre direkte Beantwortung der gestellten Frage.

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
        "first_name": "Gerade",
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
          "Guten Tag Herr Gerade In, schön, Sie bei uns zu haben! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?",
          "Das freut uns sehr, dass Sie vorbeikommen möchten! Kann ich Ihnen unsere Öffnungszeiten geben, damit Sie wissen, wann wir für Sie da sind?",
          "Unsere Adresse ist Maximilianstraße 36, 53111 Bonn – wir freuen uns auf Ihren Besuch! Heute haben wir bis 23:00 Uhr für Sie geöffnet.",
          "Gerne! Sie finden uns unter Maximilianstraße 36, 53111 Bonn – heute Freitag sind wir noch bis 23:00 Uhr für Sie da.",
          "Kann ich Sie noch mit weiteren Informationen helfen – etwa zu Reservierungen oder Öffnungszeiten an anderen Tagen?",
          "Sehr gerne! Falls Sie noch Fragen zu unseren Reservierungen, Öffnungszeiten oder anderen Services haben, stehe ich Ihnen jederzeit zur Verfügung.",
          "Bis bald und vielen Dank, dass Sie sich für DOBOO Korean Soulfood interessieren! Guten Appetit und auf Wiedersehen!"
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
            "bot": "Unsere Adresse ist Maximilianstraße 36, 53111 Bonn – wir freuen uns auf Ihren Besuch! Heute haben wir bis 23:00 Uhr für Sie geöffnet.",
            "node": "business_info",
            "customer": "Nein, danke. Ich brauche erst mal nur die genaue Adresse."
          },
          {
            "bot": "Gerne! Sie finden uns unter Maximilianstraße 36, 53111 Bonn – heute Freitag sind wir noch bis 23:00 Uhr für Sie da.",
            "node": "greeting",
            "customer": "Wo befindet sich euer Restaurant genau?"
          },
          {
            "bot": "Kann ich Sie noch mit weiteren Informationen helfen – etwa zu Reservierungen oder Öffnungszeiten an anderen Tagen?",
            "node": "greeting",
            "customer": "Vielen Dank. Das ist genau, was ich wissen wollte."
          },
          {
            "bot": "Sehr gerne! Falls Sie noch Fragen zu unseren Reservierungen, Öffnungszeiten oder anderen Services haben, stehe ich Ihnen jederzeit zur Verfügung.",
            "node": "greeting",
            "customer": "Dann bis bald."
          },
          {
            "bot": "Bis bald und vielen Dank, dass Sie sich für DOBOO Korean Soulfood interessieren! Guten Appetit und auf Wiedersehen!",
            "node": "business_info",
            "customer": "nach Adresse. Turn zwei, kein Problem. Höfliche Nachfrage trotz technischer Störung. Turn drei, kein Problem. Erneute klare Frage nach Adresse. Turn vier, kein Problem. Höfliche Ablehnung des Angebots und Wiederholung der Frage."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Ich bin gerade in der Gegend und würde gern vorbeikommen....' [business_info] Kunde: 'Hallo, ich wollte nur wissen, wo euer Restaurant genau liegt. Könntet ihr mir die Adresse geben?...'",
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
        "get_date_info",
        "get_date_info",
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
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
        "Guten Tag Herr Gerade In, schön, Sie bei uns zu haben! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?",
        "Das freut uns sehr, dass Sie vorbeikommen möchten! Kann ich Ihnen unsere Öffnungszeiten geben, damit Sie wissen, wann wir für Sie da sind?",
        "Unsere Adresse ist Maximilianstraße 36, 53111 Bonn – wir freuen uns auf Ihren Besuch! Heute haben wir bis 23:00 Uhr für Sie geöffnet.",
        "Gerne! Sie finden uns unter Maximilianstraße 36, 53111 Bonn – heute Freitag sind wir noch bis 23:00 Uhr für Sie da.",
        "Kann ich Sie noch mit weiteren Informationen helfen – etwa zu Reservierungen oder Öffnungszeiten an anderen Tagen
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 2: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 3: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 4: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 5: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 6: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 7: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
