# Sailly — Full Call Analysis Report
## Call ID: `demo-f75f6aaf2b9e`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-f75f6aaf2b9e` |
| **Caller / channel** | `[validation:A2_tool_tag_eilig]` |
| **Started** | 2026-05-01 06:50:36 UTC |
| **Ended** | 2026-05-01 06:51:50 UTC |
| **Duration** | **74 seconds (1:14 min)** |
| **Total DB turns** | 9 |
| **Outcome / reason** | `v4_goodbye` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 1177 ms |
| **p95 latency (stored)** | 1422 ms |
| **Max latency (stored)** | 1431 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 108.9157 ¢ |

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
| Latency p50 / p95 / max (total) | 1160 / 1431 / 1431 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 1156 / 1427 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 1156 / 1427 ms (9 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    967 ✅
tts_latency_ms:    968
total_latency_ms:  971 ✅
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

**User:** Ich brauch die Adresse für die Navigation.

**Bot:** Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Ihnen heute weiterhelfen?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    1237 ✅
tts_latency_ms:    1238
total_latency_ms:  1241 ✅
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

**User:** Ähm, ich wollte nur die Adresse wissen.

**Bot:** Gerne! Unsere Adresse ist DOBOO Korean Soulfood, Bonner Talweg 1, 53113 Bonn – Sie können diese gerne in Ihre Navigation eingeben.

---

### Turn 3

```
stt_latency_ms:    4
llm_latency_ms:    929 ✅
tts_latency_ms:    930
total_latency_ms:  933 ✅
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

**User:** Können wir das jetzt klären?

**Bot:** Sehr gerne! Gibt es noch etwas, womit ich Ihnen weiterhelfen kann?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    1238 ✅
tts_latency_ms:    1238
total_latency_ms:  1241 ✅
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

**User:** Danke. Das ist alles, was ich brauche.

**Bot:** Gerne helfe ich Ihnen weiter – können Sie mir kurz sagen, was genau ich für Sie klären kann? So kann ich Ihnen am besten und schnellsten helfen!

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    1149 ✅
tts_latency_ms:    1149
total_latency_ms:  1152 ✅
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

**User:** Choose

**Bot:** Das freut mich, dass ich Ihnen helfen konnte! Falls Sie noch weitere Fragen zu DOBOO Korean Soulfood haben, rufen Sie gerne jederzeit an.

---

### Turn 6

```
stt_latency_ms:    3
llm_latency_ms:    1156 ✅
tts_latency_ms:    1156
total_latency_ms:  1160 ✅
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

**User:** Turn eins. Okay. Hallo, ich bin

**Bot:** Gerne geschehen! Wenn Sie noch Fragen haben oder einen Tisch reservieren möchten, helfe ich Ihnen jederzeit weiter.

---

### Turn 7

```
stt_latency_ms:    3
llm_latency_ms:    1056 ✅
tts_latency_ms:    1057
total_latency_ms:  1060 ✅
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

**User:** in den Eile. Wo befindet sich euer Restaurant genau?

**Bot:** Herzlich willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?

---

### Turn 8

```
stt_latency_ms:    3
llm_latency_ms:    1427 ✅
tts_latency_ms:    1427
total_latency_ms:  1431 ✅
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

**User:** Ziel erfüllt. Turn zwei. Okay, ich wollte nur die Adresse wissen. Können wir das jetzt klären?

**Bot:** Gerne helfe ich Ihnen weiter – leider habe ich die genaue Adresse unseres Restaurants gerade nicht zur Hand. Bitte rufen Sie uns direkt an oder besuchen Sie unsere Website, um die aktuelle Adresse zu erhalten!

---

### Turn 9

```
stt_latency_ms:    3
llm_latency_ms:    1404 ✅
tts_latency_ms:    1404
total_latency_ms:  1408 ✅
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

**User:** Natürliche Nachfrage. Turn drei. Okay, danke, dass Es ist alles, was ich brauche. Tschüs.

**Bot:** Entschuldigen Sie, dass ich Ihnen die Adresse nicht direkt geben konnte – Sie finden alle Informationen auf unserer Website oder erreichen uns telefonisch. Ich wünsche Ihnen einen schönen Tag!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 971 | 967 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 2 | 1241 | 1237 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 3 | 933 | 929 | 4 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 4 | 1241 | 1238 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 5 | 1152 | 1149 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 6 | 1160 | 1156 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 7 | 1060 | 1056 | 3 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 8 | 1431 | 1427 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 9 | 1408 | 1404 | 3 | None | — | 200 | info_neutral | neutral | None | end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo, ich bin in Eile. Wo befindet sich euer Restaurant genau?
- **user** (turn 1): Ich brauch die Adresse für die Navigation.
- **user** (turn 2): Ähm, ich wollte nur die Adresse wissen.
- **user** (turn 3): Können wir das jetzt klären?
- **user** (turn 4): Danke. Das ist alles, was ich brauche.
- **user** (turn 5): Choose
- **user** (turn 6): Turn eins. Okay. Hallo, ich bin
- **user** (turn 7): in den Eile. Wo befindet sich euer Restaurant genau?
- **user** (turn 8): Ziel erfüllt. Turn zwei. Okay, ich wollte nur die Adresse wissen. Können wir das jetzt klären?
- **user** (turn 9): Natürliche Nachfrage. Turn drei. Okay, danke, dass Es ist alles, was ich brauche. Tschüs.

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
        "customer_name": null,
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
          "Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Ihnen heute weiterhelfen?",
          "Gerne! Unsere Adresse ist DOBOO Korean Soulfood, Bonner Talweg 1, 53113 Bonn – Sie können diese gerne in Ihre Navigation eingeben.",
          "Sehr gerne! Gibt es noch etwas, womit ich Ihnen weiterhelfen kann?",
          "Gerne helfe ich Ihnen weiter – können Sie mir kurz sagen, was genau ich für Sie klären kann? So kann ich Ihnen am besten und schnellsten helfen!",
          "Das freut mich, dass ich Ihnen helfen konnte! Falls Sie noch weitere Fragen zu DOBOO Korean Soulfood haben, rufen Sie gerne jederzeit an.",
          "Gerne geschehen! Wenn Sie noch Fragen haben oder einen Tisch reservieren möchten, helfe ich Ihnen jederzeit weiter.",
          "Herzlich willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
          "Gerne helfe ich Ihnen weiter – leider habe ich die genaue Adresse unseres Restaurants gerade nicht zur Hand. Bitte rufen Sie uns direkt an oder besuchen Sie unsere Website, um die aktuelle Adresse zu erhalten!",
          "Entschuldigen Sie, dass ich Ihnen die Adresse nicht direkt geben konnte – Sie finden alle Informationen auf unserer Website oder erreichen uns telefonisch. Ich wünsche Ihnen einen schönen Tag!"
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
            "bot": "Das freut mich, dass ich Ihnen helfen konnte! Falls Sie noch weitere Fragen zu DOBOO Korean Soulfood haben, rufen Sie gerne jederzeit an.",
            "node": "greeting",
            "customer": "Choose"
          },
          {
            "bot": "Gerne geschehen! Wenn Sie noch Fragen haben oder einen Tisch reservieren möchten, helfe ich Ihnen jederzeit weiter.",
            "node": "greeting",
            "customer": "Turn eins. Okay. Hallo, ich bin"
          },
          {
            "bot": "Herzlich willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
            "node": "greeting",
            "customer": "in den Eile. Wo befindet sich euer Restaurant genau?"
          },
          {
            "bot": "Gerne helfe ich Ihnen weiter – leider habe ich die genaue Adresse unseres Restaurants gerade nicht zur Hand. Bitte rufen Sie uns direkt an oder besuchen Sie unsere Website, um die aktuelle Adresse zu erhalten!",
            "node": "business_info",
            "customer": "Ziel erfüllt. Turn zwei. Okay, ich wollte nur die Adresse wissen. Können wir das jetzt klären?"
          },
          {
            "bot": "Entschuldigen Sie, dass ich Ihnen die Adresse nicht direkt geben konnte – Sie finden alle Informationen auf unserer Website oder erreichen uns telefonisch. Ich wünsche Ihnen einen schönen Tag!",
            "node": "goodbye",
            "customer": "Natürliche Nachfrage. Turn drei. Okay, danke, dass Es ist alles, was ich brauche. Tschüs."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [business_info] Kunde: 'Ich brauch die Adresse für die Navigation....' [business_info] Kunde: 'Ähm, ich wollte nur die Adresse wissen....' [greeting] Kunde: 'Können wir das jetzt klären?...' [greeting] Kunde: 'Danke. Das ist alles, was ich brauche....'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 10,
      "all_tools": [
        "ai_greeting",
        "get_date_info",
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
          "value": "+4915900000002",
          "status": "partial",
          "confidence": "high",
          "source_turn": 0,
          "raw_mentions": [
            "caller_id:+4915900000002"
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
        "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Ihnen heute helfen?",
        "Guten Tag! Ich bin Sailly von DOBOO Korean Soulfood in Bonn – wie kann ich Ihnen heute weiterhelfen?",
        "Gerne! Unsere Adresse ist DOBOO Korean Soulfood, Bonner Talweg 1, 53113 Bonn – Sie können diese gerne in Ihre Navigat
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 2: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 3: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 4: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 5: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 6: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 7: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 8: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 9: intent=goodbye turn_type=finalize locked=True (conf=0.95) profile=goodbye reroute=False
Turn 10: intent=goodbye turn_type=unclear locked=True (conf=0.95) profile=goodbye reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
