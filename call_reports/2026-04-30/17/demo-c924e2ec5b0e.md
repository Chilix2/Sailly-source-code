# Sailly — Full Call Analysis Report
## Call ID: `demo-c924e2ec5b0e`
_Generated: 2026-04-30 17:57 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-c924e2ec5b0e` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-04-30 17:55:43 UTC |
| **Ended** | 2026-04-30 17:56:55 UTC |
| **Duration** | **71 seconds (1:11 min)** |
| **Total DB turns** | 2 |
| **Outcome / reason** | `v4_goodbye` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 2866 ms |
| **p95 latency (stored)** | 5126 ms |
| **Max latency (stored)** | 5377 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 101.2422 ¢ |

### Pipeline configuration (runtime snapshot)

```
STT:  DeepgramFluxSTTService (flux-general-multi, EU endpoint, eot_threshold=0.6, eot_timeout_ms=3000 ms, mip_opt_out=True)
VAD:  None — Deepgram Flux semantic EOT (eot_threshold=0.6, eot_timeout_ms=3000)
LLM:  claude-haiku-4-5 (Vertex region env: us-east5)
Worker pipeline: IntentSessionManager (shadow) → WorkerRouter (15 profiles) → WorkerExecutor (Required≤280ms / Optional≤350ms / Background)
TTS:  SaillyGeminiTTSService — voice=Kore, engine=chirp3hd
      GLOBAL_SPEED_MULTIPLIER=2.25 (env override possible)
Filler: pre-baked PCM 12-phrase pool, 400ms trigger (ENABLE_PRE_LLM_FILLER=true) | Backchannel: 6-phrase pool, 200-500ms hesitation window (ENABLE_BACKCHANNEL=true)
MULTI-INTENT / ADK: Enabled per brain configuration for browser demo
ValidationRegistry: async validation when configured
TTS Conditioning: Phase 2 — situation + mood → prosody_rate_pct → Gemini speaking_rate
Barge-in: enabled post-greeting when BargeInHandler is in pipeline
Monitoring thresholds (env): MONITOR_LATENCY_P95_MS=3000 ms, MONITOR_SUCCESS_THRESHOLD=80, Redis monitor=1
```

---

## 2. Aggregate health (from `google_turn_metrics`)

| Check | Value | Notes |
|-------|-------|-------|
| Latency p50 / p95 / max (total) | 355 / 5377 / 5377 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 5373 / 5373 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| Call-level observability (stored on `google_calls`) | validation_registry_invocations=0, loop_incidents=0 | From `persist_call_aggregates` |

---

## 3. Caller-flag insights (`Achtung Sailly: …` / `Attention Sailly: …`)

_Test harness, caller-bot, or human reviewer: phrases like **Achtung Sailly:** (also **Attention Sailly:** / **Warnung Sailly:**) mark what Sailly did **wrong** — use this for qualitative issues that **latency and tool metrics may not show**._

_No matching caller markers in `google_transcripts` (non-assistant roles), `session_data.transcripts`, or `user_text` in turn metrics._
## 4. Per-turn breakdown (DB)

### Turn 1

```
stt_latency_ms:    3
llm_latency_ms:    352 ✅
tts_latency_ms:    0
total_latency_ms:  355 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     greeting_first
tts_mood:          neutral
tts_rate_pct:      200
node_name:         greeting
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['ai_greeting', 'get_date_info', 'ai_greeting']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Hallo Sally. Wie ist das Wetter heute bei euch und habt ihr heute Abend noch einen Tisch für zwei Personen um neunzehn Uhr frei?

**Bot:** Was darf ich für Sie tun?

---

### Turn 2

```
stt_latency_ms:    4
llm_latency_ms:    5373 ⚠️
tts_latency_ms:    0
total_latency_ms:  5377 ⚠️
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_rate_pct:      200
node_name:         goodbye
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['end_call', 'end_call']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Achtung, Sally. Eins noch, bitte hinzufügen zum Transkript. Turn one, Begrüßung okay. Turn zwei, ich habe zwei klare Fragen gestellt. Turn drei, Du hast nur, was darf ich für Sie tun, zweimal hintereinander gesagt. Turn vier, Du hast schon wieder nur, was darf ich für Sie tun gesagt, obwohl ich dir bereits geantwortet hatte. Du bist in einer Schleife und hörst nicht zu. Das war's für diesen Call.

**Bot:** Was darf ich für Sie tun?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-------|-------|
| 1 | 355 | 352 | 3 | None | — | 200 | greeting_first | neutral | ai_greeting,get_date_info,ai_greeting |  |
| 2 | 5377 | 5373 | 4 | None | — | 200 | info_neutral | neutral | end_call,end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?
- **user** (turn 1): Hallo Sally. Wie ist das Wetter heute bei euch und habt ihr heute Abend noch einen Tisch für zwei Personen um neunzehn Uhr frei?
- **user** (turn 2): Achtung, Sally. Eins noch, bitte hinzufügen zum Transkript. Turn one, Begrüßung okay. Turn zwei, ich habe zwei klare Fragen gestellt. Turn drei, Du hast nur, was darf ich für Sie tun, zweimal hintereinander gesagt. Turn vier, Du hast schon wieder nur, was darf ich für Sie tun gesagt, obwohl ich dir bereits geantwortet hatte. Du bist in einer Schleife und hörst nicht zu. Das war's für diesen Call.

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
        "customer_name": null,
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": null,
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [],
        "reservation_date": "Heute",
        "reservation_time": "19:00",
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
            "bot": "Was darf ich für Sie tun?",
            "node": "greeting",
            "customer": "Hallo Sally. Wie ist das Wetter heute bei euch und habt ihr heute Abend noch einen Tisch für zwei Personen um neunzehn Uhr frei?"
          },
          {
            "bot": "Was darf ich für Sie tun?",
            "node": "goodbye",
            "customer": "Achtung, Sally. Eins noch, bitte hinzufügen zum Transkript. Turn one, Begrüßung okay. Turn zwei, ich habe zwei klare Fragen gestellt. Turn drei, Du hast nur, was darf ich für Sie tun, zweimal hintereinander gesagt. Turn vier, Du hast schon wieder nur, was darf ich für Sie tun gesagt, obwohl ich dir bereits geantwortet hatte. Du bist in einer Schleife und hörst nicht zu. Das war's für diesen Call."
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
      "turn_idx": 2,
      "all_tools": [
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "end_call",
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
      "recent_responses": []
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-c924e2ec5b0e",
  "ended_at": "2026-04-30T19:56:55.074654+02:00",
  "started_at": "2026-04-30T19:55:43.831521+02:00",
  "started_ts": 1777571743.8315556,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "assistant",
      "text": "Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?",
      "timestamp": "2026-04-30T19:55:43.836360+02:00"
    },
    {
      "role": "user",
      "text": "Hallo Sally. Wie ist das Wetter heute bei euch und habt ihr heute Abend noch einen Tisch für zwei Personen um neunzehn Uhr frei?",
      "timestamp": "2026-04-30T19:56:09.408606+02:00"
    },
    {
      "role": "user",
      "text": "Achtung, Sally. Eins noch, bitte hinzufügen zum Transkript. Turn one, Begrüßung okay. Turn zwei, ich habe zwei klare Fragen gestellt. Turn drei, Du hast nur, was darf ich für Sie tun, zweimal hintereinander gesagt. Turn vier, Du hast schon wieder nur, was darf ich für Sie tun gesagt, obwohl ich dir bereits geantwortet hatte. Du bist in einer Schleife und hörst nicht zu. Das war's für diesen Call.",
      "timestamp": "2026-04-30T19:56:45.966452+02:00"
    }
  ],
  "duration_secs": 71.2,
  "emergency_events": [],
  "emergency_detected": false,
  "recording_consent_at": "2026-04-30T19:55:43.831521+02:00",
  "insurance_data_collected": false
}
```

---

## 8.5 Intent Session (shadow — `google_context_documents`)

```python
# Phase 3 shadow data — intent classification running alongside legacy pipeline.
# MIGRATED_PROFILES is currently empty; these are observations only, not driving responses.
Turn 1: intent=greeting turn_type=start_intent locked=False (conf=0.00) profile=greeting reroute=False
Turn 2: intent=goodbye turn_type=finalize locked=True (conf=0.95) profile=goodbye reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
