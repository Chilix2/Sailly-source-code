# Sailly — Full Call Analysis Report
## Call ID: `demo-f8423cd12f9d`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-f8423cd12f9d` |
| **Caller / channel** | `[validation:A4_basic_order_eilig]` |
| **Started** | 2026-05-01 04:59:37 UTC |
| **Ended** | 2026-05-01 05:00:43 UTC |
| **Duration** | **65 seconds (1:05 min)** |
| **Total DB turns** | 5 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1630 ms |
| **p95 latency (stored)** | 1923 ms |
| **Max latency (stored)** | 1962 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 94.6732 ¢ |

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
| Latency p50 / p95 / max (total) | 1700 / 1962 / 1962 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1693 / 1946 ms | From `llm_latency_ms` column |
| STT p50 | 5 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1693 / 1946 ms (5 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1296 ✅
tts_latency_ms:    1297
total_latency_ms:  1300 ✅
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

**User:** Hallo, hier ist Dobu. Wie kann ich Ihnen helfen?

**Bot:** Schön, Sie bei uns zu begrüßen, Dobu! Was kann ich für Sie reservieren oder welche Fragen haben Sie zu DOBOO?

---

### Turn 2

```
stt_latency_ms:    5
llm_latency_ms:    1414 ✅
tts_latency_ms:    1415
total_latency_ms:  1419 ✅
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

**User:** Möchten Sie etwas bestellen oder haben Sie eine andere Frage?

**Bot:** Schön, Sie bei uns zu begrüßen, Dobu! Was kann ich für Sie reservieren oder welche Fragen haben Sie zu DOBOO?

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    1765 ✅
tts_latency_ms:    1765
total_latency_ms:  1769 ✅
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

**User:** Guten Tag, hier ist das Restaurant Dobu. Wie kann ich Ihnen helfen?

**Bot:** Entschuldigung, ich habe Sie missverständlich begrüßt – Sie sind ja unser DOBOO Restaurant! Wie kann ich Ihnen heute helfen oder welche Information benötigen Sie?

---

### Turn 4

```
stt_latency_ms:    16
llm_latency_ms:    1946 ✅
tts_latency_ms:    1946
total_latency_ms:  1962 ✅
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

**User:** Möchten Sie etwas bestellen oder haben Sie eine andere Anfrage?

**Bot:** Entschuldigen Sie, ich glaube es gibt hier ein Missverständnis – ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?

---

### Turn 5

```
stt_latency_ms:    6
llm_latency_ms:    1693 ✅
tts_latency_ms:    1693
total_latency_ms:  1700 ✅
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

**User:** Ja, ich möchte was bestellen. Zum Abholen

**Bot:** Gerne helfe ich Ihnen weiter – möchten Sie einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage zu DOBOO? Was kann ich für Sie tun?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1300 | 1296 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1419 | 1414 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1769 | 1765 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1962 | 1946 | 16 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1700 | 1693 | 6 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo, hier ist Dobu. Wie kann ich Ihnen helfen?
- **user** (turn 1): Möchten Sie etwas bestellen oder haben Sie eine andere Frage?
- **user** (turn 2): Guten Tag, hier ist das Restaurant Dobu. Wie kann ich Ihnen helfen?
- **user** (turn 3): Möchten Sie etwas bestellen oder haben Sie eine andere Anfrage?
- **user** (turn 4): Ja, ich möchte was bestellen. Zum Abholen

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
        "first_name": "Dobu",
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
          "Schön, Sie bei uns zu begrüßen, Dobu! Was kann ich für Sie reservieren oder welche Fragen haben Sie zu DOBOO?",
          "Schön, Sie bei uns zu begrüßen, Dobu! Was kann ich für Sie reservieren oder welche Fragen haben Sie zu DOBOO?",
          "Entschuldigung, ich habe Sie missverständlich begrüßt – Sie sind ja unser DOBOO Restaurant! Wie kann ich Ihnen heute helfen oder welche Information benötigen Sie?",
          "Entschuldigen Sie, ich glaube es gibt hier ein Missverständnis – ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?",
          "Gerne helfe ich Ihnen weiter – möchten Sie einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage zu DOBOO? Was kann ich für Sie tun?"
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
            "bot": "Schön, Sie bei uns zu begrüßen, Dobu! Was kann ich für Sie reservieren oder welche Fragen haben Sie zu DOBOO?",
            "node": "greeting",
            "customer": "Hallo, hier ist Dobu. Wie kann ich Ihnen helfen?"
          },
          {
            "bot": "Schön, Sie bei uns zu begrüßen, Dobu! Was kann ich für Sie reservieren oder welche Fragen haben Sie zu DOBOO?",
            "node": "greeting",
            "customer": "Möchten Sie etwas bestellen oder haben Sie eine andere Frage?"
          },
          {
            "bot": "Entschuldigung, ich habe Sie missverständlich begrüßt – Sie sind ja unser DOBOO Restaurant! Wie kann ich Ihnen heute helfen oder welche Information benötigen Sie?",
            "node": "greeting",
            "customer": "Guten Tag, hier ist das Restaurant Dobu. Wie kann ich Ihnen helfen?"
          },
          {
            "bot": "Entschuldigen Sie, ich glaube es gibt hier ein Missverständnis – ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?",
            "node": "greeting",
            "customer": "Möchten Sie etwas bestellen oder haben Sie eine andere Anfrage?"
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter – möchten Sie einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage zu DOBOO? Was kann ich für Sie tun?",
            "node": "greeting",
            "customer": "Ja, ich möchte was bestellen. Zum Abholen"
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
        "Schön, Sie bei uns zu begrüßen, Dobu! Was kann ich für Sie reservieren oder welche Fragen haben Sie zu DOBOO?",
        "Schön, Sie bei uns zu begrüßen, Dobu! Was kann ich für Sie reservieren oder welche Fragen haben Sie zu DOBOO?",
        "Entschuldigung, ich habe Sie missverständlich begrüßt – Sie sind ja unser DOBOO Restaurant! Wie kann ich Ihnen heute helfen oder welche Information benötigen Sie?",
        "Entschuldigen Sie, ich glaube es gibt hier ein Missverständnis – ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?",
        "Gerne helfe ich Ihnen weiter – möchten Sie einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage zu DOBOO? Was kann ich für Sie tun?"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-f8423cd12f9d",
  "ended_at": "2026-05-01T07:00:43.722534+02:00",
  "started_at": "2026-05-01T06:59:37.897545+02:00",
  "started_ts": 1777611577.8975503,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Hallo, hier ist Dobu. Wie kann ich Ihnen helfen?",
      "timestamp": "2026-05-01T06:59:50.180307+02:00"
    },
    {
      "ro
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 4: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 5: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
