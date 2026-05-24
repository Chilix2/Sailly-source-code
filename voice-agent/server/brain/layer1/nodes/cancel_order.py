from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE, PERSONA

CANCEL_ORDER = Node(
    id=NodeId.CANCEL_ORDER_NODE,
    description="Caller wants to cancel an order; team executes via request_callback.",
    prompt=(
        PERSONA
        + "Der Anrufer möchte eine Bestellung stornieren.\n"
        "1. Identifiziere die Bestellung (Telefonnummer oder Bestellnummer).\n"
        "2. Bestätige die Stornierung verbal.\n"
        "3. Rufe request_callback auf — das Team führt die Stornierung durch.\n"
        "Keine Stornierungsgebühr, wenn > 10 Minuten vor Zubereitung."
        + SIE_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "request_callback", "transfer_to_tier2", "transfer_to_human", "end_call",
    ]),
)
