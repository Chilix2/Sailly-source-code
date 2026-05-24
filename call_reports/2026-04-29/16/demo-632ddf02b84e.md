# Sailly — Full Call Analysis Report
## Call ID: `demo-632ddf02b84e`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-632ddf02b84e` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-04-29 16:35:16 UTC |
| **Ended** | 2026-04-29 16:40:42 UTC |
| **Duration** | **325 seconds (5:25 min)** |
| **Total DB turns** | 8 |
| **Outcome / reason** | `forced_end_loop` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1160 ms |
| **p95 latency (stored)** | 1396 ms |
| **Max latency (stored)** | 1420 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 466.078 ¢ |

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
| Latency p50 / p95 / max (total) | 1192 / 1420 / 1420 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1187 / 1415 ms | From `llm_latency_ms` column |
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
stt_latency_ms:    3
llm_latency_ms:    1349 ✅
tts_latency_ms:    0
total_latency_ms:  1352 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1328 / None / 19 / None
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

**User:** Sali, Achtung, Du hast grade nur irgendwie gesagt. Das klingt sehr abgehackt und unnatürlich.

**Bot:** Ah, verstanden — danke für die ehrliche Rückmeldung! Ich achte drauf, dass es natürlicher klingt und nicht so gehackt wirkt. Was kann ich denn für Sie tun?

---

### Turn 2

```
stt_latency_ms:    4
llm_latency_ms:    936 ✅
tts_latency_ms:    0
total_latency_ms:  940 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1014 / None / 45 / None
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

**User:** Sadi, Achtung, Du hast jetzt nur eingegangen.

**Bot:** Ah, sorry — ich höre Sie jetzt besser! Womit kann ich Ihnen helfen?

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    1415 ✅
tts_latency_ms:    0
total_latency_ms:  1420 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1468 / None / 2 / None
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

**User:** Salut, à toi.

**Bot:** Salut! Schön, Sie zu hören — wie kann ich Ihnen heute helfen?

---

### Turn 4

```
stt_latency_ms:    4
llm_latency_ms:    984 ✅
tts_latency_ms:    0
total_latency_ms:  988 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1015 / None / 14 / None
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

**User:** Moment. Ich hab mich nicht verstanden.

**Bot:** Kein Problem — nehmen Sie sich Zeit, ich bin ganz Ohr!

---

### Turn 5

```
stt_latency_ms:    6
llm_latency_ms:    1234 ✅
tts_latency_ms:    0
total_latency_ms:  1241 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1409 / None / 90 / None
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

**User:** Sally, Achtung, jedem Wirklichkeit ist kein deutsches Ort. Das klingt komplett falsch und gut verständlich. Ein Mensch würde so etwas nicht sagen.

**Bot:** Da haben Sie vollkommen recht — entschuldigen Sie, das war wirr! Lassen Sie mich neu anfangen: Womit kann ich Ihnen heute helfen?

---

### Turn 6

```
stt_latency_ms:    5
llm_latency_ms:    1118 ✅
tts_latency_ms:    0
total_latency_ms:  1124 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1969 / None / 459 / None
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
tools_called:      ['technical_issues_callback']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Charlie, Achtung, der Satz, ich habe gerade Verbindungsprobleme, passt nicht zu einer Restaurantkartenassistentin. Ein Mensch im Restaurant würde eher sagen, Entschuldigung, die Verbindung ist gerade etwas schlecht oder einfach einen Moment bitte, die Leitung ist kurz gestört. Das klang sehr technisch und unnatürlich.

**Bot:** Danke für den Hinweis — Sie haben völlig recht, das war zu technisch! Ich merke mir: Bei Verbindungsproblemen sage ich lieber "Entschuldigung, die Leitung ist kurz gestört" oder "Einen Moment bitte, ich höre Sie gleich besser" — viel natürlicher. Womit kann ich Ihnen helfen?

---

### Turn 7

```
stt_latency_ms:    5
llm_latency_ms:    1187 ✅
tts_latency_ms:    0
total_latency_ms:  1192 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1323 / None / 112 / None
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
tools_called:      ['get_date_info']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Das war jetzt wirklich gut. Du hast das Feedback direkt angenommen, erklärt, was Du anders machen wirst und bis dann natürlich zur nächsten Frage übergegangen. Das klang menschlich und angenehm. Gute Reaktion.

**Bot:** Danke der Nachfrage — das freut mich, dass es besser läuft! Womit kann ich Sie denn jetzt unterstützen?

---

### Turn 8

```
stt_latency_ms:    4
llm_latency_ms:    1019 ✅
tts_latency_ms:    0
total_latency_ms:  1024 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1290 / None / 233 / None
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
tools_called:      ['end_call']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Das war auch schon deutlich besser, nur eine kleine Anmerkung. Womit kann ich Sie denn jetzt unterstützen? Klingt immer noch etwas zu formell und distanziert. Ein Mensch würde eher sagen, womit kann ich dir helfen oder einfach, was kann ich für dich tun?

**Bot:** Danke für das Feedback — Sie haben recht, das war zu steif von mir. Ich achte drauf und bleibe lockerer. Was kann ich denn für Sie tun?

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1352 | 1349 | 3 | None | — | 200 | greeting_first | neutral | None | get_menu,ai_greeting |  |
| 2 | 940 | 936 | 4 | None | — | 200 | info_neutral | neutral | None | — |  |
| 3 | 1420 | 1415 | 4 | None | — | 200 | info_neutral | neutral | None | — |  |
| 4 | 988 | 984 | 4 | None | — | 200 | info_neutral | neutral | None | — |  |
| 5 | 1241 | 1234 | 6 | None | — | 200 | info_neutral | neutral | None | — |  |
| 6 | 1124 | 1118 | 5 | None | — | 200 | info_neutral | neutral | None | technical_issues_callback |  |
| 7 | 1192 | 1187 | 5 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 8 | 1024 | 1019 | 4 | None | — | 200 | info_neutral | neutral | None | end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?
- **user** (turn 1): Sali, Achtung, Du hast grade nur irgendwie gesagt. Das klingt sehr abgehackt und unnatürlich.
- **user** (turn 2): Sadi, Achtung, Du hast jetzt nur eingegangen.
- **user** (turn 3): Salut, à toi.
- **user** (turn 4): Moment. Ich hab mich nicht verstanden.
- **user** (turn 5): Sally, Achtung, jedem Wirklichkeit ist kein deutsches Ort. Das klingt komplett falsch und gut verständlich. Ein Mensch würde so etwas nicht sagen.
- **user** (turn 6): Charlie, Achtung, der Satz, ich habe gerade Verbindungsprobleme, passt nicht zu einer Restaurantkartenassistentin. Ein Mensch im Restaurant würde eher sagen, Entschuldigung, die Verbindung ist gerade etwas schlecht oder einfach einen Moment bitte, die Leitung ist kurz gestört. Das klang sehr technisch und unnatürlich.
- **user** (turn 7): Das war jetzt wirklich gut. Du hast das Feedback direkt angenommen, erklärt, was Du anders machen wirst und bis dann natürlich zur nächsten Frage übergegangen. Das klang menschlich und angenehm. Gute Reaktion.
- **user** (turn 8): Das war auch schon deutlich besser, nur eine kleine Anmerkung. Womit kann ich Sie denn jetzt unterstützen? Klingt immer noch etwas zu formell und distanziert. Ein Mensch würde eher sagen, womit kann ich dir helfen oder einfach, was kann ich für dich tun?

---

## 7. Tool calls (`google_tool_calls`)

- `technical_issues_callback` @ turn 0 — success=None — {'status': 'logged', 'message': 'Das technische Problem wurde gemeldet. Ein Mitarbeiter wird sich bei Ihnen melden.', 'issue': 'technisches Problem'}
- `get_date_info` @ turn 1 — success=None — {'success': True, 'date': '2026-04-29', 'weekday': 'Mittwoch', 'relative': 'heute', 'message': '29.04.2026 ist ein Mittwoch (heute).'}

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
