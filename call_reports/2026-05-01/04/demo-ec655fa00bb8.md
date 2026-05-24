# Sailly — Full Call Analysis Report
## Call ID: `demo-ec655fa00bb8`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-ec655fa00bb8` |
| **Caller / channel** | `[validation:A1_greeting_eilig]` |
| **Started** | 2026-05-01 04:59:37 UTC |
| **Ended** | 2026-05-01 05:00:37 UTC |
| **Duration** | **59 seconds (0:59 min)** |
| **Total DB turns** | 6 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 2325 ms |
| **p95 latency (stored)** | 6151 ms |
| **Max latency (stored)** | 7589 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 85.9502 ¢ |

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
| Latency p50 / p95 / max (total) | 1145 / 7589 / 7589 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1243 / 7578 ms | From `llm_latency_ms` column |
| STT p50 | 10 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1243 / 7578 ms (6 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1142 ✅
tts_latency_ms:    1142
total_latency_ms:  1145 ✅
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

**User:** Was kann ich für Sie tun?

**Bot:** Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – wie kann ich Ihnen heute helfen?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    1243 ✅
tts_latency_ms:    1243
total_latency_ms:  1247 ✅
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

**User:** Kein Problem, ich warte.

**Bot:** Entschuldigung, ich glaube da ist ein kleines Missverständnis – ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood. Wie kann ich Ihnen heute helfen?

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    1079 ✅
tts_latency_ms:    1079
total_latency_ms:  1083 ✅
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

**User:** Lassen Sie sich Zeit.

**Bot:** Gerne helfe ich Ihnen weiter – worüber kann ich Sie heute informieren?

---

### Turn 4

```
stt_latency_ms:    59
llm_latency_ms:    1777 ✅
tts_latency_ms:    1778
total_latency_ms:  1837 ✅
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

**User:** Alles gut, ich bin hier.

**Bot:** Danke der Nachfrage, Herr Hier! Wie kann ich Sie heute bei DOBOO Korean Soulfood unterstützen?

---

### Turn 5

```
stt_latency_ms:    10
llm_latency_ms:    1036 ✅
tts_latency_ms:    1037
total_latency_ms:  1047 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          relaxed
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

**User:** Sagen Sie einfach Bescheid, wenn Sie so weit sind.

**Bot:** Gerne helfe ich Ihnen weiter – möchten Sie eine Bestellung aufgeben oder haben Sie eine Frage zu uns?

---

### Turn 6

```
stt_latency_ms:    11
llm_latency_ms:    7578 ⚠️
tts_latency_ms:    7578
total_latency_ms:  7589 ⚠️
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

**User:** Gerne, kein Problem.

**Bot:** Ich bin bereit – möchten Sie gerne eine Bestellung aufgeben oder haben Sie Fragen zu DOBOO Korean Soulfood?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1145 | 1142 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1247 | 1243 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1083 | 1079 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1837 | 1777 | 59 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1047 | 1036 | 10 | None | — | 200 | info_neutral | relaxed | None | ai_greeting,get_date_info |  |
| 6 | 7589 | 7578 | 11 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Was kann ich für Sie tun?
- **user** (turn 1): Kein Problem, ich warte.
- **user** (turn 2): Lassen Sie sich Zeit.
- **user** (turn 3): Alles gut, ich bin hier.
- **user** (turn 4): Sagen Sie einfach Bescheid, wenn Sie so weit sind.
- **user** (turn 5): Gerne, kein Problem.

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
        "first_name": "Hier",
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
          "Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – wie kann ich Ihnen heute helfen?",
          "Entschuldigung, ich glaube da ist ein kleines Missverständnis – ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood. Wie kann ich Ihnen heute helfen?",
          "Gerne helfe ich Ihnen weiter – worüber kann ich Sie heute informieren?",
          "Danke der Nachfrage, Herr Hier! Wie kann ich Sie heute bei DOBOO Korean Soulfood unterstützen?",
          "Gerne helfe ich Ihnen weiter – möchten Sie eine Bestellung aufgeben oder haben Sie eine Frage zu uns?",
          "Ich bin bereit – möchten Sie gerne eine Bestellung aufgeben oder haben Sie Fragen zu DOBOO Korean Soulfood?"
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
            "bot": "Entschuldigung, ich glaube da ist ein kleines Missverständnis – ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood. Wie kann ich Ihnen heute helfen?",
            "node": "greeting",
            "customer": "Kein Problem, ich warte."
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter – worüber kann ich Sie heute informieren?",
            "node": "greeting",
            "customer": "Lassen Sie sich Zeit."
          },
          {
            "bot": "Danke der Nachfrage, Herr Hier! Wie kann ich Sie heute bei DOBOO Korean Soulfood unterstützen?",
            "node": "greeting",
            "customer": "Alles gut, ich bin hier."
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter – möchten Sie eine Bestellung aufgeben oder haben Sie eine Frage zu uns?",
            "node": "greeting",
            "customer": "Sagen Sie einfach Bescheid, wenn Sie so weit sind."
          },
          {
            "bot": "Ich bin bereit – möchten Sie gerne eine Bestellung aufgeben oder haben Sie Fragen zu DOBOO Korean Soulfood?",
            "node": "greeting",
            "customer": "Gerne, kein Problem."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Was kann ich für Sie tun?...'",
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
        "Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – wie kann ich Ihnen heute helfen?",
        "Entschuldigung, ich glaube da ist ein kleines Missverständnis – ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood. Wie kann ich Ihnen heute helfen?",
        "Gerne helfe ich Ihnen weiter – worüber kann ich Sie heute informieren?",
        "Danke der Nachfrage, Herr Hier! Wie kann ich Sie heute bei DOBOO Korean Soulfood unterstützen?",
        "Gerne helfe ich Ihnen weiter – möchten Sie eine Bestellung aufgeben oder haben Sie eine Frage zu uns?",
        "Ich bin bereit – möchten Sie gerne eine Bestellung aufgeben oder haben Sie Fragen zu DOBOO Korean Soulfood?"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-ec655fa00bb8",
  "ended_at": "2026-05-01T07:00:37.773685+02:00",
  "started_at": "2026-05-01T06:59:37.892737+02:00",
  "started_ts": 1777611577.892747,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Was kann ich für Sie tun?",
      "timestamp": "2026-05-01T06:59:46.639923+02:00"
    },
    {
      "role": "user",
      "text": "Kein Problem, ich warte.",
      "timestamp": "2026-05-01T06:59:59.440234+02:00"
    },
    {
      "role": "user",
      "text": "Lassen Sie sich Zeit.",
      "timestamp": "2026-05-01T07:00:00.935865+02:00"
    },
    {
      "role": "user",
      "text": "Alles gut, ich bin hier.",
      "timestamp": "2026-
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
Turn 6: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
