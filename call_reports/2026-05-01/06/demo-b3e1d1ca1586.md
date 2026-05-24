# Sailly — Full Call Analysis Report
## Call ID: `demo-b3e1d1ca1586`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-b3e1d1ca1586` |
| **Caller / channel** | `[validation:A2_tool_tag_neutral]` |
| **Started** | 2026-05-01 06:37:31 UTC |
| **Ended** | 2026-05-01 06:38:30 UTC |
| **Duration** | **59 seconds (0:59 min)** |
| **Total DB turns** | 5 |
| **Outcome / reason** | `v4_goodbye` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1548 ms |
| **p95 latency (stored)** | 2442 ms |
| **Max latency (stored)** | 2654 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 85.9442 ¢ |

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
| Latency p50 / p95 / max (total) | 1425 / 2654 / 2654 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1421 / 2650 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1422 / 2651 ms (5 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    954 ✅
tts_latency_ms:    955
total_latency_ms:  957 ✅
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

**Bot:** Guten Tag! Was kann ich für Sie tun?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    2650 ✅
tts_latency_ms:    2651
total_latency_ms:  2654 ✅
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

**User:** Ähm, ich wollte nur die genaue Adresse von Ihrem Restaurant wissen. Haben Sie die Adresse parat?

**Bot:** Guten Tag! Ich bin Sailly vom DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute unterstützen?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1421 ✅
tts_latency_ms:    1422
total_latency_ms:  1425 ✅
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

**User:** Hallo, Seily. Ich wollte nur wissen, wo genau sich euer Restaurant in Bonn befindet. Können Sie mir die Adresse sagen?

**Bot:** Entschuldigen Sie, die genaue Adresse habe ich leider gerade nicht verfügbar – aber Sie können diese gerne auf unserer Website finden oder mich fragen, wenn Sie noch andere Informationen benötigen!

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1592 ✅
tts_latency_ms:    1593
total_latency_ms:  1596 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          frustrated
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

**User:** Ach, schade. Aber vielen Dank. Dann schaue ich auf der Website nach.

**Bot:** Gerne helfe ich Ihnen weiter – unsere Adresse finden Sie auf unserer Website, oder Sie können mich direkt anrufen, um sie zu erfahren. Kann ich Sie noch bei etwas anderem unterstützen?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    1102 ✅
tts_latency_ms:    1102
total_latency_ms:  1106 ✅
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

**User:** Auf Wiederhören.

**Bot:** Sehr gerne, und vielen Dank, dass Sie angerufen haben – wir freuen uns auf Ihren Besuch bei DOBOO Korean Soulfood! Auf Wiedersehen!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 957 | 954 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 2654 | 2650 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 3 | 1425 | 1421 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 4 | 1596 | 1592 | 3 | None | — | 200 | info_neutral | frustrated | None | ai_greeting,get_date_info |  |
| 5 | 1106 | 1102 | 4 | None | — | 200 | info_neutral | neutral | None | end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo,
- **user** (turn 1): Ich wollte fragen, wo genau sich Ihr Restaurant befindet. Können Sie mir die Adresse sagen?
- **user** (turn 2): Ähm, ich wollte nur die genaue Adresse von Ihrem Restaurant wissen. Haben Sie die Adresse parat?
- **user** (turn 3): Hallo, Seily. Ich wollte nur wissen, wo genau sich euer Restaurant in Bonn befindet. Können Sie mir die Adresse sagen?
- **user** (turn 4): Ach, schade. Aber vielen Dank. Dann schaue ich auf der Website nach.
- **user** (turn 5): Auf Wiederhören.

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
        "customer_name": "Auf Wiederhören",
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
          "Guten Tag! Was kann ich für Sie tun?",
          "Guten Tag! Ich bin Sailly vom DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute unterstützen?",
          "Entschuldigen Sie, die genaue Adresse habe ich leider gerade nicht verfügbar – aber Sie können diese gerne auf unserer Website finden oder mich fragen, wenn Sie noch andere Informationen benötigen!",
          "Gerne helfe ich Ihnen weiter – unsere Adresse finden Sie auf unserer Website, oder Sie können mich direkt anrufen, um sie zu erfahren. Kann ich Sie noch bei etwas anderem unterstützen?",
          "Sehr gerne, und vielen Dank, dass Sie angerufen haben – wir freuen uns auf Ihren Besuch bei DOBOO Korean Soulfood! Auf Wiedersehen!"
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
            "bot": "Guten Tag! Was kann ich für Sie tun?",
            "node": "greeting",
            "customer": "Hallo,"
          },
          {
            "bot": "Guten Tag! Ich bin Sailly vom DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute unterstützen?",
            "node": "business_info",
            "customer": "Ähm, ich wollte nur die genaue Adresse von Ihrem Restaurant wissen. Haben Sie die Adresse parat?"
          },
          {
            "bot": "Entschuldigen Sie, die genaue Adresse habe ich leider gerade nicht verfügbar – aber Sie können diese gerne auf unserer Website finden oder mich fragen, wenn Sie noch andere Informationen benötigen!",
            "node": "business_info",
            "customer": "Hallo, Seily. Ich wollte nur wissen, wo genau sich euer Restaurant in Bonn befindet. Können Sie mir die Adresse sagen?"
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter – unsere Adresse finden Sie auf unserer Website, oder Sie können mich direkt anrufen, um sie zu erfahren. Kann ich Sie noch bei etwas anderem unterstützen?",
            "node": "greeting",
            "customer": "Ach, schade. Aber vielen Dank. Dann schaue ich auf der Website nach."
          },
          {
            "bot": "Sehr gerne, und vielen Dank, dass Sie angerufen haben – wir freuen uns auf Ihren Besuch bei DOBOO Korean Soulfood! Auf Wiedersehen!",
            "node": "goodbye",
            "customer": "Auf Wiederhören."
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
        "ai_greeting",
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
        "Guten Tag! Was kann ich für Sie tun?",
        "Guten Tag! Ich bin Sailly vom DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute unterstützen?",
        "Entschuldigen Sie, die genaue Adresse habe ich leider gerade nicht verfügbar – aber Sie können diese gerne auf unserer Website finden oder mich fragen, wenn Sie noch andere Informationen benötigen!",
        "Gerne helfe ich Ihnen weiter – unsere Adresse finden Sie auf unserer Website, oder Sie können mich direkt anrufen, um sie zu erfahren. Kann ich Sie noch bei etwas anderem unterstützen?",
        "Sehr gerne, und vielen Dank, dass Sie angerufen haben – wir freuen uns auf Ihren Besuch bei DOBOO Korean Soulfood! Auf Wiedersehen!"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-b3e1d1ca1586",
  "ended_at": "2026-05-01T08:38:30.456188+02:00",
  "started_at": "2026-05-01T08:37:31.059891+02:00",
  "started_ts": 1777617451.0599194,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Hallo,",
      "timestamp": "2026-05-01T08:37:35.410891+02:00"
    },
    {
      "role": "user",
      "text": "Ich wollte fragen, wo genau sich Ihr Restaurant befindet. Können Sie mir die Adresse sagen?",
      "timestamp": "2026-05-01T08:37:36.631494+02:00"
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=faq turn_type=start_intent locked=False (conf=0.90) profile=business_info reroute=True
Turn 3: intent=faq turn_type=start_intent locked=False (conf=0.90) profile=business_info reroute=True
Turn 4: intent=unknown turn_type=unclear locked=False (conf=0.90) profile=greeting reroute=True
Turn 5: intent=goodbye turn_type=finalize locked=True (conf=0.95) profile=goodbye reroute=True
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
