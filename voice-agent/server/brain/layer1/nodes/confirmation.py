from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import (
    PERSONA, NO_GREETING_RULE, SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE,
)

# Numbered readback template for multi-intent confirmation (Phase 4 C1).
# The LLM receives this prompt and is expected to:
#   1. List captured intents as a numbered list
#   2. Ask "Stimmt das so?" or equivalent
#   3. Accept one of: confirm_all / restart_all / correct_specific
_CONFIRMATION_PROMPT = (
    PERSONA
    + "\n\nDu befindest dich im BESTÄTIGUNGSSCHRITT.\n"
    "Der Anrufer hat mehrere Anliegen in einem Satz genannt.\n"
    "\n"
    "AUFGABE — Lies alle erkannten Anliegen als nummerierte Liste zurück:\n"
    "  1. [Anliegen 1 — z.B. 'Bestellung: 2× Bibimbap zum Abholen']\n"
    "  2. [Anliegen 2 — z.B. 'Reservierung: Tisch für 4, Freitag 19 Uhr']\n"
    "  ...\n"
    "\n"
    "Schließe mit GENAU EINER dieser Fragen:\n"
    "  → 'Stimmt das so?'  (wenn alles klar ist)\n"
    "  → 'Ist das korrekt?' (bei technischen Details)\n"
    "\n"
    "REAKTION AUF ANTWORT DES ANRUFERS:\n"
    "  • 'Ja / Stimmt / Korrekt / Genau'        → confirmation_response=confirm_all\n"
    "  • 'Nein / Alles nochmal / Neu anfangen'  → confirmation_response=restart_all\n"
    "  • 'Punkt 2 stimmt nicht / Korrektur bei ...' → confirmation_response=correct_specific\n"
    "\n"
    "Rufe [TOOL:update_state] mit field='confirmation_response' und dem entsprechenden Wert auf.\n"
    "NIEMALS ohne Bestätigung weiterfahren.\n"
    + SIE_RULE
    + NO_GREETING_RULE
    + PLAIN_TEXT_RULE
    + WORD_CAP_RULE
)

CONFIRMATION = Node(
    id=NodeId.CONFIRMATION,
    description="Multi-intent readback gate: numbered list readback + 3-way confirmation branching.",
    prompt=_CONFIRMATION_PROMPT,
    tools=frozenset({"update_state"}),
)
