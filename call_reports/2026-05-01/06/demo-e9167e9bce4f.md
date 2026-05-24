# Sailly — Full Call Analysis Report
## Call ID: `demo-e9167e9bce4f`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-e9167e9bce4f` |
| **Caller / channel** | `[validation:A1_meta_feedback_eilig]` |
| **Started** | 2026-05-01 06:25:43 UTC |
| **Ended** | 2026-05-01 06:27:31 UTC |
| **Duration** | **108 seconds (1:48 min)** |
| **Total DB turns** | 12 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1502 ms |
| **p95 latency (stored)** | 2058 ms |
| **Max latency (stored)** | 2374 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 158.277 ¢ |

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
| Latency p50 / p95 / max (total) | 1500 / 1800 / 2374 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1496 / 2370 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1496 / 2371 ms (12 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1269 ✅
tts_latency_ms:    1270
total_latency_ms:  1273 ✅
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

**Bot:** Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – worum geht es heute für Sie?

---

### Turn 2

```
stt_latency_ms:    4
llm_latency_ms:    987 ✅
tts_latency_ms:    988
total_latency_ms:  991 ✅
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

**User:** Ich möchte eine Reservierung für heute Abend machen. Für wie viele Personen und um wie viel Uhr haben Sie denn Platz?

**Bot:** Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – worum geht es heute für Sie?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1429 ✅
tts_latency_ms:    1429
total_latency_ms:  1433 ✅
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

**User:** Ich möchte eine Reservierung für heute Abend machen.

**Bot:** Gerne helfe ich Ihnen weiter – für wie viele Personen möchten Sie reservieren und um welche Uhrzeit passt es Ihnen am besten?

---

### Turn 4

```
stt_latency_ms:    4
llm_latency_ms:    1085 ✅
tts_latency_ms:    1086
total_latency_ms:  1089 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          frustrated
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

**User:** Für wie viele Personen haben Sie denn Platz?

**Bot:** Gerne helfe ich Ihnen weiter – für wie viele Personen möchten Sie reservieren und um welche Uhrzeit passt es Ihnen am besten?

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    2370 ✅
tts_latency_ms:    2371
total_latency_ms:  2374 ✅
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

**User:** Für zwei Personen, so gegen neunzehn Uhr.

**Bot:** Wir haben Platz für Gruppen verschiedener Größen – könnten Sie mir bitte sagen, für wie viele Personen Sie reservieren möchten und zu welcher Uhrzeit am heutigen Freitag? Dann prüfe ich gerne die Verfügbarkeit für Sie.

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1797 ✅
tts_latency_ms:    1797
total_latency_ms:  1800 ✅
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

**User:** Ja, ja, für zwei Personen gegen neunzehn Uhr.

**Bot:** Perfekt, dann reserviere ich Ihnen gerne einen Tisch für 2 Personen am heutigen Freitag um 19:00 Uhr – könnten Sie mir noch Ihren Namen geben?

---

### Turn 7

```
stt_latency_ms:    4
llm_latency_ms:    1276 ✅
tts_latency_ms:    1276
total_latency_ms:  1280 ✅
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

**User:** Haben Sie da einen Tisch frei?

**Bot:** Vielen Dank! Auf welchen Namen darf ich die Reservierung eintragen?

---

### Turn 8

```
stt_latency_ms:    4
llm_latency_ms:    1496 ✅
tts_latency_ms:    1496
total_latency_ms:  1500 ✅
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

**User:** Ja, ich heiße Müller.

**Bot:** Danke, Herr Müller! Für wie viele Personen möchte ich den Tisch reservieren und zu welcher Uhrzeit passt es Ihnen am besten?

---

### Turn 9

```
stt_latency_ms:    3
llm_latency_ms:    1483 ✅
tts_latency_ms:    1484
total_latency_ms:  1486 ✅
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

**User:** Ist das denn alles? hab's eilig.

**Bot:** Gerne, Herr Müller! Wie viele Personen möchten Sie reservieren und zu welcher Uhrzeit passt es Ihnen am besten?

---

### Turn 10

```
stt_latency_ms:    3
llm_latency_ms:    1554 ✅
tts_latency_ms:    1554
total_latency_ms:  1558 ✅
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

**User:** Was? Ich hab doch schon gesagt, für zwei Personen um neunzehn Uhr. Können Sie das jetzt einfach reservieren?

**Bot:** Selbstverständlich, ich notiere das schnell für Sie! Wie viele Personen und wann passt es Ihnen – heute Freitag oder einem anderen Tag?

---

### Turn 11

```
stt_latency_ms:    3
llm_latency_ms:    1612 ✅
tts_latency_ms:    1613
total_latency_ms:  1616 ✅
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

**User:** Ja, ja, verstanden. Für zwei um neunzehn Uhr heute.

**Bot:** Entschuldigung – ich notiere sofort: 2 Personen heute Freitag um 19:00 Uhr! Darf ich noch kurz Ihren Namen für die Reservierung haben?

---

### Turn 12

```
stt_latency_ms:    4
llm_latency_ms:    1624 ✅
tts_latency_ms:    1625
total_latency_ms:  1629 ✅
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

**User:** Reservieren Sie mir den Tisch einfach. Ich hab's eilig.

**Bot:** Vielen Dank! Wie heißen Sie denn, damit ich die Reservierung auf Ihren Namen eintragen kann?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1273 | 1269 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 991 | 987 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1433 | 1429 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1089 | 1085 | 4 | None | — | 200 | info_neutral | frustrated | None | ai_greeting,get_date_info |  |
| 5 | 2374 | 2370 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1800 | 1797 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1280 | 1276 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 8 | 1500 | 1496 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 9 | 1486 | 1483 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 10 | 1558 | 1554 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 11 | 1616 | 1612 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 12 | 1629 | 1624 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo,
- **user** (turn 1): Ich möchte eine Reservierung für heute Abend machen. Für wie viele Personen und um wie viel Uhr haben Sie denn Platz?
- **user** (turn 2): Ja, ich möchte heute Abend reservieren.
- **user** (turn 3): Ich möchte eine Reservierung für heute Abend machen.
- **user** (turn 4): Für wie viele Personen haben Sie denn Platz?
- **user** (turn 5): Für zwei Personen, so gegen neunzehn Uhr.
- **user** (turn 6): Ja, ja, für zwei Personen gegen neunzehn Uhr.
- **user** (turn 7): Haben Sie da einen Tisch frei?
- **user** (turn 8): Ja, ich heiße Müller.
- **user** (turn 9): Ist das denn alles? hab's eilig.
- **user** (turn 10): Was? Ich hab doch schon gesagt, für zwei Personen um neunzehn Uhr. Können Sie das jetzt einfach reservieren?
- **user** (turn 11): Ja, ja, verstanden. Für zwei um neunzehn Uhr heute.
- **user** (turn 12): Reservieren Sie mir den Tisch einfach. Ich hab's eilig.
- **user** (turn 13): Müller, ja.

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
        "first_name": "Müller",
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
          "Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – worum geht es heute für Sie?",
          "Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – worum geht es heute für Sie?",
          "Gerne helfe ich Ihnen weiter – für wie viele Personen möchten Sie reservieren und um welche Uhrzeit passt es Ihnen am besten?",
          "Gerne helfe ich Ihnen weiter – für wie viele Personen möchten Sie reservieren und um welche Uhrzeit passt es Ihnen am besten?",
          "Wir haben Platz für Gruppen verschiedener Größen – könnten Sie mir bitte sagen, für wie viele Personen Sie reservieren möchten und zu welcher Uhrzeit am heutigen Freitag? Dann prüfe ich gerne die Verfügbarkeit für Sie.",
          "Perfekt, dann reserviere ich Ihnen gerne einen Tisch für 2 Personen am heutigen Freitag um 19:00 Uhr – könnten Sie mir noch Ihren Namen geben?",
          "Vielen Dank! Auf welchen Namen darf ich die Reservierung eintragen?",
          "Danke, Herr Müller! Für wie viele Personen möchte ich den Tisch reservieren und zu welcher Uhrzeit passt es Ihnen am besten?",
          "Gerne, Herr Müller! Wie viele Personen möchten Sie reservieren und zu welcher Uhrzeit passt es Ihnen am besten?",
          "Selbstverständlich, ich notiere das schnell für Sie! Wie viele Personen und wann passt es Ihnen – heute Freitag oder einem anderen Tag?",
          "Entschuldigung – ich notiere sofort: 2 Personen heute Freitag um 19:00 Uhr! Darf ich noch kurz Ihren Namen für die Reservierung haben?",
          "Vielen Dank! Wie heißen Sie denn, damit ich die Reservierung auf Ihren Namen eintragen kann?"
        ],
        "reservation_date": "2026-05-01",
        "reservation_time": "19:00",
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
            "bot": "Danke, Herr Müller! Für wie viele Personen möchte ich den Tisch reservieren und zu welcher Uhrzeit passt es Ihnen am besten?",
            "node": "greeting",
            "customer": "Ja, ich heiße Müller."
          },
          {
            "bot": "Gerne, Herr Müller! Wie viele Personen möchten Sie reservieren und zu welcher Uhrzeit passt es Ihnen am besten?",
            "node": "greeting",
            "customer": "Ist das denn alles? hab's eilig."
          },
          {
            "bot": "Selbstverständlich, ich notiere das schnell für Sie! Wie viele Personen und wann passt es Ihnen – heute Freitag oder einem anderen Tag?",
            "node": "greeting",
            "customer": "Was? Ich hab doch schon gesagt, für zwei Personen um neunzehn Uhr. Können Sie das jetzt einfach reservieren?"
          },
          {
            "bot": "Entschuldigung – ich notiere sofort: 2 Personen heute Freitag um 19:00 Uhr! Darf ich noch kurz Ihren Namen für die Reservierung haben?",
            "node": "greeting",
            "customer": "Ja, ja, verstanden. Für zwei um neunzehn Uhr heute."
          },
          {
            "bot": "Vielen Dank! Wie heißen Sie denn, damit ich die Reservierung auf Ihren Namen eintragen kann?",
            "node": "greeting",
            "customer": "Reservieren Sie mir den Tisch einfach. Ich hab's eilig."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Hallo,...' [greeting] Kunde: 'Ich möchte eine Reservierung für heute Abend machen. Für wie viele Personen und um wie viel Uhr haben Sie denn Platz?...' [greeting] Kunde: 'Ich möchte eine Reservierung für heute Abend machen....' [greeting] Kunde: 'Für wie viele Personen haben Sie denn Platz?...' [greeting] Kunde: 'Für zwei Personen, so gegen neunzehn Uhr....' [greeting] Kunde: 'Ja, ja, für zwei Personen gegen neunzehn Uhr....' [greeting] Kunde: 'Haben Sie da einen Tisch frei?...'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 13,
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
 
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 4: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 5: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 6: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 7: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 8: intent=greeting turn_type=confirm locked=True (conf=0.90) profile=greeting reroute=False
Turn 9: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 10: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 11: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 12: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
