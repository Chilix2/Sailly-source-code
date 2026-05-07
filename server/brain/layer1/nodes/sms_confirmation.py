"""
sms_confirmation.py — Phase 7.2: SMS_CONFIRMATION node.

This node handles the post-commit verbal readback and (for real-phone callers)
the optional SMS confirmation flow. It is the ONLY node allowed to mention SMS.

State machine (managed by NodeManager, not the LLM):
    ORDER_COMMITTED
        → VERBAL_READBACK     (bot reads back order/reservation details)
        → caller confirms?
            yes + real_phone  → fire send_sms → wait → ask "haben Sie die SMS?"
            yes + no_phone    → farewell → end_call
            no               → correct slots → readback again
        → SMS received?
            yes               → farewell → end_call
            no (retry ≤ 2x)   → retry send_sms (30s gap)
            still no          → tech fallback → end_call
"""
from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import (
    NO_GREETING_RULE,
    PLAIN_TEXT_RULE,
    SIE_RULE,
    WORD_CAP_RULE,
)

SMS_CONFIRMATION = Node(
    id=NodeId.SMS_CONFIRMATION,
    description="Post-commit verbal readback and optional SMS confirmation flow.",
    prompt=(
        "=== AUFGABE: BESTÄTIGUNG ===\n"
        "Du hast gerade eine Bestellung oder Reservierung abgeschlossen.\n"
        "Lies die wichtigsten Daten zur Bestätigung zurück:\n"
        "- Für Reservierungen: Datum, Uhrzeit, Personenanzahl, Name.\n"
        "- Für Bestellungen: Gerichte, Gesamtbetrag, Lieferart, Adresse/Name.\n"
        "\n"
        "Dann: 'Stimmt das so?'\n"
        "\n"
        "Bei Bestätigung: kurz verabschieden.\n"
        "Bei Korrektur: frage nach dem zu ändernden Detail.\n"
        "\n"
        "WICHTIG: Du darfst in diesem Kontext von 'SMS' oder 'Bestätigung per SMS' sprechen,\n"
        "wenn das System explizit SMS_CONFIRMATION als aktiven Node gesetzt hat.\n"
        + SIE_RULE
        + NO_GREETING_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "send_sms",
        "end_call",
    ]),
)
