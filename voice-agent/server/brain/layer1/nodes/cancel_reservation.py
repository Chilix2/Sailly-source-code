from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE, PERSONA

CANCEL_RESERVATION = Node(
    id=NodeId.CANCEL_RESERVATION_NODE,
    description="Caller wants to cancel a reservation; team executes via request_callback.",
    prompt=(
        PERSONA
        + "Der Anrufer möchte eine Reservierung stornieren.\n"
        "1. Datum und Uhrzeit der Reservierung?\n"
        "2. Name auf der Reservierung?\n"
        "3. Bestätige verbal, dass storniert wird.\n"
        "4. Rufe request_callback auf.\n"
        "Schade — aber gerne ein nächstes Mal!"
        + SIE_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "request_callback", "transfer_to_tier2", "end_call",
    ]),
)
