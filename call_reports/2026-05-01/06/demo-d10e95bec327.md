# Sailly — Full Call Analysis Report
## Call ID: `demo-d10e95bec327`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-d10e95bec327` |
| **Caller / channel** | `[validation:A1_meta_feedback_eilig]` |
| **Started** | 2026-05-01 06:40:01 UTC |
| **Ended** | 2026-05-01 06:41:48 UTC |
| **Duration** | **107 seconds (1:47 min)** |
| **Total DB turns** | 7 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 514 ms |
| **p95 latency (stored)** | 1292 ms |
| **Max latency (stored)** | 1321 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 153.8202 ¢ |

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
| Latency p50 / p95 / max (total) | 14 / 1321 / 1321 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 5 / 1317 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 5 / 1317 ms (7 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    22
llm_latency_ms:    993 ✅
tts_latency_ms:    993
total_latency_ms:  1015 ✅
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

**Bot:** Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood begrüßen zu dürfen – wie kann ich Ihnen heute weiterhelfen?

---

### Turn 2

```
stt_latency_ms:    5
llm_latency_ms:    1220 ✅
tts_latency_ms:    1220
total_latency_ms:  1225 ✅
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

**User:** Ich möchte einen Tisch für heute Abend reservieren. Für wie viele Personen und um welche Uhrzeit?

**Bot:** Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – worum geht es Ihnen heute?

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    1317 ✅
tts_latency_ms:    1317
total_latency_ms:  1321 ✅
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

**User:** Was?

**Bot:** Sehr gerne helfe ich Ihnen weiter! Für wie viele Personen und um welche Uhrzeit möchten Sie den Tisch reservieren?

---

### Turn 4

```
stt_latency_ms:    4
llm_latency_ms:    3 ✅
tts_latency_ms:    3
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

**User:** Ich wollte nur einen Tisch für zwei Personen heute Abend reservieren. Können wir das jetzt bitte machen?

**Bot:** Um wie viel Uhr darf ich reservieren?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  8 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          impatient
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

**User:** für zwei Personen, heute Abend. Haben Sie da was frei?

**Bot:** Um wie viel Uhr darf ich reservieren?

---

### Turn 6

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

**User:** Ist da noch was frei?

**Bot:** Um wie viel Uhr darf ich reservieren?

---

### Turn 7

```
stt_latency_ms:    8
llm_latency_ms:    5 ✅
tts_latency_ms:    5
total_latency_ms:  14 ✅
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

**User:** Ja, ja, verstanden. neunzehn Uhr.

**Bot:** Um wie viel Uhr darf ich reservieren?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1015 | 993 | 22 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1225 | 1220 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1321 | 1317 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 7 | 3 | 4 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 5 | 8 | 3 | 4 | None | — | 200 | info_neutral | impatient | None | get_date_info |  |
| 6 | 7 | 4 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 7 | 14 | 5 | 8 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo,
- **user** (turn 1): Ich möchte einen Tisch für heute Abend reservieren. Für wie viele Personen und um welche Uhrzeit?
- **user** (turn 2): Ja, ich brauche einen Tisch für heute Abend für zwei Personen. Um wie viel Uhr haben Sie noch etwas frei?
- **user** (turn 3): Was?
- **user** (turn 4): Ich wollte nur einen Tisch für zwei Personen heute Abend reservieren. Können wir das jetzt bitte machen?
- **user** (turn 5): für zwei Personen, heute Abend. Haben Sie da was frei?
- **user** (turn 6): Ist da noch was frei?
- **user** (turn 7): Ja, ja, verstanden. neunzehn Uhr.

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
          "Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood begrüßen zu dürfen – wie kann ich Ihnen heute weiterhelfen?",
          "Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – worum geht es Ihnen heute?",
          "Sehr gerne helfe ich Ihnen weiter! Für wie viele Personen und um welche Uhrzeit möchten Sie den Tisch reservieren?",
          "Um wie viel Uhr darf ich reservieren?",
          "Um wie viel Uhr darf ich reservieren?",
          "Um wie viel Uhr darf ich reservieren?",
          "Um wie viel Uhr darf ich reservieren?"
        ],
        "reservation_date": "2026-05-01",
        "reservation_time": null,
        "delivery_intended": false,
        "ai_greeting_called": false,
        "current_intent_idx": null,
        "customer_confirmed": true,
        "get_weather_called": false,
        "reservation_intent": true,
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
            "bot": "Sehr gerne helfe ich Ihnen weiter! Für wie viele Personen und um welche Uhrzeit möchten Sie den Tisch reservieren?",
            "node": "greeting",
            "customer": "Was?"
          },
          {
            "bot": "Um wie viel Uhr darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Ich wollte nur einen Tisch für zwei Personen heute Abend reservieren. Können wir das jetzt bitte machen?"
          },
          {
            "bot": "Um wie viel Uhr darf ich reservieren?",
            "node": "reservation_start",
            "customer": "für zwei Personen, heute Abend. Haben Sie da was frei?"
          },
          {
            "bot": "Um wie viel Uhr darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Ist da noch was frei?"
          },
          {
            "bot": "Um wie viel Uhr darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Ja, ja, verstanden. neunzehn Uhr."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Hallo,...' [greeting] Kunde: 'Ich möchte einen Tisch für heute Abend reservieren. Für wie viele Personen und um welche Uhrzeit?...'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 8,
      "all_tools": [
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
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
        "Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood begrüßen zu dürfen – wie kann ich Ihnen heute weiterhelfen?",
        "Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – worum geht es Ihnen heute?",
        "Sehr gerne helfe ich Ihnen weiter! Für wie viele Personen und um welche Uhrzeit möchten Sie den Tisch reservieren?",
        "Um wie viel Uhr darf ich reservieren?",
        "Um wie viel Uhr darf ich reservieren?",
        "Um wie viel Uhr darf ich reservieren?",
        "Um wie viel Uhr darf ich reservieren?"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-d10e95bec327",
  "ended_at": "2026-05-01T08:41:48.861196+02:00",
  "started_at": "2026-05-01T08:40:01.825986+02:00",
  "started_ts": 1777617601.8260152,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Hallo,",
      "timestamp": "2026-05-01T08:40:06.102177+02:00"
    },
    {
      "role": "user",
      "text": "Ich möchte einen Tisch für heute Abend reservieren. Für wie viele Personen und um welche Uhrzeit?",
      "timestamp": "2026-05-01T08:40:07.754583+02:00"
    },
    {
      "role": "user",
      "text": "Ja, ich brauche einen Tisch für heute Abend für zwei Personen. Um wie viel Uhr haben Sie noch etwas frei?",
      "timestamp": "2026-05-01T08:40:28.415795+02:00"
    },
    {
      "role": "user",
      "text": "Was?",
      "timestamp": "2026-05-01T08:40:30.597311+02:00"
    },
    {
      "role": "user",
      "text": "Ich wollte nur einen Tisch für zwei Personen heute Abend reservieren. Können wir das jetzt bitte machen?
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=finalize locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 4: intent=reservation turn_type=finalize locked=True (conf=0.85) profile=reservation_start reroute=True
Turn 5: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=True
Turn 6: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=True
Turn 7: intent=reservation turn_type=confirm locked=True (conf=0.85) profile=reservation_start reroute=True
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
