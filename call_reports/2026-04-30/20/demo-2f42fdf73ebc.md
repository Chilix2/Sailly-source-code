# Sailly — Full Call Analysis Report
## Call ID: `demo-2f42fdf73ebc`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-2f42fdf73ebc` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-04-30 20:57:19 UTC |
| **Ended** | 2026-04-30 20:58:57 UTC |
| **Duration** | **98 seconds (1:38 min)** |
| **Total DB turns** | 8 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1625 ms |
| **p95 latency (stored)** | 2465 ms |
| **Max latency (stored)** | 2856 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 143.3337 ¢ |

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
| Latency p50 / p95 / max (total) | 1441 / 2856 / 2856 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1437 / 2853 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | None / None ms (0 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1735 ✅
tts_latency_ms:    0
total_latency_ms:  1739 ✅
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
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Hallo Sally. Wie ist das Wetter heute bei euch?

**Bot:** Guten Tag! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute behilflich sein?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    2853 ✅
tts_latency_ms:    0
total_latency_ms:  2856 ✅
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
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** und hab die heute Abend noch ein Ich für zwei

**Bot:** Diese Information habe ich gerade leider nicht zur Hand.

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1382 ✅
tts_latency_ms:    0
total_latency_ms:  1385 ✅
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
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Bitte hinzufügen zum Transcript Turn one. Die Grüße mit doppelter Wiederholung. Turn zwei? Ja, bin gleich bei Ihnen. Klingt gut.

**Bot:** Entschuldigung, ich habe Sie nicht ganz verstanden – möchten Sie heute Abend einen Tisch für zwei Personen reservieren? Gerne helfe ich Ihnen weiter, wenn Sie mir noch ein paar Details geben!

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1546 ✅
tts_latency_ms:    0
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
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Turn drei. Diese Information

**Bot:** Entschuldigung, ich möchte Sie gerne richtig verstehen – wünschen Sie sich eine Reservierung bei DOBOO Korean Soulfood, oder kann ich Ihnen mit etwas anderem helfen?

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    1436 ✅
tts_latency_ms:    0
total_latency_ms:  1440 ✅
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
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** nicht zur Hand.

**Bot:** Entschuldigung, ich bin mir nicht ganz sicher, was Sie mit "Turn drei" meinen – könnten Sie mir bitte präzisieren, womit ich Ihnen weiterhelfen kann, ob es eine Reservierung, Öffnungszeiten oder etwas anderes ist?

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1195 ✅
tts_latency_ms:    0
total_latency_ms:  1198 ✅
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
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Alles klar,

**Bot:** Entschuldigung, ich bin mir nicht ganz sicher, was Sie mit "Turn drei" meinen – könnten Sie mir bitte präzisieren, womit ich Ihnen weiterhelfen kann, ob es eine Reservierung, Öffnungszeiten oder etwas anderes ist?

---

### Turn 7

```
stt_latency_ms:    3
llm_latency_ms:    1389 ✅
tts_latency_ms:    0
total_latency_ms:  1393 ✅
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
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Klar, schau nach.

**Bot:** Gerne helfe ich Ihnen weiter – könnten Sie mir nur kurz sagen, womit ich Sie unterstützen kann, zum Beispiel mit einer Reservierung oder Informationen zu unseren Öffnungszeiten?

---

### Turn 8

```
stt_latency_ms:    3
llm_latency_ms:    1437 ✅
tts_latency_ms:    0
total_latency_ms:  1441 ✅
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
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Okay, ich warte.

**Bot:** Sehr gerne – ich bin bereit, Ihnen zu helfen! Was kann ich für Sie tun: Möchten Sie einen Tisch reservieren, unsere Öffnungszeiten erfahren oder haben Sie eine andere Frage?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1739 | 1735 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info,get_weather |  |
| 2 | 2856 | 2853 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1385 | 1382 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1549 | 1546 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1440 | 1436 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1198 | 1195 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1393 | 1389 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 8 | 1441 | 1437 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO. Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?
- **user** (turn 1): Hallo Sally. Wie ist das Wetter heute bei euch?
- **user** (turn 2): und hab die heute Abend noch ein Ich für zwei
- **user** (turn 3): Achtung, Sali. eins noch.
- **bot** (turn 4): Verstanden, ich habe das notiert.
- **user** (turn 5): Bitte hinzufügen zum Transcript Turn one. Die Grüße mit doppelter Wiederholung. Turn zwei? Ja, bin gleich bei Ihnen. Klingt gut.
- **user** (turn 6): Turn drei. Diese Information
- **user** (turn 7): nicht zur Hand.
- **user** (turn 8): Alles klar,
- **user** (turn 9): Klar, schau nach.
- **user** (turn 10): Okay, ich warte.

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
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
          "Guten Tag! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute behilflich sein?",
          "Diese Information habe ich gerade leider nicht zur Hand.",
          "Entschuldigung, ich habe Sie nicht ganz verstanden – möchten Sie heute Abend einen Tisch für zwei Personen reservieren? Gerne helfe ich Ihnen weiter, wenn Sie mir noch ein paar Details geben!",
          "Entschuldigung, ich möchte Sie gerne richtig verstehen – wünschen Sie sich eine Reservierung bei DOBOO Korean Soulfood, oder kann ich Ihnen mit etwas anderem helfen?",
          "Entschuldigung, ich bin mir nicht ganz sicher, was Sie mit \"Turn drei\" meinen – könnten Sie mir bitte präzisieren, womit ich Ihnen weiterhelfen kann, ob es eine Reservierung, Öffnungszeiten oder etwas anderes ist?",
          "Entschuldigung, ich bin mir nicht ganz sicher, was Sie mit \"Turn drei\" meinen – könnten Sie mir bitte präzisieren, womit ich Ihnen weiterhelfen kann, ob es eine Reservierung, Öffnungszeiten oder etwas anderes ist?",
          "Gerne helfe ich Ihnen weiter – könnten Sie mir nur kurz sagen, womit ich Sie unterstützen kann, zum Beispiel mit einer Reservierung oder Informationen zu unseren Öffnungszeiten?",
          "Sehr gerne – ich bin bereit, Ihnen zu helfen! Was kann ich für Sie tun: Möchten Sie einen Tisch reservieren, unsere Öffnungszeiten erfahren oder haben Sie eine andere Frage?"
        ],
        "reservation_date": "2026-04-30",
        "reservation_time": null,
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
            "bot": "Entschuldigung, ich möchte Sie gerne richtig verstehen – wünschen Sie sich eine Reservierung bei DOBOO Korean Soulfood, oder kann ich Ihnen mit etwas anderem helfen?",
            "node": "greeting",
            "customer": "Turn drei. Diese Information"
          },
          {
            "bot": "Entschuldigung, ich bin mir nicht ganz sicher, was Sie mit \"Turn drei\" meinen – könnten Sie mir bitte präzisieren, womit ich Ihnen weiterhelfen kann, ob es eine Reservierung, Öffnungszeiten oder etwas anderes ist?",
            "node": "greeting",
            "customer": "nicht zur Hand."
          },
          {
            "bot": "Entschuldigung, ich bin mir nicht ganz sicher, was Sie mit \"Turn drei\" meinen – könnten Sie mir bitte präzisieren, womit ich Ihnen weiterhelfen kann, ob es eine Reservierung, Öffnungszeiten oder etwas anderes ist?",
            "node": "greeting",
            "customer": "Alles klar,"
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter – könnten Sie mir nur kurz sagen, womit ich Sie unterstützen kann, zum Beispiel mit einer Reservierung oder Informationen zu unseren Öffnungszeiten?",
            "node": "greeting",
            "customer": "Klar, schau nach."
          },
          {
            "bot": "Sehr gerne – ich bin bereit, Ihnen zu helfen! Was kann ich für Sie tun: Möchten Sie einen Tisch reservieren, unsere Öffnungszeiten erfahren oder haben Sie eine andere Frage?",
            "node": "greeting",
            "customer": "Okay, ich warte."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [business_info] Kunde: 'Hallo Sally. Wie ist das Wetter heute bei euch?...' [greeting] Kunde: 'und hab die heute Abend noch ein Ich für zwei...' [greeting] Kunde: 'Bitte hinzufügen zum Transcript Turn one. Die Grüße mit doppelter Wiederholung. Turn zwei? Ja, bin gleich bei Ihnen. Klingt gut....'",
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
        "get_date_info",
        "get_weather",
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
        "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
        "Guten Tag! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute behilflich sein?",
        "Diese Information habe ich gerade
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 2: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 3: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 4: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 5: intent=unknown turn_type=deny locked=True (conf=0.95) profile=greeting reroute=False
Turn 6: intent=unknown turn_type=confirm locked=True (conf=0.95) profile=greeting reroute=False
Turn 7: intent=unknown turn_type=unclear locked=True (conf=0.95) profile=greeting reroute=False
Turn 8: intent=unknown turn_type=confirm locked=True (conf=0.95) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
