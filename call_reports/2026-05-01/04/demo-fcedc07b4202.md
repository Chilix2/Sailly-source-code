# Sailly — Full Call Analysis Report
## Call ID: `demo-fcedc07b4202`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-fcedc07b4202` |
| **Caller / channel** | `[validation:A1_greeting_neutral]` |
| **Started** | 2026-05-01 04:59:37 UTC |
| **Ended** | 2026-05-01 05:00:48 UTC |
| **Duration** | **70 seconds (1:10 min)** |
| **Total DB turns** | 5 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1372 ms |
| **p95 latency (stored)** | 1719 ms |
| **Max latency (stored)** | 1762 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 101.7203 ¢ |

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
| Latency p50 / p95 / max (total) | 1403 / 1762 / 1762 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1310 / 1758 ms | From `llm_latency_ms` column |
| STT p50 | 5 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1310 / 1759 ms (5 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1017 ✅
tts_latency_ms:    1018
total_latency_ms:  1023 ✅
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

**User:** Ich rufe an, um mich nach den Öffnungszeiten zu erkundigen.

**Bot:** Guten Tag! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?

---

### Turn 2

```
stt_latency_ms:    6
llm_latency_ms:    1538 ✅
tts_latency_ms:    1539
total_latency_ms:  1545 ✅
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

**User:** Können Sie -- Danke, ich warte.

**Bot:** Gerne! Unsere Öffnungszeiten finden Sie auf unserer Website oder Sie können uns direkt anrufen – leider habe ich die genauen Zeiten gerade nicht zur Hand, aber ich helfe Ihnen sehr gerne weiter!

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    1120 ✅
tts_latency_ms:    1121
total_latency_ms:  1125 ✅
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

**User:** Können Sie mir sagen, ob Sie heute geöffnet haben?

**Bot:** Heute ist Freitag, der 1. Mai 2026 – wie kann ich Sie sonst noch unterstützen?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1758 ✅
tts_latency_ms:    1759
total_latency_ms:  1762 ✅
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

**User:** Alles klar, ich warte. Ich melde mich dann wieder bei Ihnen.

**Bot:** Entschuldigung, meine vorherige Antwort war nicht hilfreich – leider habe ich keinen Zugriff auf unsere aktuellen Öffnungszeiten. Können Sie mich bitte kurz mit unserer Filiale verbinden, damit wir Ihre Frage klären können?

---

### Turn 5

```
stt_latency_ms:    93
llm_latency_ms:    1310 ✅
tts_latency_ms:    1310
total_latency_ms:  1403 ✅
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

**User:** Vielen Dank für die Auskunft. Dann versuche ich es vielleicht später noch einmal. Einen schönen Tag noch.

**Bot:** Sehr gerne, ich freue mich auf Ihren Anruf! Auf Wiedersehen und vielen Dank, dass Sie sich bei uns gemeldet haben.

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1023 | 1017 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1545 | 1538 | 6 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1125 | 1120 | 4 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 4 | 1762 | 1758 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1403 | 1310 | 93 | None | — | 200 | info_neutral | neutral | None | end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Ich rufe an, um mich nach den Öffnungszeiten zu erkundigen.
- **user** (turn 1): Können Sie -- Danke, ich warte.
- **user** (turn 2): Können Sie mir sagen, ob Sie heute geöffnet haben?
- **user** (turn 3): Alles klar, ich warte. Ich melde mich dann wieder bei Ihnen.
- **user** (turn 4): Vielen Dank für die Auskunft. Dann versuche ich es vielleicht später noch einmal. Einen schönen Tag noch.

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
        "caller_id_phone": null,
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
          "Guten Tag! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?",
          "Gerne! Unsere Öffnungszeiten finden Sie auf unserer Website oder Sie können uns direkt anrufen – leider habe ich die genauen Zeiten gerade nicht zur Hand, aber ich helfe Ihnen sehr gerne weiter!",
          "Heute ist Freitag, der 1. Mai 2026 – wie kann ich Sie sonst noch unterstützen?",
          "Entschuldigung, meine vorherige Antwort war nicht hilfreich – leider habe ich keinen Zugriff auf unsere aktuellen Öffnungszeiten. Können Sie mich bitte kurz mit unserer Filiale verbinden, damit wir Ihre Frage klären können?",
          "Sehr gerne, ich freue mich auf Ihren Anruf! Auf Wiedersehen und vielen Dank, dass Sie sich bei uns gemeldet haben."
        ],
        "reservation_date": "2026-05-01",
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
            "bot": "Guten Tag! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?",
            "node": "greeting",
            "customer": "Ich rufe an, um mich nach den Öffnungszeiten zu erkundigen."
          },
          {
            "bot": "Gerne! Unsere Öffnungszeiten finden Sie auf unserer Website oder Sie können uns direkt anrufen – leider habe ich die genauen Zeiten gerade nicht zur Hand, aber ich helfe Ihnen sehr gerne weiter!",
            "node": "greeting",
            "customer": "Können Sie -- Danke, ich warte."
          },
          {
            "bot": "Heute ist Freitag, der 1. Mai 2026 – wie kann ich Sie sonst noch unterstützen?",
            "node": "business_info",
            "customer": "Können Sie mir sagen, ob Sie heute geöffnet haben?"
          },
          {
            "bot": "Entschuldigung, meine vorherige Antwort war nicht hilfreich – leider habe ich keinen Zugriff auf unsere aktuellen Öffnungszeiten. Können Sie mich bitte kurz mit unserer Filiale verbinden, damit wir Ihre Frage klären können?",
            "node": "greeting",
            "customer": "Alles klar, ich warte. Ich melde mich dann wieder bei Ihnen."
          },
          {
            "bot": "Sehr gerne, ich freue mich auf Ihren Anruf! Auf Wiedersehen und vielen Dank, dass Sie sich bei uns gemeldet haben.",
            "node": "goodbye",
            "customer": "Vielen Dank für die Auskunft. Dann versuche ich es vielleicht später noch einmal. Einen schönen Tag noch."
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
        "Guten Tag! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?",
        "Gerne! Unsere Öffnungszeiten finden Sie auf unserer Website oder Sie können uns direkt anrufen – leider habe ich die genauen Zeiten gerade nicht zur Hand, aber ich helfe Ihnen sehr gerne weiter!",
        "Heute ist Freitag, der 1. Mai 2026 – wie kann ich Sie sonst noch unterstützen?",
        "Entschuldigung, meine vorherige Antwort war nicht hilfreich – leider habe ich keinen Zugriff auf unsere aktuellen Öffnungszeiten. Können Sie mich bitte kurz mit unserer Filiale verbinden, damit wir Ihre Frage klären können?",
        "Sehr gerne, ich freue mich auf Ihren Anruf! Auf Wiedersehen und vielen Dank, dass Sie sich bei uns gemeldet haben."
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-fcedc07b4202",
  "ended_at": "2026-05-01T07:00:48.021871+02:00",
  "started_at": "2026-05-01T06:59:37.892926+02:00",
  "started_ts": 1777611577.8929317,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Ich rufe an, um mich nach den Öffnungszeiten zu erkundigen.",
      "timestamp": "2026-05-01T06:59:46.709786+02:00"
    },
    {
      "role": "user",
      "text": "Können Sie -- Danke, ich warte.",
      "timest
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
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
