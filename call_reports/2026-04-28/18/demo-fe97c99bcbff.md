# Sailly — Full Call Analysis Report
## Call ID: `demo-fe97c99bcbff`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-fe97c99bcbff` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-04-28 18:29:57 UTC |
| **Ended** | 2026-04-28 18:32:46 UTC |
| **Duration** | **169 seconds (2:49 min)** |
| **Total DB turns** | 11 |
| **Outcome / reason** | `client_disconnect` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1253 ms |
| **p95 latency (stored)** | 1602 ms |
| **Max latency (stored)** | 1661 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 244.5461 ¢ |

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
| Latency p50 / p95 / max (total) | 1108 / 1661 / 1661 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1103 / 1656 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | None / None ms (0 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    7
llm_latency_ms:    1439 ✅
tts_latency_ms:    0
total_latency_ms:  1446 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1418 / None / 16 / None
tts_situation:     greeting_first
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['get_menu', 'ai_greeting']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Hallo, Sally. Ich

**Bot:** Ah, der Satz ist noch nicht fertig — was kann ich denn für Sie tun?

---

### Turn 2

```
stt_latency_ms:    4
llm_latency_ms:    1656 ✅
tts_latency_ms:    0
total_latency_ms:  1661 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1706 / None / 3 / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      []
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** würde gern eine Bestellung aufgeben.

**Bot:** Sehr gerne — dann schauen wir mal, was Sie sich heute vorstellen können!

Darf ich fragen: Möchten Sie abholen oder liefern lassen?

---

### Turn 3

```
stt_latency_ms:    5
llm_latency_ms:    914 ✅
tts_latency_ms:    0
total_latency_ms:  920 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1016 / None / 75 / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      []
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Sally, Achtung.

**Bot:** Ah, der Satz ist noch nicht fertig — was kann ich denn für Sie tun?

---

### Turn 4

```
stt_latency_ms:    5
llm_latency_ms:    1508 ✅
tts_latency_ms:    0
total_latency_ms:  1513 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 2639 / None / 3 / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      []
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Hast jetzt schon wieder eine neue Schleife angefangen.

**Bot:** Sie haben recht, Entschuldigung — lassen Sie mich neu anfangen. Möchten Sie abholen oder liefern lassen?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    884 ✅
tts_latency_ms:    0
total_latency_ms:  888 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1014 / None / 118 / None
tts_situation:     info_neutral
tts_mood:          frustrated
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      []
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Das Gespräch ist beendet.

**Bot:** Alles klar — vielen Dank für den Anruf und bis bald beim DOBOO!

---

### Turn 6

```
stt_latency_ms:    4
llm_latency_ms:    1538 ✅
tts_latency_ms:    0
total_latency_ms:  1543 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1896 / None / 3 / None
tts_situation:     info_neutral
tts_mood:          frustrated
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      []
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Sally, Achtung, Du hast die Bestellung komplett ignoriert.

**Bot:** Sie haben vollkommen recht, das tut mir leid — lassen Sie mich das sofort korrigieren. Was möchten Sie denn bestellen?

---

### Turn 7

```
stt_latency_ms:    4
llm_latency_ms:    1094 ✅
tts_latency_ms:    0
total_latency_ms:  1099 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1163 / None / 3 / None
tts_situation:     info_neutral
tts_mood:          frustrated
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      []
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** ist wirklich schlecht.

**Bot:** Das tut mir leid — das hätte besser laufen sollen. Lassen Sie mich jetzt richtig helfen: Was möchten Sie gerne bestellen?

---

### Turn 8

```
stt_latency_ms:    3
llm_latency_ms:    1041 ✅
tts_latency_ms:    0
total_latency_ms:  1044 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1062 / None / 3 / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      []
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** ist wirklich schlecht.

**Bot:** Ich verstehe Ihre Frustration — das war wirklich nicht in Ordnung. Lassen Sie mich von vorne anfangen: Was würden Sie gerne bestellen?

---

### Turn 9

```
stt_latency_ms:    4
llm_latency_ms:    1512 ✅
tts_latency_ms:    0
total_latency_ms:  1516 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1678 / None / 3 / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      []
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Achtung.

**Bot:** Ich höre Sie — entschuldigen Sie die bisherigen Probleme. Lassen Sie mich jetzt konzentriert arbeiten: Was möchten Sie bestellen?

---

### Turn 10

```
stt_latency_ms:    3
llm_latency_ms:    1038 ✅
tts_latency_ms:    0
total_latency_ms:  1042 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1074 / None / 4 / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      []
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Du wiederholst dich nur noch mit. Was möchten Sie denn bestellen? Das ist echt un

**Bot:** Sie haben recht, entschuldigen Sie — ich mache das besser. Sagen Sie mir einfach, was Sie gerne hätten, und ich kümmere mich darum.

---

### Turn 11

```
stt_latency_ms:    4
llm_latency_ms:    1103 ✅
tts_latency_ms:    0
total_latency_ms:  1108 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1142 / None / 3 / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         None
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      []
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Tschüs.

**Bot:** Gern geschehen — lassen Sie es sich schmecken und bis bald!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1446 | 1439 | 7 | None | — | 200 | greeting_first | neutral | None | get_menu,ai_greeting |  |
| 2 | 1661 | 1656 | 4 | None | — | 200 | info_neutral | neutral | None | — |  |
| 3 | 920 | 914 | 5 | None | — | 200 | info_neutral | neutral | None | — |  |
| 4 | 1513 | 1508 | 5 | None | — | 200 | info_neutral | neutral | None | — |  |
| 5 | 888 | 884 | 4 | None | — | 200 | info_neutral | frustrated | None | — |  |
| 6 | 1543 | 1538 | 4 | None | — | 200 | info_neutral | frustrated | None | — |  |
| 7 | 1099 | 1094 | 4 | None | — | 200 | info_neutral | frustrated | None | — |  |
| 8 | 1044 | 1041 | 3 | None | — | 200 | info_neutral | neutral | None | — |  |
| 9 | 1516 | 1512 | 4 | None | — | 200 | info_neutral | neutral | None | — |  |
| 10 | 1042 | 1038 | 3 | None | — | 200 | info_neutral | neutral | None | — |  |
| 11 | 1108 | 1103 | 4 | None | — | 200 | info_neutral | neutral | None | — |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?
- **user** (turn 1): Hallo, Sally. Ich
- **user** (turn 2): würde gern eine Bestellung aufgeben.
- **user** (turn 3): Sally, Achtung.
- **user** (turn 4): Hast jetzt schon wieder eine neue Schleife angefangen.
- **user** (turn 5): Das Gespräch ist beendet.
- **user** (turn 6): Sally, Achtung, Du hast die Bestellung komplett ignoriert.
- **user** (turn 7): ist wirklich schlecht.
- **user** (turn 8): ist wirklich schlecht.
- **user** (turn 9): Achtung.
- **user** (turn 10): Du wiederholst dich nur noch mit. Was möchten Sie denn bestellen? Das ist echt un
- **user** (turn 11): Tschüs.

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
              "description": "Avocado Maki, Kappa Maki, Inari Nigiri, 3 Stück Doboo Rolle, 4 St
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
# (no context documents for this call — predates v4 migration)
```

_(no context documents for this call — predates v4 migration)_

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
