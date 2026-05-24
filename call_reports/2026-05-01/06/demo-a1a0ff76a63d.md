# Sailly — Full Call Analysis Report
## Call ID: `demo-a1a0ff76a63d`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-a1a0ff76a63d` |
| **Caller / channel** | `[validation:A1_meta_feedback_aeltere_person]` |
| **Started** | 2026-05-01 06:46:08 UTC |
| **Ended** | 2026-05-01 06:47:55 UTC |
| **Duration** | **107 seconds (1:47 min)** |
| **Total DB turns** | 15 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1424 ms |
| **p95 latency (stored)** | 1811 ms |
| **Max latency (stored)** | 1908 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 157.8372 ¢ |

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
| Latency p50 / p95 / max (total) | 1424 / 1769 / 1908 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1420 / 1904 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1420 / 1905 ms (15 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    6
llm_latency_ms:    1135 ✅
tts_latency_ms:    1135
total_latency_ms:  1141 ✅
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

**Bot:** Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?

---

### Turn 2

```
stt_latency_ms:    7
llm_latency_ms:    1238 ✅
tts_latency_ms:    1238
total_latency_ms:  1245 ✅
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

**User:** Ich hab gerade gesagt, ich möchte einen Tisch reservieren für zwei Personen am Freitagabend. Können Sie mir da helfen?

**Bot:** Guten Tag! Wie kann ich Sie bei DOBOO Korean Soulfood unterstützen – möchten Sie einen Tisch reservieren oder haben Sie eine andere Frage?

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    1709 ✅
tts_latency_ms:    1709
total_latency_ms:  1713 ✅
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

**User:** Ja, ich möchte einen Tisch reservieren.

**Bot:** Sehr gerne helfe ich Ihnen bei der Reservierung für zwei Personen am Freitagabend! Für welche Uhrzeit möchten Sie den Tisch reservieren?

---

### Turn 4

```
stt_latency_ms:    10
llm_latency_ms:    1084 ✅
tts_latency_ms:    1084
total_latency_ms:  1095 ✅
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

**User:** Für wie viele Personen soll die Reservierung sein?

**Bot:** Gerne! Für welche Uhrzeit möchten Sie den Tisch reservieren?

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    995 ✅
tts_latency_ms:    996
total_latency_ms:  999 ✅
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

**User:** Moment, ich versteh nicht ganz. Ich hab doch gesagt am Freitagabend.

**Bot:** Entschuldigung, ich habe Ihre Frage übersehen – für wie viele Personen möchten Sie einen Tisch reservieren?

---

### Turn 6

```
stt_latency_ms:    5
llm_latency_ms:    1518 ✅
tts_latency_ms:    1518
total_latency_ms:  1524 ✅
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

**User:** für zwei Personen.

**Bot:** Sehr gerne – ich verstehe, Sie möchten den Tisch für heute Freitagabend reservieren. Für wie viele Personen möchten Sie einen Platz bei uns?

---

### Turn 7

```
stt_latency_ms:    4
llm_latency_ms:    1755 ✅
tts_latency_ms:    1755
total_latency_ms:  1760 ✅
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

**User:** Ja, für zwei Personen.

**Bot:** Perfekt, ich habe notiert: Tisch für zwei Personen heute Freitagabend. Zu welcher Uhrzeit würden Sie gerne bei uns speisen?

---

### Turn 8

```
stt_latency_ms:    3
llm_latency_ms:    1157 ✅
tts_latency_ms:    1158
total_latency_ms:  1161 ✅
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

**User:** Haben Sie am Freitagabend um neunzehn Uhr noch etwas frei?

**Bot:** Zu welcher Uhrzeit würden Sie gerne Ihren Tisch bei uns reservieren?

---

### Turn 9

```
stt_latency_ms:    3
llm_latency_ms:    1904 ✅
tts_latency_ms:    1905
total_latency_ms:  1908 ✅
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

**User:** Moment, ich versteh nicht ganz. Ich hab doch schon neunzehn Uhr gesagt, oder?

**Bot:** Gerne helfe ich Ihnen weiter – meinen Sie heute Freitag um 19:00 Uhr oder einen anderen Freitag? Wie viele Personen sollen es denn sein?

---

### Turn 10

```
stt_latency_ms:    5
llm_latency_ms:    1618 ✅
tts_latency_ms:    1619
total_latency_ms:  1623 ✅
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

**User:** Ist das für heute? oder für einen anderen Freitag.

**Bot:** Entschuldigung, Sie haben recht – heute Freitag um 19:00 Uhr ist notiert! Für wie viele Personen möchte ich die Reservierung vornehmen?

---

### Turn 11

```
stt_latency_ms:    3
llm_latency_ms:    1420 ✅
tts_latency_ms:    1420
total_latency_ms:  1424 ✅
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

**User:** Moment, ich versteh nicht. Jetzt fragen Sie schon wieder nach der Anzahl der Personen?

**Bot:** Gerne, für wie viele Personen darf ich die Reservierung für heute um 19:00 Uhr vornehmen?

---

### Turn 12

```
stt_latency_ms:    3
llm_latency_ms:    1765 ✅
tts_latency_ms:    1768
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

**User:** Ich hab doch schon gesagt für zwei Personen.

**Bot:** Entschuldigung für die Nachfrage – ich benötige nur noch die Anzahl der Personen, um Ihre Reservierung abzuschließen. Für wie viele Gäste soll der Tisch sein?

---

### Turn 13

```
stt_latency_ms:    3
llm_latency_ms:    1242 ✅
tts_latency_ms:    1243
total_latency_ms:  1246 ✅
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

**User:** Ich hab doch schon mehrmals gesagt für zwei Personen. Können Sie das jetzt endlich notieren?

**Bot:** Danke der Nachfrage – ich habe notiert, dass Sie einen Tisch für 2 Personen reservieren möchten. Kann ich Ihre Reservierung jetzt mit Namen und Uhrzeit abschließen?

---

### Turn 14

```
stt_latency_ms:    4
llm_latency_ms:    1535 ✅
tts_latency_ms:    1535
total_latency_ms:  1539 ✅
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

**User:** Ja, das wäre gut.

**Bot:** Gerne – ich habe Ihre Reservierung für 2 Personen notiert. Bitte teilen Sie mir noch Ihren Namen und die gewünschte Uhrzeit mit, damit ich alles abschließen kann.

---

### Turn 15

```
stt_latency_ms:    5
llm_latency_ms:    1215 ✅
tts_latency_ms:    1215
total_latency_ms:  1220 ✅
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

**User:** Können Sie das dann bitte bestätigen?

**Bot:** Wie heißen Sie denn und um welche Uhrzeit möchten Sie gerne bei uns reserviert sein? Dann kann ich Ihre Buchung gleich abspeichern.

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1141 | 1135 | 6 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1245 | 1238 | 7 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1713 | 1709 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1095 | 1084 | 10 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 999 | 995 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1524 | 1518 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1760 | 1755 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 8 | 1161 | 1157 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 9 | 1908 | 1904 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 10 | 1623 | 1618 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 11 | 1424 | 1420 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 12 | 1769 | 1765 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 13 | 1246 | 1242 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 14 | 1539 | 1535 | 4 | None | — | 200 | info_neutral | frustrated | None | ai_greeting,get_date_info |  |
| 15 | 1220 | 1215 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo, ich möchte gerne einen Tisch reservieren für zwei Personen am Freitagabend.
- **user** (turn 1): Hallo,
- **user** (turn 2): Ich hab gerade gesagt, ich möchte einen Tisch reservieren für zwei Personen am Freitagabend. Können Sie mir da helfen?
- **user** (turn 3): Ja, ich möchte einen Tisch reservieren.
- **user** (turn 4): Für wie viele Personen soll die Reservierung sein?
- **user** (turn 5): Moment, ich versteh nicht ganz. Ich hab doch gesagt am Freitagabend.
- **user** (turn 6): für zwei Personen.
- **user** (turn 7): Ja, für zwei Personen.
- **user** (turn 8): Haben Sie am Freitagabend um neunzehn Uhr noch etwas frei?
- **user** (turn 9): Moment, ich versteh nicht ganz. Ich hab doch schon neunzehn Uhr gesagt, oder?
- **user** (turn 10): Ist das für heute? oder für einen anderen Freitag.
- **user** (turn 11): Moment, ich versteh nicht. Jetzt fragen Sie schon wieder nach der Anzahl der Personen?
- **user** (turn 12): Ich hab doch schon gesagt für zwei Personen.
- **user** (turn 13): Ich hab doch schon mehrmals gesagt für zwei Personen. Können Sie das jetzt endlich notieren?
- **user** (turn 14): Ja, das wäre gut.
- **user** (turn 15): Können Sie das dann bitte bestätigen?

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
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
          "Guten Tag! Wie kann ich Sie bei DOBOO Korean Soulfood unterstützen – möchten Sie einen Tisch reservieren oder haben Sie eine andere Frage?",
          "Sehr gerne helfe ich Ihnen bei der Reservierung für zwei Personen am Freitagabend! Für welche Uhrzeit möchten Sie den Tisch reservieren?",
          "Gerne! Für welche Uhrzeit möchten Sie den Tisch reservieren?",
          "Entschuldigung, ich habe Ihre Frage übersehen – für wie viele Personen möchten Sie einen Tisch reservieren?",
          "Sehr gerne – ich verstehe, Sie möchten den Tisch für heute Freitagabend reservieren. Für wie viele Personen möchten Sie einen Platz bei uns?",
          "Perfekt, ich habe notiert: Tisch für zwei Personen heute Freitagabend. Zu welcher Uhrzeit würden Sie gerne bei uns speisen?",
          "Zu welcher Uhrzeit würden Sie gerne Ihren Tisch bei uns reservieren?",
          "Gerne helfe ich Ihnen weiter – meinen Sie heute Freitag um 19:00 Uhr oder einen anderen Freitag? Wie viele Personen sollen es denn sein?",
          "Entschuldigung, Sie haben recht – heute Freitag um 19:00 Uhr ist notiert! Für wie viele Personen möchte ich die Reservierung vornehmen?",
          "Gerne, für wie viele Personen darf ich die Reservierung für heute um 19:00 Uhr vornehmen?",
          "Entschuldigung für die Nachfrage – ich benötige nur noch die Anzahl der Personen, um Ihre Reservierung abzuschließen. Für wie viele Gäste soll der Tisch sein?",
          "Danke der Nachfrage – ich habe notiert, dass Sie einen Tisch für 2 Personen reservieren möchten. Kann ich Ihre Reservierung jetzt mit Namen und Uhrzeit abschließen?",
          "Gerne – ich habe Ihre Reservierung für 2 Personen notiert. Bitte teilen Sie mir noch Ihren Namen und die gewünschte Uhrzeit mit, damit ich alles abschließen kann.",
          "Wie heißen Sie denn und um welche Uhrzeit möchten Sie gerne bei uns reserviert sein? Dann kann ich Ihre Buchung gleich abspeichern."
        ],
        "reservation_date": "2026-05-08",
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
            "bot": "Gerne, für wie viele Personen darf ich die Reservierung für heute um 19:00 Uhr vornehmen?",
            "node": "greeting",
            "customer": "Moment, ich versteh nicht. Jetzt fragen Sie schon wieder nach der Anzahl der Personen?"
          },
          {
            "bot": "Entschuldigung für die Nachfrage – ich benötige nur noch die Anzahl der Personen, um Ihre Reservierung abzuschließen. Für wie viele Gäste soll der Tisch sein?",
            "node": "greeting",
            "customer": "Ich hab doch schon gesagt für zwei Personen."
          },
          {
            "bot": "Danke der Nachfrage – ich habe notiert, dass Sie einen Tisch für 2 Personen reservieren möchten. Kann ich Ihre Reservierung jetzt mit Namen und Uhrzeit abschließen?",
            "node": "greeting",
            "customer": "Ich hab doch schon mehrmals gesagt für zwei Personen. Können Sie das jetzt endlich notieren?"
          },
          {
            "bot": "Gerne – ich habe Ihre Reservierung für 2 Personen notiert. Bitte teilen Sie mir noch Ihren Namen und die gewünschte Uhrzeit mit, damit ich alles abschließen kann.",
            "node": "greeting",
            "customer": "Ja, das wäre gut."
          },
          {
            "bot": "Wie heißen Sie denn und um welche Uhrzeit möchten Sie gerne bei uns reserviert sein? Dann kann ich Ihre Buchung gleich abspeichern.",
            "node": "greeting",
            "customer": "Können Sie das dann bitte bestätigen?"
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Hallo,...' [greeting] Kunde: 'Ich hab gerade gesagt, ich möchte einen Tisch reservieren für zwei Personen am Freitagabend. Können Sie mir da helfen?...' [greeting] Kunde: 'Ja, ich möchte einen Tisch reservieren....' [greeting] Kunde: 'Für wie viele Personen soll die Reservierung sein?...' [greeting] Kunde: 'Moment, ich versteh nicht ganz. Ich hab doch gesagt am Freitagabend....' [greeting] Kunde: 'für zwei Personen....' [greeting] Kunde: 'Ja, für zwei Personen....' [greeting] Kunde: 'Haben Sie am Freitagabend um neunzehn Uhr noch etwas frei?...' [greeting] Kunde: 'Moment, ich versteh nicht ganz. Ich hab doch schon neunzehn Uhr gesagt, oder?...' [greeting] Kunde: 'Ist das für heute? oder für einen anderen Freitag....'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 16,
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
    
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=finalize locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=greeting turn_type=confirm locked=True (conf=0.90) profile=greeting reroute=False
Turn 4: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 5: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 6: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 7: intent=greeting turn_type=confirm locked=True (conf=0.90) profile=greeting reroute=False
Turn 8: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 9: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 10: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 11: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 12: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 13: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 14: intent=greeting turn_type=confirm locked=True (conf=0.90) profile=greeting reroute=False
Turn 15: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
