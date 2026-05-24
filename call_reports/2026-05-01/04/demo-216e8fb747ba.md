# Sailly — Full Call Analysis Report
## Call ID: `demo-216e8fb747ba`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-216e8fb747ba` |
| **Caller / channel** | `[validation:A2_faq_hours_froehlich]` |
| **Started** | 2026-05-01 04:57:03 UTC |
| **Ended** | 2026-05-01 04:58:13 UTC |
| **Duration** | **69 seconds (1:09 min)** |
| **Total DB turns** | 5 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1558 ms |
| **p95 latency (stored)** | 1726 ms |
| **Max latency (stored)** | 1729 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 100.0925 ¢ |

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
| Latency p50 / p95 / max (total) | 1621 / 1729 / 1729 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1617 / 1718 ms | From `llm_latency_ms` column |
| STT p50 | 7 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1617 / 1719 ms (5 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1113 ✅
tts_latency_ms:    1114
total_latency_ms:  1121 ✅
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

**User:** Wir freuen uns, von Ihnen zu hören.

**Bot:** Guten Tag! Wie kann ich Sie heute bei DOBOO Korean Soulfood unterstützen?

---

### Turn 2

```
stt_latency_ms:    10
llm_latency_ms:    1718 ✅
tts_latency_ms:    1719
total_latency_ms:  1729 ✅
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
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Hallo, guten Tag. Wir haben ja herrlich Wetter heute, oder?

**Bot:** Das Wetter heute ist Klar mit 8.9°C. Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute helfen?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1617 ✅
tts_latency_ms:    1617
total_latency_ms:  1621 ✅
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

**User:** Ich wollte fragen, wann Sie geöffnet haben.

**Bot:** Ja, heute ist ein schöner Freitag! Womit kann ich Sie bei DOBOO Korean Soulfood unterstützen?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1604 ✅
tts_latency_ms:    1604
total_latency_ms:  1607 ✅
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

**User:** Danke, ich warte gerne. Kein Problem.

**Bot:** Entschuldigen Sie, ich habe Ihre Frage zu den Öffnungszeiten überhört – können Sie mir sagen, für welchen Tag Sie die Öffnungszeiten von DOBOO Korean Soulfood benötigen?

---

### Turn 5

```
stt_latency_ms:    18
llm_latency_ms:    1694 ✅
tts_latency_ms:    1695
total_latency_ms:  1713 ✅
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

**Bot:** Vielen Dank für Ihre Geduld! Für welchen Tag möchten Sie die Öffnungszeiten von DOBOO Korean Soulfood wissen – für heute Freitag oder einen anderen Tag?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1121 | 1113 | 7 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1729 | 1718 | 10 | None | — | 200 | info_neutral | neutral | None | get_date_info,get_weather |  |
| 3 | 1621 | 1617 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 4 | 1607 | 1604 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1713 | 1694 | 18 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Wir freuen uns, von Ihnen zu hören.
- **user** (turn 1): Hallo, guten Tag. Wir haben ja herrlich Wetter heute, oder?
- **user** (turn 2): Ich wollte fragen, wann Sie geöffnet haben.
- **user** (turn 3): Danke, ich warte gerne. Kein Problem.
- **user** (turn 4): Lassen Sie sich Zeit.

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
          "Guten Tag! Wie kann ich Sie heute bei DOBOO Korean Soulfood unterstützen?",
          "Das Wetter heute ist Klar mit 8.9°C. Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute helfen?",
          "Ja, heute ist ein schöner Freitag! Womit kann ich Sie bei DOBOO Korean Soulfood unterstützen?",
          "Entschuldigen Sie, ich habe Ihre Frage zu den Öffnungszeiten überhört – können Sie mir sagen, für welchen Tag Sie die Öffnungszeiten von DOBOO Korean Soulfood benötigen?",
          "Vielen Dank für Ihre Geduld! Für welchen Tag möchten Sie die Öffnungszeiten von DOBOO Korean Soulfood wissen – für heute Freitag oder einen anderen Tag?"
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
            "bot": "Guten Tag! Wie kann ich Sie heute bei DOBOO Korean Soulfood unterstützen?",
            "node": "greeting",
            "customer": "Wir freuen uns, von Ihnen zu hören."
          },
          {
            "bot": "Das Wetter heute ist Klar mit 8.9°C. Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute helfen?",
            "node": "business_info",
            "customer": "Hallo, guten Tag. Wir haben ja herrlich Wetter heute, oder?"
          },
          {
            "bot": "Ja, heute ist ein schöner Freitag! Womit kann ich Sie bei DOBOO Korean Soulfood unterstützen?",
            "node": "business_info",
            "customer": "Ich wollte fragen, wann Sie geöffnet haben."
          },
          {
            "bot": "Entschuldigen Sie, ich habe Ihre Frage zu den Öffnungszeiten überhört – können Sie mir sagen, für welchen Tag Sie die Öffnungszeiten von DOBOO Korean Soulfood benötigen?",
            "node": "greeting",
            "customer": "Danke, ich warte gerne. Kein Problem."
          },
          {
            "bot": "Vielen Dank für Ihre Geduld! Für welchen Tag möchten Sie die Öffnungszeiten von DOBOO Korean Soulfood wissen – für heute Freitag oder einen anderen Tag?",
            "node": "greeting",
            "customer": "Lassen Sie sich Zeit."
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
        "get_weather",
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
        "Guten Tag! Wie kann ich Sie heute bei DOBOO Korean Soulfood unterstützen?",
        "Das Wetter heute ist Klar mit 8.9°C. Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute helfen?",
        "Ja, heute ist ein schöner Freitag! Womit kann ich Sie bei DOBOO Korean Soulfood unterstützen?",
        "Entschuldigen Sie, ich habe Ihre Frage zu den Öffnungszeiten überhört – können Sie mir sagen, für welchen Tag Sie die Öffnungszeiten von DOBOO Korean Soulfood benötigen?",
        "Vielen Dank für Ihre Geduld! Für welchen Tag möchten Sie die Öffnungszeiten von DOBOO Korean Soulfood wissen – für heute Freitag oder einen anderen Tag?"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-216e8fb747ba",
  "ended_at": "2026-05-01T06:58:13.214467+02:00",
  "started_at": "2026-05-01T06:57:03.878219+02:00",
  "started_ts": 1777611423.8782248,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Wir freuen uns, von Ihnen zu hören.",
      "timestamp": "2026-05-01T06:57:14.089878+02:00"
    },
    {
      "role": "user",
      "text": "Hallo, guten Tag. Wir haben ja herrlich Wetter heute, oder?",
      "timestamp": "2026-05-01T06:57:33.723305+02:00"
    },
    {
      "role": "user",
      "text": "Ich wollte fragen, wann Sie geöffnet haben.",
      "timestamp": "2026-05-01T06:57:35.510112+02:00"
    },
    {
      "role": "user",
      "text": "Danke, ich warte gerne. Kein Problem
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
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
