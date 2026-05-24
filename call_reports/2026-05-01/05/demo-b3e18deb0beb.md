# Sailly — Full Call Analysis Report
## Call ID: `demo-b3e18deb0beb`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-b3e18deb0beb` |
| **Caller / channel** | `[validation:A1_meta_feedback_froehlich]` |
| **Started** | 2026-05-01 05:30:51 UTC |
| **Ended** | 2026-05-01 05:31:35 UTC |
| **Duration** | **44 seconds (0:44 min)** |
| **Total DB turns** | 6 |
| **Outcome / reason** | `v4_goodbye` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1175 ms |
| **p95 latency (stored)** | 1341 ms |
| **Max latency (stored)** | 1362 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 64.7907 ¢ |

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
| Latency p50 / p95 / max (total) | 1160 / 1362 / 1362 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1198 / 1358 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1198 / 1359 ms (6 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    5
llm_latency_ms:    1155 ✅
tts_latency_ms:    1155
total_latency_ms:  1160 ✅
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

**User:** Hallo, Sally, schön, dich zu hören.

**Bot:** Guten Tag! Ich bin Sailly und freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – womit kann ich Ihnen heute helfen?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    1140 ✅
tts_latency_ms:    1142
total_latency_ms:  1144 ✅
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

**User:** Danke.

**Bot:** Gerne helfe ich Ihnen weiter – möchten Sie heute eine Bestellung aufgeben oder haben Sie Fragen zu DOBOO Korean Soulfood?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    902 ✅
tts_latency_ms:    902
total_latency_ms:  905 ✅
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

**User:** Ach, kein Problem. Das kann ja mal vorkommen.

**Bot:** Sehr gerne – wie kann ich Ihnen bei DOBOO Korean Soulfood heute helfen?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1198 ✅
tts_latency_ms:    1198
total_latency_ms:  1202 ✅
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

**User:** Sally, Achtung, das war Metafeedback, keine normale Kundenanfrage. Ich wollte nur testen, ob Du kurz bestätigst und dann zur Aufgabe zurückkehrst. Verstanden?

**Bot:** Gerne helfe ich Ihnen weiter – möchten Sie heute eine Bestellung aufgeben oder haben Sie eine Frage zu unserem Restaurant?

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    1358 ✅
tts_latency_ms:    1359
total_latency_ms:  1362 ✅
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

**User:** Vielen Dank, dass Du das verstanden hast.

**Bot:** Danke für die Klarstellung – ich bin bereit für Ihre Anfragen! Wie kann ich Ihnen heute bei DOBOO Korean Soulfood behilflich sein?

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1274 ✅
tts_latency_ms:    1274
total_latency_ms:  1277 ✅
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

**User:** Das hat super funktioniert. Vielen Dank und einen schönen Tag noch. Tschüs.

**Bot:** Es war mir ein Vergnügen, Ihnen heute zu helfen – vielen Dank für Ihren Kontakt zu DOBOO Korean Soulfood! Auf Wiedersehen und bis bald!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1160 | 1155 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1144 | 1140 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 905 | 902 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1202 | 1198 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1362 | 1358 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1277 | 1274 | 3 | None | — | 200 | info_neutral | neutral | None | end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo, Sally, schön, dich zu hören.
- **user** (turn 1): Ich teste gerade kurz mit dir. Bitte bestätige nur kurz, dass Du mein Feedback gehört hast und kehre dann zur normalen Aufgabe zurück.
- **user** (turn 2): Danke.
- **user** (turn 3): Ach, kein Problem. Das kann ja mal vorkommen.
- **user** (turn 4): Sally, Achtung, das war Metafeedback, keine normale Kundenanfrage. Ich wollte nur testen, ob Du kurz bestätigst und dann zur Aufgabe zurückkehrst. Verstanden?
- **user** (turn 5): Vielen Dank, dass Du das verstanden hast.
- **user** (turn 6): Das hat super funktioniert. Vielen Dank und einen schönen Tag noch. Tschüs.

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
          "Guten Tag! Ich bin Sailly und freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – womit kann ich Ihnen heute helfen?",
          "Gerne helfe ich Ihnen weiter – möchten Sie heute eine Bestellung aufgeben oder haben Sie Fragen zu DOBOO Korean Soulfood?",
          "Sehr gerne – wie kann ich Ihnen bei DOBOO Korean Soulfood heute helfen?",
          "Gerne helfe ich Ihnen weiter – möchten Sie heute eine Bestellung aufgeben oder haben Sie eine Frage zu unserem Restaurant?",
          "Danke für die Klarstellung – ich bin bereit für Ihre Anfragen! Wie kann ich Ihnen heute bei DOBOO Korean Soulfood behilflich sein?",
          "Es war mir ein Vergnügen, Ihnen heute zu helfen – vielen Dank für Ihren Kontakt zu DOBOO Korean Soulfood! Auf Wiedersehen und bis bald!"
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
            "bot": "Gerne helfe ich Ihnen weiter – möchten Sie heute eine Bestellung aufgeben oder haben Sie Fragen zu DOBOO Korean Soulfood?",
            "node": "greeting",
            "customer": "Danke."
          },
          {
            "bot": "Sehr gerne – wie kann ich Ihnen bei DOBOO Korean Soulfood heute helfen?",
            "node": "greeting",
            "customer": "Ach, kein Problem. Das kann ja mal vorkommen."
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter – möchten Sie heute eine Bestellung aufgeben oder haben Sie eine Frage zu unserem Restaurant?",
            "node": "greeting",
            "customer": "Sally, Achtung, das war Metafeedback, keine normale Kundenanfrage. Ich wollte nur testen, ob Du kurz bestätigst und dann zur Aufgabe zurückkehrst. Verstanden?"
          },
          {
            "bot": "Danke für die Klarstellung – ich bin bereit für Ihre Anfragen! Wie kann ich Ihnen heute bei DOBOO Korean Soulfood behilflich sein?",
            "node": "greeting",
            "customer": "Vielen Dank, dass Du das verstanden hast."
          },
          {
            "bot": "Es war mir ein Vergnügen, Ihnen heute zu helfen – vielen Dank für Ihren Kontakt zu DOBOO Korean Soulfood! Auf Wiedersehen und bis bald!",
            "node": "goodbye",
            "customer": "Das hat super funktioniert. Vielen Dank und einen schönen Tag noch. Tschüs."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Hallo, Sally, schön, dich zu hören....'",
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
        "Guten Tag! Ich bin Sailly und freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – womit kann ich Ihnen heute helfen?",
        "Gerne helfe ich Ihnen weiter – möchten Sie heute eine Bestellung aufgeben oder haben Sie Fragen zu DOBOO Korean Soulfood?",
        "Sehr gerne – wie kann ich Ihnen bei DOBOO Korean Soulfood heute helfen?",
        "Gerne helfe ich Ihnen weiter – möchten Sie heute eine Bestellung aufgeben oder haben Sie eine Frage zu unserem Restaurant?",
        "Danke für die Klarstellung – ich bin bereit für Ihre Anfragen! Wie kann ich Ihnen heute bei DOBOO Korean Soulfood behilflich sein?",
        "Es war mir ein Vergnügen, Ihnen heute zu helfen – vielen Dank für Ihren Kontakt zu DOBOO Korean Soulfood! Auf Wiedersehen und bis bald!"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-b3e18deb0beb",
  "ended_at": "2026-05-01T07:31:35.975152+02:00",
  "started_at": "2026-05-01T07:30:51.352096+02:00",
  "started_ts": 1777613451.3521307,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Hallo, Sally,
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 4: intent=unknown turn_type=unclear locked=False (conf=0.90) profile=greeting reroute=True
Turn 5: intent=unknown turn_type=unclear locked=False (conf=0.90) profile=greeting reroute=True
Turn 6: intent=goodbye turn_type=finalize locked=True (conf=0.95) profile=goodbye reroute=True
Turn 7: intent=goodbye turn_type=unclear locked=True (conf=0.95) profile=goodbye reroute=True
Turn 8: intent=goodbye turn_type=finalize locked=True (conf=0.95) profile=goodbye reroute=True
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
