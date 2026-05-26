from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE, PERSONA

ORDER_STATUS = Node(
    id=NodeId.ORDER_STATUS_NODE,
    description="Caller asking about delivery status; connects to tier2 or offers callback.",
    prompt=(
        PERSONA
        + "Der Anrufer fragt nach dem Status seiner Bestellung.\n"
        "1. Frage nach Telefonnummer oder Bestellnummer.\n"
        "2. Erkläre, dass du den Status nicht direkt abrufen kannst.\n"
        "3. Verbinde mit Team (transfer_to_tier2) oder biete Rückruf an.\n"
        "Typische Lieferzeit: 30 bis 60 Minuten ab Bestelleingang."
        + SIE_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "transfer_to_tier2", "transfer_to_human", "request_callback", "end_call",
    ]),
)
