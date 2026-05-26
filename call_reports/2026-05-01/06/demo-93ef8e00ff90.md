# Sailly — Full Call Analysis Report
## Call ID: `demo-93ef8e00ff90`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-93ef8e00ff90` |
| **Caller / channel** | `[validation:A3_opening_hours_froehlich]` |
| **Started** | 2026-05-01 06:13:24 UTC |
| **Ended** | 2026-05-01 06:15:12 UTC |
| **Duration** | **108 seconds (1:48 min)** |
| **Total DB turns** | 22 |
| **Outcome / reason** | `v4_goodbye` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 353 ms |
| **p95 latency (stored)** | 1901 ms |
| **Max latency (stored)** | 2073 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 157.68 ¢ |

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
| Latency p50 / p95 / max (total) | 10 / 1932 / 2073 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 5 / 2069 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 5 / 2070 ms (22 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1927 ✅
tts_latency_ms:    1927
total_latency_ms:  1932 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         business_info
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_date_info', 'get_weather']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Hala Saleh, shown this to her. We're having a hairy Wetter heute order.

**Bot:** Das Wetter heute ist Klar mit 10.9°C. Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Sie heute unterstützen?

---

### Turn 2

```
stt_latency_ms:    4
llm_latency_ms:    2069 ✅
tts_latency_ms:    2070
total_latency_ms:  2073 ✅
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

**User:** Iets valt hem al naak vraging. Wanneer had ik een oefenetapte?

**Bot:** Entschuldigung, ich habe Ihre Anfrage nicht ganz verstanden – könnten Sie mir bitte wiederholen, was ich für Sie tun kann? Ich helfe Ihnen gerne weiter!

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    1100 ✅
tts_latency_ms:    1100
total_latency_ms:  1104 ✅
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

**User:** Yeah, this letter is vertically shown heute.

**Bot:** Es tut mir leid, aber ich konnte Ihre Frage leider nicht verstehen – könnten Sie mir bitte auf Deutsch erklären, wobei ich Ihnen helfen kann?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1164 ✅
tts_latency_ms:    1164
total_latency_ms:  1167 ✅
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

**User:** Is Guatemala within one year Hotica often tapped?

**Bot:** Entschuldigung, ich verstehe leider immer noch nicht, worum es geht – könnten Sie mir bitte konkret sagen, wobei ich Ihnen bei DOBOO Korean Soulfood helfen kann?

---

### Turn 5

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

**User:** Ich möchte wissen, wann ihr heute geöffnet habt.

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 6

```
stt_latency_ms:    6
llm_latency_ms:    5 ✅
tts_latency_ms:    5
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

**User:** Kannst Du mir da weiterhelfen?

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 7

```
stt_latency_ms:    4
llm_latency_ms:    6 ✅
tts_latency_ms:    6
total_latency_ms:  10 ✅
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

**User:** Nein, ich möchte nichts bestellen. Ich will nur wissen, wann ihr heute geöffnet habt.

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 8

```
stt_latency_ms:    4
llm_latency_ms:    5 ✅
tts_latency_ms:    5
total_latency_ms:  10 ✅
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

**User:** Ich rufe nicht zum Bestellen an, sondern nur wegen der Öffnungszeiten.

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 9

```
stt_latency_ms:    6
llm_latency_ms:    4 ✅
tts_latency_ms:    4
total_latency_ms:  10 ✅
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

**User:** Hello,

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 10

```
stt_latency_ms:    6
llm_latency_ms:    7 ✅
tts_latency_ms:    7
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

**User:** Ich hab doch gerade gesagt, dass ich nichts bestellen möchte. Ich will nur die Öffnungszeiten wissen für heute.

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 11

```
stt_latency_ms:    4
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  8 ✅
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

**User:** Hallo,

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 12

```
stt_latency_ms:    22
llm_latency_ms:    9 ✅
tts_latency_ms:    10
total_latency_ms:  32 ✅
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

**User:** Ich möchte nur wissen, wann ihr heute geöffnet habt.

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 13

```
stt_latency_ms:    4
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  8 ✅
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

**User:** Könntest Du mir da helfen?

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 14

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

**User:** Nein, ich möchte gar nichts bestellen. Ich will nur die Öffnungszeiten für heute wissen.

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

**User:** Kannst Du mir bitte einfach sagen, wann das Restaurant heute geöffnet hat? Danke.

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 16

```
stt_latency_ms:    4
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  8 ✅
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

**User:** Ich möchte nichts bestellen, nur die Öffnungszeiten wissen.

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 17

```
stt_latency_ms:    4
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  8 ✅
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

**User:** Das sagst Du jetzt schon zum fünften Mal, aber ich bin wirklich nur wegen der Öffnungszeiten dran. Kannst Du mir da nicht einfach helfen?

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 18

```
stt_latency_ms:    4
llm_latency_ms:    3 ✅
tts_latency_ms:    3
total_latency_ms:  8 ✅
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

**User:** Das ist ja wie eine Endlosschleife hier.

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 19

```
stt_latency_ms:    6
llm_latency_ms:    3 ✅
tts_latency_ms:    3
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

**User:** Hörst Du mir überhaupt zu?

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 20

```
stt_latency_ms:    4
llm_latency_ms:    4 ✅
tts_latency_ms:    4
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

**User:** Ich will wirklich keine Bestellung aufgeben, sondern nur die Öffnungszeiten für heute wissen. Wenn Du mir da nicht helfen kannst, dann lass uns das Gespräch beenden.

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 21

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

**User:** Das ist jetzt wirklich eine Endlosschleife.

**Bot:** Was möchten Sie gerne bestellen?

---

### Turn 22

```
stt_latency_ms:    4
llm_latency_ms:    1306 ✅
tts_latency_ms:    1307
total_latency_ms:  1311 ✅
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

**User:** Ich lege jetzt auf, da Du mir offenbar nicht helfen kannst. Auf Wiederhören.

**Bot:** Entschuldigen Sie, ich möchte Ihnen gerne helfen – welche Gerichte möchten Sie von uns bestellen? Geben Sie mir einfach Ihre Wünsche durch, dann kümmere ich mich darum.

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1932 | 1927 | 5 | None | — | 200 | info_neutral | neutral | None | get_date_info,get_weather |  |
| 2 | 2073 | 2069 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1104 | 1100 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1167 | 1164 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 10 | 7 | 3 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 6 | 11 | 5 | 6 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 7 | 10 | 6 | 4 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 8 | 10 | 5 | 4 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 9 | 10 | 4 | 6 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 10 | 13 | 7 | 6 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 11 | 8 | 3 | 4 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 12 | 32 | 9 | 22 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 13 | 8 | 3 | 4 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 14 | 8 | 4 | 4 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 15 | 8 | 3 | 4 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 16 | 8 | 3 | 4 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 17 | 8 | 3 | 4 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 18 | 8 | 3 | 4 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 19 | 9 | 3 | 6 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 20 | 9 | 4 | 4 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 21 | 7 | 3 | 4 | None | — | 200 | info_neutral | neutral | None | get_menu |  |
| 22 | 1311 | 1306 | 4 | None | — | 200 | info_neutral | neutral | None | get_menu |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hala Saleh, shown this to her. We're having a hairy Wetter heute order.
- **user** (turn 1): Iets valt hem al naak vraging. Wanneer had ik een oefenetapte?
- **assistant** (turn 2): Entschuldigung, ich habe Ihre Anfrage nicht ganz verstanden – könnten Sie mir bitte wiederholen, was ich für Sie tun kann? Ich helfe Ihnen gerne weiter!
- **user** (turn 3): Yeah, this letter is vertically shown heute.
- **user** (turn 4): Is Guatemala within one year Hotica often tapped?
- **user** (turn 5): Ich möchte wissen, wann ihr heute geöffnet habt.
- **user** (turn 6): Kannst Du mir da weiterhelfen?
- **user** (turn 7): Nein, ich möchte nichts bestellen. Ich will nur wissen, wann ihr heute geöffnet habt.
- **user** (turn 8): Ich rufe nicht zum Bestellen an, sondern nur wegen der Öffnungszeiten.
- **user** (turn 9): Hello,
- **user** (turn 10): Ich hab doch gerade gesagt, dass ich nichts bestellen möchte. Ich will nur die Öffnungszeiten wissen für heute.
- **user** (turn 11): Könntest Du mir bitte einfach sagen, wann heute geöffnet ist?
- **user** (turn 12): Hallo,
- **user** (turn 13): Ich möchte nur wissen, wann ihr heute geöffnet habt.
- **user** (turn 14): Könntest Du mir da helfen?
- **user** (turn 15): Nein, ich möchte gar nichts bestellen. Ich will nur die Öffnungszeiten für heute wissen.
- **user** (turn 16): Kannst Du mir bitte einfach sagen, wann das Restaurant heute geöffnet hat? Danke.
- **user** (turn 17): Ich möchte nichts bestellen, nur die Öffnungszeiten wissen.
- **user** (turn 18): Das sagst Du jetzt schon zum fünften Mal, aber ich bin wirklich nur wegen der Öffnungszeiten dran. Kannst Du mir da nicht einfach helfen?
- **user** (turn 19): Das ist ja wie eine Endlosschleife hier.
- **user** (turn 20): Hörst Du mir überhaupt zu?
- **user** (turn 21): Ich will wirklich keine Bestellung aufgeben, sondern nur die Öffnungszeiten für heute wissen. Wenn Du mir da nicht helfen kannst, dann lass uns das Gespräch beenden.
- **user** (turn 22): Das ist jetzt wirklich eine Endlosschleife.
- **user** (turn 23): Ich lege jetzt auf, da Du mir offenbar nicht helfen kannst. Auf Wiederhören.
- **assistant** (turn 24): Entschuldigen Sie, ich möchte Ihnen gerne helfen – welche Gerichte möchten Sie von uns bestellen? Geben Sie mir einfach Ihre Wünsche durch, dann kümmere ich mich darum.

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
        "first_name": "Wirklich",
        "party_size": null,
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
              "description": "Avocado Maki, Kappa Maki, Inari Nigiri, 3 Stück Doboo Rolle
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 2: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 3: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 4: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 5: intent=takeaway turn_type=start_intent locked=True (conf=0.85) profile=order_start reroute=False
Turn 6: intent=takeaway turn_type=unclear locked=True (conf=0.85) profile=order_start reroute=False
Turn 7: intent=takeaway turn_type=start_intent locked=True (conf=0.85) profile=order_start reroute=True
Turn 8: intent=takeaway turn_type=correct_previous locked=True (conf=0.85) profile=order_start reroute=True
Turn 9: intent=takeaway turn_type=unclear locked=True (conf=0.85) profile=order_start reroute=True
Turn 10: intent=takeaway turn_type=start_intent locked=True (conf=0.85) profile=order_start reroute=True
Turn 11: intent=takeaway turn_type=unclear locked=True (conf=0.85) profile=order_start reroute=True
Turn 12: intent=takeaway turn_type=start_intent locked=True (conf=0.85) profile=order_start reroute=True
Turn 13: intent=takeaway turn_type=unclear locked=True (conf=0.85) profile=order_start reroute=True
Turn 14: intent=takeaway turn_type=start_intent locked=True (conf=0.85) profile=order_start reroute=True
Turn 15: intent=takeaway turn_type=start_intent locked=True (conf=0.85) profile=order_start reroute=True
Turn 16: intent=takeaway turn_type=start_intent locked=True (conf=0.85) profile=order_start reroute=True
Turn 17: intent=takeaway turn_type=unclear locked=True (conf=0.85) profile=order_start reroute=True
Turn 18: intent=takeaway turn_type=unclear locked=True (conf=0.85) profile=order_start reroute=True
Turn 19: intent=takeaway turn_type=unclear locked=True (conf=0.85) profile=order_start reroute=True
Turn 20: intent=takeaway turn_type=finalize locked=True (conf=0.85) profile=order_start reroute=True
Turn 21: intent=takeaway turn_type=unclear locked=True (conf=0.85) profile=order_start reroute=True
Turn 22: intent=takeaway turn_type=finalize locked=True (conf=0.85) profile=order_start reroute=True
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
