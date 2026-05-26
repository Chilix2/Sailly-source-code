# Sailly — Full Call Analysis Report
## Call ID: `demo-d1fb97b5ecd8`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-d1fb97b5ecd8` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-04-29 15:22:13 UTC |
| **Ended** | 2026-04-29 15:25:20 UTC |
| **Duration** | **187 seconds (3:07 min)** |
| **Total DB turns** | 5 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1401 ms |
| **p95 latency (stored)** | 2298 ms |
| **Max latency (stored)** | 2494 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 268.6978 ¢ |

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
| Latency p50 / p95 / max (total) | 1235 / 2494 / 2494 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1231 / 2490 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | ['ERR_STRICT_GATE_FAILED'] | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | None / None ms (0 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    2490 ✅
tts_latency_ms:    0
total_latency_ms:  2494 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1803 / None / 685 / 666
tts_situation:     greeting_first
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info', 'ai_greeting', 'get_weather', 'check_availability', 'create_reservation', 'send_sms']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       ['ERR_STRICT_GATE_FAILED']
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Hallo, Sally. Wie ist das Wetter heute bei euch und habt ihr heute Abend noch einen Tisch für zwei Personen um neunzehn Uhr frei?

**Bot:** In Bonn ist es gerade 20.0°C, Klar.

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    1508 ✅
tts_latency_ms:    0
total_latency_ms:  1512 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1599 / None / 2 / None
tts_situation:     confirm_success
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      []
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Sally, Achtung, Du hast jetzt siebenmal direkt hintereinander, alles klar, einen Augenblick noch wiederholt. Das ist eine massive Schleife und

**Bot:** Sie haben völlig recht — Entschuldigung für die Wiederholungen, das war nicht okay. Lassen Sie mich neu anfangen: Wie ist das Wetter bei Ihnen, und für wann genau möchten Sie den Tisch reservieren?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    961 ✅
tts_latency_ms:    0
total_latency_ms:  964 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1009 / None / 27 / None
tts_situation:     confirm_success
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      []
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Roboter habt.

**Bot:** Ja, ich bin Sailly, die KI-Assistentin vom DOBOO — und ich helfe gerne weiter, womit kann ich für Sie tun?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    795 ✅
tts_latency_ms:    0
total_latency_ms:  799 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1349 / None / 27 / None
tts_situation:     confirm_success
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      []
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Sally, Achtung, jetzt hast Du gleich mehrere Sachen auf einmal vermasselt. Du hast mich gefragt, wie das Wetter bei mir ist. Das ergibt keinen Sinn. Ich hab dich gern gerufen. Du hast dich als Sally von Duolingo vorgestellt. Komplett falsch. Die Formulierung, womit kann ich für Sie tun, ist grammatikalisch falsch. Das war ziemlich chaotisch.

**Bot:** Sie haben völlig recht, entschuldigen Sie — das war wirklich nicht okay. Ich bin Sailly, die KI-Assistentin vom DOBOO Korean Soulfood hier in Bonn, und ich hätte das von Anfang an klar sagen sollen. Was kann ich für Sie tun?

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    1231 ✅
tts_latency_ms:    0
total_latency_ms:  1235 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1295 / None / 38 / None
tts_situation:     confirm_success
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['technical_issues_callback', 'end_call']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Sally, Achtung, Du hast dich schon wieder falsch vorgestellt. Du bist Sally, nicht Sally. Außerdem klingt, was kann ich für Sie tun, nach dem, was gerade passiert ist, immer noch sehr mechanisch. Ein Mensch würde nach so einem Fehler eher etwas Wärmeres oder Persönlicheres sagen.

**Bot:** Sie haben völlig recht, entschuldigen Sie — das war wirklich chaotisch von mir. Ich bin Sailly, die KI-Assistentin vom DOBOO, und ich habe da gerade einiges durcheinander gebracht. Wie kann ich es besser machen?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 2494 | 2490 | 3 | None | — | 200 | greeting_first | neutral | None | get_date_info,ai_greeting,get_weather,check_availability,create_reservation,send_sms |  |
| 2 | 1512 | 1508 | 3 | None | — | 200 | confirm_success | neutral | None | — |  |
| 3 | 964 | 961 | 3 | None | — | 200 | confirm_success | neutral | None | — |  |
| 4 | 799 | 795 | 3 | None | — | 200 | confirm_success | neutral | None | — |  |
| 5 | 1235 | 1231 | 3 | None | — | 200 | confirm_success | neutral | None | technical_issues_callback,end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?
- **user** (turn 1): Hallo, Sally. Wie ist das Wetter heute bei euch und habt ihr heute Abend noch einen Tisch für zwei Personen um neunzehn Uhr frei?
- **user** (turn 2): Sally, Achtung, Du hast jetzt siebenmal direkt hintereinander, alles klar, einen Augenblick noch wiederholt. Das ist eine massive Schleife und
- **user** (turn 3): Roboter habt.
- **user** (turn 4): Sally, Achtung, jetzt hast Du gleich mehrere Sachen auf einmal vermasselt. Du hast mich gefragt, wie das Wetter bei mir ist. Das ergibt keinen Sinn. Ich hab dich gern gerufen. Du hast dich als Sally von Duolingo vorgestellt. Komplett falsch. Die Formulierung, womit kann ich für Sie tun, ist grammatikalisch falsch. Das war ziemlich chaotisch.
- **user** (turn 5): Sally, Achtung, Du hast dich schon wieder falsch vorgestellt. Du bist Sally, nicht Sally. Außerdem klingt, was kann ich für Sie tun, nach dem, was gerade passiert ist, immer noch sehr mechanisch. Ein Mensch würde nach so einem Fehler eher etwas Wärmeres oder Persönlicheres sagen.

---

## 7. Tool calls (`google_tool_calls`)

- `get_weather` @ turn 0 — success=None — {'temperature': 20.0, 'description': 'Klar', 'location': 'Bonn', 'source': 'Open Meteo', 'outdoor_recommendation': 'Ja, Terrasse ist empfehlenswert!', 'message': 'In Bonn: 20.0°C, Klar. Terrasse mö...
- `technical_issues_callback` @ turn 1 — success=None — {'status': 'logged', 'message': 'Das technische Problem wurde gemeldet. Ein Mitarbeiter wird sich bei Ihnen melden.', 'issue': 'technisches Problem'}

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
        "recent_responses": [
          "In Bonn ist es gerade 20.0°C, Klar.",
          "Da bin ich leider nicht die Richtige — aber beim Essen oder Reservieren helfe ich Ihnen gerne!",
          "Da bin ich leider nicht die Richtige — aber beim Essen oder Reservieren helfe ich Ihnen gerne!",
          "Da bin ich leider nicht die Richtige — aber beim Essen oder Reservieren helfe ich Ihnen gerne!",
          "Ich komme gerade leider nicht weiter. Ich lasse einen Kollegen bei Ihnen zurückrufen, damit wir das in Ruhe regeln können."
        ],
        "reservation_date": "2026-04-29",
        "reservation_time": "19:00",
        "delivery_intended": false,
        "ai_greeting_called": true,
        "current_intent_idx": null,
        "customer_confirmed": false,
        "get_weather_called": true,
        "reservation_intent": true,
        "validation_entries": {},
        "cached_menu_at_turn": null,
        "caller_id_confirmed": false,
        "caller_said_goodbye": false,
        "reservation_created": true,
        "bulk_order_confirmed": false,
        "cached_menu_metadata": {},
        "escalation_requested": false,
        "get_date_info_called": true,
        "verify_address_called": false,
        "verify_address_failed": false,
        "multi_intent_completed": false,
        "failed_intent_summaries": [],
        "request_callback_called": true,
        "transfer_to_tier2_called": false,
        "check_availability_called": true,
        "pending_bulk_confirmation": false,
        "delivery_address_mentioned": false,
        "last_caller_confirmation_turn": null
      },
      "memory": {
        "recent_turns": [
          {
            "bot": "[TOOL:get_date_info] [TOOL:ai_greeting] [TOOL:get_weather] [TOOL:check_availability]\n[TOOL:create_reservation]\n[TOOL:send_sms]\nHallo, hier ist Sailly Ihre digitale KI vom DOBOO - Korean Soulfood. Ihre Reservierung für 2 Personen am Heute um 19:00 Uhr ist bestätigt. Sie erhalten eine Bestätigung per SMS.",
            "node": "greeting",
            "customer": "Hallo, Sally. Wie ist das Wetter heute bei euch und habt ihr heute Abend noch einen Tisch für zwei Personen um neunzehn Uhr frei?"
          },
          {
            "bot": "Da bin ich leider nicht die Richtige — aber beim Essen oder Reservieren helfe ich Ihnen gerne!",
            "node": "greeting",
            "customer": "Sally, Achtung, Du hast jetzt siebenmal direkt hintereinander, alles klar, einen Augenblick noch wiederholt. Das ist eine massive Schleife und"
          },
          {
            "bot": "Da bin ich leider nicht die Richtige — aber beim Essen oder Reservieren helfe ich Ihnen gerne!",
            "node": "greeting",
            "customer": "Roboter habt."
          },
          {
            "bot": "Da bin ich leider nicht die Richtige — aber beim Essen oder Reservieren helfe ich Ihnen gerne!",
            "node": "greeting",
            "customer": "Sally, Achtung, jetzt hast Du gleich mehrere Sachen auf einmal vermasselt. Du hast mich gefragt, wie das Wetter bei mir ist. Das ergibt keinen Sinn. Ich hab dich gern gerufen. Du hast dich als Sally von Duolingo vorgestellt. Komplett falsch. Die Formulierung, womit kann ich für Sie tun, ist grammatikalisch falsch. Das war ziemlich chaotisch."
          },
          {
            "bot": "Ich komme gerade leider nicht weiter. Ich lasse einen Kollegen bei Ihnen zurückrufen, damit wir das in Ruhe regeln können.\n[TOOL:technical_issues_callback]\n[TOOL:end_call]",
            "node": "greeting",
            "customer": "Sally, Achtung, Du hast dich schon wieder falsch vorgestellt. Du bist Sally, nicht Sally. Außerdem klingt, was kann ich für Sie tun, nach dem, was gerade passiert ist, immer noch sehr mechanisch. Ein Mensch würde nach so einem Fehler eher etwas Wärmeres oder Persönlicheres sagen."
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
      "turn_idx": 5,
      "all_tools": [
        "get_date_info",
        "ai_greeting",
        "get_weather",
        "check_availability",
        "create_reservation",
        "send_sms",
        "technical_issues_callback",
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
      "recent_responses": [
        "In Bonn ist es gerade 20.0°C, Klar.",
        "Da bin ich leider nicht die Richtige — aber beim Essen oder Reservieren helfe ich Ihnen gerne!",
        "Da bin ich leider nicht die Richtige — aber beim Essen oder Reservieren helfe ich Ihnen gerne!",
        "Da bin ich leider nicht die Richtige — aber beim Essen oder Reservieren helfe ich Ihnen gerne!",
        "Ich komme gerade leider nicht weiter. Ich lasse einen Kollegen bei Ihnen zurückrufen, damit wir das in Ruhe regeln können."
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-d1fb97b5ecd8",
  "ended_at": "2026-04-29T17:25:20.315141+02:00",
  "started_at": "2026-04-29T17:22:13.056243+02:00",
  "started_ts": 1777476133.0562792,
  "tool_calls": [
    {
      "args": {
        "location": "Bonn"
      },
      "tool": "get_weather",
      "timestamp": "2026-04-29T17:22:39.401104+02:00",
      "duration_ms": 0,
      "result_summary": "{'temperature': 20.0, 'description': 'Klar', 'location': 'Bonn', 'source': 'Open Meteo', 'outdoor_recommendation': 'Ja, Terrasse ist empfehlenswert!', 'message': 'In Bonn: 20.0°C, Klar. Terr
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
# (no context documents for this call — predates v4 migration)
```

_(no context documents for this call — predates v4 migration)_

---

## 9. Auto-generated observations

- **Error codes present**: ['ERR_STRICT_GATE_FAILED'].

---

_Report end._
