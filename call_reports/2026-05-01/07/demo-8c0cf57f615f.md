# Sailly — Full Call Analysis Report
## Call ID: `demo-8c0cf57f615f`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-8c0cf57f615f` |
| **Caller / channel** | `[validation:A1_meta_feedback_wuetend]` |
| **Started** | 2026-05-01 07:04:32 UTC |
| **Ended** | 2026-05-01 07:06:20 UTC |
| **Duration** | **108 seconds (1:48 min)** |
| **Total DB turns** | 15 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1024 ms |
| **p95 latency (stored)** | 1739 ms |
| **Max latency (stored)** | 1747 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 158.133 ¢ |

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
| Latency p50 / p95 / max (total) | 1187 / 1736 / 1747 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1183 / 1736 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1183 / 1736 ms (15 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    992 ✅
tts_latency_ms:    993
total_latency_ms:  997 ✅
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

**User:** Für vier Personen um neunzehn Uhr. Was? Schon wieder ein technisches Problem?

**Bot:** Guten Tag und willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?

---

### Turn 2

```
stt_latency_ms:    5
llm_latency_ms:    1731 ✅
tts_latency_ms:    1731
total_latency_ms:  1736 ✅
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

**User:** Das ist doch Quatsch.

**Bot:** Sehr gerne reserviere ich einen Tisch für Sie für vier Personen heute Freitag um 19:00 Uhr – unter welchem Namen soll die Reservierung laufen?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1498 ✅
tts_latency_ms:    1499
total_latency_ms:  1502 ✅
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

**User:** Ich rufe jetzt an und Sie haben ein technisches Problem. Können Sie mir dann wenigstens sagen, wann ich wieder anrufen soll oder soll ich einfach auflegen?

**Bot:** Ich verstehe Ihren Zweifel – lassen Sie mich die Reservierung für Sie perfekt umsetzen. Unter welchem Namen soll ich den Tisch für Sie reservieren?

---

### Turn 4

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

**User:** Na endlich, geht doch. Mein Name ist Müller.

**Bot:** Vielen Dank, Herr Müller! Für welchen Tag und welche Uhrzeit möchten Sie einen Tisch reservieren, und für wie viele Personen?

---

### Turn 5

```
stt_latency_ms:    6
llm_latency_ms:    1244 ✅
tts_latency_ms:    1244
total_latency_ms:  1250 ✅
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

**User:** Für zwei Personen heute Abend um neunzehn Uhr. Haben Sie da noch was frei?

**Bot:** Gerne, Herr Müller! Könnten Sie mir bitte mitteilen, für welchen Tag, welche Uhrzeit und wie viele Personen Sie reservieren möchten?

---

### Turn 6

```
stt_latency_ms:    10
llm_latency_ms:    1736 ✅
tts_latency_ms:    1736
total_latency_ms:  1747 ✅
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

**User:** Heute Abend um neunzehn Uhr für zwei Personen.

**Bot:** Perfekt, ich reserviere Ihnen einen Tisch für 2 Personen heute Freitag um 19:00 Uhr! Auf welchen Namen darf ich die Reservierung eintragen?

---

### Turn 7

```
stt_latency_ms:    3
llm_latency_ms:    1071 ✅
tts_latency_ms:    1071
total_latency_ms:  1075 ✅
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

**User:** Ich trage das für Sie ein. Ist der Name Müller korrekt?

**Bot:** Auf welchen Namen darf ich die Reservierung eintragen?

---

### Turn 8

```
stt_latency_ms:    4
llm_latency_ms:    1634 ✅
tts_latency_ms:    1634
total_latency_ms:  1638 ✅
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

**User:** und gibt es noch eine Telefonnummer, unter der wir Sie erreichen können?

**Bot:** Ja, gerne – ich trage die Reservierung auf den Namen Müller ein. Für welchen Tag, welche Uhrzeit und für wie viele Personen möchte ich die Reservierung vornehmen?

---

### Turn 9

```
stt_latency_ms:    3
llm_latency_ms:    1450 ✅
tts_latency_ms:    1450
total_latency_ms:  1453 ✅
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

**User:** Müller, wie ich schon gesagt habe.

**Bot:** Sehr gerne – unter welcher Telefonnummer können wir Sie denn am besten erreichen, falls wir noch Rückfragen zur Reservierung haben?

---

### Turn 10

```
stt_latency_ms:    3
llm_latency_ms:    1183 ✅
tts_latency_ms:    1183
total_latency_ms:  1187 ✅
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

**User:** Haben Sie das jetzt notiert oder soll ich's auch mal buchstabieren?

**Bot:** Vielen Dank, Herr Müller! Unter welcher Telefonnummer können wir Sie am besten erreichen?

---

### Turn 11

```
stt_latency_ms:    4
llm_latency_ms:    1173 ✅
tts_latency_ms:    1174
total_latency_ms:  1178 ✅
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

**User:** Sieben vier eins zwei drei vier sechs vier null acht nur. Das ist meine Handynummer.

**Bot:** Ja, ich habe alles notiert, danke der Nachfrage! Unter welcher Telefonnummer können wir Sie am besten erreichen?

---

### Turn 12

```
stt_latency_ms:    3
llm_latency_ms:    6 ✅
tts_latency_ms:    5
total_latency_ms:  9 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         order_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_menu']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Haben Sie jetzt alles, was Sie brauchen? Ich will keine Überraschungen mehr.

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 13

```
stt_latency_ms:    7
llm_latency_ms:    4 ✅
tts_latency_ms:    4
total_latency_ms:  11 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         order_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_menu']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Ich will doch nur einen Tisch reservieren, keine Bestellung aufgeben.

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 14

```
stt_latency_ms:    10
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  13 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         order_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_menu']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Das haben Sie jetzt schon wieder verwechselt. Ich will reservieren, nicht bestellen.

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 15

```
stt_latency_ms:    4
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  8 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          frustrated
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         order_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_menu']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Ich habe Ihnen schon dreimal gesagt, dass ich nur einen Tisch reservieren will, nicht bestellen. Warum fragen Sie das ständig?

**Bot:** Was möchten Sie gerne bestellen?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 997 | 992 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1736 | 1731 | 5 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1502 | 1498 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1558 | 1554 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1250 | 1244 | 6 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1747 | 1736 | 10 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1075 | 1071 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 8 | 1638 | 1634 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 9 | 1453 | 1450 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 10 | 1187 | 1183 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 11 | 1178 | 1173 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 12 | 9 | 6 | 3 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 13 | 11 | 4 | 7 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 14 | 13 | 3 | 10 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 15 | 8 | 3 | 4 | None | — | 200 | info_neutral | frustrated | None | get_menu |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo, ich möchte gern einen Tisch für heute Abend reservieren.
- **user** (turn 1): Für vier Personen um neunzehn Uhr. Was? Schon wieder ein technisches Problem?
- **user** (turn 2): Das ist doch Quatsch.
- **user** (turn 3): Ich rufe jetzt an und Sie haben ein technisches Problem. Können Sie mir dann wenigstens sagen, wann ich wieder anrufen soll oder soll ich einfach auflegen?
- **user** (turn 4): Na endlich, geht doch. Mein Name ist Müller.
- **user** (turn 5): Für zwei Personen heute Abend um neunzehn Uhr. Haben Sie da noch was frei?
- **user** (turn 6): Heute Abend um neunzehn Uhr für zwei Personen.
- **user** (turn 7): Ich trage das für Sie ein. Ist der Name Müller korrekt?
- **user** (turn 8): und gibt es noch eine Telefonnummer, unter der wir Sie erreichen können?
- **user** (turn 9): Müller, wie ich schon gesagt habe.
- **user** (turn 10): Haben Sie das jetzt notiert oder soll ich's auch mal buchstabieren?
- **user** (turn 11): Sieben vier eins zwei drei vier sechs vier null acht nur. Das ist meine Handynummer.
- **user** (turn 12): Haben Sie jetzt alles, was Sie brauchen? Ich will keine Überraschungen mehr.
- **user** (turn 13): Ich will doch nur einen Tisch reservieren, keine Bestellung aufgeben.
- **user** (turn 14): Das haben Sie jetzt schon wieder verwechselt. Ich will reservieren, nicht bestellen.
- **user** (turn 15): Ich habe Ihnen schon dreimal gesagt, dass ich nur einen Tisch reservieren will, nicht bestellen. Warum fragen Sie das ständig?

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
        "cached_menu": {
          "sushi": [
            {
              "name": "Tuna Roll (8 Stk.)",
              "price": 8.5,
              "allergens": [
                "Fisch",
                "Sesam"
              ],
              "vegetarian": false,
              "description": "Klassischer Thunfischcreme-Roll, classic tuna creme roll"
            },
            {
              "name": "Avocado Lachs Roll (8 Stk.)",
              "price": 8.9,
              "allergens": [
                "Fisch",
                "Sesam"
              ],
              "vegetarian": false,
              "description": "Avocado und Lachs, avocado salmon roll"
            },
            {
              "name": "Avocado Lachs Rucola Roll (8 Stk.)",
              "price": 9.5,
              "allergens": [
                "Fisch",
                "Sesam"
              ],
              "vegetarian": false,
              "description": "Avocado, Lachs, Rucola"
            },
            {
              "name": "Rainbow Roll (8 Stk.)",
              "price": 10.9,
              "allergens": [
                "Fisch",
                "Sesam"
              ],
              "vegetarian": false,
              "description": "Lachs, Thunfisch, Avocado"
            },
            {
              "name": "Ebi Tempura Roll (8 Stk.)",
              "price": 9.9,
              "allergens": [
                "Krebstiere",
                "Weizen",
                "Sesam"
              ],
              "vegetarian": false,
              "description": "Frittierte Garnele, deep fried shrimp roll"
            },
            {
              "name": "Ebi Tempura Rucola Roll (8 Stk.)",
              "price": 10.2,
              "allergens": [
                "Krebstiere",
                "Weizen",
                "Sesam"
              ],
              "vegetarian": false,
              "description": "Frittierte Garnele mit Rucola"
            },
            {
              "name": "Gimbap Roll (8 Stk.)",
              "price": 7.8,
              "allergens": [
                "Ei",
                "Sesam"
              ],
              "vegetarian": false,
              "description": "Gurke, Möhre, Ei, Rettich — koreanischer Klassiker"
            },
            {
              "name": "Veggi Roll (8 Stk.)",
              "price": 7.8,
              "allergens": [
                "Milch",
                "Sesam"
              ],
              "vegetarian": true,
              "description": "Avocado, Gurke, Paprika, Frischkäse"
            },
            {
              "name": "Inari-Veggi Roll (8 Stk.)",
              "price": 8.5,
              "allergens": [
                "Soja",
                "Sesam"
              ],
              "vegetarian": true,
              "description": "Inari, Röstzwiebeln, Avocado"
            },
            {
              "name": "Unagi Roll (8 Stk.)",
              "price": 9.5,
              "allergens": [
                "Fisch",
                "Sesam"
              ],
              "vegetarian": false,
              "description": "Unagi (Aal), Avocado, Gurke, eel roll"
            },
            {
              "name": "Mango-Lachs Roll (8 Stk.)",
              "price": 10.9,
              "allergens": [
                "Fisch",
                "Milch",
                "Sesam"
              ],
              "vegetarian": false,
              "description": "Frischkäse, Mango, Lachs"
            },
            {
              "name": "Spicy Tekkatartar Roll (8 Stk.)",
              "price": 13.5,
              "allergens": [
                "Fisch",
                "Sesam"
              ],
              "vegetarian": false,
              "description": "Scharfes Thunfischtartar, Gurke, Avocado on top"
            },
            {
              "name": "Veggi mit Lachs on top Roll (8 Stk.)",
              "price": 13.5,
              "allergens": [
                "Fisch",
                "Milch",
                "Sesam"
              ],
              "vegetarian": false,
              "description": "Avocado, Gurke, Paprika, Frischkäse mit Lachs on top"
            },
            {
              "name": "Crunchy Roll Aufpreis",
              "price": 2.5,
              "allergens": [
                "Weizen"
              ],
              "vegetarian": true,
              "description": "Alle Rollen auch als Crunchy Roll frittiert, all rolls also available as crunchy fried"
            },
            {
              "name": "Nigiri Doboo Tofu-Tasche",
              "price": 2.7,
              "allergens": [
                "Soja"
              ],
              "vegetarian": true,
              "description": "1 Stück Nigiri mit Tofu-Tasche (Inari)"
            },
            {
              "name": "Nigiri Sake (Lachs)",
              "price": 3.2,
              "allergens": [
                "Fisch"
              ],
              "vegetarian": false,
              "description": "1 Stück Nigiri mit Lachs"
            },
            {
              "name": "Nigiri Ebi (Garnele)",
              "price": 3.2,
              "allergens": [
                "Krebstiere"
              ],
              "vegetarian": false,
              "description": "1 Stück Nigiri mit Garnele"
            },
            {
              "name": "Nigiri Maguro (Thunfisch)",
              "price": 3.5,
              "allergens": [
                "Fisch"
              ],
              "vegetarian": false,
              "description": "1 Stück Nigiri mit Thunfisch"
            },
            {
              "name": "Nigiri Unagi (Aal)",
              "price": 3.5,
              "allergens": [
                "Fisch"
              ],
              "vegetarian": false,
              "description": "1 Stück Nigiri mit Aal"
            },
            {
              "name": "Maki Kappa (6 Stk.)",
              "price": 4.2,
              "allergens": [
                "Sesam"
              ],
              "vegetarian": true,
              "description": "Gurken-Maki, cucumber maki"
            },
            {
              "name": "Maki Avocado (6 Stk.)",
              "price": 4.5,
              "allergens": [
                "Sesam"
              ],
              "vegetarian": true
            },
            {
              "name": "Maki Sake (Lachs) (6 Stk.)",
              "price": 5.5,
              "allergens": [
                "Fisch",
                "Sesam"
              ],
              "vegetarian": false
            },
            {
              "name": "Maki Sake Rucola (6 Stk.)",
              "price": 5.9,
              "allergens": [
                "Fisch",
                "Sesam"
              ],
              "vegetarian": false
            },
            {
              "name": "Maki Tekka (Thunfisch) (6 Stk.)",
              "price": 5.9,
              "allergens": [
                "Fisch",
                "Sesam"
              ],
              "vegetarian": false
            },
            {
              "name": "Maki Tekka Rucola (6 Stk.)",
              "price": 6.2,
              "allergens": [
                "Fisch",
                "Sesam"
              ],
              "vegetarian": false
            },
            {
              "name": "Maki Avocado Lachs (6 Stk.)",
              "price": 5.9,
              "allergens": [
                "Fisch",
                "Sesam"
              ],
              "vegetarian": false
            },
            {
              "name": "Sushi Mix Nr. 1 vegetarisch",
              "price": 13.5,
              "allergens": [
                "Soja",
                "Ei",
                "Sesam"
              ],
              "vegetarian": true,
              "description": "Avocado Maki, Kappa Maki, Inari Nigiri, 3 Stück Doboo Rolle, 4 S
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
Turn 12: intent=takeaway turn_type=start_intent locked=True (conf=0.85) profile=order_start reroute=False
Turn 13: intent=takeaway turn_type=finalize locked=True (conf=0.85) profile=order_start reroute=False
Turn 14: intent=takeaway turn_type=finalize locked=True (conf=0.85) profile=order_start reroute=False
Turn 15: intent=takeaway turn_type=unclear locked=True (conf=0.85) profile=order_start reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
