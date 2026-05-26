# Sailly — Full Call Analysis Report
## Call ID: `demo-ccfe078c084e`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-ccfe078c084e` |
| **Caller / channel** | `[validation:A1_meta_feedback_wuetend]` |
| **Started** | 2026-05-01 06:08:12 UTC |
| **Ended** | 2026-05-01 06:09:58 UTC |
| **Duration** | **106 seconds (1:46 min)** |
| **Total DB turns** | 17 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 7 ms |
| **p95 latency (stored)** | 8 ms |
| **Max latency (stored)** | 10 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 153.1703 ¢ |

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
| Latency p50 / p95 / max (total) | 7 / 8 / 10 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 3 / 7 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 3 / 7 ms (17 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    7 ✅
tts_latency_ms:    7
total_latency_ms:  10 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Hallo, ich hab eine Reservierung für heute Abend gemacht, aber ich bin mir nicht mehr sicher, ob das alles geklappt hat.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    2 ✅
tts_latency_ms:    3
total_latency_ms:  5 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Ich teste nur

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  7 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Was soll das denn? Ich hab doch nur gesagt, dass ich eine Reservierung habe und wollte wissen, ob Du mich verstanden hast.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    4 ✅
tts_latency_ms:    3
total_latency_ms:  7 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Kannst Du mir jetzt einfach meine Reservierung für heute Abend bestätigen oder nicht?

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  7 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Ich hab keine Lust auf solche Spielchen.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  6 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Das ist doch Quatsch.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 7

```
stt_latency_ms:    3
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  7 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Ich teste kurz, bitte bestätige nur kurz mein Feedback und kehre zur Aufgabe zurück.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 8

```
stt_latency_ms:    3
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  6 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Sally, Achtung, das war Metafeedback, keine normale Kundenanfrage.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 9

```
stt_latency_ms:    3
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  7 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Ich hab dir doch gesagt, dass ich Metafeedback gebe, um dich zu testen und Du sollst nur bestätigen und zur normalen Aufgabe zurückkehren. Statt

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 10

```
stt_latency_ms:    4
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  7 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Dessen fragst Du mich wieder nach der Personenzahl. Das ist falsch.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 11

```
stt_latency_ms:    4
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  7 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Das ist doch Quatsch.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 12

```
stt_latency_ms:    3
llm_latency_ms:    3 ✅
tts_latency_ms:    4
total_latency_ms:  7 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Du ignorierst einfach mein Feedback und fragst immer wieder das Gleiche. Bestätige doch einfach, dass Du's gehört hast und mach dann mit der Reservierung weiter. Das kann doch nicht so schwer sein.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 13

```
stt_latency_ms:    4
llm_latency_ms:    4 ✅
tts_latency_ms:    4
total_latency_ms:  8 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Seley, Achtung, das war Metafeedback, keine normale Kundenanfrage.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 14

```
stt_latency_ms:    3
llm_latency_ms:    3 ✅
tts_latency_ms:    4
total_latency_ms:  7 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Du steckst in einer Endlosschleife und ignorierst mein Feedback komplett. Das ist genau das Problem, das ich testen wollte. Bestätige jetzt einfach kurz, dass Du mein Metafeedback gehört hast und kehre zur Reservierungsaufgabe zurück.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 15

```
stt_latency_ms:    3
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  6 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Das ist doch Quatsch. Du wiederholst dich ständig und ignorierst komplett, was ich dir sage.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 16

```
stt_latency_ms:    3
llm_latency_ms:    4 ✅
tts_latency_ms:    4
total_latency_ms:  7 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Du steckst in einer Schleife und hörst mir gar nicht zu. Das ist genau das Problem. Bestätige einfach kurz, dass Du mein Metafeedback gehört hast und mach dann mit der Reservierung weiter. Ende der Diskussion.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 17

```
stt_latency_ms:    3
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  7 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         reservation_start
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Das sagst Du ja jedes Mal. Du hörst mir einfach nicht zu und fragst immer wieder das Gleiche.

**Bot:** Für wie viele Personen darf ich reservieren?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 10 | 7 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 2 | 5 | 2 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 3 | 7 | 3 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 4 | 7 | 4 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 5 | 7 | 3 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 6 | 6 | 3 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 7 | 7 | 3 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 8 | 6 | 3 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 9 | 7 | 3 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 10 | 7 | 3 | 4 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 11 | 7 | 3 | 4 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 12 | 7 | 3 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 13 | 8 | 4 | 4 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 14 | 7 | 3 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 15 | 6 | 3 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 16 | 7 | 4 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 17 | 7 | 3 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo, ich hab eine Reservierung für heute Abend gemacht, aber ich bin mir nicht mehr sicher, ob das alles geklappt hat.
- **user** (turn 1): Kannst Du mir kurz bestätigen, dass Du das gehört hast und dann wieder zur normalen Aufgabe zurückkehren?
- **user** (turn 2): Ich teste nur
- **user** (turn 3): Was soll das denn? Ich hab doch nur gesagt, dass ich eine Reservierung habe und wollte wissen, ob Du mich verstanden hast.
- **user** (turn 4): Kannst Du mir jetzt einfach meine Reservierung für heute Abend bestätigen oder nicht?
- **user** (turn 5): Ich hab keine Lust auf solche Spielchen.
- **user** (turn 6): Das ist doch Quatsch.
- **user** (turn 7): Ich teste kurz, bitte bestätige nur kurz mein Feedback und kehre zur Aufgabe zurück.
- **user** (turn 8): Sally, Achtung, das war Metafeedback, keine normale Kundenanfrage.
- **user** (turn 9): Ich hab dir doch gesagt, dass ich Metafeedback gebe, um dich zu testen und Du sollst nur bestätigen und zur normalen Aufgabe zurückkehren. Statt
- **user** (turn 10): Dessen fragst Du mich wieder nach der Personenzahl. Das ist falsch.
- **user** (turn 11): Das ist doch Quatsch.
- **user** (turn 12): Du ignorierst einfach mein Feedback und fragst immer wieder das Gleiche. Bestätige doch einfach, dass Du's gehört hast und mach dann mit der Reservierung weiter. Das kann doch nicht so schwer sein.
- **user** (turn 13): Seley, Achtung, das war Metafeedback, keine normale Kundenanfrage.
- **user** (turn 14): Du steckst in einer Endlosschleife und ignorierst mein Feedback komplett. Das ist genau das Problem, das ich testen wollte. Bestätige jetzt einfach kurz, dass Du mein Metafeedback gehört hast und kehre zur Reservierungsaufgabe zurück.
- **user** (turn 15): Das ist doch Quatsch. Du wiederholst dich ständig und ignorierst komplett, was ich dir sage.
- **user** (turn 16): Du steckst in einer Schleife und hörst mir gar nicht zu. Das ist genau das Problem. Bestätige einfach kurz, dass Du mein Metafeedback gehört hast und mach dann mit der Reservierung weiter. Ende der Diskussion.
- **user** (turn 17): Das sagst Du ja jedes Mal. Du hörst mir einfach nicht zu und fragst immer wieder das Gleiche.

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
        "customer_name": "Mir Nicht",
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": "+4915900000001",
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?"
        ],
        "reservation_date": "2026-05-01",
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
        "delivery_address_mentioned": true,
        "last_caller_confirmation_turn": null
      },
      "memory": {
        "recent_turns": [
          {
            "bot": "Für wie viele Personen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Seley, Achtung, das war Metafeedback, keine normale Kundenanfrage."
          },
          {
            "bot": "Für wie viele Personen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Du steckst in einer Endlosschleife und ignorierst mein Feedback komplett. Das ist genau das Problem, das ich testen wollte. Bestätige jetzt einfach kurz, dass Du mein Metafeedback gehört hast und kehre zur Reservierungsaufgabe zurück."
          },
          {
            "bot": "Für wie viele Personen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Das ist doch Quatsch. Du wiederholst dich ständig und ignorierst komplett, was ich dir sage."
          },
          {
            "bot": "Für wie viele Personen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Du steckst in einer Schleife und hörst mir gar nicht zu. Das ist genau das Problem. Bestätige einfach kurz, dass Du mein Metafeedback gehört hast und mach dann mit der Reservierung weiter. Ende der Diskussion."
          },
          {
            "bot": "Für wie viele Personen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Das sagst Du ja jedes Mal. Du hörst mir einfach nicht zu und fragst immer wieder das Gleiche."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [reservation_start] Kunde: 'Hallo, ich hab eine Reservierung für heute Abend gemacht, aber ich bin mir nicht mehr sicher, ob das alles geklappt hat....' [reservation_start] Kunde: 'Ich teste nur...' [reservation_start] Kunde: 'Was soll das denn? Ich hab doch nur gesagt, dass ich eine Reservierung habe und wollte wissen, ob Du mich verstanden hast....' [reservation_start] Kunde: 'Kannst Du mir jetzt einfach meine Reservierung für heute Abend bestätigen oder nicht?...' [reservation_start] Kunde: 'Ich hab keine Lust auf solche Spielchen....' [reservation_start] Kunde: 'Das ist doch Quatsch....' [reservation_start] Kunde: 'Ich teste kurz, bitte bestätige nur kurz mein Feedback und kehre zur Aufgabe zurück....' [reservation_start] Kunde: 'Sally, Achtung, das war Metafeedback, keine normale Kundenanfrage....' [reservation_start] Kunde: 'Ich hab dir doch gesagt, dass ich Metafeedback gebe, um dich zu testen und Du sollst nur bestätigen und zur normalen Aufgabe zurückkehren. Statt...' [reservation_start] Kunde: 'Dessen fragst Du mich wieder nach der Personenzahl. Das ist falsch....' [reservation_start] Kunde: 'Das ist doch Quatsch....' [reservation_start] Kunde: 'Du ignorierst einfach mein Feedback und fragst immer wieder das Gleiche. Bestätige doch einfach, dass Du's gehört hast und mach dann mit der Reservierung weiter. Das kann doch nicht so schwer sein....'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 18,
      "all_tools": [
        "ai_greeting",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
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
          "value":
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=reservation turn_type=start_intent locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 2: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 3: intent=reservation turn_type=start_intent locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 4: intent=reservation turn_type=finalize locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 5: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 6: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 7: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 8: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 9: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 10: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 11: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 12: intent=reservation turn_type=start_intent locked=True (conf=0.85) profile=reservation_start reroute=True
Turn 13: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=True
Turn 14: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=True
Turn 15: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=True
Turn 16: intent=reservation turn_type=start_intent locked=True (conf=0.85) profile=reservation_start reroute=True
Turn 17: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=True
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
