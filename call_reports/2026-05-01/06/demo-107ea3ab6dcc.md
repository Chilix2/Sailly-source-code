# Sailly — Full Call Analysis Report
## Call ID: `demo-107ea3ab6dcc`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-107ea3ab6dcc` |
| **Caller / channel** | `[validation:A3_opening_hours_eilig]` |
| **Started** | 2026-05-01 06:48:23 UTC |
| **Ended** | 2026-05-01 06:49:15 UTC |
| **Duration** | **52 seconds (0:52 min)** |
| **Total DB turns** | 6 |
| **Outcome / reason** | `v4_goodbye` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1659 ms |
| **p95 latency (stored)** | 2541 ms |
| **Max latency (stored)** | 2670 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 76.8473 ¢ |

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
| Latency p50 / p95 / max (total) | 1328 / 2670 / 2670 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1529 / 2666 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1530 / 2667 ms (6 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    5
llm_latency_ms:    1047 ✅
tts_latency_ms:    1048
total_latency_ms:  1052 ✅
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

**User:** Hallo?

**Bot:** Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?

---

### Turn 2

```
stt_latency_ms:    4
llm_latency_ms:    1324 ✅
tts_latency_ms:    1325
total_latency_ms:  1328 ✅
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

**User:** Ich wollte nur die Öffnungszeiten für heute wissen.

**Bot:** Gerne helfe ich Ihnen weiter – möchten Sie einen Tisch reservieren, Informationen zu unseren Speisen erhalten oder haben Sie eine andere Frage?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1529 ✅
tts_latency_ms:    1530
total_latency_ms:  1533 ✅
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

**User:** Von elf Uhr dreißig bis zwei zwanzig null. Brauchen Sie noch weitere Informationen?

**Bot:** Entschuldigung – leider habe ich keinen Zugriff auf unsere aktuellen Öffnungszeiten für heute, Freitag. Ich empfehle Ihnen, uns direkt anzurufen oder unsere Website zu besuchen, um die genauen Zeiten zu erfahren!

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    2150 ✅
tts_latency_ms:    2150
total_latency_ms:  2153 ✅
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

**User:** Das ist ja ärgerlich, dass Sie mir das nicht sagen können.

**Bot:** Vielen Dank für die Information – falls diese Zeiten für heute Freitag korrekt sind, können Sie uns gerne in diesem Zeitfenster erreichen! Kann ich Ihnen noch bei etwas anderem behilflich sein?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    2666 ✅
tts_latency_ms:    2667
total_latency_ms:  2670 ✅
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

**User:** Ich rufe doch extra deswegen an. Danke trotzdem.

**Bot:** Entschuldigen Sie, falls ich Ihre Frage nicht vollständig beantworten konnte – ich helfe Ihnen gerne weiter, wenn Sie mir mehr darüber erzählen, wobei ich Sie unterstützen kann. Was kann ich für Sie tun?

---

### Turn 6

```
stt_latency_ms:    7
llm_latency_ms:    1209 ✅
tts_latency_ms:    1210
total_latency_ms:  1217 ✅
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

**User:** Nein, das war's schon.

**Bot:** Sehr gerne – danke Ihnen für den Anruf bei DOBOO Korean Soulfood! Wir freuen uns auf Ihren nächsten Besuch.

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1052 | 1047 | 5 | None | — | 200 | info_neutral | impatient | None | ai_greeting,get_date_info |  |
| 2 | 1328 | 1324 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1533 | 1529 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 2153 | 2150 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 2670 | 2666 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1217 | 1209 | 7 | None | — | 200 | info_neutral | neutral | None | end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo, ich möchte wissen, wann ihr heute geöffnet habt. Schneller bitte, ich hab's eilig.
- **user** (turn 1): Hallo?
- **user** (turn 2): Ich wollte nur die Öffnungszeiten für heute wissen.
- **user** (turn 3): Von elf Uhr dreißig bis zwei zwanzig null. Brauchen Sie noch weitere Informationen?
- **user** (turn 4): Das ist ja ärgerlich, dass Sie mir das nicht sagen können.
- **user** (turn 5): Ich rufe doch extra deswegen an. Danke trotzdem.
- **user** (turn 6): Nein, das war's schon.

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
        "customer_name": null,
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": "+4915900000003",
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?",
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?",
          "Gerne helfe ich Ihnen weiter – möchten Sie einen Tisch reservieren, Informationen zu unseren Speisen erhalten oder haben Sie eine andere Frage?",
          "Entschuldigung – leider habe ich keinen Zugriff auf unsere aktuellen Öffnungszeiten für heute, Freitag. Ich empfehle Ihnen, uns direkt anzurufen oder unsere Website zu besuchen, um die genauen Zeiten zu erfahren!",
          "Vielen Dank für die Information – falls diese Zeiten für heute Freitag korrekt sind, können Sie uns gerne in diesem Zeitfenster erreichen! Kann ich Ihnen noch bei etwas anderem behilflich sein?",
          "Entschuldigen Sie, falls ich Ihre Frage nicht vollständig beantworten konnte – ich helfe Ihnen gerne weiter, wenn Sie mir mehr darüber erzählen, wobei ich Sie unterstützen kann. Was kann ich für Sie tun?",
          "Sehr gerne – danke Ihnen für den Anruf bei DOBOO Korean Soulfood! Wir freuen uns auf Ihren nächsten Besuch."
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
            "bot": "Gerne helfe ich Ihnen weiter – möchten Sie einen Tisch reservieren, Informationen zu unseren Speisen erhalten oder haben Sie eine andere Frage?",
            "node": "greeting",
            "customer": "Ich wollte nur die Öffnungszeiten für heute wissen."
          },
          {
            "bot": "Entschuldigung – leider habe ich keinen Zugriff auf unsere aktuellen Öffnungszeiten für heute, Freitag. Ich empfehle Ihnen, uns direkt anzurufen oder unsere Website zu besuchen, um die genauen Zeiten zu erfahren!",
            "node": "greeting",
            "customer": "Von elf Uhr dreißig bis zwei zwanzig null. Brauchen Sie noch weitere Informationen?"
          },
          {
            "bot": "Vielen Dank für die Information – falls diese Zeiten für heute Freitag korrekt sind, können Sie uns gerne in diesem Zeitfenster erreichen! Kann ich Ihnen noch bei etwas anderem behilflich sein?",
            "node": "greeting",
            "customer": "Das ist ja ärgerlich, dass Sie mir das nicht sagen können."
          },
          {
            "bot": "Entschuldigen Sie, falls ich Ihre Frage nicht vollständig beantworten konnte – ich helfe Ihnen gerne weiter, wenn Sie mir mehr darüber erzählen, wobei ich Sie unterstützen kann. Was kann ich für Sie tun?",
            "node": "greeting",
            "customer": "Ich rufe doch extra deswegen an. Danke trotzdem."
          },
          {
            "bot": "Sehr gerne – danke Ihnen für den Anruf bei DOBOO Korean Soulfood! Wir freuen uns auf Ihren nächsten Besuch.",
            "node": "goodbye",
            "customer": "Nein, das war's schon."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Hallo?...'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 7,
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
        "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?",
        "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?",
        "Gerne helfe ich Ihnen weiter – möchten Sie einen Tisch reservieren, Informationen zu unseren Speisen erhalten oder haben Sie eine andere Frage?",
        "Entschuldigung – leider habe ich keinen Zugriff auf unsere aktuellen Öffnungszeiten für heute, Freitag. Ich empfehle Ihnen, uns direkt anzurufen oder unsere Website zu besuchen, um die genauen Zeiten zu erfahren!",
        "Vielen Dank für die Information – falls diese Zeiten für heute Freitag korrekt sind, können Sie uns gerne in diesem Zeitfenster erreichen! Kann ich Ihnen noch bei etwas anderem behilflich sein?",
        "Entschuldigen Sie, falls ich Ihre Fr
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=unknown turn_type=unclear locked=False (conf=0.90) profile=greeting reroute=True
Turn 3: intent=unknown turn_type=unclear locked=False (conf=0.90) profile=greeting reroute=True
Turn 4: intent=unknown turn_type=unclear locked=False (conf=0.90) profile=greeting reroute=True
Turn 5: intent=unknown turn_type=unclear locked=False (conf=0.90) profile=greeting reroute=True
Turn 6: intent=goodbye turn_type=finalize locked=True (conf=0.95) profile=goodbye reroute=True
Turn 7: intent=goodbye turn_type=unclear locked=True (conf=0.95) profile=goodbye reroute=True
Turn 8: intent=goodbye turn_type=unclear locked=True (conf=0.95) profile=goodbye reroute=True
Turn 9: intent=goodbye turn_type=unclear locked=True (conf=0.95) profile=goodbye reroute=True
Turn 10: intent=goodbye turn_type=unclear locked=True (conf=0.95) profile=goodbye reroute=True
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
