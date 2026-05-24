# Sailly — Full Call Analysis Report
## Call ID: `demo-d4de0461c87c`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-d4de0461c87c` |
| **Caller / channel** | `[validation:A4_basic_order_aeltere_person]` |
| **Started** | 2026-05-01 04:57:04 UTC |
| **Ended** | 2026-05-01 04:58:01 UTC |
| **Duration** | **57 seconds (0:57 min)** |
| **Total DB turns** | 5 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1169 ms |
| **p95 latency (stored)** | 1474 ms |
| **Max latency (stored)** | 1526 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 82.9585 ¢ |

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
| Latency p50 / p95 / max (total) | 1062 / 1526 / 1526 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1055 / 1521 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1056 / 1522 ms (5 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    7
llm_latency_ms:    1055 ✅
tts_latency_ms:    1056
total_latency_ms:  1062 ✅
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

**User:** Gutani ist das Dobu Restaurant. Wie kann ich Ihnen helfen?

**Bot:** Willkommen bei DOBOO Korean Soulfood in Bonn! Woran kann ich Sie heute helfen?

---

### Turn 2

```
stt_latency_ms:    4
llm_latency_ms:    1030 ✅
tts_latency_ms:    1031
total_latency_ms:  1035 ✅
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

**User:** Möchten Sie etwas bestellen oder haben Sie eine Frage?

**Bot:** Vielen Dank für Ihren Anruf bei DOBOO Korean Soulfood! Wie kann ich Ihnen heute weiterhelfen – möchten Sie einen Tisch reservieren oder haben Sie eine Frage zu unserem Restaurant?

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    955 ✅
tts_latency_ms:    955
total_latency_ms:  959 ✅
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

**User:** Kein Problem. Ich warte gerne.

**Bot:** Gerne helfe ich Ihnen weiter – was kann ich für Sie tun?

---

### Turn 4

```
stt_latency_ms:    5
llm_latency_ms:    1521 ✅
tts_latency_ms:    1522
total_latency_ms:  1526 ✅
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

**User:** Was möchten Sie denn bestellen?

**Bot:** Vielen Dank für Ihre Geduld! Wie kann ich Ihnen heute bei DOBOO Korean Soulfood helfen – möchten Sie einen Tisch reservieren oder haben Sie eine Frage zu uns?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    1260 ✅
tts_latency_ms:    1260
total_latency_ms:  1264 ✅
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

**User:** In Ordnung. Lassen Sie sich Zeit.

**Bot:** Entschuldigung, ich habe Sie falsch verstanden – möchten Sie gerne eine Bestellung aufgeben oder einen Tisch bei uns reservieren?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1062 | 1055 | 7 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1035 | 1030 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 959 | 955 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1526 | 1521 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1264 | 1260 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Gutani ist das Dobu Restaurant. Wie kann ich Ihnen helfen?
- **user** (turn 1): Möchten Sie etwas bestellen oder haben Sie eine Frage?
- **user** (turn 2): Kein Problem. Ich warte gerne.
- **user** (turn 3): Was möchten Sie denn bestellen?
- **user** (turn 4): In Ordnung. Lassen Sie sich Zeit.

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
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Woran kann ich Sie heute helfen?",
          "Vielen Dank für Ihren Anruf bei DOBOO Korean Soulfood! Wie kann ich Ihnen heute weiterhelfen – möchten Sie einen Tisch reservieren oder haben Sie eine Frage zu unserem Restaurant?",
          "Gerne helfe ich Ihnen weiter – was kann ich für Sie tun?",
          "Vielen Dank für Ihre Geduld! Wie kann ich Ihnen heute bei DOBOO Korean Soulfood helfen – möchten Sie einen Tisch reservieren oder haben Sie eine Frage zu uns?",
          "Entschuldigung, ich habe Sie falsch verstanden – möchten Sie gerne eine Bestellung aufgeben oder einen Tisch bei uns reservieren?"
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
            "bot": "Willkommen bei DOBOO Korean Soulfood in Bonn! Woran kann ich Sie heute helfen?",
            "node": "greeting",
            "customer": "Gutani ist das Dobu Restaurant. Wie kann ich Ihnen helfen?"
          },
          {
            "bot": "Vielen Dank für Ihren Anruf bei DOBOO Korean Soulfood! Wie kann ich Ihnen heute weiterhelfen – möchten Sie einen Tisch reservieren oder haben Sie eine Frage zu unserem Restaurant?",
            "node": "greeting",
            "customer": "Möchten Sie etwas bestellen oder haben Sie eine Frage?"
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter – was kann ich für Sie tun?",
            "node": "greeting",
            "customer": "Kein Problem. Ich warte gerne."
          },
          {
            "bot": "Vielen Dank für Ihre Geduld! Wie kann ich Ihnen heute bei DOBOO Korean Soulfood helfen – möchten Sie einen Tisch reservieren oder haben Sie eine Frage zu uns?",
            "node": "greeting",
            "customer": "Was möchten Sie denn bestellen?"
          },
          {
            "bot": "Entschuldigung, ich habe Sie falsch verstanden – möchten Sie gerne eine Bestellung aufgeben oder einen Tisch bei uns reservieren?",
            "node": "greeting",
            "customer": "In Ordnung. Lassen Sie sich Zeit."
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
        "Willkommen bei DOBOO Korean Soulfood in Bonn! Woran kann ich Sie heute helfen?",
        "Vielen Dank für Ihren Anruf bei DOBOO Korean Soulfood! Wie kann ich Ihnen heute weiterhelfen – möchten Sie einen Tisch reservieren oder haben Sie eine Frage zu unserem Restaurant?",
        "Gerne helfe ich Ihnen weiter – was kann ich für Sie tun?",
        "Vielen Dank für Ihre Geduld! Wie kann ich Ihnen heute bei DOBOO Korean Soulfood helfen – möchten Sie einen Tisch reservieren oder haben Sie eine Frage zu uns?",
        "Entschuldigung, ich habe Sie falsch verstanden – möchten Sie gerne eine Bestellung aufgeben oder einen Tisch bei uns reservieren?"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-d4de0461c87c",
  "ended_at": "2026-05-01T06:58:01.352481+02:00",
  "started_at": "2026-05-01T06:57:04.190046+02:00",
  "started_ts": 1777611424.1900606,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Gutani ist das Dobu Restaurant. Wie kann ich Ihnen helfen?",
      "timestamp": "2026-05-01T06:57:22.196052+02:00"
    },
    {
      "role": "user",
      "text": "Möchten Sie etwas bestellen oder haben Sie eine Frage?",
      "timestamp": "2026-05-01T06:57:23.470294+02:00"
    },
    {
      "role": "user",
      "text": "Kein Problem. Ich warte gerne.",
      "timestamp": "2026-05-01T06:57:34.439877+02:00"
    },
    {
      "role": "user",
      "text": "Was möchten Sie denn bestellen?",
      "timestamp": "2026-05-01
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 2: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 3: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 4: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 5: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
