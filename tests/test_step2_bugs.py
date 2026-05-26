"""Step 2 bug-pack unit tests (Bugs A-F). Bug G tested via live call."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.brain.conversation_state import (
    ConversationState,
    _is_valid_name_candidate,
    _extract_name_from_utterance,
    _extract_address_from_utterance,
    _extract_phone_digits,
    _convert_number_words,
    strip_tool_call_leakage,
    update_state_from_utterance,
)

failures: list[str] = []


def check(cond, label):
    if cond:
        print(f"  PASS: {label}")
    else:
        print(f"  FAIL: {label}")
        failures.append(label)


# ============================================================
# Bug A — validity helpers + fields_to_collect / next_field_to_ask
# ============================================================
print("\n=== Bug A: validity + gate flow ===")

s = ConversationState()
s.order_intent = True
s.selected_dish = "Bibimbap"
s.customer_name = "Markus Schmidt"
s.phone_number = "015212345678"
s.delivery_intended = True
s.delivery_address = "Friedrichstraße 20, Bonn"
check(s.has_valid_name(), "A1: has_valid_name('Markus Schmidt')")
check(s.has_valid_phone(), "A2: has_valid_phone('015212345678')")
check(s.has_valid_address(), "A3: has_valid_address(Friedrichstraße 20, Bonn)")
check(s.has_valid_address_or_pickup(), "A4: has_valid_address_or_pickup delivery")
check(s.next_field_to_ask() is None, "A5: next_field_to_ask()==None (all valid)")
check(not s.should_escalate(), "A6: not should_escalate (all valid)")

s2 = ConversationState()
s2.order_intent = True
s2.customer_name = "Ist"
s2.field_attempts["name"] = 3
check(not s2.has_valid_name(), "A7: has_valid_name('Ist') == False")
check(s2.should_escalate(), "A8: should_escalate when name='Ist' and attempts=3")
check(s2.next_field_to_ask() != "name",
      "A9a: name capped -> next_field_to_ask skips name (returns another field or None)")

# All-capped case: every missing field hit 3 attempts -> None + escalate
s2b = ConversationState()
s2b.order_intent = True
s2b.customer_name = "Ist"
s2b.delivery_intended = True
s2b.delivery_address = "bad"  # invalid
s2b.phone_number = "111"  # invalid (no mobile prefix)
s2b.field_attempts["name"] = 3
s2b.field_attempts["address"] = 3
s2b.field_attempts["phone"] = 3
s2b.field_attempts["delivery_choice"] = 3
check(s2b.next_field_to_ask() is None,
      "A9b: all fields capped -> next_field_to_ask None")
check(s2b.should_escalate(), "A9c: all fields capped -> should_escalate True")

s3 = ConversationState()
s3.customer_name = "Markus Schmidt"
s3.phone_number = "015212345678"
s3.delivery_intended = False
s3.delivery_confirmed = True
check(s3.has_valid_address_or_pickup(), "A10: pickup satisfies address requirement")

s4 = ConversationState()
s4.customer_name = "Markus Schmidt"
s4.delivery_intended = True
s4.delivery_address = "Friedrichstraße 20, Bonn"
s4.phone_number = "015212345678"
for _ in range(10):
    f = s4.next_field_to_ask()
    check(f not in ("address_verified", "plz", "postcode", "postleitzahl", "phone_mobile"),
          f"E-guard: next_field_to_ask never returns {f!r}")


# ============================================================
# Bug B — Name extractor
# ============================================================
print("\n=== Bug B: name extractor ===")

check(_extract_name_from_utterance("Mein Name ist Markus Schmidt.") == "Markus Schmidt",
      "B1: 'Mein Name ist Markus Schmidt.' -> 'Markus Schmidt'")
check(_extract_name_from_utterance("Ich heiße Anna Müller") == "Anna Müller",
      "B2: 'Ich heiße Anna Müller' -> 'Anna Müller'")
check(_extract_name_from_utterance("Markus Schneider.") == "Markus Schneider",
      "B3: bare 'Markus Schneider.' -> 'Markus Schneider'")
check(_extract_name_from_utterance("N") is None, "B4: 'N' -> None")
check(_extract_name_from_utterance("Ja") is None, "B5: 'Ja' -> None")
check(_extract_name_from_utterance("Ich bin") is None, "B6: 'Ich bin' -> None")
check(_extract_name_from_utterance("Du brauchst doch meinen Namen.") is None,
      "B7: rambling denial -> None")

result = _extract_name_from_utterance("Mein Name ist Markus Schmidt.")
check("Ist" not in (result or "").split(), f"B8: result {result!r} never contains 'Ist'")

check(not _is_valid_name_candidate("Ist Markus"), "B9: 'Ist Markus' rejected (blocklist)")
check(not _is_valid_name_candidate("Markus"), "B10: single word rejected")
check(not _is_valid_name_candidate("N M"), "B11: too short rejected")
check(_is_valid_name_candidate("Markus Schmidt"), "B12: 'Markus Schmidt' accepted")


# ============================================================
# Bug C — Address extractor
# ============================================================
print("\n=== Bug C: address extractor ===")

check(_extract_address_from_utterance("Friedrichstraße 20, Bonn") == "Friedrichstraße 20, Bonn",
      "C1: digit form 'Friedrichstraße 20, Bonn'")
r = _extract_address_from_utterance("Friedrichstraße zwanzig Bonn.")
check(r == "Friedrichstraße 20, Bonn", f"C2: word-form zwanzig -> 20 (got {r!r})")

check(_extract_address_from_utterance("Friedrichstraße zwanzig von") is None,
      "C3: garbage city 'von' rejected")
check(_extract_address_from_utterance("Friedrichstraße 20") is None,
      "C4: missing city rejected")
check(_extract_address_from_utterance("Friedrichstraße") is None,
      "C5: partial 'Friedrichstraße' rejected")

r2 = _extract_address_from_utterance("Hauptallee 5, Köln")
check(r2 == "Hauptallee 5, Köln", f"C6: 'Hauptallee 5, Köln' (got {r2!r})")


# ============================================================
# Bug D — Phone extractor (digit-by-digit)
# ============================================================
print("\n=== Bug D: phone extractor ===")

r = _extract_phone_digits("null eins fünf zwei eins zwei drei vier fünf sechs sieben acht")
check(r == "015212345678", f"D1: spoken digits -> 015212345678 (got {r!r})")

r2 = _extract_phone_digits("Meine Nummer ist 0152 12345678")
check(r2 == "015212345678", f"D2: digit form 0152 12345678 (got {r2!r})")

r3 = _extract_phone_digits("0172-1234567")
check(r3 == "01721234567", f"D3: 0172-1234567 (got {r3!r})")

r4 = _extract_phone_digits("")
check(r4 is None, "D4: empty -> None")

r5 = _extract_phone_digits("Meine Lieblingszahl ist 7")
check(r5 is None, "D5: single digit -> None (too short)")


# ============================================================
# Bug E — update_state_from_utterance integration
# ============================================================
print("\n=== Bug E: update_state_from_utterance integration ===")

state = ConversationState()
state.order_intent = True
state.selected_dish = "Bibimbap"
update_state_from_utterance(state, "Mein Name ist Markus Schmidt.")
check(state.customer_name == "Markus Schmidt",
      f"E1: full-turn name extraction (got {state.customer_name!r})")

update_state_from_utterance(state, "Lieferung bitte.")
check(state.delivery_confirmed and state.delivery_intended,
      "E2: delivery_confirmed + delivery_intended after 'Lieferung bitte'")

update_state_from_utterance(state, "Friedrichstraße zwanzig Bonn.")
check(state.delivery_address == "Friedrichstraße 20, Bonn",
      f"E3: address word-form extracted ({state.delivery_address!r})")

update_state_from_utterance(state,
    "null eins fünf zwei eins zwei drei vier fünf sechs sieben acht")
check(state.phone_number == "015212345678",
      f"E4: phone digit-by-digit ({state.phone_number!r})")

check(state.next_field_to_ask() is None,
      f"E5: after all data, next_field_to_ask is None (got {state.next_field_to_ask()!r})")
check(state.has_valid_name() and state.has_valid_phone() and state.has_valid_address_or_pickup(),
      "E6: all validity checks pass after clean collection")


# ============================================================
# Bug F — strip_tool_call_leakage
# ============================================================
print("\n=== Bug F: strip_tool_call_leakage ===")

t, stripped = strip_tool_call_leakage("Einen Moment bitte.")
check(not stripped and t == "Einen Moment bitte.", "F1: normal text unchanged")

t, stripped = strip_tool_call_leakage(
    "Einen Moment. TOOL CALL: print(verify_address(address='...'))"
)
check(stripped and "TOOL" not in t and "print" not in t,
      f"F2: 'TOOL CALL: print(...)' stripped (got {t!r})")

t, stripped = strip_tool_call_leakage("Danke. [TOOL:create_order]")
check(stripped and "TOOL" not in t, f"F3: [TOOL:create_order] stripped (got {t!r})")

t, stripped = strip_tool_call_leakage(
    'Ich sage: {"name": "create_order", "args": {}}'
)
check(stripped, f"F4: JSON tool-call leak stripped (got {t!r})")

t, stripped = strip_tool_call_leakage("TOOL CALL: print(verify_address())")
check(stripped and t.strip(), f"F5: fallback text when all stripped (got {t!r})")

t, stripped = strip_tool_call_leakage("Ich rufe verify_address(foo='bar') auf.")
check(stripped and "verify_address(" not in t,
      f"F6: inline verify_address() stripped (got {t!r})")


print("\n" + "=" * 60)
if failures:
    print(f"FAILED: {len(failures)} test(s)")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("ALL STEP 2 UNIT TESTS PASS")
