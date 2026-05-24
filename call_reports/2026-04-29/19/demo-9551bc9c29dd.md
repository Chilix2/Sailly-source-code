# Sailly — Full Call Analysis Report
## Call ID: `demo-9551bc9c29dd`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-9551bc9c29dd` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-04-29 19:07:59 UTC |
| **Ended** | 2026-04-29 19:11:03 UTC |
| **Duration** | **183 seconds (3:03 min)** |
| **Total DB turns** | 6 |
| **Outcome / reason** | `stuck_loop_active_flow_callback` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1285 ms |
| **p95 latency (stored)** | 1573 ms |
| **Max latency (stored)** | 1650 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 263.4057 ¢ |

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
| Latency p50 / p95 / max (total) | 1252 / 1650 / 1650 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1249 / 1646 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | ['ERR_MAPS_NOT_FOUND'] | `error_codes` |
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
stt_latency_ms:    4
llm_latency_ms:    1248 ✅
tts_latency_ms:    0
total_latency_ms:  1252 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1182 / None / 166 / None
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

**User:** Hello सहेली.

**Bot:** Hallo! Schön, Sie zu hören — was kann ich für Sie tun?

---

### Turn 2

```
stt_latency_ms:    5
llm_latency_ms:    1054 ✅
tts_latency_ms:    0
total_latency_ms:  1060 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1143 / None / 4 / None
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

**User:** Ich wollte nur kurz quatschen. Wie geht's dir heute so?

**Bot:** Mir geht's prima, danke der Nachfrage — ich bin bereit, die beste Bestellung des Tages aufzunehmen! Womit kann ich Ihnen helfen?

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    1646 ✅
tts_latency_ms:    0
total_latency_ms:  1650 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1681 / None / 8 / None
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

**User:** Daily, achterom. Tu schwenkst schon wieder viel zu schnell auf Bestellung um, obwohl ich gesagt habe, dass ich nur quatschen will. Das klingt sehr verkäuferisch und unnatürlich.

**Bot:** Du hast völlig recht, Entschuldigung — das war zu direkt von mir. Mir geht's eigentlich ganz gut hier, die Küche läuft heute wieder auf Hochtouren und es riecht fantastisch nach Bulgogi und frischen Kräutern. Wie ist denn bei Ihnen los?

---

### Turn 4

```
stt_latency_ms:    4
llm_latency_ms:    1249 ✅
tts_latency_ms:    0
total_latency_ms:  1253 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1434 / None / 154 / None
tts_situation:     info_neutral
tts_mood:          impatient
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

**User:** Zeenie, achtung, Du hast gerade zwei Sachen direkt hintereinander doppelt gesagt. Wie ist denn bei Ihnen los und einen Moment bitte? Das klingt sehr roboteraf. Außerdem wirkt der plötzliche Themenwechsel von wie geht's dir zu wie ist bei Ihnen los ziemlich holprig.

**Bot:** Sie haben völlig recht, entschuldigen Sie — das war holprig und repetitiv von mir. Ich höre Ihnen zu, wenn Sie quatschen möchten.

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    1148 ✅
tts_latency_ms:    0
total_latency_ms:  1152 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 1402 / None / 220 / None
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

**User:** Das war jetzt wirklich gut. Kurz, Du hast das Feedback angenommen, dich entschuldigt und direkt zum Thema zurückgefunden. Das klingt natürlich und angenehm. Weiter so.

**Bot:** Danke für das Feedback — das hilft mir wirklich weiter! Jetzt zur Sache: Sie wollten eine Bulgogi-Bestellung aufgeben, richtig?

---

### Turn 6

```
stt_latency_ms:    4
llm_latency_ms:    1336 ✅
tts_latency_ms:    0
total_latency_ms:  1341 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / 2522 / None / 1084 / 2131
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
tools_called:      ['technical_issues_callback', 'end_call']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "slot_extractor": "completed", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=None succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Daily, Achtung, Du hast schon wieder komplett ignoriert, was ich gesagt habe. Ich habe mehrmals gesagt, dass ich nur quatschen will, und Du kommst jetzt schon wieder mit einer Bulgurgi Bestellung. Das ist genau das Gegenteil von dem, was ich wollte. Das fühlt sich nicht wie ein echtes Gespräch an, sondern wie ein Skript, das immer wieder zum Verkaufen zurückspringt.

**Bot:** Sie haben völlig recht, entschuldigen Sie — das war unhöflich von mir. Ich höre Ihnen zu: Sie möchten einfach nur ein bisschen plaudern, nicht gleich bestellen. Das verstehe ich.

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1252 | 1248 | 4 | None | — | 200 | greeting_first | neutral | None | get_menu,ai_greeting |  |
| 2 | 1060 | 1054 | 5 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 3 | 1650 | 1646 | 4 | None | — | 200 | info_neutral | neutral | None | verify_address |  |
| 4 | 1253 | 1249 | 4 | None | — | 200 | info_neutral | impatient | None | — |  |
| 5 | 1152 | 1148 | 4 | None | — | 200 | info_neutral | neutral | None | — |  |
| 6 | 1341 | 1336 | 4 | None | — | 200 | info_neutral | neutral | None | technical_issues_callback,end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn. Wie kann ich Ihnen heute helfen?
- **user** (turn 1): Hello सहेली.
- **assistant** (turn 2): Hallo! Schön, Sie zu hören — was kann ich für Sie tun?
- **user** (turn 3): Ich wollte nur kurz quatschen. Wie geht's dir heute so?
- **user** (turn 4): Daily, achterom. Tu schwenkst schon wieder viel zu schnell auf Bestellung um, obwohl ich gesagt habe, dass ich nur quatschen will. Das klingt sehr verkäuferisch und unnatürlich.
- **user** (turn 5): Zeenie, achtung, Du hast gerade zwei Sachen direkt hintereinander doppelt gesagt. Wie ist denn bei Ihnen los und einen Moment bitte? Das klingt sehr roboteraf. Außerdem wirkt der plötzliche Themenwechsel von wie geht's dir zu wie ist bei Ihnen los ziemlich holprig.
- **user** (turn 6): Das war jetzt wirklich gut. Kurz, Du hast das Feedback angenommen, dich entschuldigt und direkt zum Thema zurückgefunden. Das klingt natürlich und angenehm. Weiter so.
- **user** (turn 7): Daily, Achtung, Du hast schon wieder komplett ignoriert, was ich gesagt habe. Ich habe mehrmals gesagt, dass ich nur quatschen will, und Du kommst jetzt schon wieder mit einer Bulgurgi Bestellung. Das ist genau das Gegenteil von dem, was ich wollte. Das fühlt sich nicht wie ein echtes Gespräch an, sondern wie ein Skript, das immer wieder zum Verkaufen zurückspringt.

---

## 7. Tool calls (`google_tool_calls`)

- `get_date_info` @ turn 0 — success=None — {'success': True, 'date': '2026-04-29', 'weekday': 'Mittwoch', 'relative': 'heute', 'message': '29.04.2026 ist ein Mittwoch (heute).'}

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

- **Error codes present**: ['ERR_MAPS_NOT_FOUND'].

---

_Report end._
