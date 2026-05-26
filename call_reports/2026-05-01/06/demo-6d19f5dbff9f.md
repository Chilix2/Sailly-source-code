# Sailly — Full Call Analysis Report
## Call ID: `demo-6d19f5dbff9f`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-6d19f5dbff9f` |
| **Caller / channel** | `[validation:A1_meta_feedback_aeltere_person]` |
| **Started** | 2026-05-01 06:21:35 UTC |
| **Ended** | 2026-05-01 06:23:25 UTC |
| **Duration** | **109 seconds (1:49 min)** |
| **Total DB turns** | 13 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1755 ms |
| **p95 latency (stored)** | 2630 ms |
| **Max latency (stored)** | 3079 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 161.0658 ¢ |

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
| Latency p50 / p95 / max (total) | 1670 / 2330 / 3079 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1665 / 3071 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1666 / 3072 ms (13 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    12
llm_latency_ms:    819 ✅
tts_latency_ms:    819
total_latency_ms:  832 ✅
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

**User:** Für zwei Personen, heute Abend.

**Bot:** Guten Tag! Wie kann ich Sie bei DOBOO Korean Soulfood unterstützen?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    1593 ✅
tts_latency_ms:    1597
total_latency_ms:  1596 ✅
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

**User:** Ach, Moment, ich verstehe nicht ganz.

**Bot:** Gerne helfe ich Ihnen weiter! Um Ihnen einen Tisch für zwei Personen heute Abend zu reservieren, benötige ich noch die gewünschte Uhrzeit – wann würden Sie gerne bei uns vorbeikommen?

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    1882 ✅
tts_latency_ms:    1882
total_latency_ms:  1886 ✅
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

**User:** Ich wollte einen Tisch reservieren für heute Abend.

**Bot:** Selbstverständlich, gerne erkläre ich das nochmal: Für Ihre Reservierung brauchen wir nur noch zu wissen, um wie viel Uhr Sie heute Abend bei uns essen möchten. Welche Uhrzeit passt Ihnen am besten?

---

### Turn 4

```
stt_latency_ms:    5
llm_latency_ms:    1665 ✅
tts_latency_ms:    1666
total_latency_ms:  1670 ✅
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

**User:** Können Sie mir da helfen?

**Bot:** Gerne helfe ich Ihnen mit der Reservierung – können Sie mir noch sagen, zu welcher Uhrzeit Sie heute bei uns vorbeischauen möchten? Für wie viele Personen soll der Tisch sein?

---

### Turn 5

```
stt_latency_ms:    12
llm_latency_ms:    2317 ✅
tts_latency_ms:    2318
total_latency_ms:  2330 ✅
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

**User:** Ja, also Moment, ich komme um sieben Uhr. Ist das möglich?

**Bot:** Gerne helfe ich Ihnen mit der Reservierung – können Sie mir noch sagen, zu welcher Uhrzeit Sie heute bei uns vorbeischauen möchten? Für wie viele Personen soll der Tisch sein?

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1556 ✅
tts_latency_ms:    1556
total_latency_ms:  1559 ✅
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

**User:** Moment, ich hab doch gerade gesagt um sieben Uhr.

**Bot:** Sehr gerne, um 19:00 Uhr am heutigen Freitag ist möglich – für wie viele Personen darf ich den Tisch reservieren?

---

### Turn 7

```
stt_latency_ms:    5
llm_latency_ms:    1364 ✅
tts_latency_ms:    1364
total_latency_ms:  1369 ✅
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

**User:** Für zwei Personen. Ist das in Ordnung?

**Bot:** Entschuldigen Sie, ich habe das verstanden – 19:00 Uhr am heutigen Freitag ist perfekt für Sie. Für wie viele Personen soll ich den Tisch reservieren?

---

### Turn 8

```
stt_latency_ms:    3
llm_latency_ms:    1423 ✅
tts_latency_ms:    1424
total_latency_ms:  1427 ✅
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

**User:** Für zwei Personen. Haben Sie das nicht verstanden?

**Bot:** Wunderbar, ich reserviere Ihnen gerne einen Tisch für 2 Personen um 19:00 Uhr am heutigen Freitag. Darf ich bitte Ihren Namen für die Reservierung haben?

---

### Turn 9

```
stt_latency_ms:    8
llm_latency_ms:    3071 ⚠️
tts_latency_ms:    3072
total_latency_ms:  3079 ⚠️
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

**User:** Für zwei Personen ja.

**Bot:** Entschuldigen Sie bitte, ich habe Sie selbstverständlich verstanden – die Reservierung für 2 Personen ist notiert. Wie lautet denn Ihr Name für die Buchung?

---

### Turn 10

```
stt_latency_ms:    3
llm_latency_ms:    1325 ✅
tts_latency_ms:    1325
total_latency_ms:  1329 ✅
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

**User:** Ist das jetzt alles

**Bot:** Gerne – unter welchem Namen soll ich die Reservierung für Sie eintragen?

---

### Turn 11

```
stt_latency_ms:    4
llm_latency_ms:    1863 ✅
tts_latency_ms:    1864
total_latency_ms:  1867 ✅
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

**User:** Ach Moment, ich hab doch gerade gesagt, ich heiße Müller, Gertrud Müller. Haben Sie das jetzt?

**Bot:** Perfekt, dann trage ich die Reservierung auf den Namen Müller ein – können Sie mir noch sagen, für wie viele Personen und zu welcher Uhrzeit Sie kommen möchten?

---

### Turn 12

```
stt_latency_ms:    4
llm_latency_ms:    1860 ✅
tts_latency_ms:    1860
total_latency_ms:  1864 ✅
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

**User:** Ach, jetzt fragen Sie schon wieder nach der Uhrzeit. und der Anzahl.

**Bot:** Danke, Frau Müller – ich habe Ihren Namen notiert! Für wie viele Personen möchten Sie reservieren und zu welcher Uhrzeit passt es Ihnen am besten?

---

### Turn 13

```
stt_latency_ms:    5
llm_latency_ms:    1997 ✅
tts_latency_ms:    1998
total_latency_ms:  2003 ✅
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

**User:** Für zwei Personen um neunzehn Uhr. Das hab ich Ihnen doch schon gesagt. Haben Sie das jetzt?

**Bot:** Entschuldigung, Frau Müller – ich verstehe Ihre Ungeduld! Könnten Sie mir bitte einfach mitteilen, für wie viele Personen und um wie viel Uhr Sie reservieren möchten, damit ich Ihnen direkt weiterhelfen kann?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 832 | 819 | 12 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1596 | 1593 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1886 | 1882 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1670 | 1665 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 2330 | 2317 | 12 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1559 | 1556 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1369 | 1364 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 8 | 1427 | 1423 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 9 | 3079 | 3071 | 8 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 10 | 1329 | 1325 | 3 | None | — | 200 | info_neutral | frustrated | None | ai_greeting,get_date_info |  |
| 11 | 1867 | 1863 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 12 | 1864 | 1860 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 13 | 2003 | 1997 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Ja, hallo. Ich möchte gerne einen Tisch reservieren.
- **user** (turn 1): Für zwei Personen, heute Abend.
- **user** (turn 2): Ach, Moment, ich verstehe nicht ganz.
- **user** (turn 3): Ich wollte einen Tisch reservieren für heute Abend.
- **user** (turn 4): Können Sie mir da helfen?
- **user** (turn 5): Ja, also Moment, ich komme um sieben Uhr. Ist das möglich?
- **user** (turn 6): Moment, ich hab doch gerade gesagt um sieben Uhr.
- **user** (turn 7): Für zwei Personen. Ist das in Ordnung?
- **user** (turn 8): Für zwei Personen. Haben Sie das nicht verstanden?
- **assistant** (turn 9): Wunderbar, ich reserviere Ihnen gerne einen Tisch für 2 Personen um 19:00 Uhr am heutigen Freitag. Darf ich bitte Ihren Namen für die Reservierung haben?
- **user** (turn 10): Für zwei Personen ja.
- **user** (turn 11): Ist das jetzt alles
- **user** (turn 12): Ach Moment, ich hab doch gerade gesagt, ich heiße Müller, Gertrud Müller. Haben Sie das jetzt?
- **assistant** (turn 13): Perfekt, dann trage ich die Reservierung auf den Namen Müller ein – können Sie mir noch sagen, für wie viele Personen und zu welcher Uhrzeit Sie kommen möchten?
- **user** (turn 14): Ach, jetzt fragen Sie schon wieder nach der Uhrzeit. und der Anzahl.
- **user** (turn 15): Für zwei Personen um neunzehn Uhr. Das hab ich Ihnen doch schon gesagt. Haben Sie das jetzt?

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
          "Guten Tag! Wie kann ich Sie bei DOBOO Korean Soulfood unterstützen?",
          "Gerne helfe ich Ihnen weiter! Um Ihnen einen Tisch für zwei Personen heute Abend zu reservieren, benötige ich noch die gewünschte Uhrzeit – wann würden Sie gerne bei uns vorbeikommen?",
          "Selbstverständlich, gerne erkläre ich das nochmal: Für Ihre Reservierung brauchen wir nur noch zu wissen, um wie viel Uhr Sie heute Abend bei uns essen möchten. Welche Uhrzeit passt Ihnen am besten?",
          "Gerne helfe ich Ihnen mit der Reservierung – können Sie mir noch sagen, zu welcher Uhrzeit Sie heute bei uns vorbeischauen möchten? Für wie viele Personen soll der Tisch sein?",
          "Gerne helfe ich Ihnen mit der Reservierung – können Sie mir noch sagen, zu welcher Uhrzeit Sie heute bei uns vorbeischauen möchten? Für wie viele Personen soll der Tisch sein?",
          "Sehr gerne, um 19:00 Uhr am heutigen Freitag ist möglich – für wie viele Personen darf ich den Tisch reservieren?",
          "Entschuldigen Sie, ich habe das verstanden – 19:00 Uhr am heutigen Freitag ist perfekt für Sie. Für wie viele Personen soll ich den Tisch reservieren?",
          "Wunderbar, ich reserviere Ihnen gerne einen Tisch für 2 Personen um 19:00 Uhr am heutigen Freitag. Darf ich bitte Ihren Namen für die Reservierung haben?",
          "Entschuldigen Sie bitte, ich habe Sie selbstverständlich verstanden – die Reservierung für 2 Personen ist notiert. Wie lautet denn Ihr Name für die Buchung?",
          "Gerne – unter welchem Namen soll ich die Reservierung für Sie eintragen?",
          "Perfekt, dann trage ich die Reservierung auf den Namen Müller ein – können Sie mir noch sagen, für wie viele Personen und zu welcher Uhrzeit Sie kommen möchten?",
          "Danke, Frau Müller – ich habe Ihren Namen notiert! Für wie viele Personen möchten Sie reservieren und zu welcher Uhrzeit passt es Ihnen am besten?",
          "Entschuldigung, Frau Müller – ich verstehe Ihre Ungeduld! Könnten Sie mir bitte einfach mitteilen, für wie viele Personen und um wie viel Uhr Sie reservieren möchten, damit ich Ihnen direkt weiterhelfen kann?"
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
            "bot": "Entschuldigen Sie bitte, ich habe Sie selbstverständlich verstanden – die Reservierung für 2 Personen ist notiert. Wie lautet denn Ihr Name für die Buchung?",
            "node": "greeting",
            "customer": "Für zwei Personen ja."
          },
          {
            "bot": "Gerne – unter welchem Namen soll ich die Reservierung für Sie eintragen?",
            "node": "greeting",
            "customer": "Ist das jetzt alles"
          },
          {
            "bot": "Perfekt, dann trage ich die Reservierung auf den Namen Müller ein – können Sie mir noch sagen, für wie viele Personen und zu welcher Uhrzeit Sie kommen möchten?",
            "node": "greeting",
            "customer": "Ach Moment, ich hab doch gerade gesagt, ich heiße Müller, Gertrud Müller. Haben Sie das jetzt?"
          },
          {
            "bot": "Danke, Frau Müller – ich habe Ihren Namen notiert! Für wie viele Personen möchten Sie reservieren und zu welcher Uhrzeit passt es Ihnen am besten?",
            "node": "greeting",
            "customer": "Ach, jetzt fragen Sie schon wieder nach der Uhrzeit. und der Anzahl."
          },
          {
            "bot": "Entschuldigung, Frau Müller – ich verstehe Ihre Ungeduld! Könnten Sie mir bitte einfach mitteilen, für wie viele Personen und um wie viel Uhr Sie reservieren möchten, damit ich Ihnen direkt weiterhelfen kann?",
            "node": "greeting",
            "customer": "Für zwei Personen um neunzehn Uhr. Das hab ich Ihnen doch schon gesagt. Haben Sie das jetzt?"
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Für zwei Personen, heute Abend....' [greeting] Kunde: 'Ach, Moment, ich verstehe nicht ganz....' [greeting] Kunde: 'Ich wollte einen Tisch reservieren für heute Abend....' [greeting] Kunde: 'Können Sie mir da helfen?...' [greeting] Kunde: 'Ja, also Moment, ich komme um sieben Uhr. Ist das möglich?...' [greeting] Kunde: 'Moment, ich hab doch gerade gesagt um sieben Uhr....' [greeting] Kunde: 'Für zwei Personen. Ist das in Ordnung?...' [greeting] Kunde: 'Für zwei Personen. Haben Sie das nicht verstanden?...'",
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
Turn 6: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 7: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 8: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 9: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 10: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 11: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 12: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 13: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
