# Sailly — Full Call Analysis Report
## Call ID: `demo-0b8b07a50fc4`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-0b8b07a50fc4` |
| **Caller / channel** | `[validation:A1_greeting_eilig]` |
| **Started** | 2026-05-01 04:42:40 UTC |
| **Ended** | 2026-05-01 04:43:24 UTC |
| **Duration** | **44 seconds (0:44 min)** |
| **Total DB turns** | 4 |
| **Outcome / reason** | `client_hangup` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1588 ms |
| **p95 latency (stored)** | 2263 ms |
| **Max latency (stored)** | 2364 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 63.8997 ¢ |

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
| Latency p50 / p95 / max (total) | 1688 / 2364 / 2364 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1684 / 1899 ms | From `llm_latency_ms` column |
| STT p50 | 19 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1684 / 1900 ms (4 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    465
llm_latency_ms:    1899 ✅
tts_latency_ms:    1900
total_latency_ms:  2364 ✅
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

**User:** Guten Tag, ich wollte nur kurz schauen, ob ihr auf habt.

**Bot:** Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?

---

### Turn 2

```
stt_latency_ms:    19
llm_latency_ms:    1259 ✅
tts_latency_ms:    1259
total_latency_ms:  1279 ✅
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

**User:** ich hab sein bisschen eilig.

**Bot:** Ja, natürlich haben wir heute Freitag geöffnet! Kann ich Ihnen noch weitere Informationen geben oder möchten Sie einen Tisch reservieren?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1684 ✅
tts_latency_ms:    1684
total_latency_ms:  1688 ✅
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

**User:** Ja, ich bin auch in Eile.

**Bot:** Sehr gerne, Herr Auch In – was kann ich Ihnen schnell helfen, möchten Sie reservieren oder bestellen?

---

### Turn 4

```
stt_latency_ms:    5
llm_latency_ms:    1015 ✅
tts_latency_ms:    1015
total_latency_ms:  1020 ✅
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

**User:** Sind Sie heute geöffnet?

**Bot:** Gerne helfe ich Ihnen weiter – möchten Sie einen Tisch reservieren oder eine Bestellung aufgeben?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 2364 | 1899 | 465 | None | — | 200 | greeting_first | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1279 | 1259 | 19 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1688 | 1684 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1020 | 1015 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Guten Tag, ich wollte nur kurz schauen, ob ihr auf habt.
- **user** (turn 1): ich hab sein bisschen eilig.
- **user** (turn 2): Ja, ich bin auch in Eile.
- **user** (turn 3): Sind Sie heute geöffnet?

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
        "first_name": "Auch",
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
          "Ja, natürlich haben wir heute Freitag geöffnet! Kann ich Ihnen noch weitere Informationen geben oder möchten Sie einen Tisch reservieren?",
          "Sehr gerne, Herr Auch In – was kann ich Ihnen schnell helfen, möchten Sie reservieren oder bestellen?",
          "Gerne helfe ich Ihnen weiter – möchten Sie einen Tisch reservieren oder eine Bestellung aufgeben?"
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
            "bot": "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
            "node": "greeting",
            "customer": "Guten Tag, ich wollte nur kurz schauen, ob ihr auf habt."
          },
          {
            "bot": "Ja, natürlich haben wir heute Freitag geöffnet! Kann ich Ihnen noch weitere Informationen geben oder möchten Sie einen Tisch reservieren?",
            "node": "greeting",
            "customer": "ich hab sein bisschen eilig."
          },
          {
            "bot": "Sehr gerne, Herr Auch In – was kann ich Ihnen schnell helfen, möchten Sie reservieren oder bestellen?",
            "node": "greeting",
            "customer": "Ja, ich bin auch in Eile."
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter – möchten Sie einen Tisch reservieren oder eine Bestellung aufgeben?",
            "node": "greeting",
            "customer": "Sind Sie heute geöffnet?"
          }
        ],
        "context_summary": "",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 4,
      "all_tools": [
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
        "Ja, natürlich haben wir heute Freitag geöffnet! Kann ich Ihnen noch weitere Informationen geben oder möchten Sie einen Tisch reservieren?",
        "Sehr gerne, Herr Auch In – was kann ich Ihnen schnell helfen, möchten Sie reservieren oder bestellen?",
        "Gerne helfe ich Ihnen weiter – möchten Sie einen Tisch reservieren oder eine Bestellung aufgeben?"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-0b8b07a50fc4",
  "ended_at": "2026-05-01T06:43:24.159160+02:00",
  "started_at": "2026-05-01T06:42:40.131468+02:00",
  "started_ts": 1777610560.1314785,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Guten Tag, ich wollte nur kurz schauen, ob ihr auf habt.",
      "timestamp": "2026-05-01T06:42:43.270168+02:00"
    },
    {
      "role": "user",
      "text": "ich hab sein bisschen eilig.",
      "timestamp": "2026-05-01T06:42:45.668769+02:00"
    },
    {
      "role": "user",
      "text": "Ja, ich bin auch in Eile.",
      "timestamp": "2026-05-01T06:42:53.000924+02:00"
    },
    {
      "role": "user",
      "text": "Sind Sie heute geöffnet?",
      "timestamp": "2026-05-01T06:42:55.137574+02:00"
    }
  ],
  "duration_secs": 44.0,
  "emergency_events": [],
  "emergency_detected": false,
  "recording_consent_at": "2026-05-01T06:42:40.131468+02:00",
  "insurance_data_collected": false
}
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=False (conf=0.00) profile=greeting reroute=False
Turn 2: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 3: intent=unknown turn_type=confirm locked=True (conf=0.95) profile=greeting reroute=False
Turn 4: intent=unknown turn_type=start_intent locked=True (conf=0.95) profile=greeting reroute=False
Turn 5: intent=unknown turn_type=confirm locked=True (conf=0.95) profile=greeting reroute=False
Turn 6: intent=unknown turn_type=unclear locked=True (conf=0.95) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
