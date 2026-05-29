# FSM Phases Specification

## Overview

The Sailly FSM has 6 deterministic phases. Each phase:
- Has well-defined entry/exit conditions
- Collects specific slots (if applicable)
- Emits Category A (data) or B (state-change) tools
- Transitions to next phase based on state + LLM output

**Key**: Transitions are code-driven, not LLM-delegated.

---

## Phase 1: GREETING

**Purpose**: Intro message + intent detection (Order vs Reservation vs FAQ)

**Entry**: Call starts, no state

**State Collection**: 
- `intent` — extracted from LLM + fallback keywords
- `language_hint` — from Deepgram language detection

**Example Flow**:
```
Agent: "Hallo, willkommen bei Doboo. Möchten Sie einen Tisch reservieren oder eine Bestellung aufgeben?"
Customer: "Ich möchte einen Tisch für 4 Personen reservieren"
FSM Transition: intent = "RESERVATION" → goto RESERVE
```

**Exit Condition**: 
- `slots.intent` is not None AND
- Intent is one of: ORDER, RESERVATION, FAQ, TECHNICAL

**Next Phase**: 
- ORDER if intent = "ORDER"
- RESERVE if intent = "RESERVATION"
- INFO if intent = "FAQ" or "INFORMATION"
- COMMITTED if intent = "TECHNICAL" + automatic transfer_to_human

---

## Phase 2: INFO

**Purpose**: FAQ, menu lookup, business hours, special offers

**Entry**: User asked for information (not ready to transact)

**State Collection**: None (slots unchanged)

**Category A Tools**:
- `get_menu()` — return menu items + prices
- `get_business_hours()` — open/close times
- `faq()` — common questions
- `get_date_info()` — date calculations (e.g., "next Monday")
- `check_availability()` — check reservations/capacity

**Example Flow**:
```
Customer: "Was sind die Öffnungszeiten?"
FSM: emit get_business_hours()
Agent: "Wir haben Mo-Fr 11:00-23:00, Sa-So 12:00-24:00 geöffnet."
Customer: "Danke, ich möchte einen Tisch buchen"
FSM Transition: user ready to transact → goto ORDER or RESERVE (re-detect intent)
```

**Exit Condition**:
- LLM detected customer ready for transaction OR
- Timeout (>10 exchanges in INFO) → fallback to ORDER with warning

**Next Phase**: ORDER or RESERVE (re-detect intent from latest LLM output)

---

## Phase 3: ORDER

**Purpose**: Collect order details (items, quantities, delivery address, payment, name, phone)

**Entry**: User wants to order

**Slots to Collect** (in priority order):
1. `order_type` — delivery, pickup, dine-in (from TenantConfig.order_types)
2. `items` — menu items + quantities (extracted from LLM output)
3. `customer_name` — customer name (German NLP: Karl, Müller, etc.)
4. `phone_number` — phone (German: +49, 0, or 10-digit, with extensions)
5. `delivery_address` — address (if delivery)
6. `payment_method` — payment type (cash, card, online)

**Category A Tools**:
- `check_availability()` — check if items in stock
- `get_menu()` — re-fetch menu on request

**Example Flow**:
```
Agent: "Was möchten Sie bestellen?"
Customer: "Ich hätte gerne zwei Margheritas und eine Carbonara"
FSM Extract: items=[("Margherita", 2), ("Carbonara", 1)]
Agent: "Prima, das sind 2x Margherita und 1x Carbonara. Wie heißen Sie?"
Customer: "Ich bin Karl Müller"
FSM Extract: customer_name="Karl Müller"
Agent: "Danke. Unter welcher Nummer können wir Sie erreichen?"
Customer: "+49 123 45678"
FSM Extract: phone_number="+49-123-45678"
...continue until all slots collected...
FSM Transition: goto READBACK
```

**Exit Condition**: All required slots filled AND LLM confirmed readiness

**Required Slots by Order Type**:
- All: order_type, items, customer_name, phone_number, payment_method
- delivery: + delivery_address, + city, + postcode

**Next Phase**: READBACK

---

## Phase 4: RESERVE

**Purpose**: Collect reservation details (date, time, party size, name, phone)

**Entry**: User wants to make a reservation

**Slots to Collect** (in priority order):
1. `party_size` — number of guests (1-20, German text extraction)
2. `reservation_date` — date (German: "morgen", "nächsten Dienstag", "15. Juni", etc.)
3. `reservation_time` — time (German: "19:00", "sieben Uhr", "um acht", etc.)
4. `customer_name` — customer name
5. `phone_number` — phone number

**Category A Tools**:
- `check_availability()` — check if time slot free
- `get_business_hours()` — validate time within hours
- `get_date_info()` — parse German dates (skill: date-time-parser)

**Example Flow**:
```
Agent: "Für wie viele Personen möchten Sie reservieren?"
Customer: "Für vier"
FSM Extract: party_size=4
Agent: "An welchem Datum?"
Customer: "Nächsten Dienstag"
FSM Extract: reservation_date="2026-06-03" (computed)
Agent: "Zu welcher Zeit?"
Customer: "Um acht Uhr"
FSM Extract: reservation_time="20:00"
Agent: "Können Sie mir noch Ihren Namen und eine Telefonnummer geben?"
Customer: "Anna Schmidt, +49 30 123456"
FSM Extract: customer_name="Anna Schmidt", phone_number="+49-30-123456"
FSM Transition: goto READBACK
```

**Exit Condition**: All 5 slots filled AND availability confirmed

**Next Phase**: READBACK

---

## Phase 5: READBACK

**Purpose**: Read back order/reservation summary + confirm (two-pass guard)

**Entry**: All slots collected (from ORDER or RESERVE)

**Two-Pass Confirmation Guard**:
1. **Pass 1**: Exact token match
   - Agent reads back summary
   - Customer says exact confirmation token (e.g., "Ja", "Bestätigt", "Korrekt")
   - FSM checks for exact match (use TenantConfig.confirmation_tokens)
   
2. **Pass 2**: LLM scorer (if Pass 1 fails)
   - LLM analyzes customer response
   - Score intent confidence (0.0-1.0)
   - If score > TenantConfig.confirmation_threshold (default 0.85): accept
   - Else: re-read and retry

**Category A Tools**:
- None (read-only phase)

**Example Flow**:
```
Agent: "Zusammenfassung: Sie bestellen 2x Margherita, 1x Carbonara für Karl Müller, +49-123-45678. Zur Adresse Berliner Str. 42, 10115 Berlin. Stimmt das?"
Customer: "Ja"
FSM Pass 1: "Ja" matches TenantConfig.confirmation_tokens["de"] → ACCEPT
FSM Transition: goto COMMITTED
```

**Edge Case** (Pass 1 fails, LLM scorer used):
```
Customer: "Ja, alles richtig"
FSM Pass 1: "Ja, alles richtig" does NOT match token "Ja" → FAIL
LLM Scorer: intent_confidence = 0.92 > threshold 0.85 → ACCEPT
FSM Transition: goto COMMITTED
```

**Exit Condition**: Pass 1 OR (Pass 2 score > threshold)

**Next Phase**: COMMITTED

---

## Phase 6: COMMITTED

**Purpose**: Execute Category B tools (create_order, send_sms, transfer_to_human, etc.)

**Entry**: Confirmation passed

**Category B Tools** (code-driven, never LLM):
- `create_order()` — persist order to backend
- `create_reservation()` — persist reservation
- `send_sms()` — send order confirmation SMS
- `transfer_to_human()` — human agent handoff if needed
- `end_call()` — conclude call

**Critical**: These tools modify system state. Emitted ONLY by FSM.check_forced_commits(), never by LLM.

**Example Flow**:
```
FSM Phase = COMMITTED, all slots valid
FSM.check_forced_commits() evaluates:
  - Is order complete? YES → emit create_order()
  - Is SMS needed? YES → emit send_sms()
  - Is human transfer needed? NO
  - Is call complete? YES → emit end_call()

BillingLogger logs: call_id=conv_abc123, tenant_id=doboo, fsm_phase=COMMITTED, tools=[create_order, send_sms, end_call]
```

**Exit Condition**: All Category B tools executed AND call_id logged

**Next Phase**: None (call ends)

---

## Phase Transitions (State Machine)

```
GREETING → INFO (user asks question)
        → ORDER (user wants to order)
        → RESERVE (user wants reservation)
        → COMMITTED (technical issue → transfer_to_human)

INFO → ORDER (user ready, re-detect order intent)
    → RESERVE (user ready, re-detect reservation intent)
    → INFO (loop if user asks more questions)

ORDER → READBACK (all slots collected)
     → ORDER (loop if slot missing, ask again)

RESERVE → READBACK (all slots collected)
       → RESERVE (loop if slot missing, ask again)

READBACK → COMMITTED (confirmation passed)
        → ORDER or RESERVE (re-collect if confirmation failed, up to 2 retries)
        → COMMITTED + transfer_to_human (3rd retry fail, escalate)

COMMITTED → (call ends)
```

---

## Timeout Handling

| Phase | Timeout (s) | Action |
|-------|------------|--------|
| GREETING | 30 | No response → repeat intro → end_call |
| INFO | 300 (5 min) | Repeat question → ORDER (fallback) |
| ORDER | 300 | Repeat question → repeat up to 2x → transfer_to_human |
| RESERVE | 300 | Repeat question → repeat up to 2x → transfer_to_human |
| READBACK | 30 | No confirmation → 1 retry → transfer_to_human |
| COMMITTED | 60 | Tool timeout → transfer_to_human |

---

## Slot Extraction Details

See slot_extractors.py for German NLP:

| Slot | Extractor | Examples |
|------|-----------|----------|
| `phone_number` | German phone parser | +49 30 123456, 030-123456, +49123456 |
| `reservation_date` | German date parser (skill) | "morgen", "nächsten Montag", "15. Juni" |
| `reservation_time` | German time parser | "19:00", "sieben Uhr", "um acht" |
| `customer_name` | German name recognizer | "Karl", "Müller", "Anna Schmidt" |
| `items` | Menu item lookup | "Margherita", "Carbonara", "Bier" |
| `party_size` | Number extraction | "vier", "4", "für vier Personen" |

---

## Testing

All 6 phases tested in `server/tests/test_conversation_fsm.py`:
- 24 golden scenarios × 2 tenants (doboo, pizzeria_napoli)
- Each test verifies phase transitions, slot collection, tool emission

Run tests:
```bash
pytest server/tests/test_conversation_fsm.py -v
```

---

**Last Updated**: 2026-05-30 | **Schema**: v7 | **Phases**: 6 (deterministic)
