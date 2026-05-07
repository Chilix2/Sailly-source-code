from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE, PERSONA

PAYMENT_ISSUE = Node(
    id=NodeId.PAYMENT_ISSUE_NODE,
    description="Payment problem: duplicate charge, card declined, refund request.",
    prompt=(
        PERSONA
        + "Der Anrufer hat ein Zahlungsproblem.\n"
        "Mögliche Fälle: doppelt abgebucht, Karte abgelehnt, Rückerstattung.\n"
        "1. Erfasse: Art des Problems + Bestellnummer/Datum.\n"
        "2. Versichere: 'Ich leite das sofort an unser Team weiter.'\n"
        "3. Verbinde (transfer_to_tier2) oder Rückruf (request_callback).\n"
        "Rückerstattungen werden innerhalb von 3 bis 5 Werktagen bearbeitet."
        + SIE_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "transfer_to_tier2", "transfer_to_human", "request_callback", "end_call",
    ]),
)
