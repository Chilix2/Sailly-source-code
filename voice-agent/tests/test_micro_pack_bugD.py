"""Micro-pack tests: Bug D cross-turn buffer + pre-commit sanitizer."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.brain.conversation_state import (
    ConversationState,
    sanitize_bot_text_pre_commit,
    _SPOKEN_DIGITS,
)

failures = []

def check(cond, label):
    if cond:
        print(f"  PASS: {label}")
    else:
        print(f"  FAIL: {label}")
        failures.append(label)


# ============================================================
# Bug D follow-up — cross-turn phone digit buffer
# ============================================================
print("\n=== Bug D follow-up: cross-turn phone digit buffer ===")

# Simulate the exact trace case: digits arrive in 4 turns
state = ConversationState()
state.order_intent = True
state.selected_dish = "Bibimbap"

# T10: "Meine Telefonnummer ist null eins fünf eins"
from server.brain.conversation_state import update_state_from_utterance
update_state_from_utterance(state, "Meine Telefonnummer ist null eins fünf eins")
check(state.phone_digits_buffer == "0151", 
      f"D1a: T10 buffers 0151 (got {state.phone_digits_buffer!r})")
check(state.phone_number is None, "D1b: phone_number still None after T10")

# T11: "eins zwei drei vier fünf sechs sieben acht."
update_state_from_utterance(state, "eins zwei drei vier fünf sechs sieben acht.")
# Buffer gets cleared after successful extraction
check(state.phone_number == "015112345678",
      f"D2a: phone_number extracted from buffer (got {state.phone_number!r})")
check(state.phone_is_landline is False, "D2b: phone confirmed as mobile")
check(state.phone_digits_buffer == "",
      f"D2c: buffer cleared after use (got {state.phone_digits_buffer!r})") 

# Partial T12–T13 case (incomplete after 2 turns)
state2 = ConversationState()
update_state_from_utterance(state2, "null eins fünf zwei eins zwei drei vier")
# Buffer contains these digits until threshold is met
check(len(state2.phone_digits_buffer) > 0,
      f"D3a: partial buffer accumulated (got {len(state2.phone_digits_buffer)} digits)")

# Landline in buffer (should reject)
state3 = ConversationState()
update_state_from_utterance(state3, "null zwei zwei null drei")  # 02203 — landline
update_state_from_utterance(state3, "eins zwei drei vier fünf")   # buffer 0220312345
check(state3.phone_is_landline is True, "D4a: buffer landline detected")
check(state3.phone_number is None, "D4b: phone_number stays None on landline")


# ============================================================
# Bug D follow-up — pre-commit sanitizer
# ============================================================
print("\n=== Bug D follow-up: sanitize_bot_text_pre_commit ===")

state = ConversationState()
state.customer_name = None  # invalid
state.delivery_intended = True
state.delivery_address = "Friedrichstraße 20, Bonn"  # valid
state.phone_number = None  # invalid

# LLM false-positive case from T17
bot_text = (
    "Es fehlt nichts mehr, Herr Schmidt. Ich habe alle Informationen, "
    "die ich benötige. Ihre Bestellung wird aufgenommen."
)
sanitized = sanitize_bot_text_pre_commit(bot_text, state, escalating=True)
check("Es fehlt" in sanitized, f"D5a: rewrite triggers on escalation")
check("noch Ihre Telefonnummer" in sanitized,
      f"D5b: rewritten to phone-missing message (got {sanitized[:80]!r})")

# No rewrite when not escalating
bot_text2 = "Es fehlt nichts mehr."
result = sanitize_bot_text_pre_commit(bot_text2, state, escalating=False)
check(result == bot_text2, "D6a: no rewrite when escalating=False")

# Valid state + escalating (edge: shouldn't happen, but graceful)
state_valid = ConversationState()
state_valid.customer_name = "Markus Schmidt"
state_valid.phone_number = "015212345678"
state_valid.delivery_address = "Friedrichstraße 20, Bonn"
state_valid.delivery_intended = True
bot_text3 = "Es fehlt nichts mehr."
result3 = sanitize_bot_text_pre_commit(bot_text3, state_valid, escalating=True)
check(result3 == bot_text3, "D7: no rewrite when all fields valid (even if escalating)")


print("\n" + "=" * 60)
if failures:
    print(f"FAILED: {len(failures)} test(s)")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("ALL MICRO-PACK TESTS PASS")
