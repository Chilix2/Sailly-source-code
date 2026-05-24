# Sailly — Full Call Analysis Report
## Call ID: `demo-4ac8d26a034c`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-4ac8d26a034c` |
| **Caller / channel** | `[validation:A1_meta_feedback_neutral]` |
| **Started** | 2026-05-01 06:45:38 UTC |
| **Ended** | 2026-05-01 06:47:25 UTC |
| **Duration** | **107 seconds (1:47 min)** |
| **Total DB turns** | 13 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1280 ms |
| **p95 latency (stored)** | 1763 ms |
| **Max latency (stored)** | 1959 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 156.1362 ¢ |

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
| Latency p50 / p95 / max (total) | 1198 / 1632 / 1959 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1194 / 1953 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1195 / 1953 ms (13 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    896 ✅
tts_latency_ms:    896
total_latency_ms:  900 ✅
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

**Bot:** Guten Tag! Ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute unterstützen?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    1083 ✅
tts_latency_ms:    1084
total_latency_ms:  1087 ✅
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

**User:** Hallo, ich würde gerne einen Tisch für zwei Personen reservieren. Für wann hätten Sie noch etwas frei?

**Bot:** Gerne helfe ich Ihnen weiter – was möchten Sie über DOBOO Korean Soulfood erfahren?

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    1331 ✅
tts_latency_ms:    1332
total_latency_ms:  1336 ✅
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

**User:** Ich möchte einen Tisch für zwei Personen reservieren.

**Bot:** Sehr gerne! Für welche Uhrzeit und welchen Tag würden Sie gerne einen Tisch für zwei Personen reservieren?

---

### Turn 4

```
stt_latency_ms:    6
llm_latency_ms:    1953 ✅
tts_latency_ms:    1953
total_latency_ms:  1959 ✅
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

**User:** Haben Sie heute Abend noch etwas frei?

**Bot:** Gerne helfe ich Ihnen weiter! Für welchen Tag und zu welcher Uhrzeit möchten Sie den Tisch reservieren?

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    1381 ✅
tts_latency_ms:    1381
total_latency_ms:  1385 ✅
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

**User:** Heute Abend um neunzehn Uhr.

**Bot:** Sie möchten heute Freitag Abend reservieren – zu welcher Uhrzeit passt es Ihnen am besten und für wie viele Personen?

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1362 ✅
tts_latency_ms:    1363
total_latency_ms:  1366 ✅
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

**User:** Passt es bei Ihnen?

**Bot:** Perfekt, heute Freitag um 19:00 Uhr – für wie viele Personen möchte ich die Reservierung vornehmen?

---

### Turn 7

```
stt_latency_ms:    3
llm_latency_ms:    1078 ✅
tts_latency_ms:    1079
total_latency_ms:  1081 ✅
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

**User:** Heute Abend für zwei Personen um neunzehn Uhr.

**Bot:** Gerne helfe ich Ihnen weiter – für wie viele Personen darf ich die Reservierung vornehmen?

---

### Turn 8

```
stt_latency_ms:    10
llm_latency_ms:    1621 ✅
tts_latency_ms:    1621
total_latency_ms:  1632 ✅
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

**User:** Passt es bei Ihnen?

**Bot:** Perfekt, ich reserviere einen Tisch für zwei Personen heute um 19:00 Uhr – darf ich bitte Ihren Namen für die Reservierung haben?

---

### Turn 9

```
stt_latency_ms:    3
llm_latency_ms:    1194 ✅
tts_latency_ms:    1195
total_latency_ms:  1198 ✅
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

**User:** Für zwei Personen.

**Bot:** Gerne, unter welchem Namen darf ich die Reservierung für Sie eintragen?

---

### Turn 10

```
stt_latency_ms:    5
llm_latency_ms:    1191 ✅
tts_latency_ms:    1191
total_latency_ms:  1197 ✅
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

**User:** Heute Abend um neunzehn Uhr.

**Bot:** Vielen Dank! Unter welchem Namen darf ich die Reservierung für Sie eintragen?

---

### Turn 11

```
stt_latency_ms:    3
llm_latency_ms:    1119 ✅
tts_latency_ms:    1120
total_latency_ms:  1123 ✅
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

**User:** Müller. Pastas?

**Bot:** Gerne! Unter welchem Namen darf ich die Reservierung für Sie eintragen?

---

### Turn 12

```
stt_latency_ms:    4
llm_latency_ms:    1337 ✅
tts_latency_ms:    1337
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

**User:** Miller. Können Sie das notieren?

**Bot:** Sehr gerne, Herr Müller! Für wann und für wie viele Personen möchte ich die Reservierung eintragen?

---

### Turn 13

```
stt_latency_ms:    4
llm_latency_ms:    1034 ✅
tts_latency_ms:    1034
total_latency_ms:  1038 ✅
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

**User:** Heute Abend um neunzehn Uhr für zwei Personen. Haben Sie da noch etwas frei?

**Bot:** Sehr gerne, Herr Miller! Für wann und für wie viele Personen möchte ich die Reservierung eintragen?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 900 | 896 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1087 | 1083 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1336 | 1331 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1959 | 1953 | 6 | None | — | 200 | info_neutral | frustrated | None | ai_greeting,get_date_info |  |
| 5 | 1385 | 1381 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1366 | 1362 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1081 | 1078 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 8 | 1632 | 1621 | 10 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 9 | 1198 | 1194 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 10 | 1197 | 1191 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 11 | 1123 | 1119 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 12 | 1342 | 1337 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 13 | 1038 | 1034 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo,
- **user** (turn 1): Ich hätte gern einen Tisch für zwei Personen reserviert. Für wann hätten Sie noch etwas frei?
- **user** (turn 2): Hallo, ich würde gerne einen Tisch für zwei Personen reservieren. Für wann hätten Sie noch etwas frei?
- **user** (turn 3): Ich möchte einen Tisch für zwei Personen reservieren.
- **user** (turn 4): Haben Sie heute Abend noch etwas frei?
- **user** (turn 5): Heute Abend um neunzehn Uhr.
- **user** (turn 6): Passt es bei Ihnen?
- **assistant** (turn 7): Perfekt, heute Freitag um 19:00 Uhr – für wie viele Personen möchte ich die Reservierung vornehmen?
- **user** (turn 8): Heute Abend für zwei Personen um neunzehn Uhr.
- **user** (turn 9): Passt es bei Ihnen?
- **user** (turn 10): Für zwei Personen.
- **user** (turn 11): Heute Abend um neunzehn Uhr.
- **user** (turn 12): Müller. Pastas?
- **user** (turn 13): Miller. Können Sie das notieren?
- **user** (turn 14): Heute Abend um neunzehn Uhr für zwei Personen. Haben Sie da noch etwas frei?

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
        "customer_name": "Müller Pastas",
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": "+4915900000001",
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Guten Tag! Ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute unterstützen?",
          "Guten Tag! Ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute unterstützen?",
          "Gerne helfe ich Ihnen weiter – was möchten Sie über DOBOO Korean Soulfood erfahren?",
          "Sehr gerne! Für welche Uhrzeit und welchen Tag würden Sie gerne einen Tisch für zwei Personen reservieren?",
          "Gerne helfe ich Ihnen weiter! Für welchen Tag und zu welcher Uhrzeit möchten Sie den Tisch reservieren?",
          "Sie möchten heute Freitag Abend reservieren – zu welcher Uhrzeit passt es Ihnen am besten und für wie viele Personen?",
          "Perfekt, heute Freitag um 19:00 Uhr – für wie viele Personen möchte ich die Reservierung vornehmen?",
          "Gerne helfe ich Ihnen weiter – für wie viele Personen darf ich die Reservierung vornehmen?",
          "Perfekt, ich reserviere einen Tisch für zwei Personen heute um 19:00 Uhr – darf ich bitte Ihren Namen für die Reservierung haben?",
          "Gerne, unter welchem Namen darf ich die Reservierung für Sie eintragen?",
          "Vielen Dank! Unter welchem Namen darf ich die Reservierung für Sie eintragen?",
          "Gerne! Unter welchem Namen darf ich die Reservierung für Sie eintragen?",
          "Sehr gerne, Herr Müller! Für wann und für wie viele Personen möchte ich die Reservierung eintragen?",
          "Sehr gerne, Herr Miller! Für wann und für wie viele Personen möchte ich die Reservierung eintragen?"
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
            "bot": "Gerne, unter welchem Namen darf ich die Reservierung für Sie eintragen?",
            "node": "greeting",
            "customer": "Für zwei Personen."
          },
          {
            "bot": "Vielen Dank! Unter welchem Namen darf ich die Reservierung für Sie eintragen?",
            "node": "greeting",
            "customer": "Heute Abend um neunzehn Uhr."
          },
          {
            "bot": "Gerne! Unter welchem Namen darf ich die Reservierung für Sie eintragen?",
            "node": "greeting",
            "customer": "Müller. Pastas?"
          },
          {
            "bot": "Sehr gerne, Herr Müller! Für wann und für wie viele Personen möchte ich die Reservierung eintragen?",
            "node": "greeting",
            "customer": "Miller. Können Sie das notieren?"
          },
          {
            "bot": "Sehr gerne, Herr Miller! Für wann und für wie viele Personen möchte ich die Reservierung eintragen?",
            "node": "greeting",
            "customer": "Heute Abend um neunzehn Uhr für zwei Personen. Haben Sie da noch etwas frei?"
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Hallo,...' [greeting] Kunde: 'Hallo, ich würde gerne einen Tisch für zwei Personen reservieren. Für wann hätten Sie noch etwas frei?...' [greeting] Kunde: 'Ich möchte einen Tisch für zwei Personen reservieren....' [greeting] Kunde: 'Haben Sie heute Abend noch etwas frei?...' [greeting] Kunde: 'Heute Abend um neunzehn Uhr....' [greeting] Kunde: 'Passt es bei Ihnen?...' [greeting] Kunde: 'Heute Abend für zwei Personen um neunzehn Uhr....' [greeting] Kunde: 'Passt es bei Ihnen?...'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 14,
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
        "Guten Tag! Ich bin Sa
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=finalize locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=greeting turn_type=finalize locked=True (conf=0.90) profile=greeting reroute=False
Turn 4: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 5: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 6: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 7: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 8: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 9: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 10: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 11: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 12: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 13: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
