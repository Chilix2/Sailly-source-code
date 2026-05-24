# Sailly — Full Call Analysis Report
## Call ID: `demo-d8eff5e35be0`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-d8eff5e35be0` |
| **Caller / channel** | `[validation:A2_tool_tag_eilig]` |
| **Started** | 2026-05-01 06:54:03 UTC |
| **Ended** | 2026-05-01 06:55:05 UTC |
| **Duration** | **62 seconds (1:02 min)** |
| **Total DB turns** | 9 |
| **Outcome / reason** | `v4_goodbye` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1322 ms |
| **p95 latency (stored)** | 1693 ms |
| **Max latency (stored)** | 1718 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 91.7937 ¢ |

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
| Latency p50 / p95 / max (total) | 1267 / 1718 / 1718 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1260 / 1714 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1261 / 1715 ms (9 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1006 ✅
tts_latency_ms:    1006
total_latency_ms:  1011 ✅
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

**Bot:** Gerne helfe ich Ihnen weiter – worum geht es Ihnen heute?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    1104 ✅
tts_latency_ms:    1104
total_latency_ms:  1108 ✅
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

**Bot:** Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen – möchten Sie reservieren, Informationen zu uns erhalten oder etwas anderes wissen?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1266 ✅
tts_latency_ms:    1269
total_latency_ms:  1269 ✅
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

**User:** Ich hab nach der Adresse gefragt. Wo seid ihr genau?

**Bot:** Gerne helfe ich Ihnen weiter! Welches Anliegen haben Sie heute?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1653 ✅
tts_latency_ms:    1653
total_latency_ms:  1656 ✅
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

**User:** Schneller bitte. Ich hab keine Zeit für technische Probleme.

**Bot:** Entschuldigung, ich habe Ihre Frage zur Adresse leider nicht direkt beantwortet – könnten Sie mir Ihren Namen oder weitere Details geben, damit ich Ihnen besser helfen kann?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    1714 ✅
tts_latency_ms:    1715
total_latency_ms:  1718 ✅
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

**User:** Ich hab's schon zweimal gesagt.

**Bot:** Selbstverständlich – sagen Sie mir einfach, wie ich Sie schnell unterstützen kann, ob es um eine Reservierung, Bestellung oder Öffnungszeiten geht! Ich kümmere mich sofort darum.

---

### Turn 6

```
stt_latency_ms:    6
llm_latency_ms:    1260 ✅
tts_latency_ms:    1261
total_latency_ms:  1267 ✅
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

**User:** Die Adresse

**Bot:** Entschuldigung – ich möchte Ihnen wirklich helfen! Können Sie mir bitte kurz sagen, was genau Sie benötigen – Reservierung, Bestellung oder eine andere Information?

---

### Turn 7

```
stt_latency_ms:    4
llm_latency_ms:    1518 ✅
tts_latency_ms:    1519
total_latency_ms:  1522 ✅
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

**User:** Ich brauch nur die genaue Adresse, sonst nichts.

**Bot:** Gerne helfe ich Ihnen mit unserer Adresse weiter – DOBOO Korean Soulfood finden Sie in der Bonngasse 1, 53111 Bonn. Kann ich Sie sonst noch bei etwas unterstützen?

---

### Turn 8

```
stt_latency_ms:    4
llm_latency_ms:    1185 ✅
tts_latency_ms:    1186
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

**User:** Können Sie mir die einfach geben?

**Bot:** Sehr gerne – Sie finden uns unter Bonngasse 1, 53111 Bonn. Falls Sie noch Fragen haben, helfe ich gerne weiter!

---

### Turn 9

```
stt_latency_ms:    3
llm_latency_ms:    1156 ✅
tts_latency_ms:    1156
total_latency_ms:  1160 ✅
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

**User:** Danke, das war's.

**Bot:** Gerne geschehen – wir freuen uns auf Ihren Besuch bei DOBOO! Auf Wiedersehen und viel Spaß beim Essen!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1011 | 1006 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1108 | 1104 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1269 | 1266 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1656 | 1653 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1718 | 1714 | 4 | None | — | 200 | info_neutral | impatient | None | ai_greeting,get_date_info |  |
| 6 | 1267 | 1260 | 6 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1522 | 1518 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 8 | 1190 | 1185 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 9 | 1160 | 1156 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo,
- **user** (turn 1): Wo befindet sich euer Restaurant genau? Ich hab's eilig.
- **user** (turn 2): Hallo,
- **user** (turn 3): Ich hab nach der Adresse gefragt. Wo seid ihr genau?
- **user** (turn 4): Schneller bitte. Ich hab keine Zeit für technische Probleme.
- **user** (turn 5): Ich hab's schon zweimal gesagt.
- **user** (turn 6): Die Adresse
- **user** (turn 7): Ich brauch nur die genaue Adresse, sonst nichts.
- **user** (turn 8): Können Sie mir die einfach geben?
- **user** (turn 9): Danke, das war's.

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
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute helfen?",
          "Gerne helfe ich Ihnen weiter – worum geht es Ihnen heute?",
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen – möchten Sie reservieren, Informationen zu uns erhalten oder etwas anderes wissen?",
          "Gerne helfe ich Ihnen weiter! Welches Anliegen haben Sie heute?",
          "Entschuldigung, ich habe Ihre Frage zur Adresse leider nicht direkt beantwortet – könnten Sie mir Ihren Namen oder weitere Details geben, damit ich Ihnen besser helfen kann?",
          "Selbstverständlich – sagen Sie mir einfach, wie ich Sie schnell unterstützen kann, ob es um eine Reservierung, Bestellung oder Öffnungszeiten geht! Ich kümmere mich sofort darum.",
          "Entschuldigung – ich möchte Ihnen wirklich helfen! Können Sie mir bitte kurz sagen, was genau Sie benötigen – Reservierung, Bestellung oder eine andere Information?",
          "Gerne helfe ich Ihnen mit unserer Adresse weiter – DOBOO Korean Soulfood finden Sie in der Bonngasse 1, 53111 Bonn. Kann ich Sie sonst noch bei etwas unterstützen?",
          "Sehr gerne – Sie finden uns unter Bonngasse 1, 53111 Bonn. Falls Sie noch Fragen haben, helfe ich gerne weiter!",
          "Gerne geschehen – wir freuen uns auf Ihren Besuch bei DOBOO! Auf Wiedersehen und viel Spaß beim Essen!"
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
            "bot": "Selbstverständlich – sagen Sie mir einfach, wie ich Sie schnell unterstützen kann, ob es um eine Reservierung, Bestellung oder Öffnungszeiten geht! Ich kümmere mich sofort darum.",
            "node": "greeting",
            "customer": "Ich hab's schon zweimal gesagt."
          },
          {
            "bot": "Entschuldigung – ich möchte Ihnen wirklich helfen! Können Sie mir bitte kurz sagen, was genau Sie benötigen – Reservierung, Bestellung oder eine andere Information?",
            "node": "greeting",
            "customer": "Die Adresse"
          },
          {
            "bot": "Gerne helfe ich Ihnen mit unserer Adresse weiter – DOBOO Korean Soulfood finden Sie in der Bonngasse 1, 53111 Bonn. Kann ich Sie sonst noch bei etwas unterstützen?",
            "node": "greeting",
            "customer": "Ich brauch nur die genaue Adresse, sonst nichts."
          },
          {
            "bot": "Sehr gerne – Sie finden uns unter Bonngasse 1, 53111 Bonn. Falls Sie noch Fragen haben, helfe ich gerne weiter!",
            "node": "greeting",
            "customer": "Können Sie mir die einfach geben?"
          },
          {
            "bot": "Gerne geschehen – wir freuen uns auf Ihren Besuch bei DOBOO! Auf Wiedersehen und viel Spaß beim Essen!",
            "node": "greeting",
            "customer": "Danke, das war's."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Hallo,...' [greeting] Kunde: 'Hallo,...' [greeting] Kunde: 'Ich hab nach der Adresse gefragt. Wo seid ihr genau?...' [greeting] Kunde: 'Schneller bitte. Ich hab keine Zeit für technische Probleme....'",
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
        "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute helfen?",
        "Gerne helfe ich Ihnen weiter – worum geht es Ihnen heute?",
        "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen – möchten Sie reservieren, Informationen zu uns erhalten oder etwas anderes wissen?",
        "Gerne helfe ich Ihnen weiter! Welches Anliegen haben Sie heute?",
        "Entschuldigung, ich habe I
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 4: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 5: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 6: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 7: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 8: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 9: intent=greeting turn_type=finalize locked=True (conf=0.90) profile=greeting reroute=False
Turn 10: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 11: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 12: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 13: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 14: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 15: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 16: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
