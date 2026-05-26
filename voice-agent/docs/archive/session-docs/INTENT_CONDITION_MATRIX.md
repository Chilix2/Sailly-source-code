# Intent Condition Matrix — All Requirements by Context

**Purpose:** Map every condition, validation rule, and extraction strategy across reservation, order, and FAQ intents. Identify which conditions are always-on vs context-specific.

---

## 1. PHONE NUMBER

### Extraction Rules

| Context | Rule | Min Length | Max Length | Accepts | Rejects | Location |
|---------|------|-----------|-----------|---------|---------|----------|
| **All Intents** | Phone digit assembly | 10 digits | 13 digits | Any digit string + spoken digits ("eins", "zwei") | <10 or >13 digits | `conversation_state.py:501` |
| **All Intents** | Spoken shorthand expansion | — | — | "eins"→"1", "doppel"→"11", "null"→"0" | Non-digit words | `conversation_state.py:509-510` |
| **All Intents** | Address word guard | — | — | Stops collection on street names (Straße, Platz, etc.) | Street numbers contaminating phone | `conversation_state.py:525-541` |
| **All Intents** | Format tolerance | — | — | "+49 89 4521 8834", "089 4521 8834", "+4989452​18834" | Other formats | `conversation_state.py:512-516` |

### Required For

| Intent | Tool | Field | Required | Fallback | Impact if Missing |
|--------|------|-------|----------|----------|-------------------|
| **Reservation** | `create_reservation` | `phone_number` | ✅ YES | None | ❌ Commit blocked (gate won't fire) |
| **Order** | `create_order` | `phone_number` | ✅ YES | None | ❌ Commit blocked (gate won't fire) |
| **SMS** | `send_sms` | `phone_number` | ✅ YES | None | ❌ Tool call fails |
| **FAQ/Inquiry** | None | — | ❌ NO | — | ✅ OK (informational, no commit) |

### Validation Gates

```python
# In context_doc_builder.py line 24-26
COMMIT_TOOLS_REQUIRED_SLOTS["create_reservation"]  = [..., "phone_number"]
COMMIT_TOOLS_REQUIRED_SLOTS["create_order"]        = [..., "phone_number"]
COMMIT_TOOLS_REQUIRED_SLOTS["send_sms"]            = ["phone_number"]

# In v4_pipeline.py line 209
"phone_number": getattr(state, "phone_number", None),
```

### Current State & Issues

| Issue | Status | Fix Applied | Details |
|-------|--------|-------------|---------|
| Mobile-only prefix filter (015x, 016x, 017x) | ✅ FIXED | Removed filters in `conversation_state.py` lines 1954-2026 | Now accepts landlines (089, 030, 040, etc.) |
| Format: callers say "089" not "+49 89" | ✅ FIXED | `phase_runner.py`: strips "+49" prefix, converts to "089..." | Realistic German caller behavior |
| Cross-turn buffer assembly | ✅ ACTIVE | Lines 1967-2031 | Supports digit-by-digit collection ("eins", "vier", "vier", "vier"...) |
| No persistence to `required_data` pre-load | ✅ FIXED | Added `required_data["phone_number"]` to `scenario_generator.py` | Caller bot now has phone pre-loaded |

---

## 2. NAME (Customer / Caller)

### Extraction Rules

| Context | Rule | Requirement | Example | Rejected | Location |
|---------|------|-------------|---------|----------|----------|
| **Full Name (Delivery/Order)** | Two capitalized words | `^[A-ZÄÖÜ][a-zäöüß\-]{2,}\s+[A-ZÄÖÜ][a-zäöüß\-]{2,}$` | "Markus Bauer", "Hans-Peter Koch" | "Mueller" (single word), "john Smith" (lowercase) | `conversation_state.py:117` |
| **Full Name (Marker-based)** | Must follow marker + optional title | Regex with markers: "ich heiße", "mein name ist" | "Ich heiße Markus Bauer", "Hier ist Sabine Hoffmann" | "Bibimbap" (dish), "Berlin" (city) | `conversation_state.py:129-150` |
| **Single First Name** | Marker + capitalized ≥3 chars | `^[A-ZÄÖÜ][a-zäöüß]{2,}$` + NOT in blocklist | "Hier ist Julius", "Ich bin Maria" | "I" (1 char), "Bibimbap" (dish name) | `conversation_state.py:163-240` |
| **Fallback (Reservation)** | Allow single name via `customer_name ⇐ first_name` | Works if `first_name` is set | "Müller" alone satisfies reservation | N/A (fallback only) | `v4_pipeline.py:208` |

### Data Flow

```
Utterance
    ↓
_extract_name_from_utterance()  → "Markus Bauer" (full name)
    ↓ [if None]
_extract_first_name_from_utterance()  → "Markus" (single first)
    ↓ [persisted as state.first_name]
    ↓ [at commit gate, if customer_name is None]
_state_snapshot_for_gate() falls back: customer_name = first_name or customer_name
    ↓
Reservation: single name OK; Order: requires full name + address (separate)
```

### Required For

| Intent | Field | Requirement | Impact if Missing |
|--------|-------|-------------|-------------------|
| **Reservation** | `customer_name` | ✅ Required (COMMIT_TOOLS_REQUIRED_SLOTS) | ❌ Commit gate blocks |
| **Order** | `customer_name` | ✅ Required (COMMIT_TOOLS_REQUIRED_SLOTS) | ❌ Commit gate blocks |
| **FAQ** | — | ❌ Not needed | ✅ OK |

### Current State & Issues

| Issue | Status | Fix Applied | Details |
|-------|--------|-------------|---------|
| Single name loops (name loop bug) | ✅ FIXED | `v4_pipeline.py:208` fallback: `customer_name = customer_name or first_name` | Reservation now accepts "Müller" alone |
| Two-word validation too strict | ✅ WORKING AS DESIGNED | Allows delivery to validate full address (separate flow) | Not a bug; intended for orders |
| Name blocklist contamination | ✅ ACTIVE | Blocks: known dishes (Bibimbap, Bulgogi), cities (Bonn, Berlin) | See `_NAME_BLOCKLIST` in `conversation_state.py:50-80` |
| `required_data` pre-loading | ✅ FIXED | Added `required_data["customer_name"]` to `scenario_generator.py` | Caller bot has name pre-loaded |

---

## 3. PARTY SIZE (Personenzahl)

### Extraction Rules

| Context | Rule | Min | Max | Example | Rejected | Location |
|---------|------|-----|-----|---------|----------|----------|
| **German phrases** | "für X Personen", "Tisch für X" | 1 | 50+ | "für 2 Personen", "für drei" | "für 0", "für 100" | `conversation_state.py:283-350` |
| **Direct numbers** | Digits 1–50 after "Personen" | 1 | 50 | "2", "drei", "3" | "51", "0", negative | `conversation_state.py:297-320` |
| **Spoken numbers** | "eins"→1, "zwei"→2, etc. | 1 | 50 | "zwei Personen", "vier Leute" | "null", "hundert" | `conversation_state.py:334-345` |

### Default Fallback

```python
# In executor.py and v4_pipeline.py
party_size = getattr(state, "party_size", None) or 2  # Default: 2 if not extracted
```

### Required For

| Intent | Field | Requirement | Impact if Missing |
|--------|-------|-------------|-------------------|
| **Reservation** | `party_size` | ✅ Required (COMMIT_TOOLS_REQUIRED_SLOTS) | ❌ Commit gate blocks |
| **Check Availability** | `party_size` | ✅ Required | ❌ Tool fails |
| **Order** | — | ❌ Not needed | ✅ OK (implicit: 1 person) |
| **FAQ** | — | ❌ Not needed | ✅ OK |

### Current State & Issues

| Issue | Status | Details |
|-------|--------|---------|
| German number words ("zwei", "drei") | ✅ ACTIVE | Supported; mapped in `_SPOKEN_DIGITS` dict |
| Phrase detection ("für X Personen") | ✅ ACTIVE | Regex: `r"(?:für|tisch für|platz für|reservierung für)\s+(\d+|[a-z]+)\s*(?:personen\|leute\|gäste)"` |
| Boundary checking | ✅ ACTIVE | Rejects >50 (suggests transfer for large groups) |
| Pre-load in `required_data` | ✅ FIXED | All A1 scripts have `required_data["party_size"]` |

---

## 4. RESERVATION DATE & TIME

### Extraction Rules — Date

| Context | Rule | Format | Example | Rejected | Location |
|---------|------|--------|---------|----------|----------|
| **Relative (today/tomorrow)** | heute, morgen, übermorgen | String | "heute", "morgen Abend" | "vorgestern" (past) | `conversation_state.py:370-410` |
| **Next weekday** | "nächsten Montag", etc. | String | "nächste Woche Samstag" | "letzte Woche" (past) | `conversation_state.py:411-460` |
| **German date phrase** | "15. April", "1. Mai" | DE locale | "15. April 2026" | "00.00.0000" (invalid) | `conversation_state.py:461-500` |
| **ISO 8601** | YYYY-MM-DD | Date object | 2026-05-06 | Before today | `tools/executor.py:549-596` |

### Extraction Rules — Time

| Context | Rule | Format | Example | Rejected | Location |
|---------|------|--------|---------|----------|----------|
| **Hour + minute** | HH:MM (24h) | "19:00", "19 Uhr 30" | "19:30", "20 Uhr" | "25:00", "14:75" | `conversation_state.py:707-780` |
| **Half hours** | "halb" + hour | "halb acht" → 19:30 | "halb neun" → 20:30 | Floating-point half | `conversation_state.py:745-755` |
| **German hour words** | "neun", "zehn", "sieben" | Spoken word | "um sieben Uhr", "um neun" | Non-hour words | `conversation_state.py:760-780` |

### Required For

| Intent | Field | Requirement | Impact if Missing |
|--------|-------|-------------|-------------------|
| **Reservation** | `reservation_date` | ✅ Required (COMMIT_TOOLS_REQUIRED_SLOTS) | ❌ Commit gate blocks |
| **Reservation** | `reservation_time` | ✅ Required (COMMIT_TOOLS_REQUIRED_SLOTS) | ❌ Commit gate blocks |
| **Check Availability** | Both fields | ✅ Required | ❌ Tool returns "wait time" only |
| **Order** | — | ❌ Not needed | ✅ OK |
| **FAQ** | — | ❌ Not needed | ✅ OK |

### Current State & Issues

| Issue | Status | Fix Applied | Details |
|-------|--------|-------------|---------|
| Date confusion (speaker says "Saturday 9th", system sees "Tuesday 12th") | ⚠️ KNOWN | Deterministic clarify gate re-asks | User must confirm/correct |
| Time bucket alignment | ✅ ACTIVE | `_bucket_reservation_time()` rounds to 60-min slots (doboo config) | `_count_seats_in_slot()` uses bucketed time |
| Cross-turn persistence | ✅ ACTIVE | `hydrate_slots_from_history()` in `v4_pipeline.py:535-605` | Re-extracted on every turn unless `state.reservation_date` is set |
| Pre-load in `required_data` | ✅ FIXED | All A1 scripts have `required_data["reservation_date"]` and `["reservation_time"]` | Caller bot knows exact values |

---

## 5. ORDER ITEMS

### Extraction Rules

| Context | Rule | Format | Example | Rejected | Location |
|---------|------|--------|---------|----------|----------|
| **Menu keyword match** | Must be in doboo menu | Case-insensitive | "Bibimbap", "Bulgogi", "Sushi" | "Schnitzel" (not in menu), typos | `conversation_state.py:837-880` |
| **Quantity** | Integer or "zwei" (2) | N x Dish | "zwei Bibimbap", "3 Bulgogi" | "many Bibimbap", "einige" | `conversation_state.py:855-870` |
| **Combo phrases** | "Set", "Menü", "All-in" | Phrase | "Menü Ramyun Hähnchen" | Random dishes | `doboo.yaml` menu structure |

### Required For

| Intent | Field | Requirement | Impact if Missing |
|--------|-------|-------------|-------------------|
| **Order** | `order_items` (selected_items) | ✅ Required (COMMIT_TOOLS_REQUIRED_SLOTS) | ❌ Commit gate blocks |
| **Reservation** | — | ❌ Not needed | ✅ OK |
| **FAQ** | — | ❌ Not needed | ✅ OK |

### Current State & Issues

| Issue | Status | Details |
|-------|--------|---------|
| Menu sync | ✅ ACTIVE | Menu loaded from `doboo.yaml` tool_data section |
| Quantity parsing | ✅ ACTIVE | Supports digits and German number words |
| Combo detection | ✅ ACTIVE | Recognizes "Menü Ramyun", "Sushi Mix Nr. 3" |
| Pre-load in `required_data` | ⚠️ NOT YET | Order scenarios don't pre-load items | May be needed for Order phase |

---

## 6. DELIVERY ADDRESS (for Orders)

### Extraction Rules

| Context | Rule | Requirement | Example | Rejected | Location |
|---------|------|-------------|---------|----------|----------|
| **Address verification** | Must call `verify_address()` before `create_order` | Tool call gate | "Friedrich-Ebert-Allee 69, Bonn" | Unverified addresses | `tools/executor.py:773-810` |
| **Google Geocoding** | Address must resolve via Google Maps API | Lat/Lng returned | Valid Bonn address | "Moon Base 1" | `tools/executor.py:773` |
| **Delivery zone check** | Optional: polygon boundary check | If zone configured | Within 5km of restaurant | Outside zone | `doboo.yaml:1149-1150` |

### Required For

| Intent | Tool | Requirement | Impact if Missing |
|--------|------|-------------|-------------------|
| **Order (Delivery)** | `create_order` | ✅ MUST call `verify_address()` first | ❌ Tool call fails (guardrail) |
| **Order (Takeaway)** | `create_order` | ❌ Not needed | ✅ OK |
| **Reservation** | — | ❌ Not needed | ✅ OK |

### Current State & Issues

| Issue | Status | Details |
|-------|--------|---------|
| Address extraction | ⚠️ SEPARATE FLOW | Not in core slot extraction; part of delivery order flow |
| Zone polygon | ✅ CONFIGURED | `doboo.yaml:1150` empty (no restriction) |
| Pre-load in `required_data` | ❌ NOT APPLICABLE | Addresses are specific to caller; not pre-defined |

---

## 7. COMMIT GATE: ALL REQUIRED SLOTS PER TOOL

### Universal Gate (v4_pipeline.py:935–950)

```python
_all_slots = _all_slots_present(  # line 938
    intent=_is_reservation_intent,
    state=state,
    required_slots=COMMIT_TOOLS_REQUIRED_SLOTS.get(commit_tool, []),
)
```

### Reservation (`create_reservation`)

```python
REQUIRED: ["party_size", "reservation_date", "reservation_time", "customer_name", "phone_number"]

GATE LOGIC (v4_pipeline.py:206–211):
snapshot = {
    "party_size":       getattr(state, "party_size", None),
    "reservation_date": getattr(state, "reservation_date", None),
    "reservation_time": getattr(state, "reservation_time", None),
    "customer_name":    getattr(state, "customer_name", None) or getattr(state, "first_name", None),
    "phone_number":     getattr(state, "phone_number", None),
    "order_items":      None (not needed for reservation),
}

PASS CONDITION: all(snapshot[key] for key in required) == True
FAIL CONDITION: any(snapshot[key] is None or "") == True → gate blocks, clarify loop continues
```

### Order (`create_order`)

```python
REQUIRED: ["order_items", "customer_name", "phone_number"]
ALSO REQUIRED (guardrail): verify_address() must be called before create_order for delivery

GATE LOGIC (same snapshot):
snapshot = {
    "order_items":   getattr(state, "selected_items", None) or getattr(state, "selected_dish", None),
    "customer_name": getattr(state, "customer_name", None) or getattr(state, "first_name", None),
    "phone_number":  getattr(state, "phone_number", None),
}

PASS: all([order_items, customer_name, phone_number]) and address_verified (if delivery)
```

---

## 8. AVAILABILITY GATE (Reservation-Specific)

### Conditions

| Condition | When | Action | Location |
|-----------|------|--------|----------|
| **Slot is full** | `available == False` | Return unavailable message; set `availability_unavailable_at_commit = True` | `v4_pipeline.py:972–990` |
| **Already checked** | `availability_unavailable_at_commit == True` | Short-circuit; don't re-check (same slots) | `v4_pipeline.py:935–947` |
| **User corrects date/time** | `end_call_stage == "correction_pending"` | Reset flag; clear `check_availability_called` | `v4_pipeline.py:654–658` |
| **Capacity config** | Always | Use `reservation_slot_capacity` (20) and `reservation_slot_minutes` (60) from `TenantConfig` | `tools/executor.py:610–611` |

### Current State & Issues

| Issue | Status | Fix Applied | Details |
|-------|--------|-------------|---------|
| Infinite availability re-check loop | ✅ FIXED | Flag `availability_unavailable_at_commit` replaces `check_availability_called = False` reset | `v4_pipeline.py:980–990` |
| Capacity config mismatch | ✅ FIXED | `TenantConfig` now has `reservation_slot_capacity` and `reservation_slot_minutes` fields | `server/core/tenant_config.py:151–163` |
| No persistent calendar | ✅ FIXED | `reservations` table in Postgres; `_count_seats_in_slot_async()` queries it | `server/database.py:358–383` |
| 20/hour limit not enforced | ✅ FIXED | `doboo.yaml` sets `reservation_slot_capacity: 20`, `reservation_slot_minutes: 60` | Cross-restart persistence |

---

## 9. DETERMINISTIC CLARIFY GATE (v4_pipeline.py:1053–1094)

### Trigger Condition

```python
if (ctx_doc.next_action == "clarify" and 
    ctx_doc.missing_slots and 
    end_call_stage == "idle" and
    len(ctx_doc.missing_slots) > 0):
    
    # Use hardcoded German question instead of LLM TinyGenerator
    question = get_deterministic_slot_question(slot_name)
    # Examples:
    # - "Für wie viele Personen?" (party_size)
    # - "Um wie viel Uhr?" (reservation_time)
    # - "Auf welchen Namen?" (customer_name)
    # - "Unter welcher Nummer erreichbar?" (phone_number)
    return question
```

### When It Fires

| Condition | Result |
|-----------|--------|
| `ctx_doc.next_action == "clarify"` AND `missing_slots` is not empty | ✅ Fire deterministic question |
| `end_call_stage != "idle"` | ❌ Skip (in readback, correction, or escalation) |
| All slots present | ❌ Skip (gate opens, allow commit) |

### Current State

| Status | Issue | Location |
|--------|-------|----------|
| ✅ ACTIVE | Deterministic question pool | `v4_pipeline.py:1060–1080` |
| ✅ INTEGRATED | Fires on `next_action="clarify"` | `v4_pipeline.py:1053–1057` |
| ✅ FIXED | Guards `end_call_stage` to prevent re-asking during readback | `v4_pipeline.py:1052–1055` |

---

## SUMMARY TABLE: Which Conditions Apply Where?

| Condition | Reservation | Order | FAQ | Check Availability | Notes |
|-----------|-------------|-------|-----|-------------------|-------|
| Phone (10–13 digits) | ✅ REQUIRED | ✅ REQUIRED | ❌ | ✅ (optional) | Gate blocks if missing |
| Name (full or single) | ✅ REQUIRED | ✅ REQUIRED | ❌ | ❌ | Fallback: single→full for res |
| Party Size (1–50) | ✅ REQUIRED | ❌ | ❌ | ✅ REQUIRED | Default: 2 |
| Date (future) | ✅ REQUIRED | ❌ | ❌ | ✅ REQUIRED | Cross-turn persistence |
| Time (HH:MM) | ✅ REQUIRED | ❌ | ❌ | ✅ REQUIRED | Bucketed to 60-min slots |
| Order Items | ❌ | ✅ REQUIRED | ❌ | ❌ | Menu keyword match |
| Address (verified) | ❌ | ✅ (Delivery only) | ❌ | ❌ | Google Geocoding gate |
| Availability (20/hour) | ✅ GATE | ❌ | ❌ | ✅ OUTPUT | Postgres-backed calendar |
| Deterministic clarify | ✅ ACTIVE | ✅ ACTIVE | ❌ | ❌ | Hardcoded German questions |

---

## FAILURE ROOT CAUSES — Matched to This Matrix

### Scenario: Reservation fails at commit gate

**Why:** One of `[party_size, reservation_date, reservation_time, customer_name, phone_number]` is `None` or empty.

**Diagnosis Path:**

1. Check `phone_number` extraction in `conversation_state.py:1950–2030`
   - Is utterance long enough (≥10 digits)?
   - Are address-break words stopping the scan prematurely?
   - Is cross-turn buffer being used correctly?

2. Check `customer_name` extraction in `conversation_state.py:117–160`
   - Did user provide two capitalized words?
   - If single word, was `first_name` extracted and used in fallback?

3. Check `reservation_date` / `reservation_time` in `conversation_state.py:370–500` and `conversation_state.py:707–780`
   - Is relative date ("morgen") converted to ISO format (2026-05-07)?
   - Is time bucketed to grid? (19:00 → 19:00, 19:45 → 19:00 for 60-min bucket)

4. Check `party_size` extraction in `conversation_state.py:283–350`
   - Is German phrase matched? ("für X Personen")
   - Is default (2) applied if missing?

5. Check gate logic in `v4_pipeline.py:206–211`
   - Does `_state_snapshot_for_gate()` return all required keys?
   - Are fallbacks (e.g., `customer_name or first_name`) applied?

### Scenario: Availability check loops infinitely

**Why:** `state.check_availability_called == False` is reset when availability fails, triggering re-check on next turn with same slots.

**Fixed By:** `availability_unavailable_at_commit = True` flag + guard at commit gate + reset in `correction_pending`.

---

## NEXT STEPS FOR IMPLEMENTATION

1. **Reduce condition complexity** — collapse multi-condition gates into simpler state machines
2. **Add condition observability** — log every condition check + pass/fail result
3. **Per-turn condition report** — include in turn metrics: which conditions failed, why
4. **Refactor deterministic clarify** — move hardcoded questions to YAML config (doboo.yaml)
5. **Add fallback strategy per condition** — e.g., "if phone_number fails, ask name twice for verification"

