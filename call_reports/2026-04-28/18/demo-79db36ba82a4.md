# Sailly — Full Call Analysis Report
## Call ID: `demo-79db36ba82a4`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-79db36ba82a4` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-04-28 18:21:10 UTC |
| **Ended** | 2026-04-28 18:23:28 UTC |
| **Duration** | **137 seconds (2:17 min)** |
| **Total DB turns** | 10 |
| **Outcome / reason** | `transfer_to_human` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1235 ms |
| **p95 latency (stored)** | 1680 ms |
| **Max latency (stored)** | 1780 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 199.451 ¢ |

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
| Latency p50 / p95 / max (total) | 1159 / 1780 / 1780 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1176 / 1769 ms | From `llm_latency_ms` column |
| STT p50 | 7 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | ['ERR_CALLBACK_NO_PHONE', 'ERR_MAPS_NOT_FOUND'] | `error_codes` |
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
llm_latency_ms:    1554 ✅
tts_latency_ms:    0
total_latency_ms:  1557 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1486 / None / 53 / None
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

**User:** Hallo Sally, ich möchte eine Bestellung stornieren.

**Bot:** Gerne helfe ich Ihnen dabei — können Sie mir die Bestellnummer oder Ihre Telefonnummer geben, unter der die Bestellung läuft?

---

### Turn 2

```
stt_latency_ms:    4
llm_latency_ms:    884 ✅
tts_latency_ms:    0
total_latency_ms:  889 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1015 / None / 80 / None
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

**Bot:** Entschuldigung — können Sie mir sagen, was los ist oder wie ich Ihnen helfen kann?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    1027 ✅
tts_latency_ms:    0
total_latency_ms:  1031 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1050 / None / 3 / None
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

**User:** Du hast meine Begrüßung komplett ignoriert und einfach

**Bot:** Sie haben vollkommen recht, entschuldigen Sie — ich höre Ihnen jetzt zu, was ist denn los?

---

### Turn 4

```
stt_latency_ms:    7
llm_latency_ms:    1152 ✅
tts_latency_ms:    0
total_latency_ms:  1159 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1185 / None / 3 / None
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

**User:** weitergeredet. Ich hab gesagt, ich will eine Bestellung stornieren.

**Bot:** Das tut mir leid — Sie wollen eine Bestellung stornieren, das habe ich verstanden. Können Sie mir die Bestellnummer oder Ihre Telefonnummer geben, damit ich das für Sie klären kann?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    1245 ✅
tts_latency_ms:    0
total_latency_ms:  1249 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1326 / None / 3 / None
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

**User:** 0 1 7 2 3 4 5 6 7 8. Stunde

**Bot:** Danke — ist das Ihre Telefonnummer null eins sieben zwei drei vier fünf sechs sieben acht?

---

### Turn 6

```
stt_latency_ms:    5
llm_latency_ms:    1138 ✅
tts_latency_ms:    0
total_latency_ms:  1143 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1169 / None / 2 / None
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

**User:** die letzte Bestellung.

**Bot:** Verstanden — ich schaue mir Ihre letzte Bestellung unter dieser Nummer an und kümmere mich um die Stornierung, einen Moment bitte.

---

### Turn 7

```
stt_latency_ms:    20
llm_latency_ms:    1176 ✅
tts_latency_ms:    0
total_latency_ms:  1197 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1191 / None / 6 / None
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

**User:** Gut, mach das einfach.

**Bot:** Alles klar, ich kümmere mich darum und verbinde Sie gleich mit einem Kollegen, der die Stornierung direkt in unserem System durchführen kann.

---

### Turn 8

```
stt_latency_ms:    7
llm_latency_ms:    1244 ✅
tts_latency_ms:    0
total_latency_ms:  1252 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1361 / None / 6 / None
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

**Bot:** Ja, ich bin hier — was ist denn?

---

### Turn 9

```
stt_latency_ms:    11
llm_latency_ms:    1084 ✅
tts_latency_ms:    0
total_latency_ms:  1095 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1100 / None / 17 / None
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
tools_called:      ['verify_address']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       ['ERR_MAPS_NOT_FOUND']
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Du hast die Stornierung nicht selbst gemacht und willst mich stattdessen verbinden.

**Bot:** Sie haben vollkommen recht — entschuldigen Sie. Ich kann die Stornierung leider nicht selbst im System durchführen, deshalb verbinde ich Sie mit einem Kollegen, der das für Sie erledigt.

---

### Turn 10

```
stt_latency_ms:    11
llm_latency_ms:    1769 ✅
tts_latency_ms:    0
total_latency_ms:  1780 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1752 / None / 11 / None
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
tools_called:      ['transfer_to_human']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       ['ERR_CALLBACK_NO_PHONE']
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Das ist keine Lösung. Mache es einfach selbst.

**Bot:** Ich verstehe Ihre Frustration, aber ich habe leider technisch nicht die Möglichkeit, Bestellungen selbst zu stornieren — das kann nur unser Team vor Ort im System machen. Lassen Sie mich Sie jetzt verbinden, damit das schnell geklärt wird.

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1557 | 1554 | 3 | None | — | 200 | greeting_first | neutral | None | get_menu,ai_greeting |  |
| 2 | 889 | 884 | 4 | None | — | 200 | info_neutral | neutral | None | — |  |
| 3 | 1031 | 1027 | 3 | None | — | 200 | info_neutral | neutral | None | — |  |
| 4 | 1159 | 1152 | 7 | None | — | 200 | info_neutral | neutral | None | — |  |
| 5 | 1249 | 1245 | 4 | None | — | 200 | info_neutral | neutral | None | — |  |
| 6 | 1143 | 1138 | 5 | None | — | 200 | info_neutral | neutral | None | — |  |
| 7 | 1197 | 1176 | 20 | None | — | 200 | info_neutral | neutral | None | — |  |
| 8 | 1252 | 1244 | 7 | None | — | 200 | info_neutral | neutral | None | — |  |
| 9 | 1095 | 1084 | 11 | None | — | 200 | info_neutral | neutral | None | verify_address |  |
| 10 | 1780 | 1769 | 11 | None | — | 200 | info_neutral | neutral | None | transfer_to_human |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?
- **user** (turn 1): Hallo Sally, ich möchte eine Bestellung stornieren.
- **assistant** (turn 2): Gerne helfe ich Ihnen dabei — können Sie mir die Bestellnummer oder Ihre Telefonnummer geben, unter der die Bestellung läuft?
- **user** (turn 3): Achtung.
- **user** (turn 4): Du hast meine Begrüßung komplett ignoriert und einfach
- **user** (turn 5): weitergeredet. Ich hab gesagt, ich will eine Bestellung stornieren.
- **user** (turn 6): 0 1 7 2 3 4 5 6 7 8. Stunde
- **user** (turn 7): die letzte Bestellung.
- **user** (turn 8): Gut, mach das einfach.
- **user** (turn 9): Sally, Achtung.
- **user** (turn 10): Du hast die Stornierung nicht selbst gemacht und willst mich stattdessen verbinden.
- **user** (turn 11): Das ist keine Lösung. Mache es einfach selbst.

---

## 7. Tool calls (`google_tool_calls`)

- `ai_greeting` @ turn 0 — success=None — {'status': 'greeted'}
- `verify_address` @ turn 1 — success=None — {'success': False, 'error': 'maps_lookup_failed', 'address': 'Bonn'}

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

- **Error codes present**: ['ERR_CALLBACK_NO_PHONE', 'ERR_MAPS_NOT_FOUND'].

---

_Report end._
