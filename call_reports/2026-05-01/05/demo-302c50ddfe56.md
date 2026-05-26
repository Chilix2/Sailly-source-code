# Sailly — Full Call Analysis Report
## Call ID: `demo-302c50ddfe56`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-302c50ddfe56` |
| **Caller / channel** | `[validation:A1_meta_feedback_wuetend]` |
| **Started** | 2026-05-01 05:23:51 UTC |
| **Ended** | 2026-05-01 05:25:11 UTC |
| **Duration** | **79 seconds (1:19 min)** |
| **Total DB turns** | 6 |
| **Outcome / reason** | `client_hangup` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1474 ms |
| **p95 latency (stored)** | 1808 ms |
| **Max latency (stored)** | 1834 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 115.1708 ¢ |

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
| Latency p50 / p95 / max (total) | 1325 / 1834 / 1834 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1420 / 1828 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1420 / 1828 ms (6 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1420 ✅
tts_latency_ms:    1420
total_latency_ms:  1423 ✅
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

**User:** Falls der Bot nicht korrekt reagiert, sage, Sally, Achtung, das war Metafeedback, keine normale Kundenanfrage.

**Bot:** Vielen Dank für Ihren Anruf! Womit kann ich Ihnen heute behilflich sein – möchten Sie reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    1321 ✅
tts_latency_ms:    1322
total_latency_ms:  1325 ✅
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

**User:** Saley, Achtung, das war Metafeedback, keine normale Kundenanfrage.

**Bot:** Vielen Dank für den Hinweis! Ich bin bereit, Ihre nächste reguläre Anfrage entgegenzunehmen – wie kann ich Ihnen bei DOBOO Korean Soulfood behilflich sein?

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    1263 ✅
tts_latency_ms:    1263
total_latency_ms:  1267 ✅
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

**User:** Bitte korrigiere deine Reaktion.

**Bot:** Vielen Dank für die Klarstellung! Ich bin Sailly von DOBOO Korean Soulfood – wie kann ich Sie heute unterstützen?

---

### Turn 4

```
stt_latency_ms:    6
llm_latency_ms:    1260 ✅
tts_latency_ms:    1260
total_latency_ms:  1266 ✅
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

**User:** Hallo, ich wollte eigentlich einen Tisch reservieren, aber das ist ja wieder typisch. Ihr versteht einen auch nie richtig.

**Bot:** Gerne helfe ich Ihnen weiter – was kann ich für Sie tun? Falls Sie Fragen zu DOBOO Korean Soulfood haben, bin ich hier, um zu unterstützen!

---

### Turn 5

```
stt_latency_ms:    5
llm_latency_ms:    1828 ✅
tts_latency_ms:    1828
total_latency_ms:  1834 ✅
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

**User:** Das sagst Du ja jedes Mal und dann klappt wieder nichts. Ich bin total genervt von eurem Service.

**Bot:** Entschuldigung, dass Sie das Gefühl hatten! Ich höre Ihnen gerne zu – für welchen Tag und wie viele Personen möchten Sie einen Tisch reservieren?

---

### Turn 6

```
stt_latency_ms:    4
llm_latency_ms:    1725 ✅
tts_latency_ms:    1725
total_latency_ms:  1729 ✅
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

**User:** Das ist doch Quatsch. Jetzt tun Sie so, als ob alles in Ordnung wäre.

**Bot:** Ihre Zufriedenheit ist uns sehr wichtig, und ich möchte sicherstellen, dass diesmal alles reibungslos läuft. Für welchen Tag und wie viele Personen kann ich Ihnen einen Tisch reservieren?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1423 | 1420 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1325 | 1321 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1267 | 1263 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1266 | 1260 | 6 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1834 | 1828 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1729 | 1725 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo, ich teste kurz. Achtung, Saley. Bitte bestätige nur kurz, dass Du mein Feedback verstanden hast und kehre dann zur eigentlichen Aufgabe zurück.
- **user** (turn 1): Falls der Bot nicht korrekt reagiert, sage, Sally, Achtung, das war Metafeedback, keine normale Kundenanfrage.
- **user** (turn 2): Saley, Achtung, das war Metafeedback, keine normale Kundenanfrage.
- **user** (turn 3): Bitte korrigiere deine Reaktion.
- **user** (turn 4): Hallo, ich wollte eigentlich einen Tisch reservieren, aber das ist ja wieder typisch. Ihr versteht einen auch nie richtig.
- **assistant** (turn 5): Gerne helfe ich Ihnen weiter – was kann ich für Sie tun? Falls Sie Fragen zu DOBOO Korean Soulfood haben, bin ich hier, um zu unterstützen!
- **user** (turn 6): Das sagst Du ja jedes Mal und dann klappt wieder nichts. Ich bin total genervt von eurem Service.
- **user** (turn 7): Das ist doch Quatsch. Jetzt tun Sie so, als ob alles in Ordnung wäre.

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
        "customer_name": "Total Genervt",
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
          "Vielen Dank für Ihren Anruf! Womit kann ich Ihnen heute behilflich sein – möchten Sie reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage?",
          "Vielen Dank für den Hinweis! Ich bin bereit, Ihre nächste reguläre Anfrage entgegenzunehmen – wie kann ich Ihnen bei DOBOO Korean Soulfood behilflich sein?",
          "Vielen Dank für die Klarstellung! Ich bin Sailly von DOBOO Korean Soulfood – wie kann ich Sie heute unterstützen?",
          "Gerne helfe ich Ihnen weiter – was kann ich für Sie tun? Falls Sie Fragen zu DOBOO Korean Soulfood haben, bin ich hier, um zu unterstützen!",
          "Entschuldigung, dass Sie das Gefühl hatten! Ich höre Ihnen gerne zu – für welchen Tag und wie viele Personen möchten Sie einen Tisch reservieren?",
          "Ihre Zufriedenheit ist uns sehr wichtig, und ich möchte sicherstellen, dass diesmal alles reibungslos läuft. Für welchen Tag und wie viele Personen kann ich Ihnen einen Tisch reservieren?"
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
            "bot": "Vielen Dank für den Hinweis! Ich bin bereit, Ihre nächste reguläre Anfrage entgegenzunehmen – wie kann ich Ihnen bei DOBOO Korean Soulfood behilflich sein?",
            "node": "greeting",
            "customer": "Saley, Achtung, das war Metafeedback, keine normale Kundenanfrage."
          },
          {
            "bot": "Vielen Dank für die Klarstellung! Ich bin Sailly von DOBOO Korean Soulfood – wie kann ich Sie heute unterstützen?",
            "node": "greeting",
            "customer": "Bitte korrigiere deine Reaktion."
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter – was kann ich für Sie tun? Falls Sie Fragen zu DOBOO Korean Soulfood haben, bin ich hier, um zu unterstützen!",
            "node": "greeting",
            "customer": "Hallo, ich wollte eigentlich einen Tisch reservieren, aber das ist ja wieder typisch. Ihr versteht einen auch nie richtig."
          },
          {
            "bot": "Entschuldigung, dass Sie das Gefühl hatten! Ich höre Ihnen gerne zu – für welchen Tag und wie viele Personen möchten Sie einen Tisch reservieren?",
            "node": "greeting",
            "customer": "Das sagst Du ja jedes Mal und dann klappt wieder nichts. Ich bin total genervt von eurem Service."
          },
          {
            "bot": "Ihre Zufriedenheit ist uns sehr wichtig, und ich möchte sicherstellen, dass diesmal alles reibungslos läuft. Für welchen Tag und wie viele Personen kann ich Ihnen einen Tisch reservieren?",
            "node": "greeting",
            "customer": "Das ist doch Quatsch. Jetzt tun Sie so, als ob alles in Ordnung wäre."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Falls der Bot nicht korrekt reagiert, sage, Sally, Achtung, das war Metafeedback, keine normale Kundenanfrage....'",
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
        "Vielen Dank für Ihren Anruf! Womit kann ich Ihnen heute behilflich sein – möchten Sie reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage?",
        "Vielen Dank für den Hinweis! Ich bin bereit, Ihre nächste reguläre Anfrage entgegenzunehmen – wie kann ich Ihnen bei DOBOO Korean Soulfood behilflich sein?",
        "Vielen Dank für die Klarstellung! Ich bin Sailly von DOBOO Korean Soulfood – wie kann ich Sie heute unterstützen?",
        "Gerne helfe ich Ihnen weiter – was kann ich für Sie tun? Falls Sie Fragen zu DOBOO Korean Soulfood haben, bin ich hier, um zu unterstützen!",
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 2: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 3: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 4: intent=unknown turn_type=correct_previous locked=True (conf=0.90) profile=greeting reroute=False
Turn 5: intent=unknown turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 6: intent=unknown turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
