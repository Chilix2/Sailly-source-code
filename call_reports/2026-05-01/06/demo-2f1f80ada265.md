# Sailly — Full Call Analysis Report
## Call ID: `demo-2f1f80ada265`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-2f1f80ada265` |
| **Caller / channel** | `[validation:A3_opening_hours_aeltere_person]` |
| **Started** | 2026-05-01 06:12:32 UTC |
| **Ended** | 2026-05-01 06:14:17 UTC |
| **Duration** | **105 seconds (1:45 min)** |
| **Total DB turns** | 11 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1418 ms |
| **p95 latency (stored)** | 1974 ms |
| **Max latency (stored)** | 2164 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 154.7615 ¢ |

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
| Latency p50 / p95 / max (total) | 1323 / 2164 / 2164 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1318 / 2160 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1318 / 2161 ms (11 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1365 ✅
tts_latency_ms:    1366
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

**User:** Hallo, guten Tag.

**Bot:** Guten Tag! Möchten Sie gerne einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage zu DOBOO?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    1247 ✅
tts_latency_ms:    1247
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

**User:** Moment, ich verstehe nicht.

**Bot:** Guten Tag! Womit kann ich Sie heute helfen – möchten Sie einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine Frage zu DOBOO?

---

### Turn 3

```
stt_latency_ms:    5
llm_latency_ms:    1175 ✅
tts_latency_ms:    1175
total_latency_ms:  1180 ✅
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
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Ich wollte nur wissen, wann ihr heute geöffnet habt. Können Sie mir das sagen?

**Bot:** Gerne helfe ich Ihnen weiter! Könnten Sie mir sagen, wobei ich Sie unterstützen kann – geht es um eine Reservierung, eine Bestellung oder etwas anderes?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    2160 ✅
tts_latency_ms:    2161
total_latency_ms:  2164 ✅
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

**User:** Ja, hallo. Ich hab nur eine ganz einfache Frage.

**Bot:** Entschuldigen Sie, die genauen Öffnungszeiten für heute, Freitag, habe ich leider gerade nicht verfügbar – gerne können Sie uns aber direkt anrufen oder auf unserer Website nachschauen! Kann ich Ihnen sonst noch helfen?

---

### Turn 5

```
stt_latency_ms:    6
llm_latency_ms:    919 ✅
tts_latency_ms:    919
total_latency_ms:  926 ✅
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

**User:** Das wollt ich nur wissen.

**Bot:** Sehr gerne, ich höre Sie! Was kann ich für Sie tun?

---

### Turn 6

```
stt_latency_ms:    4
llm_latency_ms:    1302 ✅
tts_latency_ms:    1302
total_latency_ms:  1306 ✅
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

**User:** Turn eins. Kein Problem. Begrüßung und Frage nach Hilfe. Korrekte Begrüßung und

**Bot:** Gerne helfe ich Ihnen weiter – könnten Sie mir sagen, zu welchem Thema Sie eine Frage haben? Ob es um Reservierungen, Öffnungszeiten oder etwas anderes geht, ich bin für Sie da!

---

### Turn 7

```
stt_latency_ms:    4
llm_latency_ms:    1118 ✅
tts_latency_ms:    1118
total_latency_ms:  1122 ✅
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

**User:** und Öffnung für die Anfrage des Kunden. Turn zwei, Problem. Falsche Annahme, der Kunde wolle reservieren bestellen, plus technisches Problem. Sollte direkt auf die Frage nach Öffnungszeiten eingehen, ohne falsche Annahmen.

**Bot:** Gerne helfe ich Ihnen weiter – könnten Sie mir sagen, zu welchem Thema Sie eine Frage haben? Ob es um Reservierungen, Öffnungszeiten oder etwas anderes geht, ich bin für Sie da!

---

### Turn 8

```
stt_latency_ms:    4
llm_latency_ms:    1725 ✅
tts_latency_ms:    1725
total_latency_ms:  1729 ✅
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

**User:** Turn drei. wiederholt die gleiche falsche Annahme, ignoriert die konkrete Frage.

**Bot:** Entschuldigung – könnten Sie mir bitte konkret sagen, was Sie interessiert: Möchten Sie unsere Öffnungszeiten erfahren, einen Tisch reservieren oder haben Sie eine andere Frage? So kann ich Ihnen direkt helfen!

---

### Turn 9

```
stt_latency_ms:    3
llm_latency_ms:    1780 ✅
tts_latency_ms:    1781
total_latency_ms:  1784 ✅
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

**User:** sollte die Öffnungszeitenfrage direkt beantworten oder erklären, warum nicht.

**Bot:** Ich möchte Sie gerne unterstützen – könnten Sie mir präzisieren, was Sie konkret benötigen: Informationen zu unseren Öffnungszeiten, eine Tischreservierung oder etwas anderes? So kann ich Ihnen sofort weiterhelfen!

---

### Turn 10

```
stt_latency_ms:    4
llm_latency_ms:    1436 ✅
tts_latency_ms:    1436
total_latency_ms:  1441 ✅
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

**User:** Turn vier. Kein Problem. Gib ehrliche Antwort, dass Infos nicht verfügbar und bietet Alternativen an. Korrekte, hilfreiche Reaktion.

**Bot:** Gerne helfe ich Ihnen weiter – könnten Sie mir sagen, ob Sie unsere Öffnungszeiten, eine Reservierung oder Informationen zu unserem Restaurant benötigen?

---

### Turn 11

```
stt_latency_ms:    4
llm_latency_ms:    1318 ✅
tts_latency_ms:    1318
total_latency_ms:  1323 ✅
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

**User:** Gesamteinschätzung. Der Bot hat die einfache Frage des Kunden mehrmals ignoriert und falsche Annahmen getroffen, statt direkt zu helfen.

**Bot:** Ich bin gerne für Sie da – möchten Sie unsere Öffnungszeiten erfahren, einen Tisch reservieren oder haben Sie eine andere Frage zu DOBOO?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1369 | 1365 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1250 | 1247 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 3 | 1180 | 1175 | 5 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 4 | 2164 | 2160 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 926 | 919 | 6 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1306 | 1302 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1122 | 1118 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 8 | 1729 | 1725 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 9 | 1784 | 1780 | 3 | None | — | 200 | info_neutral | frustrated | None | ai_greeting,get_date_info |  |
| 10 | 1441 | 1436 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 11 | 1323 | 1318 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo, guten Tag.
- **user** (turn 1): Ähm, ich wollte mal fragen, wann ihr heute geöffnet habt. Ich bin mir nicht ganz sicher, ob ich das richtig verstanden habe.
- **user** (turn 2): Moment, ich verstehe nicht.
- **user** (turn 3): Ich wollte nur wissen, wann ihr heute geöffnet habt. Können Sie mir das sagen?
- **user** (turn 4): Ja, hallo. Ich hab nur eine ganz einfache Frage.
- **user** (turn 5): Das wollt ich nur wissen.
- **user** (turn 6): Turn eins. Kein Problem. Begrüßung und Frage nach Hilfe. Korrekte Begrüßung und
- **user** (turn 7): und Öffnung für die Anfrage des Kunden. Turn zwei, Problem. Falsche Annahme, der Kunde wolle reservieren bestellen, plus technisches Problem. Sollte direkt auf die Frage nach Öffnungszeiten eingehen, ohne falsche Annahmen.
- **user** (turn 8): Turn drei. wiederholt die gleiche falsche Annahme, ignoriert die konkrete Frage.
- **user** (turn 9): sollte die Öffnungszeitenfrage direkt beantworten oder erklären, warum nicht.
- **user** (turn 10): Turn vier. Kein Problem. Gib ehrliche Antwort, dass Infos nicht verfügbar und bietet Alternativen an. Korrekte, hilfreiche Reaktion.
- **user** (turn 11): Gesamteinschätzung. Der Bot hat die einfache Frage des Kunden mehrmals ignoriert und falsche Annahmen getroffen, statt direkt zu helfen.

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
        "order_intent": true,
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
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?",
          "Guten Tag! Möchten Sie gerne einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine andere Frage zu DOBOO?",
          "Guten Tag! Womit kann ich Sie heute helfen – möchten Sie einen Tisch reservieren, eine Bestellung aufgeben oder haben Sie eine Frage zu DOBOO?",
          "Gerne helfe ich Ihnen weiter! Könnten Sie mir sagen, wobei ich Sie unterstützen kann – geht es um eine Reservierung, eine Bestellung oder etwas anderes?",
          "Entschuldigen Sie, die genauen Öffnungszeiten für heute, Freitag, habe ich leider gerade nicht verfügbar – gerne können Sie uns aber direkt anrufen oder auf unserer Website nachschauen! Kann ich Ihnen sonst noch helfen?",
          "Sehr gerne, ich höre Sie! Was kann ich für Sie tun?",
          "Gerne helfe ich Ihnen weiter – könnten Sie mir sagen, zu welchem Thema Sie eine Frage haben? Ob es um Reservierungen, Öffnungszeiten oder etwas anderes geht, ich bin für Sie da!",
          "Gerne helfe ich Ihnen weiter – könnten Sie mir sagen, zu welchem Thema Sie eine Frage haben? Ob es um Reservierungen, Öffnungszeiten oder etwas anderes geht, ich bin für Sie da!",
          "Entschuldigung – könnten Sie mir bitte konkret sagen, was Sie interessiert: Möchten Sie unsere Öffnungszeiten erfahren, einen Tisch reservieren oder haben Sie eine andere Frage? So kann ich Ihnen direkt helfen!",
          "Ich möchte Sie gerne unterstützen – könnten Sie mir präzisieren, was Sie konkret benötigen: Informationen zu unseren Öffnungszeiten, eine Tischreservierung oder etwas anderes? So kann ich Ihnen sofort weiterhelfen!",
          "Gerne helfe ich Ihnen weiter – könnten Sie mir sagen, ob Sie unsere Öffnungszeiten, eine Reservierung oder Informationen zu unserem Restaurant benötigen?",
          "Ich bin gerne für Sie da – möchten Sie unsere Öffnungszeiten erfahren, einen Tisch reservieren oder haben Sie eine andere Frage zu DOBOO?"
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
        "delivery_address_mentioned": false,
        "last_caller_confirmation_turn": null
      },
      "memory": {
        "recent_turns": [
          {
            "bot": "Gerne helfe ich Ihnen weiter – könnten Sie mir sagen, zu welchem Thema Sie eine Frage haben? Ob es um Reservierungen, Öffnungszeiten oder etwas anderes geht, ich bin für Sie da!",
            "node": "greeting",
            "customer": "und Öffnung für die Anfrage des Kunden. Turn zwei, Problem. Falsche Annahme, der Kunde wolle reservieren bestellen, plus technisches Problem. Sollte direkt auf die Frage nach Öffnungszeiten eingehen, ohne falsche Annahmen."
          },
          {
            "bot": "Entschuldigung – könnten Sie mir bitte konkret sagen, was Sie interessiert: Möchten Sie unsere Öffnungszeiten erfahren, einen Tisch reservieren oder haben Sie eine andere Frage? So kann ich Ihnen direkt helfen!",
            "node": "greeting",
            "customer": "Turn drei. wiederholt die gleiche falsche Annahme, ignoriert die konkrete Frage."
          },
          {
            "bot": "Ich möchte Sie gerne unterstützen – könnten Sie mir präzisieren, was Sie konkret benötigen: Informationen zu unseren Öffnungszeiten, eine Tischreservierung oder etwas anderes? So kann ich Ihnen sofort weiterhelfen!",
            "node": "greeting",
            "customer": "sollte die Öffnungszeitenfrage direkt beantworten oder erklären, warum nicht."
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter – könnten Sie mir sagen, ob Sie unsere Öffnungszeiten, eine Reservierung oder Informationen zu unserem Restaurant benötigen?",
            "node": "greeting",
            "customer": "Turn vier. Kein Problem. Gib ehrliche Antwort, dass Infos nicht verfügbar und bietet Alternativen an. Korrekte, hilfreiche Reaktion."
          },
          {
            "bot": "Ich bin gerne für Sie da – möchten Sie unsere Öffnungszeiten erfahren, einen Tisch reservieren oder haben Sie eine andere Frage zu DOBOO?",
            "node": "greeting",
            "customer": "Gesamteinschätzung. Der Bot hat die einfache Frage des Kunden mehrmals ignoriert und falsche Annahmen getroffen, statt direkt zu helfen."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Hallo, guten Tag....' [greeting] Kunde: 'Moment, ich verstehe nicht....' [business_info] Kunde: 'Ich wollte nur wissen, wann ihr heute geöffnet habt. Können Sie mir das sagen?...' [greeting] Kunde: 'Ja, hallo. Ich hab nur eine ganz einfache Frage....' [greeting] Kunde: 'Das wollt ich nur wissen....' [greeting] Kunde: 'Turn eins. Kein Problem. Begrüßung und Frage nach Hilfe. Korrekte Begrüßung und...'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 12,
      "all_tools": [
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "get_date_info",
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
          "value": "+4915900000003",
          "status": "partial",
          "confidence": "high",
          "source_turn": 0,
          "raw_mentions": [
            "caller_id:+4915900000003"
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
        "address_ci
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=True (conf=0.90) profile=greeting reroute=False
Turn 2: intent=greeting turn_type=unclear locked=True (conf=0.90) profile=greeting reroute=False
Turn 3: intent=faq turn_type=start_intent locked=False (conf=0.90) profile=business_info reroute=True
Turn 4: intent=unknown turn_type=unclear locked=False (conf=0.90) profile=greeting reroute=True
Turn 5: intent=unknown turn_type=unclear locked=False (conf=0.90) profile=greeting reroute=True
Turn 6: intent=unknown turn_type=unclear locked=False (conf=0.90) profile=greeting reroute=True
Turn 7: intent=unknown turn_type=unclear locked=False (conf=0.90) profile=greeting reroute=True
Turn 8: intent=unknown turn_type=unclear locked=False (conf=0.90) profile=greeting reroute=True
Turn 9: intent=unknown turn_type=unclear locked=False (conf=0.90) profile=greeting reroute=True
Turn 10: intent=unknown turn_type=unclear locked=False (conf=0.90) profile=greeting reroute=True
Turn 11: intent=unknown turn_type=unclear locked=False (conf=0.90) profile=greeting reroute=True
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
