# Sailly — Full Call Analysis Report
## Call ID: `demo-45de9e510d0c`
_Generated: 2026-05-02 16:05 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-45de9e510d0c` |
| **Caller / channel** | `[validation:A1_meta_feedback_wuetend]` |
| **Started** | 2026-05-01 06:41:20 UTC |
| **Ended** | 2026-05-01 06:42:11 UTC |
| **Duration** | **50 seconds (0:50 min)** |
| **Total DB turns** | 8 |
| **Outcome / reason** | `v4_goodbye` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 158 ms |
| **p95 latency (stored)** | 784 ms |
| **Max latency (stored)** | 1200 ms |
| **Was escalated** | False |
| **Tenant** | `—` |
| **Est. cost (stored)** | 72.6047 ¢ |

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
| Latency p50 / p95 / max (total) | 10 / 1200 / 1200 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 6 / 1194 ms | From `llm_latency_ms` column |
| STT p50 | 3 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 6 / 1194 ms (8 turns) | From `tts_latency_ms` |
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
stt_latency_ms:    6
llm_latency_ms:    1194 ✅
tts_latency_ms:    1194
total_latency_ms:  1200 ✅
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

**User:** Ich bin total sauer, weil ich vor einer Woche schon mal versucht hab, bei euch zu reservieren und dann hat's nicht geklappt.

**Bot:** Schön, Sie bei uns zu haben, Herr Sauer! Womit kann ich Ihnen heute bei DOBOO Korean Soulfood helfen?

---

### Turn 2

```
stt_latency_ms:    3
llm_latency_ms:    7 ✅
tts_latency_ms:    7
total_latency_ms:  11 ✅
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

**User:** Jetzt will ich aber endlich eine Reservierung machen und wehe, das klappt wieder nicht. Können Sie mir einen Tisch für Samstagabend reservieren?

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    5 ✅
tts_latency_ms:    5
total_latency_ms:  9 ✅
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

**User:** Ich hab doch gerade schon gesagt, dass ich eine Reservierung für Samstagabend machen will.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 4

```
stt_latency_ms:    3
llm_latency_ms:    6 ✅
tts_latency_ms:    6
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

**User:** Hören Sie mir überhaupt zu? Ich hab doch schon gesagt, dass ich einen Tisch für Samstagabend reservieren will.

**Bot:** Für wie viele Personen darf ich reservieren?

---

### Turn 5

```
stt_latency_ms:    3
llm_latency_ms:    5 ✅
tts_latency_ms:    5
total_latency_ms:  8 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     info_neutral
tts_mood:          frustrated
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

**User:** Für vier Personen.

**Bot:** Um wie viel Uhr darf ich reservieren?

---

### Turn 6

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

**User:** Und ich würde es für Samstagabend um neunzehn Uhr.

**Bot:** Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?

---

### Turn 7

```
stt_latency_ms:    3
llm_latency_ms:    6 ✅
tts_latency_ms:    6
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
tools_called:      ['get_date_info', 'check_availability', 'create_reservation']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** null eins fünf sieben und null fünf sieben zweitausendvierhundertneunundneunzig fünf neun fünf sechs sieben neun.

**Bot:** Ich habe 4 Personen für morgen um 19:00 Uhr auf den Namen Total Sauer reserviert. Stimmt das so?

---

### Turn 8

```
stt_latency_ms:    5
llm_latency_ms:    4 ✅
tts_latency_ms:    4
total_latency_ms:  9 ✅
stt_ms / extract_ms / l2_ms / tool_ms / tts_first_byte_ms: None / None / None / None / None
tts_situation:     confirm_success
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
tools_called:      ['end_call']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** Und bestätigen Sie mir das bitte gleich, damit nix wieder schiefgeht.

**Bot:** Vielen Dank und auf Wiederhören!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1200 | 1194 | 6 | None | — | 200 | info_neutral | neutral | None | ai_greeting,get_date_info |  |
| 2 | 11 | 7 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 3 | 9 | 5 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 4 | 10 | 6 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 5 | 8 | 5 | 3 | None | — | 200 | info_neutral | frustrated | None | get_date_info |  |
| 6 | 10 | 6 | 4 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 7 | 10 | 6 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info,check_availability,create_reservation |  |
| 8 | 9 | 4 | 5 | None | — | 200 | confirm_success | neutral | None | end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Ich bin total sauer, weil ich vor einer Woche schon mal versucht hab, bei euch zu reservieren und dann hat's nicht geklappt.
- **user** (turn 1): Jetzt will ich aber endlich eine Reservierung machen und wehe, das klappt wieder nicht. Können Sie mir einen Tisch für Samstagabend reservieren?
- **user** (turn 2): Ich hab doch gerade schon gesagt, dass ich eine Reservierung für Samstagabend machen will.
- **user** (turn 3): Hören Sie mir überhaupt zu? Ich hab doch schon gesagt, dass ich einen Tisch für Samstagabend reservieren will.
- **user** (turn 4): Für vier Personen.
- **user** (turn 5): Und ich würde es für Samstagabend um neunzehn Uhr.
- **user** (turn 6): null eins fünf sieben und null fünf sieben zweitausendvierhundertneunundneunzig fünf neun fünf sechs sieben neun.
- **user** (turn 7): Und bestätigen Sie mir das bitte gleich, damit nix wieder schiefgeht.

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
        "party_size": 4,
        "cached_menu": null,
        "menu_fetched": false,
        "order_intent": false,
        "phone_number": "0177777077777",
        "shared_slots": {},
        "abuse_strikes": 0,
        "customer_name": "Total Sauer",
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "confirmed",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": "+4915900000001",
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
          "Schön, Sie bei uns zu haben, Herr Sauer! Womit kann ich Ihnen heute bei DOBOO Korean Soulfood helfen?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Für wie viele Personen darf ich reservieren?",
          "Um wie viel Uhr darf ich reservieren?",
          "Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?",
          "Ich habe 4 Personen für morgen um 19:00 Uhr auf den Namen Total Sauer reserviert. Stimmt das so?",
          "Vielen Dank und auf Wiederhören!"
        ],
        "reservation_date": "2026-05-02",
        "reservation_time": "19:00",
        "delivery_intended": false,
        "ai_greeting_called": false,
        "current_intent_idx": null,
        "customer_confirmed": true,
        "get_weather_called": false,
        "reservation_intent": true,
        "validation_entries": {},
        "cached_menu_at_turn": null,
        "caller_id_confirmed": false,
        "caller_said_goodbye": false,
        "reservation_created": true,
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
        "check_availability_called": true,
        "pending_bulk_confirmation": false,
        "delivery_address_mentioned": false,
        "last_caller_confirmation_turn": null
      },
      "memory": {
        "recent_turns": [
          {
            "bot": "Für wie viele Personen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Hören Sie mir überhaupt zu? Ich hab doch schon gesagt, dass ich einen Tisch für Samstagabend reservieren will."
          },
          {
            "bot": "Um wie viel Uhr darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Für vier Personen."
          },
          {
            "bot": "Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?",
            "node": "reservation_start",
            "customer": "Und ich würde es für Samstagabend um neunzehn Uhr."
          },
          {
            "bot": "Ich habe 4 Personen für morgen um 19:00 Uhr auf den Namen Total Sauer reserviert. Stimmt das so?",
            "node": "reservation_start",
            "customer": "null eins fünf sieben und null fünf sieben zweitausendvierhundertneunundneunzig fünf neun fünf sechs sieben neun."
          },
          {
            "bot": "Vielen Dank und auf Wiederhören!",
            "node": "reservation_start",
            "customer": "Und bestätigen Sie mir das bitte gleich, damit nix wieder schiefgeht."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...' [greeting] Kunde: 'Ich bin total sauer, weil ich vor einer Woche schon mal versucht hab, bei euch zu reservieren und dann hat's nicht geklappt....' [reservation_start] Kunde: 'Jetzt will ich aber endlich eine Reservierung machen und wehe, das klappt wieder nicht. Können Sie mir einen Tisch für Samstagabend reservieren?...' [reservation_start] Kunde: 'Ich hab doch gerade schon gesagt, dass ich eine Reservierung für Samstagabend machen will....'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 9,
      "all_tools": [
        "ai_greeting",
        "get_date_info",
        "ai_greeting",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "get_date_info",
        "check_availability",
        "create_reservation",
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
        "Schön, Sie bei uns zu haben, Herr Sauer! Womit kann ich Ihnen heute bei DOBOO Korean Soulfood helfen?",
        "Für wie viele Personen darf ich reservieren?",
        "Für wie viele Personen darf ich reservieren?",
        "Für wie viele Personen darf ich reservieren?",
        "Um wie viel Uhr darf ich reservieren?",
        "Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?",
        "Ich habe 4 Personen für morgen um 19:00 Uhr auf den Namen Total Sauer reserviert. Stimmt das so?",
        "Vielen Dank und auf Wiederhören!"
      ]
    }
  },
  "caller": "browser_demo",
  "call_sid": "demo-45de9e510d0c",
  "ended_at": "2026-05-01T08:42:11.212164+02:00",
  "started_at": "2026-05-01T08:41:20.467293+02:00",
  "started_ts": 1777617680.4673243,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Ich bin total sauer, weil ich vor einer Woche schon mal versucht hab, bei euch zu reservieren und dann hat's nicht geklappt.",
      "timestamp": "2026-05-01T08:41:28.577901+02:00"
    },
    {
      "role": "user",
      "text": "Jetzt 
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=unknown turn_type=unclear locked=False (conf=0.00) profile=greeting reroute=False
Turn 2: intent=reservation turn_type=finalize locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 3: intent=reservation turn_type=start_intent locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 4: intent=reservation turn_type=finalize locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 5: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 6: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 7: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 8: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 9: intent=unknown turn_type=unclear locked=False (conf=0.85) profile=greeting reroute=True
Turn 10: intent=reservation turn_type=add_information locked=True (conf=0.85) profile=reservation_start reroute=True
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
