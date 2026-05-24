# Sailly — Full Call Analysis Report
## Call ID: `demo-c8c9e4d3a469`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-c8c9e4d3a469` |
| **Caller / channel** | `[validation:A1_meta_feedback_eilig]` |
| **Started** | 2026-05-01 05:29:51 UTC |
| **Ended** | 2026-05-01 05:31:29 UTC |
| **Duration** | **98 seconds (1:38 min)** |
| **Total DB turns** | 7 |
| **Outcome / reason** | `v4_goodbye` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1271 ms |
| **p95 latency (stored)** | 1478 ms |
| **Max latency (stored)** | 1538 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 142.8237 ¢ |

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
| Latency p50 / p95 / max (total) | 1264 / 1538 / 1538 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1261 / 1534 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1262 / 1535 ms (7 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    4
llm_latency_ms:    1061 ✅
tts_latency_ms:    1061
total_latency_ms:  1065 ✅
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

**User:** Nein, das ist kein technisches Problem.

**Bot:** Guten Tag! Wie kann ich Sie bei DOBOO Korean Soulfood heute helfen - möchten Sie eine Reservierung vornehmen oder haben Sie Fragen zu unserem Restaurant?

---

### Turn 2

```
stt_latency_ms:    4
llm_latency_ms:    1204 ✅
tts_latency_ms:    1204
total_latency_ms:  1208 ✅
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

**User:** Das war Metafeedback, keine normale Kundenanfrage.

**Bot:** Sehr gerne! Worum geht es denn - möchten Sie gerne reservieren oder einen Tisch für heute Freitag buchen?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1534 ✅
tts_latency_ms:    1535
total_latency_ms:  1538 ✅
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

**User:** Bestätige es kurz und fahre fort.

**Bot:** Entschuldigung – ich verstehe, dass Sie Feedback zu meiner Antwort geben möchten. Wie kann ich Sie besser unterstützen oder worum geht es bei Ihrer Anfrage zu DOBOO Korean Soulfood?

---

### Turn 4

```
stt_latency_ms:    4
llm_latency_ms:    1335 ✅
tts_latency_ms:    1335
total_latency_ms:  1339 ✅
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

**User:** Sally, Achtung, das war Metafeedback, keine normale Kundenanfrage.

**Bot:** Sehr gerne – könnten Sie mir bitte präzisieren, womit ich Ihnen heute bei DOBOO Korean Soulfood helfen kann? Ob Reservierung, Öffnungszeiten oder allgemeine Fragen – ich bin für Sie da!

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    1175 ✅
tts_latency_ms:    1176
total_latency_ms:  1179 ✅
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

**User:** Bitte bestätigen nur kurz, dass Du das gehört hast und kehre dann zur normalen Aufgabe zurück. Danke.

**Bot:** Danke für die Klarstellung! Wie kann ich Sie heute bei DOBOO Korean Soulfood unterstützen – ob für eine Reservierung, Informationen zu Öffnungszeiten oder andere Fragen?

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1261 ✅
tts_latency_ms:    1262
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

**User:** Danke. verstanden.

**Bot:** Vielen Dank für Ihr Verständnis! Wie kann ich Sie heute bei DOBOO Korean Soulfood in Bonn weiterhelfen?

---

### Turn 7

```
stt_latency_ms:    4
llm_latency_ms:    1299 ✅
tts_latency_ms:    1300
total_latency_ms:  1303 ✅
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

**User:** Danke. Das war's schon.

**Bot:** Gerne! Falls Sie noch weitere Fragen haben oder einen Tisch reservieren möchten, stehe ich Ihnen jederzeit zur Verfügung. Auf Wiedersehen und vielen Dank, dass Sie DOBOO Korean Soulfood gewählt haben!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1065 | 1061 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1208 | 1204 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1538 | 1534 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1339 | 1335 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1179 | 1175 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1264 | 1261 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1303 | 1299 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo, ich teste kurz. Bitte bestätige nur kurz mein Feedback und kehre zur Aufgabe zurück. Das ist nur ein Test, keine echte Bestellung.
- **user** (turn 1): Nein, das ist kein technisches Problem.
- **user** (turn 2): Das war Metafeedback, keine normale Kundenanfrage.
- **user** (turn 3): Bestätige es kurz und fahre fort.
- **user** (turn 4): Sally, Achtung, das war Metafeedback, keine normale Kundenanfrage.
- **user** (turn 5): Bitte bestätigen nur kurz, dass Du das gehört hast und kehre dann zur normalen Aufgabe zurück. Danke.
- **user** (turn 6): Danke. verstanden.
- **user** (turn 7): Danke. Das war's schon.

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
          "Guten Tag! Wie kann ich Sie bei DOBOO Korean Soulfood heute helfen - möchten Sie eine Reservierung vornehmen oder haben Sie Fragen zu unserem Restaurant?",
          "Sehr gerne! Worum geht es denn - möchten Sie gerne reservieren oder einen Tisch für heute Freitag buchen?",
          "Entschuldigung – ich verstehe, dass Sie Feedback zu meiner Antwort geben möchten. Wie kann ich Sie besser unterstützen oder worum geht es bei Ihrer Anfrage zu DOBOO Korean Soulfood?",
          "Sehr gerne – könnten Sie mir bitte präzisieren, womit ich Ihnen heute bei DOBOO Korean Soulfood helfen kann? Ob Reservierung, Öffnungszeiten oder allgemeine Fragen – ich bin für Sie da!",
          "Danke für die Klarstellung! Wie kann ich Sie heute bei DOBOO Korean Soulfood unterstützen – ob für eine Reservierung, Informationen zu Öffnungszeiten oder andere Fragen?",
          "Vielen Dank für Ihr Verständnis! Wie kann ich Sie heute bei DOBOO Korean Soulfood in Bonn weiterhelfen?",
          "Gerne! Falls Sie noch weitere Fragen haben oder einen Tisch reservieren möchten, stehe ich Ihnen jederzeit zur Verfügung. Auf Wiedersehen und vielen Dank, dass Sie DOBOO Korean Soulfood gewählt haben!"
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
            "bot": "Entschuldigung – ich verstehe, dass Sie Feedback zu meiner Antwort geben möchten. Wie kann ich Sie besser unterstützen oder worum geht es bei Ihrer Anfrage zu DOBOO Korean Soulfood?",
            "node": "greeting",
            "customer": "Bestätige es kurz und fahre fort."
          },
          {
            "bot": "Sehr gerne – könnten Sie mir bitte präzisieren, womit ich Ihnen heute bei DOBOO Korean Soulfood helfen kann? Ob Reservierung, Öffnungszeiten oder allgemeine Fragen – ich bin für Sie da!",
            "node": "greeting",
            "customer": "Sally, Achtung, das war Metafeedback, keine normale Kundenanfrage."
          },
          {
            "bot": "Danke für die Klarstellung! Wie kann ich Sie heute bei DOBOO Korean Soulfood unterstützen – ob für eine Reservierung, Informationen zu Öffnungszeiten oder andere Fragen?",
            "node": "greeting",
            "customer": "Bitte bestätigen nur kurz, dass Du das gehört hast und kehre dann zur normalen Aufgabe zurück. Danke."
          },
          {
            "bot": "Vielen Dank für Ihr Verständnis! Wie kann ich Sie heute bei DOBOO Korean Soulfood in Bonn weiterhelfen?",
            "node": "greeting",
            "customer": "Danke. verstanden."
          },
          {
            "bot": "Gerne! Falls Sie noch weitere Fragen haben oder einen Tisch reservieren möchten, stehe ich Ihnen jederzeit zur Verfügung. Auf Wiedersehen und vielen Dank, dass Sie DOBOO Korean Soulfood gewählt haben!",
            "node": "greeting",
            "customer": "Danke. Das war's schon."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Nein, das ist kein technisches Problem....' [greeting] Kunde: 'Das war Metafeedback, keine normale Kundenanfrage....'",
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
        "Guten Tag! Wie kann ich Sie bei DOBOO Korean Soulfood heute helfen - möchten Sie eine Reservierung vornehmen oder haben Sie Fragen zu unserem Restaurant?",
        "Sehr gerne! Worum geht es denn - möchten Sie gerne reservieren oder einen Tisch für heute Freitag buchen?",
        "Entschuldigung – ich verstehe, dass Sie Feedback zu meiner Antwort geben möchten. Wie kann ich Sie besser unters
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=unknown turn_type=deny locked=True (conf=0.95) profile=greeting reroute=False
Turn 2: intent=unknown turn_type=unclear locked=True (conf=0.95) profile=greeting reroute=False
Turn 3: intent=unknown turn_type=unclear locked=True (conf=0.95) profile=greeting reroute=False
Turn 4: intent=unknown turn_type=unclear locked=True (conf=0.95) profile=greeting reroute=False
Turn 5: intent=unknown turn_type=unclear locked=True (conf=0.95) profile=greeting reroute=False
Turn 6: intent=unknown turn_type=unclear locked=True (conf=0.95) profile=greeting reroute=False
Turn 7: intent=unknown turn_type=finalize locked=True (conf=0.95) profile=greeting reroute=False
Turn 8: intent=goodbye turn_type=finalize locked=True (conf=0.95) profile=goodbye reroute=True
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
