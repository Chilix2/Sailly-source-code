# Sailly — Full Call Analysis Report
## Call ID: `demo-10ef6b72ee4e`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-10ef6b72ee4e` |
| **Caller / channel** | `[validation:A3_opening_hours_aeltere_person]` |
| **Started** | 2026-05-01 06:42:47 UTC |
| **Ended** | 2026-05-01 06:44:22 UTC |
| **Duration** | **95 seconds (1:35 min)** |
| **Total DB turns** | 6 |
| **Outcome / reason** | `client_hangup` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1433 ms |
| **p95 latency (stored)** | 1615 ms |
| **Max latency (stored)** | 1625 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 138.1772 ¢ |

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
| Latency p50 / p95 / max (total) | 1443 / 1625 / 1625 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1479 / 1622 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1479 / 1622 ms (6 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1439 ✅
tts_latency_ms:    1441
total_latency_ms:  1443 ✅
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

**User:** Hallo, guten Tag.

**Bot:** Guten Tag und vielen Dank für Ihren Anruf bei DOBOO Korean Soulfood! Wie kann ich Ihnen heute helfen – möchten Sie einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage?

---

### Turn 2

```
stt_latency_ms:    10
llm_latency_ms:    1331 ✅
tts_latency_ms:    1332
total_latency_ms:  1342 ✅
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

**User:** Moment, ich verstehe nicht.

**Bot:** Guten Tag, vielen Dank für Ihren Anruf bei DOBOO Korean Soulfood! Wie kann ich Ihnen heute helfen – möchten Sie einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage?

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    1479 ✅
tts_latency_ms:    1479
total_latency_ms:  1483 ✅
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

**User:** Ich möchte nur wissen, wann ihr heute geöffnet habt.

**Bot:** Gerne helfe ich Ihnen weiter – könnten Sie mir bitte sagen, wobei ich Sie unterstützen kann, ob es um eine Reservierung, Bestellung oder eine allgemeine Frage geht? Ich bin hier, um Ihnen zu helfen!

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1581 ✅
tts_latency_ms:    1582
total_latency_ms:  1585 ✅
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

**User:** Ich möchte wissen, wann ihr heute geöffnet habt.

**Bot:** Sehr gerne – heute Freitag haben wir von 11:30 bis 23:00 Uhr für Sie geöffnet. Kann ich Ihnen noch bei etwas anderem helfen?

---

### Turn 5

```
stt_latency_ms:    7
llm_latency_ms:    1115 ✅
tts_latency_ms:    1115
total_latency_ms:  1122 ✅
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

**User:** Turn eins, kein Problem. Begrüßung und Frage nach Anliegen, korrekt?

**Bot:** Sehr gerne – heute Freitag haben wir von 11:30 bis 23:00 Uhr für Sie geöffnet. Kann ich Ihnen noch bei etwas anderem helfen?

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1622 ✅
tts_latency_ms:    1622
total_latency_ms:  1625 ✅
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

**User:** Turn zwei, kein Problem. Wiederholung der Standardbegrüßung trotz spezifischer Frage. Besser wäre direkte Antwort. Turn drei, kein Problem. Direkte Antwort auf Öffnungszeitenfrage, korrekt. Turn zwei, ignorierte Frage. Wiederholung der Standardbegrüßung trotz klarer Öffnungszeitenfrage. Direkt auf die Frage antworten, statt Standardtext zu wiederholen.

**Bot:** Ja, genau – ich habe Sie begrüßt und Sie über unsere heutigen Öffnungszeiten informiert. Wie kann ich Ihnen sonst noch weiterhelfen?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1443 | 1439 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1342 | 1331 | 10 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1483 | 1479 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1585 | 1581 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1122 | 1115 | 7 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1625 | 1622 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO. Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?
- **user** (turn 1): Hallo, guten Tag.
- **user** (turn 2): Ich würde gerne wissen, wann ihr heute geöffnet habt.
- **user** (turn 3): Moment, ich verstehe nicht.
- **assistant** (turn 4): Guten Tag, vielen Dank für Ihren Anruf bei DOBOO Korean Soulfood! Wie kann ich Ihnen heute helfen – möchten Sie einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage?
- **user** (turn 5): Ich möchte nur wissen, wann ihr heute geöffnet habt.
- **user** (turn 6): Ich möchte wissen, wann ihr heute geöffnet habt.
- **user** (turn 7): Turn eins, kein Problem. Begrüßung und Frage nach Anliegen, korrekt?
- **user** (turn 8): Turn zwei, kein Problem. Wiederholung der Standardbegrüßung trotz spezifischer Frage. Besser wäre direkte Antwort. Turn drei, kein Problem. Direkte Antwort auf Öffnungszeitenfrage, korrekt. Turn zwei, ignorierte Frage. Wiederholung der Standardbegrüßung trotz klarer Öffnungszeitenfrage. Direkt auf die Frage antworten, statt Standardtext zu wiederholen.

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
        "phone_number": "+4915900000003",
        "shared_slots": {},
        "abuse_strikes": 0,
        "customer_name": null,
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": "+4915900000003",
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
          "Guten Tag und vielen Dank für Ihren Anruf bei DOBOO Korean Soulfood! Wie kann ich Ihnen heute helfen – möchten Sie einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage?",
          "Guten Tag, vielen Dank für Ihren Anruf bei DOBOO Korean Soulfood! Wie kann ich Ihnen heute helfen – möchten Sie einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage?",
          "Gerne helfe ich Ihnen weiter – könnten Sie mir bitte sagen, wobei ich Sie unterstützen kann, ob es um eine Reservierung, Bestellung oder eine allgemeine Frage geht? Ich bin hier, um Ihnen zu helfen!",
          "Sehr gerne – heute Freitag haben wir von 11:30 bis 23:00 Uhr für Sie geöffnet. Kann ich Ihnen noch bei etwas anderem helfen?",
          "Sehr gerne – heute Freitag haben wir von 11:30 bis 23:00 Uhr für Sie geöffnet. Kann ich Ihnen noch bei etwas anderem helfen?",
          "Ja, genau – ich habe Sie begrüßt und Sie über unsere heutigen Öffnungszeiten informiert. Wie kann ich Ihnen sonst noch weiterhelfen?"
        ],
        "reservation_date": "2026-05-01",
        "reservation_time": null,
        "delivery_intended": false,
        "ai_greeting_called": false,
        "current_intent_idx": null,
        "customer_confirmed": false,
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
            "bot": "Guten Tag, vielen Dank für Ihren Anruf bei DOBOO Korean Soulfood! Wie kann ich Ihnen heute helfen – möchten Sie einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage?",
            "node": "greeting",
            "customer": "Moment, ich verstehe nicht."
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter – könnten Sie mir bitte sagen, wobei ich Sie unterstützen kann, ob es um eine Reservierung, Bestellung oder eine allgemeine Frage geht? Ich bin hier, um Ihnen zu helfen!",
            "node": "greeting",
            "customer": "Ich möchte nur wissen, wann ihr heute geöffnet habt."
          },
          {
            "bot": "Sehr gerne – heute Freitag haben wir von 11:30 bis 23:00 Uhr für Sie geöffnet. Kann ich Ihnen noch bei etwas anderem helfen?",
            "node": "greeting",
            "customer": "Ich möchte wissen, wann ihr heute geöffnet habt."
          },
          {
            "bot": "Sehr gerne – heute Freitag haben wir von 11:30 bis 23:00 Uhr für Sie geöffnet. Kann ich Ihnen noch bei etwas anderem helfen?",
            "node": "greeting",
            "customer": "Turn eins, kein Problem. Begrüßung und Frage nach Anliegen, korrekt?"
          },
          {
            "bot": "Ja, genau – ich habe Sie begrüßt und Sie über unsere heutigen Öffnungszeiten informiert. Wie kann ich Ihnen sonst noch weiterhelfen?",
            "node": "greeting",
            "customer": "Turn zwei, kein Problem. Wiederholung der Standardbegrüßung trotz spezifischer Frage. Besser wäre direkte Antwort. Turn drei, kein Problem. Direkte Antwort auf Öffnungszeitenfrage, korrekt. Turn zwei, ignorierte Frage. Wiederholung der Standardbegrüßung trotz klarer Öffnungszeitenfrage. Direkt auf die Frage antworten, statt Standardtext zu wiederholen."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Hallo, guten Tag....'",
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
          "value": "+4915900000003",
          "status": "partial",
          "confidence": "high",
          "source_turn": 0,
          "raw_mentions": [
            "caller_id:+4915900000003"
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
        "Guten Tag und vielen Dank für Ihren Anruf bei DOBOO Korean Soulfood! Wie kann ich Ihnen heute helfen – möchten Sie einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage?",
        "Guten Tag, vielen Dank für Ihren Anruf bei DOBOO Korean Soulfood! Wie kann ich Ihnen heute helfen – möchten Sie einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage?",
        "Gerne h
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 4: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 5: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 6: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
