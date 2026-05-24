# Sailly — Full Call Analysis Report
## Call ID: `demo-3b64ad56b6e1`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-3b64ad56b6e1` |
| **Caller / channel** | `[validation:A2_tool_tag_wuetend]` |
| **Started** | 2026-05-01 06:10:45 UTC |
| **Ended** | 2026-05-01 06:12:30 UTC |
| **Duration** | **104 seconds (1:44 min)** |
| **Total DB turns** | 15 |
| **Outcome / reason** | `client_hangup` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1455 ms |
| **p95 latency (stored)** | 2164 ms |
| **Max latency (stored)** | 2986 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 153.7967 ¢ |

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
| Latency p50 / p95 / max (total) | 1289 / 1812 / 2986 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1286 / 2982 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1287 / 2982 ms (15 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1099 ✅
tts_latency_ms:    1099
total_latency_ms:  1102 ✅
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

**User:** Hallo, ich hab da eine Frage zu eurem Restaurant.

**Bot:** Gerne helfe ich Ihnen weiter – was kann ich für Sie tun, möchten Sie einen Tisch reservieren oder haben Sie eine andere Frage?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    1168 ✅
tts_latency_ms:    1169
total_latency_ms:  1172 ✅
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

**User:** Ich suche schon ewig nach euch und finde einfach nichts.

**Bot:** Sehr gerne, ich bin für Sie da! Was möchte ich gerne über DOBOO Korean Soulfood wissen?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1420 ✅
tts_latency_ms:    1421
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

**User:** Was soll das denn jetzt?

**Bot:** Gerne helfe ich Ihnen weiter – Sie erreichen uns unter unserer Adresse in Bonn, oder kann ich Ihnen noch weitere Informationen geben?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1808 ✅
tts_latency_ms:    1809
total_latency_ms:  1812 ✅
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

**User:** Das sagst Du ja jedes Mal, wenn ich was fragen will.

**Bot:** Es tut mir leid, wenn ich Sie missverstanden habe – könnten Sie mir bitte sagen, womit ich Ihnen konkret helfen kann? Ich bin gerne für Ihre Fragen zu DOBOO Korean Soulfood da!

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    1286 ✅
tts_latency_ms:    1287
total_latency_ms:  1289 ✅
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

**User:** Sag mir jetzt einfach die genaue Adresse. Ich hab keine Lust mehr auf dieses Spielchen.

**Bot:** Entschuldigen Sie, das war nicht meine Absicht – ich möchte Ihnen wirklich weiterhelfen! Was kann ich denn konkret für Sie tun?

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1432 ✅
tts_latency_ms:    1432
total_latency_ms:  1435 ✅
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

**User:** Das ist doch Quatsch. Ich hab doch schon gesagt, dass ich die genaue Adresse von eurem Restaurant wissen will. Jetzt sag mir endlich die Adresse oder ich klick auf.

**Bot:** Unsere Adresse ist DOBOO Korean Soulfood, Bonngasse 16, 53111 Bonn – Sie können uns auch gerne direkt anrufen, wenn Sie noch weitere Fragen haben!

---

### Turn 7

```
stt_latency_ms:    3
llm_latency_ms:    1279 ✅
tts_latency_ms:    1279
total_latency_ms:  1282 ✅
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

**User:** Turn eins, kein Problem. Hallo, hier ist Sallie. Korrekt.

**Bot:** Die Adresse habe ich Ihnen gerade mitgeteilt: Bonngasse 16, 53111 Bonn. Falls Sie noch Fragen haben, freue ich mich, Ihnen zu helfen!

---

### Turn 8

```
stt_latency_ms:    2
llm_latency_ms:    1210 ✅
tts_latency_ms:    1210
total_latency_ms:  1213 ✅
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

**User:** Problem. halluzinierte Fehlermeldung.

**Bot:** Sehr gerne, Sallie! Wie kann ich Ihnen sonst noch weiterhelfen?

---

### Turn 9

```
stt_latency_ms:    4
llm_latency_ms:    1533 ✅
tts_latency_ms:    1533
total_latency_ms:  1537 ✅
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

**User:** Was möchte ich gerne über Dobo, Entschuldigung, ein technisches Problem?

**Bot:** Es tut mir leid, dass Sie auf eine Fehlermeldung gestoßen sind – können Sie mir bitte beschreiben, wo genau diese Meldung auftrat, damit ich Ihnen besser helfen kann?

---

### Turn 10

```
stt_latency_ms:    4
llm_latency_ms:    2982 ✅
tts_latency_ms:    2982
total_latency_ms:  2986 ✅
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

**User:** Korrekt wäre direkte Antwort auf Adressfrage.

**Bot:** Entschuldigung, ich habe die Frage nicht ganz verstanden – möchten Sie etwas über DOBOO Korean Soulfood erfahren oder haben Sie ein technisches Problem mit unserer Website? Ich helfe Ihnen gerne weiter!

---

### Turn 11

```
stt_latency_ms:    3
llm_latency_ms:    1129 ✅
tts_latency_ms:    1129
total_latency_ms:  1132 ✅
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

**User:** Turn drei, Problem. Ignoriert Frage und fragt zurück. Könnten Sie mir bitte sagen? Korrekt wäre direkte Adressangabe.

**Bot:** Gerne – unsere Adresse ist DOBOO Korean Soulfood, Bonn. Kann ich Ihnen noch mit weiteren Informationen helfen?

---

### Turn 12

```
stt_latency_ms:    3
llm_latency_ms:    1676 ✅
tts_latency_ms:    1676
total_latency_ms:  1680 ✅
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

**User:** Turn vier, kein Problem.

**Bot:** Unsere genaue Adresse lautet DOBOO Korean Soulfood, Bonngasse 10, 53111 Bonn. Wie kann ich Sie sonst noch unterstützen?

---

### Turn 13

```
stt_latency_ms:    4
llm_latency_ms:    1176 ✅
tts_latency_ms:    1176
total_latency_ms:  1180 ✅
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

**User:** Direkte Adressangabe, korrekt.

**Bot:** Gerne! Kann ich Sie noch mit etwas anderem unterstützen, oder haben Sie alle Informationen, die Sie benötigen?

---

### Turn 14

```
stt_latency_ms:    3
llm_latency_ms:    1333 ✅
tts_latency_ms:    1333
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

**User:** Gesamteinschätzung, Bot hat die Anfrage unnötig verzögert und hallo.

**Bot:** Sehr gerne – ich freue mich, Ihnen helfen zu können! Viel Spaß bei Ihrem Besuch bei DOBOO Korean Soulfood in Bonn!

---

### Turn 15

```
stt_latency_ms:    4
llm_latency_ms:    1248 ✅
tts_latency_ms:    1248
total_latency_ms:  1252 ✅
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

**User:** beziehen Fehler, statt direkt zu helfen. Der Bot hat die Adressanfrage unnötig in die Länge gezogen und mit einer erfundenen Fehlermeldung irritiert.

**Bot:** Vielen Dank für Ihr Vertrauen – wie kann ich Sie heute bei DOBOO Korean Soulfood unterstützen?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1102 | 1099 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1172 | 1168 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1423 | 1420 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1812 | 1808 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1289 | 1286 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1435 | 1432 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1282 | 1279 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 8 | 1213 | 1210 | 2 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 9 | 1537 | 1533 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 10 | 2986 | 2982 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 11 | 1132 | 1129 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 12 | 1680 | 1676 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 13 | 1180 | 1176 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 14 | 1336 | 1333 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 15 | 1252 | 1248 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo, ich hab da eine Frage zu eurem Restaurant.
- **user** (turn 1): Ich suche schon ewig nach euch und finde einfach nichts.
- **user** (turn 2): Wo befindet sich euer Restaurant genau?
- **user** (turn 3): Was soll das denn jetzt?
- **user** (turn 4): Das sagst Du ja jedes Mal, wenn ich was fragen will.
- **user** (turn 5): Sag mir jetzt einfach die genaue Adresse. Ich hab keine Lust mehr auf dieses Spielchen.
- **user** (turn 6): Das ist doch Quatsch. Ich hab doch schon gesagt, dass ich die genaue Adresse von eurem Restaurant wissen will. Jetzt sag mir endlich die Adresse oder ich klick auf.
- **user** (turn 7): Turn eins, kein Problem. Hallo, hier ist Sallie. Korrekt.
- **user** (turn 8): Problem. halluzinierte Fehlermeldung.
- **user** (turn 9): Was möchte ich gerne über Dobo, Entschuldigung, ein technisches Problem?
- **user** (turn 10): Korrekt wäre direkte Antwort auf Adressfrage.
- **user** (turn 11): Turn drei, Problem. Ignoriert Frage und fragt zurück. Könnten Sie mir bitte sagen? Korrekt wäre direkte Adressangabe.
- **user** (turn 12): Turn vier, kein Problem.
- **user** (turn 13): Direkte Adressangabe, korrekt.
- **user** (turn 14): Gesamteinschätzung, Bot hat die Anfrage unnötig verzögert und hallo.
- **user** (turn 15): beziehen Fehler, statt direkt zu helfen. Der Bot hat die Adressanfrage unnötig in die Länge gezogen und mit einer erfundenen Fehlermeldung irritiert.

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
        "phone_number": "+4915900000002",
        "shared_slots": {},
        "abuse_strikes": 0,
        "customer_name": "Direkte Adressangabe",
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": "+4915900000002",
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?",
          "Gerne helfe ich Ihnen weiter – was kann ich für Sie tun, möchten Sie einen Tisch reservieren oder haben Sie eine andere Frage?",
          "Sehr gerne, ich bin für Sie da! Was möchte ich gerne über DOBOO Korean Soulfood wissen?",
          "Gerne helfe ich Ihnen weiter – Sie erreichen uns unter unserer Adresse in Bonn, oder kann ich Ihnen noch weitere Informationen geben?",
          "Es tut mir leid, wenn ich Sie missverstanden habe – könnten Sie mir bitte sagen, womit ich Ihnen konkret helfen kann? Ich bin gerne für Ihre Fragen zu DOBOO Korean Soulfood da!",
          "Entschuldigen Sie, das war nicht meine Absicht – ich möchte Ihnen wirklich weiterhelfen! Was kann ich denn konkret für Sie tun?",
          "Unsere Adresse ist DOBOO Korean Soulfood, Bonngasse 16, 53111 Bonn – Sie können uns auch gerne direkt anrufen, wenn Sie noch weitere Fragen haben!",
          "Die Adresse habe ich Ihnen gerade mitgeteilt: Bonngasse 16, 53111 Bonn. Falls Sie noch Fragen haben, freue ich mich, Ihnen zu helfen!",
          "Sehr gerne, Sallie! Wie kann ich Ihnen sonst noch weiterhelfen?",
          "Es tut mir leid, dass Sie auf eine Fehlermeldung gestoßen sind – können Sie mir bitte beschreiben, wo genau diese Meldung auftrat, damit ich Ihnen besser helfen kann?",
          "Entschuldigung, ich habe die Frage nicht ganz verstanden – möchten Sie etwas über DOBOO Korean Soulfood erfahren oder haben Sie ein technisches Problem mit unserer Website? Ich helfe Ihnen gerne weiter!",
          "Gerne – unsere Adresse ist DOBOO Korean Soulfood, Bonn. Kann ich Ihnen noch mit weiteren Informationen helfen?",
          "Unsere genaue Adresse lautet DOBOO Korean Soulfood, Bonngasse 10, 53111 Bonn. Wie kann ich Sie sonst noch unterstützen?",
          "Gerne! Kann ich Sie noch mit etwas anderem unterstützen, oder haben Sie alle Informationen, die Sie benötigen?",
          "Sehr gerne – ich freue mich, Ihnen helfen zu können! Viel Spaß bei Ihrem Besuch bei DOBOO Korean Soulfood in Bonn!",
          "Vielen Dank für Ihr Vertrauen – wie kann ich Sie heute bei DOBOO Korean Soulfood unterstützen?"
        ],
        "reservation_date": null,
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
        "delivery_address_mentioned": true,
        "last_caller_confirmation_turn": null
      },
      "memory": {
        "recent_turns": [
          {
            "bot": "Gerne – unsere Adresse ist DOBOO Korean Soulfood, Bonn. Kann ich Ihnen noch mit weiteren Informationen helfen?",
            "node": "greeting",
            "customer": "Turn drei, Problem. Ignoriert Frage und fragt zurück. Könnten Sie mir bitte sagen? Korrekt wäre direkte Adressangabe."
          },
          {
            "bot": "Unsere genaue Adresse lautet DOBOO Korean Soulfood, Bonngasse 10, 53111 Bonn. Wie kann ich Sie sonst noch unterstützen?",
            "node": "greeting",
            "customer": "Turn vier, kein Problem."
          },
          {
            "bot": "Gerne! Kann ich Sie noch mit etwas anderem unterstützen, oder haben Sie alle Informationen, die Sie benötigen?",
            "node": "greeting",
            "customer": "Direkte Adressangabe, korrekt."
          },
          {
            "bot": "Sehr gerne – ich freue mich, Ihnen helfen zu können! Viel Spaß bei Ihrem Besuch bei DOBOO Korean Soulfood in Bonn!",
            "node": "greeting",
            "customer": "Gesamteinschätzung, Bot hat die Anfrage unnötig verzögert und hallo."
          },
          {
            "bot": "Vielen Dank für Ihr Vertrauen – wie kann ich Sie heute bei DOBOO Korean Soulfood unterstützen?",
            "node": "greeting",
            "customer": "beziehen Fehler, statt direkt zu helfen. Der Bot hat die Adressanfrage unnötig in die Länge gezogen und mit einer erfundenen Fehlermeldung irritiert."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Hallo, ich hab da eine Frage zu eurem Restaurant....' [greeting] Kunde: 'Ich suche schon ewig nach euch und finde einfach nichts....' [greeting] Kunde: 'Was soll das denn jetzt?...' [greeting] Kunde: 'Das sagst Du ja jedes Mal, wenn ich was fragen will....' [greeting] Kunde: 'Sag mir jetzt einfach die genaue Adresse. Ich hab keine Lust mehr auf dieses Spielchen....' [greeting] Kunde: 'Das ist doch Quatsch. Ich hab doch schon gesagt, dass ich die genaue Adresse von eurem Restaurant wissen will. Jetzt sag mir endlich die Adresse oder ich klick auf....' [greeting] Kunde: 'Turn eins, kein Problem. Hallo, hier ist Sallie. Korrekt....' [greeting] Kunde: 'Problem. halluzinierte Fehlermeldung....' [greeting] Kunde: 'Was möchte ich gerne über Dobo, Entschuldigung, ein technisches Problem?...' [greeting] Kunde: 'Korrekt wäre direkte Antwort auf Adressfrage....'",
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
          "value": "+4915900000002",
          "status": "partial",
          "confidence": "high",
          "source_turn": 0,
          "raw_mentions
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 4: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 5: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 6: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 7: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 8: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 9: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 10: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 11: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 12: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 13: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 14: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 15: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
