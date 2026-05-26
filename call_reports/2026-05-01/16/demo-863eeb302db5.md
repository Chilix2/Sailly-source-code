# Sailly — Full Call Analysis Report
## Call ID: `demo-863eeb302db5`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-863eeb302db5` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-05-01 16:47:12 UTC |
| **Ended** | 2026-05-01 16:47:59 UTC |
| **Duration** | **46 seconds (0:46 min)** |
| **Total DB turns** | 6 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 8 ms |
| **p95 latency (stored)** | 11 ms |
| **Max latency (stored)** | 11 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 66.2163 ¢ |

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
| Latency p50 / p95 / max (total) | 7 / 11 / 11 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 5 / 7 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 5 / 7 ms (6 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    6 ✅
tts_latency_ms:    6
total_latency_ms:  10 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
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

**User:** Reservierung für zwei Personen.

**Bot:** Für welchen Tag möchten Sie reservieren?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    4 ✅
tts_latency_ms:    4
total_latency_ms:  7 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
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

**User:** In zwei Wochen.

**Bot:** Für welchen Tag möchten Sie reservieren?

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    7 ✅
tts_latency_ms:    7
total_latency_ms:  11 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
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

**User:** Muss ich Ihnen genau 'n Tag sagen?

**Bot:** Für welchen Tag möchten Sie reservieren?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    5 ✅
tts_latency_ms:    5
total_latency_ms:  8 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
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

**User:** Okay, dann zehnter Mal.

**Bot:** Für welchen Tag möchten Sie reservieren?

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    4 ✅
tts_latency_ms:    4
total_latency_ms:  7 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
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

**User:** Zwei Wochen.

**Bot:** Für welchen Tag möchten Sie reservieren?

---

### Turn 6

```
stt_latency_ms:    2
llm_latency_ms:    4 ✅
tts_latency_ms:    4
total_latency_ms:  7 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
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

**User:** They upload them? Yeah.

**Bot:** Für welchen Tag möchten Sie reservieren?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 10 | 6 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 2 | 7 | 4 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 3 | 11 | 7 | 4 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 4 | 8 | 5 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 5 | 7 | 4 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 6 | 7 | 4 | 2 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Reservierung für zwei Personen.
- **user** (turn 1): In zwei Wochen.
- **user** (turn 2): Muss ich Ihnen genau 'n Tag sagen?
- **user** (turn 3): Okay, dann zehnter Mal.
- **user** (turn 4): Zwei Wochen.
- **user** (turn 5): They upload them? Yeah.

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
        "customer_name": "Zwei Wochen",
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": null,
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute helfen?",
          "Für welchen Tag möchten Sie reservieren?",
          "Für welchen Tag möchten Sie reservieren?",
          "Für welchen Tag möchten Sie reservieren?",
          "Für welchen Tag möchten Sie reservieren?",
          "Für welchen Tag möchten Sie reservieren?",
          "Für welchen Tag möchten Sie reservieren?"
        ],
        "reservation_date": null,
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
            "bot": "Für welchen Tag möchten Sie reservieren?",
            "node": "reservation_start",
            "customer": "In zwei Wochen."
          },
          {
            "bot": "Für welchen Tag möchten Sie reservieren?",
            "node": "reservation_start",
            "customer": "Muss ich Ihnen genau 'n Tag sagen?"
          },
          {
            "bot": "Für welchen Tag möchten Sie reservieren?",
            "node": "reservation_start",
            "customer": "Okay, dann zehnter Mal."
          },
          {
            "bot": "Für welchen Tag möchten Sie reservieren?",
            "node": "reservation_start",
            "customer": "Zwei Wochen."
          },
          {
            "bot": "Für welchen Tag möchten Sie reservieren?",
            "node": "reservation_start",
            "customer": "They upload them? Yeah."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [reservation_start] Kunde: 'Reservierung für zwei Personen....'",
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
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
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
        "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute helfen?",
        "Für welchen Tag möchten Sie reservieren?",
        "Für welchen Tag möchten Sie reservieren?",
        "Für welchen Tag möchten Sie reservieren?",
        "Für welchen Tag möchten Sie reservieren?",
        "Für welchen Tag möchten Sie reservieren?",
        "Für welchen Tag möchten Sie reservieren?"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-863eeb302db5",
  "ended_at": "2026-05-01T18:47:59.041526+02:00",
  "started_at": "2026-05-01T18:47:12.803126+02:00",
  "started_ts": 1777654032.8034794,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Reservierung für zwei Personen.",
      "timestamp": "2026-05-01T18:47:30.901376+02:00"
    },
    {
      "role": "user",
      "text": "In zwei Wochen.",
      "timestamp": "2026-05-01T18:47:39.125438+02:00"
    },
    {
      "role": "user",
      "text": "Muss ich Ihnen genau 'n Tag sagen?",
      "timestamp": "2026-05-01T18:47:45.900572+02:00"
    },
    {
      "role": "user",
      "text": "Okay, dann zehnter Mal.",
      "timestamp": "2026-05-01T18:47:48.024584+02:00"
    },
    {
      "role": "user",
      "text": "Zwei Wochen.",
      "timestamp": "2026-05-01T18:47:56.184011+02:00"
    },
    {
      "role": "user",
      "text": "They upload them? Yeah.",
      "timestamp": "2026-05-01T18:47:58.055013+02:00"
    }
  ],
  "duration_secs": 46.2,
  "emergency_events": [],
  "emergency_detected": false,
  "recording_consent_at": "2026-05-01T18:47:12.803126+02:00",
  "insurance_data_collected": false
}
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=reservation turn_type=start_intent locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 2: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 3: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 4: intent=reservation turn_type=confirm locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 5: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 6: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
