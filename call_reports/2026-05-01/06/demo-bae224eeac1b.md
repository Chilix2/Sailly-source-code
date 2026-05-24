# Sailly — Full Call Analysis Report
## Call ID: `demo-bae224eeac1b`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-bae224eeac1b` |
| **Caller / channel** | `[validation:A1_meta_feedback_aeltere_person]` |
| **Started** | 2026-05-01 06:07:10 UTC |
| **Ended** | 2026-05-01 06:07:59 UTC |
| **Duration** | **49 seconds (0:49 min)** |
| **Total DB turns** | 6 |
| **Outcome / reason** | `v4_goodbye` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1579 ms |
| **p95 latency (stored)** | 2706 ms |
| **Max latency (stored)** | 3083 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 71.8408 ¢ |

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
| Latency p50 / p95 / max (total) | 1238 / 3083 / 3083 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1249 / 3079 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1250 / 3080 ms (6 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1154 ✅
tts_latency_ms:    1154
total_latency_ms:  1157 ✅
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

**User:** Ach, Moment, ich verstehe nicht.

**Bot:** Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – womit kann ich Sie heute helfen?

---

### Turn 2

```
stt_latency_ms:    4
llm_latency_ms:    3079 ⚠️
tts_latency_ms:    3080
total_latency_ms:  3083 ⚠️
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

**User:** Ich teste kurz.

**Bot:** Kein Problem – ich helfe Ihnen gerne weiter! Was genau möchten Sie wissen oder bestellen?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1234 ✅
tts_latency_ms:    1235
total_latency_ms:  1238 ✅
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

**User:** Bitte bestätigen nur kurz mein Feedback, um Kehre zur Aufgabe zurück.

**Bot:** Das freut mich, dass Sie uns testen! Wie kann ich Ihnen heute bei DOBOO Korean Soulfood helfen?

---

### Turn 4

```
stt_latency_ms:    11
llm_latency_ms:    1562 ✅
tts_latency_ms:    1562
total_latency_ms:  1574 ✅
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

**User:** Ich teste kurz. Bitte bestätige nur kurz mein Feedback, um Kehre zur Aufgabe zurück.

**Bot:** Sehr gerne – könnten Sie mir kurz mitteilen, welches Feedback Sie gerne bestätigt haben möchten? Dann helfe ich Ihnen gleich weiter!

---

### Turn 5

```
stt_latency_ms:    7
llm_latency_ms:    1159 ✅
tts_latency_ms:    1159
total_latency_ms:  1166 ✅
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

**User:** Haben Sie das verstanden?

**Bot:** Natürlich – könnten Sie mir bitte konkret mitteilen, welches Feedback Sie bestätigt haben möchten, damit ich Ihnen präzise weiterhelfen kann?

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1249 ✅
tts_latency_ms:    1250
total_latency_ms:  1253 ✅
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

**User:** Ja, danke. Das war's schon.

**Bot:** Vielen Dank für das Gespräch – ich wünsche Ihnen einen wunderschönen Tag und freue mich auf Ihren nächsten Besuch bei DOBOO Korean Soulfood!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1157 | 1154 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 3083 | 3079 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1238 | 1234 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1574 | 1562 | 11 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1166 | 1159 | 7 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1253 | 1249 | 3 | None | — | 200 | info_neutral | neutral | None | end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Ja, hallo, hier ist Frau Müller.
- **user** (turn 1): Ach, Moment, ich verstehe nicht.
- **user** (turn 2): Ich teste kurz.
- **user** (turn 3): Bitte bestätigen nur kurz mein Feedback, um Kehre zur Aufgabe zurück.
- **user** (turn 4): Ich teste kurz. Bitte bestätige nur kurz mein Feedback, um Kehre zur Aufgabe zurück.
- **assistant** (turn 5): Sehr gerne – könnten Sie mir kurz mitteilen, welches Feedback Sie gerne bestätigt haben möchten? Dann helfe ich Ihnen gleich weiter!
- **user** (turn 6): Haben Sie das verstanden?
- **user** (turn 7): Ja, danke. Das war's schon.

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
        "phone_number": "+4915900000001",
        "shared_slots": {},
        "abuse_strikes": 0,
        "customer_name": null,
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": "+4915900000001",
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
          "Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – womit kann ich Sie heute helfen?",
          "Kein Problem – ich helfe Ihnen gerne weiter! Was genau möchten Sie wissen oder bestellen?",
          "Das freut mich, dass Sie uns testen! Wie kann ich Ihnen heute bei DOBOO Korean Soulfood helfen?",
          "Sehr gerne – könnten Sie mir kurz mitteilen, welches Feedback Sie gerne bestätigt haben möchten? Dann helfe ich Ihnen gleich weiter!",
          "Natürlich – könnten Sie mir bitte konkret mitteilen, welches Feedback Sie bestätigt haben möchten, damit ich Ihnen präzise weiterhelfen kann?",
          "Vielen Dank für das Gespräch – ich wünsche Ihnen einen wunderschönen Tag und freue mich auf Ihren nächsten Besuch bei DOBOO Korean Soulfood!"
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
        "delivery_address_mentioned": false,
        "last_caller_confirmation_turn": null
      },
      "memory": {
        "recent_turns": [
          {
            "bot": "Kein Problem – ich helfe Ihnen gerne weiter! Was genau möchten Sie wissen oder bestellen?",
            "node": "greeting",
            "customer": "Ich teste kurz."
          },
          {
            "bot": "Das freut mich, dass Sie uns testen! Wie kann ich Ihnen heute bei DOBOO Korean Soulfood helfen?",
            "node": "greeting",
            "customer": "Bitte bestätigen nur kurz mein Feedback, um Kehre zur Aufgabe zurück."
          },
          {
            "bot": "Sehr gerne – könnten Sie mir kurz mitteilen, welches Feedback Sie gerne bestätigt haben möchten? Dann helfe ich Ihnen gleich weiter!",
            "node": "greeting",
            "customer": "Ich teste kurz. Bitte bestätige nur kurz mein Feedback, um Kehre zur Aufgabe zurück."
          },
          {
            "bot": "Natürlich – könnten Sie mir bitte konkret mitteilen, welches Feedback Sie bestätigt haben möchten, damit ich Ihnen präzise weiterhelfen kann?",
            "node": "greeting",
            "customer": "Haben Sie das verstanden?"
          },
          {
            "bot": "Vielen Dank für das Gespräch – ich wünsche Ihnen einen wunderschönen Tag und freue mich auf Ihren nächsten Besuch bei DOBOO Korean Soulfood!",
            "node": "goodbye",
            "customer": "Ja, danke. Das war's schon."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Ach, Moment, ich verstehe nicht....'",
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
          "value": "+4915900000001",
          "status": "partial",
          "confidence": "high",
          "source_turn": 0,
          "raw_mentions": [
            "caller_id:+4915900000001"
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
        "Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – womit kann ich Sie heute helfen?",
        "Kein Problem – ich helfe Ihnen gerne weiter! Was genau möchten Sie wissen oder bestellen?",
        "Das freut mich, dass Sie uns testen! Wie kann ich Ihnen heute bei DOBOO Korean Soulfood helfen?",
        "Sehr gerne – könnten Sie mir kurz mitteilen, welches Feedback Sie gerne bestätigt haben möchten? Dann helfe ich Ihnen gleich weiter!",
        "Natürlich – könnten Sie mir bitte konkret mitteilen, welches Feedback Sie bestätigt haben möchten, damit ich Ihnen präzise weiterhelfen kann?",
        "Vielen Dank für das Gespräch – ich wünsche Ihnen einen wunderschönen Tag und freue mich auf Ihren nächsten Besuch bei DOBOO Korean Soulfood!"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-bae224eeac1b",
  "ended_at": "2026-05-01T08:07:59.378351+02:00",
  "started_at": "2026-05-01T08:07:10.245115+02:00",
  "started_ts": 1777615630.2451453,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Ja, hallo, hier ist Frau Müller.",
      "timestamp": "2026-05-01T08:07:14.585565+02:00"
    },
    {
      "role": "user",
      "text": "Ach, Momen
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
Turn 6: intent=goodbye turn_type=finalize locked=True (conf=0.95) profile=goodbye reroute=False
Turn 7: intent=goodbye turn_type=unclear locked=True (conf=0.95) profile=goodbye reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
