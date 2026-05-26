# Sailly — Full Call Analysis Report
## Call ID: `demo-94986eddfd69`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-94986eddfd69` |
| **Caller / channel** | `[validation:audio_pipeline_test]` |
| **Started** | 2026-05-01 06:39:43 UTC |
| **Ended** | 2026-05-01 06:40:42 UTC |
| **Duration** | **58 seconds (0:58 min)** |
| **Total DB turns** | 5 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1338 ms |
| **p95 latency (stored)** | 1454 ms |
| **Max latency (stored)** | 1462 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 85.1893 ¢ |

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
| Latency p50 / p95 / max (total) | 1391 / 1462 / 1462 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1387 / 1458 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1387 / 1459 ms (5 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1131 ✅
tts_latency_ms:    1132
total_latency_ms:  1135 ✅
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

**User:** Hallo, ich wollte mal fragen, wann ihr denn geöffnet habt.

**Bot:** Ich bin Sailly von DOBOO Korean Soulfood in Bonn und freue mich, Sie begrüßen zu dürfen! Wie kann ich Ihnen heute helfen?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    1418 ✅
tts_latency_ms:    1418
total_latency_ms:  1421 ✅
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

**User:** Danke.

**Bot:** Gerne helfe ich Ihnen weiter! Leider habe ich die Öffnungszeiten gerade nicht zur Hand – können Sie mich mit einem kurzen Moment Geduld entschuldigen oder möchten Sie lieber direkt anrufen?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1279 ✅
tts_latency_ms:    1279
total_latency_ms:  1282 ✅
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

**User:** Hallo, ich hab eine Frage zu eurem Öffnungszeiten. Können Sie mir sagen, wann Sie geöffnet haben?

**Bot:** Unsere Öffnungszeiten können Sie gerne unter unserer Telefonnummer erfragen – ich entschuldige mich, dass ich diese Information aktuell nicht parat habe. Kann ich Ihnen sonst noch bei etwas anderem behilflich sein?

---

### Turn 4

```
stt_latency_ms:    4
llm_latency_ms:    1458 ✅
tts_latency_ms:    1459
total_latency_ms:  1462 ✅
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

**User:** Ach schade, aber danke trotzdem für die Auskunft.

**Bot:** Gerne können Sie uns auch direkt anrufen, um unsere aktuellen Öffnungszeiten zu erfahren – unsere Kolleginnen und Kollegen helfen Ihnen gerne weiter. Gibt es noch etwas anderes, das ich für Sie tun kann?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    1387 ✅
tts_latency_ms:    1387
total_latency_ms:  1391 ✅
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

**User:** Dann wünsche ich Ihnen noch einen schönen Tag. Choose

**Bot:** Sehr gerne, dann wünsche ich Ihnen noch einen schönen Tag und freue mich auf Ihren nächsten Besuch bei DOBOO Korean Soulfood! Auf Wiedersehen!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1135 | 1131 | 4 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 2 | 1421 | 1418 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1282 | 1279 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 4 | 1462 | 1458 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1391 | 1387 | 4 | None | — | 200 | info_neutral | neutral | None | end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO. Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?
- **user** (turn 1): Hallo, ich wollte mal fragen, wann ihr denn geöffnet habt.
- **user** (turn 2): Danke.
- **user** (turn 3): Hallo, ich hab eine Frage zu eurem Öffnungszeiten. Können Sie mir sagen, wann Sie geöffnet haben?
- **user** (turn 4): Ach schade, aber danke trotzdem für die Auskunft.
- **user** (turn 5): Dann wünsche ich Ihnen noch einen schönen Tag. Choose

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
        "customer_name": null,
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": "+4915900000004",
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
          "Ich bin Sailly von DOBOO Korean Soulfood in Bonn und freue mich, Sie begrüßen zu dürfen! Wie kann ich Ihnen heute helfen?",
          "Gerne helfe ich Ihnen weiter! Leider habe ich die Öffnungszeiten gerade nicht zur Hand – können Sie mich mit einem kurzen Moment Geduld entschuldigen oder möchten Sie lieber direkt anrufen?",
          "Unsere Öffnungszeiten können Sie gerne unter unserer Telefonnummer erfragen – ich entschuldige mich, dass ich diese Information aktuell nicht parat habe. Kann ich Ihnen sonst noch bei etwas anderem behilflich sein?",
          "Gerne können Sie uns auch direkt anrufen, um unsere aktuellen Öffnungszeiten zu erfahren – unsere Kolleginnen und Kollegen helfen Ihnen gerne weiter. Gibt es noch etwas anderes, das ich für Sie tun kann?",
          "Sehr gerne, dann wünsche ich Ihnen noch einen schönen Tag und freue mich auf Ihren nächsten Besuch bei DOBOO Korean Soulfood! Auf Wiedersehen!"
        ],
        "reservation_date": null,
        "reservation_time": null,
        "delivery_intended": false,
        "ai_greeting_called": false,
        "current_intent_idx": null,
        "customer_confirmed": false,
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
            "bot": "Ich bin Sailly von DOBOO Korean Soulfood in Bonn und freue mich, Sie begrüßen zu dürfen! Wie kann ich Ihnen heute helfen?",
            "node": "business_info",
            "customer": "Hallo, ich wollte mal fragen, wann ihr denn geöffnet habt."
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter! Leider habe ich die Öffnungszeiten gerade nicht zur Hand – können Sie mich mit einem kurzen Moment Geduld entschuldigen oder möchten Sie lieber direkt anrufen?",
            "node": "greeting",
            "customer": "Danke."
          },
          {
            "bot": "Unsere Öffnungszeiten können Sie gerne unter unserer Telefonnummer erfragen – ich entschuldige mich, dass ich diese Information aktuell nicht parat habe. Kann ich Ihnen sonst noch bei etwas anderem behilflich sein?",
            "node": "business_info",
            "customer": "Hallo, ich hab eine Frage zu eurem Öffnungszeiten. Können Sie mir sagen, wann Sie geöffnet haben?"
          },
          {
            "bot": "Gerne können Sie uns auch direkt anrufen, um unsere aktuellen Öffnungszeiten zu erfahren – unsere Kolleginnen und Kollegen helfen Ihnen gerne weiter. Gibt es noch etwas anderes, das ich für Sie tun kann?",
            "node": "greeting",
            "customer": "Ach schade, aber danke trotzdem für die Auskunft."
          },
          {
            "bot": "Sehr gerne, dann wünsche ich Ihnen noch einen schönen Tag und freue mich auf Ihren nächsten Besuch bei DOBOO Korean Soulfood! Auf Wiedersehen!",
            "node": "goodbye",
            "customer": "Dann wünsche ich Ihnen noch einen schönen Tag. Choose"
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 6,
      "all_tools": [
        "ai_greeting",
        "get_date_info",
        "get_date_info",
        "ai_greeting",
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
          "value": "+4915900000004",
          "status": "partial",
          "confidence": "high",
          "source_turn": 0,
          "raw_mentions": [
            "caller_id:+4915900000004"
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
        "Ich bin Sailly von DOBOO Korean Soulfood in Bonn und freue mich, Sie begrüßen zu dürfen! Wie kann ich Ihnen heute helfen?",
        "Gerne helfe ich Ihnen weiter! Leider habe ich die Öffnungszeiten gerade nicht zur Hand – können Sie mich mit einem kurzen Moment Geduld entschuldigen oder möchten Sie lieber direkt anrufen?",
        "Unsere Öffnungszeiten können Sie gerne unter unserer Telefonnummer erfragen – ich entschuldige mich, dass ich diese Information aktuell nicht parat habe. Kann ich Ihnen sonst noch bei etwas anderem behilflich sein?",
        "Gerne können Sie uns auch direkt anrufen, um unsere aktuellen Öffnungszeiten zu erfahren – unsere Kolleginnen und Kollegen helfen Ihnen gerne weiter. Gibt es noch etwas anderes, das ich für Sie tun kann?",
        "Sehr gerne, dann wünsche ich Ihnen noch einen schönen Tag und freue mich auf Ihren nächsten Besuch bei DOBOO Korean Soulfood! Au
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 2: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 3: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 4: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 5: intent=goodbye turn_type=finalize locked=True (conf=0.95) profile=goodbye reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
