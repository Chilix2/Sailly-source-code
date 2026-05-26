# Sailly — Full Call Analysis Report
## Call ID: `demo-e68eb6a232e6`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-e68eb6a232e6` |
| **Caller / channel** | `[validation:A3_opening_hours_aeltere_person]` |
| **Started** | 2026-05-01 06:48:38 UTC |
| **Ended** | 2026-05-01 06:50:26 UTC |
| **Duration** | **108 seconds (1:48 min)** |
| **Total DB turns** | 14 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1646 ms |
| **p95 latency (stored)** | 2719 ms |
| **Max latency (stored)** | 3720 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 160.605 ¢ |

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
| Latency p50 / p95 / max (total) | 1452 / 2180 / 3720 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1513 / 3714 ms | From `llm_latency_ms` column |
| STT p50 | 5 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1513 / 3714 ms (14 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1267 ✅
tts_latency_ms:    1268
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
stt_latency_ms:    5
llm_latency_ms:    1017 ✅
tts_latency_ms:    1017
total_latency_ms:  1023 ✅
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

**Bot:** Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – worum geht es heute für Sie?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1519 ✅
tts_latency_ms:    1520
total_latency_ms:  1523 ✅
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

**User:** Moment, ich bin ein bisschen durcheinander, aber ich brauche die Öffnungszeiten für heute.

**Bot:** Gerne helfe ich Ihnen weiter, Herr Ein Bisschen! Leider habe ich die genauen Öffnungszeiten für heute nicht verfügbar – bitte rufen Sie uns direkt an oder besuchen Sie unsere Website für aktuelle Informationen.

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1281 ✅
tts_latency_ms:    1282
total_latency_ms:  1285 ✅
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

**User:** Moment, ich verstehe nicht. Sie sind doch das Restaurant, oder?

**Bot:** Heute ist Freitag – unsere regulären Öffnungszeiten finden Sie auf unserer Website oder Sie erreichen uns telefonisch, damit wir Ihnen sofort weiterhelfen können!

---

### Turn 5

```
stt_latency_ms:    8
llm_latency_ms:    1444 ✅
tts_latency_ms:    1444
total_latency_ms:  1452 ✅
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

**User:** Ach, jetzt versteh ich gar nichts mehr.

**Bot:** Ja, Sie sprechen mit DOBOO Korean Soulfood in Bonn – wie kann ich Ihnen heute weiterhelfen?

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1447 ✅
tts_latency_ms:    1447
total_latency_ms:  1450 ✅
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

**User:** Können Sie mir nicht einfach sagen, wann Sie heute öffnen?

**Bot:** Gerne helfe ich Ihnen weiter – könnten Sie mir bitte sagen, wobei ich Sie unterstützen kann, zum Beispiel bei einer Bestellung oder einer Frage zu unserem Restaurant?

---

### Turn 7

```
stt_latency_ms:    5
llm_latency_ms:    3714 ⚠️
tts_latency_ms:    3714
total_latency_ms:  3720 ⚠️
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

**User:** Ich möchte nur wissen, wann Sie heute geöffnet haben.

**Bot:** Entschuldigung – leider habe ich die aktuellen Öffnungszeiten gerade nicht verfügbar, aber gerne leite ich Sie an unser Team weiter oder Sie erreichen uns direkt telefonisch für diese Information!

---

### Turn 8

```
stt_latency_ms:    4
llm_latency_ms:    1513 ✅
tts_latency_ms:    1513
total_latency_ms:  1517 ✅
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

**User:** Moment, ich verstehe nicht, warum das so schwierig ist.

**Bot:** Gerne helfe ich Ihnen weiter – könnten Sie mir kurz mitteilen, ob Sie lieber direkt anrufen möchten, oder soll ich Ihre Anfrage an unser Team weitergeben?

---

### Turn 9

```
stt_latency_ms:    4
llm_latency_ms:    1630 ✅
tts_latency_ms:    1630
total_latency_ms:  1634 ✅
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

**User:** Moment, ich versteh nicht. Sie sind doch das Restaurant, oder?

**Bot:** Ich verstehe Ihre Frustration – können Sie mir bitte genau sagen, wobei ich Ihnen helfen soll, damit ich Ihnen schnell eine Lösung anbieten kann?

---

### Turn 10

```
stt_latency_ms:    8
llm_latency_ms:    2172 ✅
tts_latency_ms:    2172
total_latency_ms:  2180 ✅
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

**User:** Sie müssen doch wissen, wann Sie heute öffnen. Ich rufe extra bei Ihnen an.

**Bot:** Ja, ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood hier in Bonn – wie kann ich Ihnen heute konkret weiterhelfen?

---

### Turn 11

```
stt_latency_ms:    12
llm_latency_ms:    2020 ✅
tts_latency_ms:    2020
total_latency_ms:  2033 ✅
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

**User:** Können Sie das bitte nachschauen?

**Bot:** Entschuldigung, dass ich Ihnen die Öffnungszeiten nicht direkt nennen kann – die Information liegt mir leider gerade nicht vor. Können Sie mich mit der Zentrale verbinden oder möchten Sie eine andere Frage stellen, bei der ich Ihnen helfe?

---

### Turn 12

```
stt_latency_ms:    3
llm_latency_ms:    1542 ✅
tts_latency_ms:    1543
total_latency_ms:  1546 ✅
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

**User:** Moment, ich versteh nicht. Sie sind doch das Restaurant selber.

**Bot:** Gerne helfe ich Ihnen weiter – was möchten Sie gerne über DOBOO Korean Soulfood wissen? Ich verbinde Sie auch gerne mit unserem Team weiter, wenn Sie direkt mit jemandem sprechen möchten.

---

### Turn 13

```
stt_latency_ms:    7
llm_latency_ms:    1225 ✅
tts_latency_ms:    1226
total_latency_ms:  1232 ✅
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

**User:** Warum können Sie mir das nicht einfach sagen?

**Bot:** Ja genau, ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood – ich helfe Ihnen gerne mit Informationen weiter oder stelle Sie direkt mit unserem Team in Verbindung! Was kann ich für Sie tun?

---

### Turn 14

```
stt_latency_ms:    3
llm_latency_ms:    1171 ✅
tts_latency_ms:    1172
total_latency_ms:  1175 ✅
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

**User:** Ach, ich hab sie jetzt satt. Ich will doch nur wissen, wann sie heute aufmachen.

**Bot:** Entschuldigen Sie, ich möchte Ihnen gerne helfen – könnten Sie mir etwas präzisieren, womit ich Sie unterstützen kann? Oder verbinde ich Sie direkt mit unserem Team vor Ort?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1273 | 1267 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1023 | 1017 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1523 | 1519 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1285 | 1281 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1452 | 1444 | 8 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1450 | 1447 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 3720 | 3714 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 8 | 1517 | 1513 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 9 | 1634 | 1630 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 10 | 2180 | 2172 | 8 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 11 | 2033 | 2020 | 12 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 12 | 1546 | 1542 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 13 | 1232 | 1225 | 7 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 14 | 1175 | 1171 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo,
- **user** (turn 1): Ich möchte wissen, wann ihr heute geöffnet habt.
- **user** (turn 2): Moment, ich bin ein bisschen durcheinander, aber ich brauche die Öffnungszeiten für heute.
- **user** (turn 3): Moment, ich verstehe nicht. Sie sind doch das Restaurant, oder?
- **user** (turn 4): Sie müssen doch wissen, wann Sie heute aufmachen. Können Sie mir das bitte sagen?
- **user** (turn 5): Ach, jetzt versteh ich gar nichts mehr.
- **user** (turn 6): Können Sie mir nicht einfach sagen, wann Sie heute öffnen?
- **user** (turn 7): Ich möchte nur wissen, wann Sie heute geöffnet haben.
- **user** (turn 8): Moment, ich verstehe nicht, warum das so schwierig ist.
- **user** (turn 9): Moment, ich versteh nicht. Sie sind doch das Restaurant, oder?
- **user** (turn 10): Sie müssen doch wissen, wann Sie heute öffnen. Ich rufe extra bei Ihnen an.
- **user** (turn 11): Können Sie das bitte nachschauen?
- **user** (turn 12): Moment, ich versteh nicht. Sie sind doch das Restaurant selber.
- **user** (turn 13): Warum können Sie mir das nicht einfach sagen?
- **user** (turn 14): Ach, ich hab sie jetzt satt. Ich will doch nur wissen, wann sie heute aufmachen.
- **user** (turn 15): Können Sie das nicht nachschauen oder mich zu jemandem verbinden, der das weiß?

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
          "Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – worum geht es heute für Sie?",
          "Guten Tag! Ich freue mich, Sie bei DOBOO Korean Soulfood in Bonn begrüßen zu dürfen – worum geht es heute für Sie?",
          "Gerne helfe ich Ihnen weiter, Herr Ein Bisschen! Leider habe ich die genauen Öffnungszeiten für heute nicht verfügbar – bitte rufen Sie uns direkt an oder besuchen Sie unsere Website für aktuelle Informationen.",
          "Heute ist Freitag – unsere regulären Öffnungszeiten finden Sie auf unserer Website oder Sie erreichen uns telefonisch, damit wir Ihnen sofort weiterhelfen können!",
          "Ja, Sie sprechen mit DOBOO Korean Soulfood in Bonn – wie kann ich Ihnen heute weiterhelfen?",
          "Gerne helfe ich Ihnen weiter – könnten Sie mir bitte sagen, wobei ich Sie unterstützen kann, zum Beispiel bei einer Bestellung oder einer Frage zu unserem Restaurant?",
          "Entschuldigung – leider habe ich die aktuellen Öffnungszeiten gerade nicht verfügbar, aber gerne leite ich Sie an unser Team weiter oder Sie erreichen uns direkt telefonisch für diese Information!",
          "Gerne helfe ich Ihnen weiter – könnten Sie mir kurz mitteilen, ob Sie lieber direkt anrufen möchten, oder soll ich Ihre Anfrage an unser Team weitergeben?",
          "Ich verstehe Ihre Frustration – können Sie mir bitte genau sagen, wobei ich Ihnen helfen soll, damit ich Ihnen schnell eine Lösung anbieten kann?",
          "Ja, ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood hier in Bonn – wie kann ich Ihnen heute konkret weiterhelfen?",
          "Entschuldigung, dass ich Ihnen die Öffnungszeiten nicht direkt nennen kann – die Information liegt mir leider gerade nicht vor. Können Sie mich mit der Zentrale verbinden oder möchten Sie eine andere Frage stellen, bei der ich Ihnen helfe?",
          "Gerne helfe ich Ihnen weiter – was möchten Sie gerne über DOBOO Korean Soulfood wissen? Ich verbinde Sie auch gerne mit unserem Team weiter, wenn Sie direkt mit jemandem sprechen möchten.",
          "Ja genau, ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood – ich helfe Ihnen gerne mit Informationen weiter oder stelle Sie direkt mit unserem Team in Verbindung! Was kann ich für Sie tun?",
          "Entschuldigen Sie, ich möchte Ihnen gerne helfen – könnten Sie mir etwas präzisieren, womit ich Sie unterstützen kann? Oder verbinde ich Sie direkt mit unserem Team vor Ort?"
        ],
        "reservation_date": "2026-05-01",
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
            "bot": "Ja, ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood hier in Bonn – wie kann ich Ihnen heute konkret weiterhelfen?",
            "node": "greeting",
            "customer": "Sie müssen doch wissen, wann Sie heute öffnen. Ich rufe extra bei Ihnen an."
          },
          {
            "bot": "Entschuldigung, dass ich Ihnen die Öffnungszeiten nicht direkt nennen kann – die Information liegt mir leider gerade nicht vor. Können Sie mich mit der Zentrale verbinden oder möchten Sie eine andere Frage stellen, bei der ich Ihnen helfe?",
            "node": "greeting",
            "customer": "Können Sie das bitte nachschauen?"
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter – was möchten Sie gerne über DOBOO Korean Soulfood wissen? Ich verbinde Sie auch gerne mit unserem Team weiter, wenn Sie direkt mit jemandem sprechen möchten.",
            "node": "greeting",
            "customer": "Moment, ich versteh nicht. Sie sind doch das Restaurant selber."
          },
          {
            "bot": "Ja genau, ich bin Sailly, die KI-Assistentin von DOBOO Korean Soulfood – ich helfe Ihnen gerne mit Informationen weiter oder stelle Sie direkt mit unserem Team in Verbindung! Was kann ich für Sie tun?",
            "node": "greeting",
            "customer": "Warum können Sie mir das nicht einfach sagen?"
          },
          {
            "bot": "Entschuldigen Sie, ich möchte Ihnen gerne helfen – könnten Sie mir etwas präzisieren, womit ich Sie unterstützen kann? Oder verbinde ich Sie direkt mit unserem Team vor Ort?",
            "node": "greeting",
            "customer": "Ach, ich hab sie jetzt satt. Ich will doch nur wissen, wann sie heute aufmachen."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Hallo,...' [greeting] Kunde: 'Ich möchte wissen, wann ihr heute geöffnet habt....' [greeting] Kunde: 'Moment, ich bin ein bisschen durcheinander, aber ich brauche die Öffnungszeiten für heute....' [greeting] Kunde: 'Moment, ich verstehe nicht. Sie sind doch das Restaurant, oder?...' [greeting] Kunde: 'Ach, jetzt versteh ich gar nichts mehr....' [greeting] Kunde: 'Können Sie mir nicht einfach sagen, wann Sie heute öffnen?...' [greeting] Kunde: 'Ich möchte nur wissen, wann Sie heute geöffnet haben....' [greeting] Kunde: 'Moment, ich verstehe nicht, warum das so schwierig ist....' [greeting] Kunde: 'Moment, ich versteh nicht. Sie sind doch das Restaurant, oder?...'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 15,
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
        "get_date_info",
        "ai_greeting",
        "get_date_info"
      ],
      "order_slots": {
        "name": {
          "value": null,
          "status": "missing",
          "confidence": "low",
          "source_tur
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
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
Turn 14: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
