# Sailly — Full Call Analysis Report
## Call ID: `demo-df5a04be60a7`
_Generated: 2026-05-02 18:28 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-df5a04be60a7` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-05-02 16:35:55 UTC |
| **Ended** | 2026-05-02 16:38:52 UTC |
| **Duration** | **176 seconds (2:56 min)** |
| **Total DB turns** | 8 |
| **Outcome / reason** | `v4_goodbye` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1472 ms |
| **p95 latency (stored)** | 1803 ms |
| **Max latency (stored)** | 1840 ms |
| **Was escalated** | False |
| **Tenant** | `doboo` |
| **Est. cost (stored)** | 254.4707 ¢ |

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
| Latency p50 / p95 / max (total) | 1574 / 1840 / 1840 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1569 / 1836 ms | From `llm_latency_ms` column |
| STT p50 | 4 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1569 / 1836 ms (8 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1314 ✅
tts_latency_ms:    1315
total_latency_ms:  1320 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     greeting_first
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

**User:** Hallo. Ich hab eine Frage zu euren Öffnungszeiten.

**Bot:** Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?

---

### Turn 2

```
stt_latency_ms:    5
llm_latency_ms:    1569 ✅
tts_latency_ms:    1569
total_latency_ms:  1574 ✅
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

**User:** Wann habt ihr denn geöffnet? Ja, ich bin noch dran.

**Bot:** Gerne helfe ich Ihnen weiter! Leider habe ich die aktuellen Öffnungszeiten gerade nicht verfügbar – können Sie mich kurz mit der Nummer kontaktieren oder möchten Sie, dass ich Ihnen helfe, jemanden aus unserem Team zu erreichen?

---

### Turn 3

```
stt_latency_ms:    2
llm_latency_ms:    1732 ✅
tts_latency_ms:    1732
total_latency_ms:  1734 ✅
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

**User:** Wann habt ihr denn geöffnet?

**Bot:** Da Sie uns heute, Samstag, anrufen, können Sie uns gerne direkt unter unserer Nummer erreichen, um die genauen Öffnungszeiten zu erfragen. Alternativ schaue ich gerne, wie ich Ihnen sonst noch weiterhelfen kann!

---

### Turn 4

```
stt_latency_ms:    4
llm_latency_ms:    1671 ✅
tts_latency_ms:    1671
total_latency_ms:  1675 ✅
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

**User:** Hallo.

**Bot:** Unsere Öffnungszeiten können sich je nach Wochentag unterscheiden – rufen Sie uns gerne direkt an, damit wir Ihnen die genauen Zeiten für heute mitteilen können! Kann ich Ihnen sonst noch bei etwas anderem helfen?

---

### Turn 5

```
stt_latency_ms:    4
llm_latency_ms:    1118 ✅
tts_latency_ms:    1119
total_latency_ms:  1123 ✅
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

**User:** Ihr mir sagen, ab wann ihr aufmacht? Wann habt ihr denn geöffnet? Von

**Bot:** Heute ist Samstag – wir freuen uns auf Ihren Besuch bei DOBOO Korean Soulfood! Kann ich Ihnen noch etwas anderes helfen?

---

### Turn 6

```
stt_latency_ms:    4
llm_latency_ms:    1392 ✅
tts_latency_ms:    1392
total_latency_ms:  1396 ✅
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

**User:** Wann bis wann seid ihr da? Ach, schade. Ich hatte gehofft, ihr könnt mir das schnell sagen. Können Sie mir nicht sagen, wann Sie heute geöffnet haben? Heute ist Mittwoch, oder? Dann müsste ich

**Bot:** Leider habe ich die genauen Öffnungszeiten für Samstag gerade nicht zur Hand – bitte rufen Sie uns direkt an oder besuchen Sie unsere Website für die aktuellen Öffnungszeiten von DOBOO Korean Soulfood!

---

### Turn 7

```
stt_latency_ms:    3
llm_latency_ms:    1836 ✅
tts_latency_ms:    1836
total_latency_ms:  1840 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          impatient
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

**User:** wissen, wann ihr heute zu habt.

**Bot:** Entschuldigung – heute ist tatsächlich Samstag! Für unsere genauen Öffnungszeiten heute rufen Sie uns bitte direkt an oder schauen Sie auf unserer Website vorbei.

---

### Turn 8

```
stt_latency_ms:    3
llm_latency_ms:    1112 ✅
tts_latency_ms:    1113
total_latency_ms:  1116 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          neutral
tts_inline_tag:    —
tts_rate_pct:      200
node_name:         goodbye
eot_event_type:    None
eot_confidence:    None
backchannel_fired: False
intent:            —
turn_type:         —
worker_profile:    —
stt_confidence:    None
tools_called:      ['end_call']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Ach okay, dann schaue ich mal auf eurer Webseite nach. Danke trotzdem. Tschüs. Ja, ich bin noch da. Dann schaue ich auf eurer Webseite nach. Tschüss.

**Bot:** Gerne helfe ich Ihnen bei weiteren Fragen – viel Spaß bei uns und bis bald!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1320 | 1314 | 5 | None | — | 200 | greeting_first | neutral | None | ai_greeting,get_date_info |  |
| 2 | 1574 | 1569 | 5 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 3 | 1734 | 1732 | 2 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 4 | 1675 | 1671 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1123 | 1118 | 4 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 6 | 1396 | 1392 | 4 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 7 | 1840 | 1836 | 3 | None | — | 200 | info_neutral | impatient | None | ai_greeting,get_date_info |  |
| 8 | 1116 | 1112 | 3 | None | — | 200 | info_neutral | neutral | None | end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **assistant** (turn 0): Hallo, hier ist Sailly, die KI-Assistentin von DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen behilflich sein?
- **user** (turn 1): Hallo.
- **assistant** (turn 2): Unsere Öffnungszeiten können sich je nach Wochentag unterscheiden – rufen Sie uns gerne direkt an, damit wir Ihnen die genauen Zeiten für heute mitteilen können! Kann ich Ihnen sonst noch bei etwas anderem helfen?
- **user** (turn 3): Ihr mir sagen, ab wann ihr aufmacht? Wann habt ihr denn geöffnet? Von
- **assistant** (turn 4): Heute ist Samstag – wir freuen uns auf Ihren Besuch bei DOBOO Korean Soulfood! Kann ich Ihnen noch etwas anderes helfen?
- **user** (turn 5): Wann bis wann seid ihr da? Ach, schade. Ich hatte gehofft, ihr könnt mir das schnell sagen. Können Sie mir nicht sagen, wann Sie heute geöffnet haben? Heute ist Mittwoch, oder? Dann müsste ich
- **assistant** (turn 6): Leider habe ich die genauen Öffnungszeiten für Samstag gerade nicht zur Hand – bitte rufen Sie uns direkt an oder besuchen Sie unsere Website für die aktuellen Öffnungszeiten von DOBOO Korean Soulfood!
- **user** (turn 7): wissen, wann ihr heute zu habt.
- **assistant** (turn 8): Entschuldigung – heute ist tatsächlich Samstag! Für unsere genauen Öffnungszeiten heute rufen Sie uns bitte direkt an oder schauen Sie auf unserer Website vorbei.
- **user** (turn 9): Ach okay, dann schaue ich mal auf eurer Webseite nach. Danke trotzdem. Tschüs. Ja, ich bin noch da. Dann schaue ich auf eurer Webseite nach. Tschüss.
- **assistant** (turn 10): Gerne helfe ich Ihnen bei weiteren Fragen – viel Spaß bei uns und bis bald!

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
        "phone_number": null,
        "shared_slots": {},
        "abuse_strikes": 0,
        "customer_name": null,
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "idle",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": null,
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
          "Gerne helfe ich Ihnen weiter! Leider habe ich die aktuellen Öffnungszeiten gerade nicht verfügbar – können Sie mich kurz mit der Nummer kontaktieren oder möchten Sie, dass ich Ihnen helfe, jemanden aus unserem Team zu erreichen?",
          "Da Sie uns heute, Samstag, anrufen, können Sie uns gerne direkt unter unserer Nummer erreichen, um die genauen Öffnungszeiten zu erfragen. Alternativ schaue ich gerne, wie ich Ihnen sonst noch weiterhelfen kann!",
          "Unsere Öffnungszeiten können sich je nach Wochentag unterscheiden – rufen Sie uns gerne direkt an, damit wir Ihnen die genauen Zeiten für heute mitteilen können! Kann ich Ihnen sonst noch bei etwas anderem helfen?",
          "Heute ist Samstag – wir freuen uns auf Ihren Besuch bei DOBOO Korean Soulfood! Kann ich Ihnen noch etwas anderes helfen?",
          "Leider habe ich die genauen Öffnungszeiten für Samstag gerade nicht zur Hand – bitte rufen Sie uns direkt an oder besuchen Sie unsere Website für die aktuellen Öffnungszeiten von DOBOO Korean Soulfood!",
          "Entschuldigung – heute ist tatsächlich Samstag! Für unsere genauen Öffnungszeiten heute rufen Sie uns bitte direkt an oder schauen Sie auf unserer Website vorbei.",
          "Gerne helfe ich Ihnen bei weiteren Fragen – viel Spaß bei uns und bis bald!"
        ],
        "reservation_date": "2026-05-02",
        "reservation_time": null,
        "delivery_intended": false,
        "ai_greeting_called": false,
        "current_intent_idx": null,
        "customer_confirmed": true,
        "get_weather_called": false,
        "reservation_intent": false,
        "validation_entries": {},
        "cached_menu_at_turn": null,
        "caller_id_confirmed": false,
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
            "bot": "Unsere Öffnungszeiten können sich je nach Wochentag unterscheiden – rufen Sie uns gerne direkt an, damit wir Ihnen die genauen Zeiten für heute mitteilen können! Kann ich Ihnen sonst noch bei etwas anderem helfen?",
            "node": "greeting",
            "customer": "Hallo."
          },
          {
            "bot": "Heute ist Samstag – wir freuen uns auf Ihren Besuch bei DOBOO Korean Soulfood! Kann ich Ihnen noch etwas anderes helfen?",
            "node": "business_info",
            "customer": "Ihr mir sagen, ab wann ihr aufmacht? Wann habt ihr denn geöffnet? Von"
          },
          {
            "bot": "Leider habe ich die genauen Öffnungszeiten für Samstag gerade nicht zur Hand – bitte rufen Sie uns direkt an oder besuchen Sie unsere Website für die aktuellen Öffnungszeiten von DOBOO Korean Soulfood!",
            "node": "business_info",
            "customer": "Wann bis wann seid ihr da? Ach, schade. Ich hatte gehofft, ihr könnt mir das schnell sagen. Können Sie mir nicht sagen, wann Sie heute geöffnet haben? Heute ist Mittwoch, oder? Dann müsste ich"
          },
          {
            "bot": "Entschuldigung – heute ist tatsächlich Samstag! Für unsere genauen Öffnungszeiten heute rufen Sie uns bitte direkt an oder schauen Sie auf unserer Website vorbei.",
            "node": "greeting",
            "customer": "wissen, wann ihr heute zu habt."
          },
          {
            "bot": "Gerne helfe ich Ihnen bei weiteren Fragen – viel Spaß bei uns und bis bald!",
            "node": "goodbye",
            "customer": "Ach okay, dann schaue ich mal auf eurer Webseite nach. Danke trotzdem. Tschüs. Ja, ich bin noch da. Dann schaue ich auf eurer Webseite nach. Tschüss."
          }
        ],
        "context_summary": " [greeting] Kunde: 'Hallo. Ich hab eine Frage zu euren Öffnungszeiten....' [business_info] Kunde: 'Wann habt ihr denn geöffnet? Ja, ich bin noch dran....' [business_info] Kunde: 'Wann habt ihr denn geöffnet?...'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 8,
      "all_tools": [
        "ai_greeting",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "ai_greeting",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "ai_greeting",
        "get_date_info",
        "end_call"
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
          "value": null,
          "status": "missing",
          "confidence": "low",
          "source_turn": null,
          "raw_mentions": []
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
          "value": null,
          "status": "missing",
          "confidence": "low",
          "source_turn": null,
          "raw_mentions": []
        },
        "reservation_time": {
          "value": null,
          "status": "missing",
          "confidence": "low",
          "source_turn": null,
          "raw_mentions": []
        }
      },
      "recent_responses": [
        "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
        "Gerne helfe ich Ihnen weiter! Leider habe ich die aktuellen Öffnungszeiten gerade nicht verfügbar – können Sie mich kurz mit der Nummer kontaktieren oder möchten Sie, dass ich Ihnen helfe, jemanden aus unserem Team zu erreichen?",
        "Da Sie uns heute, Samstag, anrufen, können Sie un
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=greeting turn_type=start_intent locked=False (conf=0.00) profile=greeting reroute=False
Turn 2: intent=faq turn_type=add_information locked=False (conf=0.00) profile=business_info reroute=False
Turn 3: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 4: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 5: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 6: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 7: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 8: intent=goodbye turn_type=finalize locked=True (conf=0.95) profile=goodbye reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
