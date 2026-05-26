# Sailly — Full Call Analysis Report
## Call ID: `demo-9db70a3efb7a`
_Generated: 2026-05-02 18:28 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-9db70a3efb7a` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-05-02 16:32:52 UTC |
| **Ended** | 2026-05-02 16:35:32 UTC |
| **Duration** | **160 seconds (2:40 min)** |
| **Total DB turns** | 8 |
| **Outcome / reason** | `client_hangup` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1426 ms |
| **p95 latency (stored)** | 1706 ms |
| **Max latency (stored)** | 1732 ms |
| **Was escalated** | False |
| **Tenant** | `doboo` |
| **Est. cost (stored)** | 231.2333 ¢ |

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
| Latency p50 / p95 / max (total) | 1508 / 1732 / 1732 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1504 / 1724 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1511 / 1724 ms (8 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    4
llm_latency_ms:    1653 ✅
tts_latency_ms:    1654
total_latency_ms:  1657 ✅
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
tools_called:      ['ai_greeting', 'get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Hallo Sally. Ich wollte mal kurz nachfragen, wie lange ihr

**Bot:** Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?

---

### Turn 2

```
stt_latency_ms:    4
llm_latency_ms:    1327 ✅
tts_latency_ms:    1328
total_latency_ms:  1332 ✅
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

**User:** heute noch offen habt.

**Bot:** Gerne helfe ich Ihnen weiter – könnten Sie Ihre Frage zu den Öffnungszeiten bitte zu Ende stellen?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1642 ✅
tts_latency_ms:    1642
total_latency_ms:  1646 ✅
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

**User:** Ach ja, genau. Und ich

**Bot:** Natürlich, wir sind heute Samstag gerne für Sie da – welche Öffnungszeiten benötigen Sie genau, oder möchten Sie einen Tisch reservieren?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1504 ✅
tts_latency_ms:    1511
total_latency_ms:  1508 ✅
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

**User:** wollte fragen, wie lange ihr heute noch offen habt.

**Bot:** Entschuldigen Sie, Ihre Nachricht wurde unterbrochen – könnten Sie mir bitte sagen, womit ich Ihnen heute helfen kann? Möchten Sie unsere Öffnungszeiten erfahren oder einen Tisch reservieren?

---

### Turn 5

```
stt_latency_ms:    8
llm_latency_ms:    1724 ✅
tts_latency_ms:    1724
total_latency_ms:  1732 ✅
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

**User:** Ja, ich bin noch da. Ich hatte nach den Öffnungszeiten für heute gefragt. Ja, ich bin noch da.

**Bot:** Gerne, Herr Noch Da! Leider habe ich die genauen Öffnungszeiten für heute nicht verfügbar – bitte rufen Sie uns direkt an oder schauen Sie auf unserer Website nach den aktuellen Zeiten.

---

### Turn 6

```
stt_latency_ms:    4
llm_latency_ms:    1130 ✅
tts_latency_ms:    1130
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

**User:** Ich wollte nur wissen, bis wann ihr heute offen habt.

**Bot:** Da heute Samstag ist, empfehle ich Ihnen, uns direkt unter unserer Telefonnummer anzurufen oder unsere Website zu besuchen, um die genauen Öffnungszeiten für heute zu erfahren.

---

### Turn 7

```
stt_latency_ms:    4
llm_latency_ms:    1360 ✅
tts_latency_ms:    1360
total_latency_ms:  1364 ✅
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

**User:** Danke, ich heiße aber nicht Herr Nochda.

**Bot:** Gerne, Herr Aber Nicht! Unsere aktuelle Telefonnummer finden Sie auf unserer Website – dort können Sie auch direkt anrufen und erfahren, bis wann wir heute geöffnet haben.

---

### Turn 8

```
stt_latency_ms:    4
llm_latency_ms:    1027 ✅
tts_latency_ms:    1027
total_latency_ms:  1031 ✅
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

**User:** Aber ich wollte eigentlich nur wissen, bis wann ihr heute offen habt.

**Bot:** Entschuldigung für das Missverständnis! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1657 | 1653 | 4 | None | — | 200 | greeting_first | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1332 | 1327 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1646 | 1642 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1508 | 1504 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1732 | 1724 | 8 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1134 | 1130 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1364 | 1360 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 8 | 1031 | 1027 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen behilflich sein?
- **user** (turn 1): wollte fragen, wie lange ihr heute noch offen habt.
- **assistant** (turn 2): Entschuldigen Sie, Ihre Nachricht wurde unterbrochen – könnten Sie mir bitte sagen, womit ich Ihnen heute helfen kann? Möchten Sie unsere Öffnungszeiten erfahren oder einen Tisch reservieren?
- **user** (turn 3): Ja, ich bin noch da. Ich hatte nach den Öffnungszeiten für heute gefragt. Ja, ich bin noch da.
- **assistant** (turn 4): Gerne, Herr Noch Da! Leider habe ich die genauen Öffnungszeiten für heute nicht verfügbar – bitte rufen Sie uns direkt an oder schauen Sie auf unserer Website nach den aktuellen Zeiten.
- **user** (turn 5): Ich wollte nur wissen, bis wann ihr heute offen habt.
- **assistant** (turn 6): Da heute Samstag ist, empfehle ich Ihnen, uns direkt unter unserer Telefonnummer anzurufen oder unsere Website zu besuchen, um die genauen Öffnungszeiten für heute zu erfahren.
- **user** (turn 7): Danke, ich heiße aber nicht Herr Nochda.
- **assistant** (turn 8): Gerne, Herr Aber Nicht! Unsere aktuelle Telefonnummer finden Sie auf unserer Website – dort können Sie auch direkt anrufen und erfahren, bis wann wir heute geöffnet haben.
- **user** (turn 9): Aber ich wollte eigentlich nur wissen, bis wann ihr heute offen habt.
- **assistant** (turn 10): Entschuldigung für das Missverständnis! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?

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
        "phone_number": null,
        "shared_slots": {},
        "abuse_strikes": 0,
        "customer_name": "Aber Nicht",
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": null,
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?",
          "Gerne helfe ich Ihnen weiter – könnten Sie Ihre Frage zu den Öffnungszeiten bitte zu Ende stellen?",
          "Natürlich, wir sind heute Samstag gerne für Sie da – welche Öffnungszeiten benötigen Sie genau, oder möchten Sie einen Tisch reservieren?",
          "Entschuldigen Sie, Ihre Nachricht wurde unterbrochen – könnten Sie mir bitte sagen, womit ich Ihnen heute helfen kann? Möchten Sie unsere Öffnungszeiten erfahren oder einen Tisch reservieren?",
          "Gerne, Herr Noch Da! Leider habe ich die genauen Öffnungszeiten für heute nicht verfügbar – bitte rufen Sie uns direkt an oder schauen Sie auf unserer Website nach den aktuellen Zeiten.",
          "Da heute Samstag ist, empfehle ich Ihnen, uns direkt unter unserer Telefonnummer anzurufen oder unsere Website zu besuchen, um die genauen Öffnungszeiten für heute zu erfahren.",
          "Gerne, Herr Aber Nicht! Unsere aktuelle Telefonnummer finden Sie auf unserer Website – dort können Sie auch direkt anrufen und erfahren, bis wann wir heute geöffnet haben.",
          "Entschuldigung für das Missverständnis! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?"
        ],
        "reservation_date": "2026-05-02",
        "reservation_time": null,
        "delivery_intended": false,
        "ai_greeting_called": false,
        "current_intent_idx": null,
        "customer_confirmed": true,
        "get_weather_called": false,
        "reservation_intent": false,
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
            "bot": "Entschuldigen Sie, Ihre Nachricht wurde unterbrochen – könnten Sie mir bitte sagen, womit ich Ihnen heute helfen kann? Möchten Sie unsere Öffnungszeiten erfahren oder einen Tisch reservieren?",
            "node": "greeting",
            "customer": "wollte fragen, wie lange ihr heute noch offen habt."
          },
          {
            "bot": "Gerne, Herr Noch Da! Leider habe ich die genauen Öffnungszeiten für heute nicht verfügbar – bitte rufen Sie uns direkt an oder schauen Sie auf unserer Website nach den aktuellen Zeiten.",
            "node": "greeting",
            "customer": "Ja, ich bin noch da. Ich hatte nach den Öffnungszeiten für heute gefragt. Ja, ich bin noch da."
          },
          {
            "bot": "Da heute Samstag ist, empfehle ich Ihnen, uns direkt unter unserer Telefonnummer anzurufen oder unsere Website zu besuchen, um die genauen Öffnungszeiten für heute zu erfahren.",
            "node": "greeting",
            "customer": "Ich wollte nur wissen, bis wann ihr heute offen habt."
          },
          {
            "bot": "Gerne, Herr Aber Nicht! Unsere aktuelle Telefonnummer finden Sie auf unserer Website – dort können Sie auch direkt anrufen und erfahren, bis wann wir heute geöffnet haben.",
            "node": "greeting",
            "customer": "Danke, ich heiße aber nicht Herr Nochda."
          },
          {
            "bot": "Entschuldigung für das Missverständnis! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?",
            "node": "greeting",
            "customer": "Aber ich wollte eigentlich nur wissen, bis wann ihr heute offen habt."
          }
        ],
        "context_summary": " [greeting] Kunde: 'Hallo Sally. Ich wollte mal kurz nachfragen, wie lange ihr...' [greeting] Kunde: 'heute noch offen habt....' [greeting] Kunde: 'Ach ja, genau. Und ich...'",
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
        "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?",
        "Gerne helfe ich Ihnen weiter – könnten Sie Ihre Frage zu den Öffnungszeiten bitte zu Ende stellen?",
        "Natürlich, wir sind heute Samstag gerne für Sie da – welche Öffnungszeiten benötigen Sie genau, oder möchten Sie einen Tisch reservieren?",
        "Entschuldigen Sie, Ihre Nachricht wurde unterbrochen – könnten Sie mir bitte sagen, womit ich Ihnen heute helfen kann? Möchten Sie unsere Öffnungszeiten erfahren oder einen Tisch reservie
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=False (conf=0.00) profile=greeting reroute=False
Turn 2: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 3: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 4: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 5: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 6: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 7: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 8: intent=unknown turn_type=correct_previous locked=True (conf=0.90) profile=greeting reroute=False
Turn 9: intent=unknown turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 10: intent=unknown turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
