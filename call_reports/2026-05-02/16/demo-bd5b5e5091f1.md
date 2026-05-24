# Sailly — Full Call Analysis Report
## Call ID: `demo-bd5b5e5091f1`
_Generated: 2026-05-02 16:22 UTC | Source: Postgres (`google_*`) + runtime env snapshot

---

## 1. Call Overview

| Parameter | Value |
|-----------|-------|
| **Call SID** | `demo-bd5b5e5091f1` |
| **Caller / channel** | `browser_demo` |
| **Started** | 2026-05-02 16:07:56 UTC |
| **Ended** | 2026-05-02 16:10:31 UTC |
| **Duration** | **154 seconds (2:34 min)** |
| **Total DB turns** | 5 |
| **Outcome / reason** | `v4_goodbye` |
| **Quality score** | 5.0 / 10 |
| **Avg latency (stored)** | 216 ms |
| **p95 latency (stored)** | 835 ms |
| **Max latency (stored)** | 1041 ms |
| **Was escalated** | False |
| **Tenant** | `doboo` |
| **Est. cost (stored)** | 220.3323 ¢ |

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
| Latency p50 / p95 / max (total) | 11 / 1041 / 1041 ms | Alert threshold env `MONITOR_LATENCY_P95_MS=3000` |
| LLM span (approx) p50 / max | 6 / 1037 ms | From `llm_latency_ms` column |
| STT p50 | 5 ms | From `stt_latency_ms` |
| Loop incidents | 0 | `loop_detected_in_stream` |
| Barge-in successes | 0 | `barge_in_succeeded` |
| Error codes (distinct) | — | `error_codes` |
| **[Phase 3] TTS latency** p50 / max | 6 / 1037 ms (5 turns) | From `tts_latency_ms` |
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
llm_latency_ms:    1037 ✅
tts_latency_ms:    1037
total_latency_ms:  1041 ✅
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

**User:** Hallo Sally. Wie ist das Wetter heute bei euch?

**Bot:** Das Wetter heute ist Bewölkt mit 26.3°C. Guten Tag! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?

---

### Turn 2

```
stt_latency_ms:    5
llm_latency_ms:    6 ✅
tts_latency_ms:    6
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

**User:** Und habt ihr heute Abend noch einen Tisch für 2 Personen 19 Uhr frei?

**Bot:** Auf welchen Namen darf ich reservieren?

---

### Turn 3

```
stt_latency_ms:    3
llm_latency_ms:    4 ✅
tts_latency_ms:    4
total_latency_ms:  8 ✅
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

**User:** Max Müller.

**Bot:** Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?

---

### Turn 4

```
stt_latency_ms:    5
llm_latency_ms:    6 ✅
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
tools_called:      ['get_date_info', 'check_availability', 'create_reservation']
validation_breakdown: {}
subsystems_fired:  {"barge_in": "enabled", "node_manager": "ran", "memory_manager": "ran", "registry_exists": true, "silence_reprompt": "armed", "tts_conditioning": "applied", "stuck_loop_detector": "skipped", "validation_registry": "silent", "validation_pending_count": 0}
error_codes:       []
barge_in:          attempted=True succeeded=None latency_ms=None
loop:              detected=None reason=None
build_sha:         None
```

**User:** 0 1 6 2 3 4 6 4 7 9 8 9.

**Bot:** Ich habe 2 Personen für heute um 19:00 Uhr auf den Namen Max Müller reserviert. Stimmt das so?

---

### Turn 5

```
stt_latency_ms:    5
llm_latency_ms:    6 ✅
tts_latency_ms:    6
total_latency_ms:  11 ✅
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

**User:** zweimal hintereinander gesagt. Stimmt das so? Das war's.

**Bot:** Vielen Dank und auf Wiederhören!

---

## 5. Timeline table (compact)

| Turn | total_ms | llm_ms | stt_ms | eot_type | intent | tts_rate_pct | situation | mood | tag | tools | flags |
|------|----------|--------|--------|----------|--------|--------------|-----------|------|-----|-------|-------|
| 1 | 1041 | 1037 | 4 | None | — | 200 | info_neutral | neutral | None | get_date_info,get_weather |  |
| 2 | 11 | 6 | 5 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 3 | 8 | 4 | 3 | None | — | 200 | info_neutral | neutral | None | get_date_info |  |
| 4 | 11 | 6 | 5 | None | — | 200 | info_neutral | neutral | None | get_date_info,check_availability,create_reservation |  |
| 5 | 11 | 6 | 5 | None | — | 200 | confirm_success | neutral | None | end_call |  |

---

## 6. Transcripts (`google_transcripts`)

- **user** (turn 0): Hallo Sally. Wie ist das Wetter heute bei euch?
- **assistant** (turn 1): Das Wetter heute ist Bewölkt mit 26.3°C. Guten Tag! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?
- **user** (turn 2): Und habt ihr heute Abend noch einen Tisch für 2 Personen 19 Uhr frei?
- **assistant** (turn 3): Auf welchen Namen darf ich reservieren?
- **user** (turn 4): Max Müller.
- **assistant** (turn 5): Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?
- **user** (turn 6): 0 1 6 2 3 4 6 4 7 9 8 9.
- **assistant** (turn 7): Ich habe 2 Personen für heute um 19:00 Uhr auf den Namen Max Müller reserviert. Stimmt das so?
- **user** (turn 8): zweimal hintereinander gesagt. Stimmt das so? Das war's.
- **assistant** (turn 9): Vielen Dank und auf Wiederhören!

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
        "party_size": 2,
        "cached_menu": null,
        "menu_fetched": false,
        "order_intent": false,
        "phone_number": "0 1 6 2 3 4 6 4 7 9",
        "shared_slots": {},
        "abuse_strikes": 0,
        "customer_name": "Max Müller",
        "order_created": false,
        "selected_dish": null,
        "end_call_stage": "confirmed",
        "order_quantity": 1,
        "schema_version": 5,
        "caller_id_phone": null,
        "farewell_spoken": false,
        "delivery_address": null,
        "recent_responses": [
          "Herzlich willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
          "Das Wetter heute ist Bewölkt mit 26.3°C. Guten Tag! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?",
          "Auf welchen Namen darf ich reservieren?",
          "Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?",
          "Ich habe 2 Personen für heute um 19:00 Uhr auf den Namen Max Müller reserviert. Stimmt das so?",
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
            "bot": "Das Wetter heute ist Bewölkt mit 26.3°C. Guten Tag! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?",
            "node": "business_info",
            "customer": "Hallo Sally. Wie ist das Wetter heute bei euch?"
          },
          {
            "bot": "Auf welchen Namen darf ich reservieren?",
            "node": "reservation_start",
            "customer": "Und habt ihr heute Abend noch einen Tisch für 2 Personen 19 Uhr frei?"
          },
          {
            "bot": "Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?",
            "node": "reservation_start",
            "customer": "Max Müller."
          },
          {
            "bot": "Ich habe 2 Personen für heute um 19:00 Uhr auf den Namen Max Müller reserviert. Stimmt das so?",
            "node": "reservation_start",
            "customer": "0 1 6 2 3 4 6 4 7 9 8 9."
          },
          {
            "bot": "Vielen Dank und auf Wiederhören!",
            "node": "reservation_start",
            "customer": "zweimal hintereinander gesagt. Stimmt das so? Das war's."
          }
        ],
        "context_summary": " [greeting] Kunde: '<call_start>...'",
        "max_recent_turns": 5,
        "max_summary_words": 300
      },
      "node_mgr": {
        "node_stack": [],
        "current_node": "greeting",
        "turns_in_node": 0
      },
      "turn_idx": 6,
      "all_tools": [
        "ai_greeting",
        "get_date_info",
        "get_date_info",
        "get_weather",
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
        "Herzlich willkommen bei DOBOO Korean Soulfood in Bonn! Wie kann ich Sie heute unterstützen?",
        "Das Wetter heute ist Bewölkt mit 26.3°C. Guten Tag! Wie kann ich Ihnen bei DOBOO Korean Soulfood heute weiterhelfen?",
        "Auf welchen Namen darf ich reservieren?",
        "Welche Telefonnummer darf ich notieren, falls wir Sie zurückrufen müssen?",
        "Ich habe 2 Personen für heute um 19:00 Uhr auf den Namen Max Müller reserviert. Stimmt das so?",
        "Vielen Dank und auf Wiederhören!"
      ]
    }
  },
  "caller": "browser_demo",
  "tenant": "doboo",
  "call_sid": "demo-bd5b5e5091f1",
  "ended_at": "2026-05-02T18:10:31.265107+02:00",
  "tenant_id": "doboo",
  "started_at": "2026-05-02T18:07:56.893138+02:00",
  "started_ts": 1777738076.893179,
  "tool_calls": [],
  "from_number": "browser",
  "transcripts": [
    {
      "role": "user",
      "text": "Hallo Sally. Wie ist das Wetter heute bei euch?",
      "timestamp": "2026-05-02T18:09:00.937047+02:00"
    },
    {
      "role": "user",
      "text": "Und habt ihr heute Abend noch einen Tisch für 2 Personen 19 Uhr frei?",
      "timestamp": "2026-05-02T18:09:01.996354+02:00"
    },
    {
      "role": "user",
      "text": "Max Müller.",
      "timestamp": "2026-05-02T18:09:23.484571+02:00"
    },
    {
      "role": "user",
      "text": "0 1 6 2 3 4 6 4 7 9 8 9.",
      "timestamp": "2026-05-02T18:09:42.734330+02:00"
    },
    {
      "role": "user",
      "text": "Achtung Sally, 1 noch, bitte hinzufügen zum Transkript. Begrüßung mit doppelter Wiederholung. Turn 2, wettergesagt, wieder 26 Grad. Dann guten Tag, doppelt gesagt. Turn 3, nach dem Namen gefragt. Turn 4, nach der Telefon Telefonnummer gefragt. TERN 5, Reservierung bestätigt, aber den gleichen Satz",
      "timestamp": "2026-05-02T18:10:27.055814+02:00"
    },
    {
      "role": "bot",
      "text": "Verstanden, ich habe das notiert.",
      "timestamp": "2026-05-02T18:10:27.062855+02:00"
    },
    {
      "role": "user",
      "text": "zweimal hintereinander gesagt. Stimmt d
```

---

## 8.5 Intent Session (`google_context_documents`)

```python
# v4 pipeline live for all intents — MIGRATED_PROFILES = set(_PROFILES.keys())
Turn 1: intent=faq turn_type=start_intent locked=False (conf=0.00) profile=business_info reroute=False
Turn 2: intent=reservation turn_type=add_information locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 3: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 4: intent=reservation turn_type=unclear locked=True (conf=0.85) profile=reservation_start reroute=False
Turn 5: intent=reservation turn_type=finalize locked=True (conf=0.85) profile=reservation_start reroute=False
```

---

## 9. Auto-generated observations

- No automatic red flags from thresholds (review per-turn section for quality).

---

_Report end._
