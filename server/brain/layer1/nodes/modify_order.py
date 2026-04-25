from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE, PERSONA

MODIFY_ORDER = Node(
    id=NodeId.MODIFY_ORDER_NODE,
    description="Caller wants to modify an existing order; routes to manual team via request_callback.",
    prompt=(
        PERSONA
        + "Der Anrufer möchte eine bestehende Bestellung ändern.\n"
        "1. Identifiziere die Bestellung (Telefonnummer oder Name).\n"
        "2. Frage was geändert werden soll.\n"
        "3. Bestätige die Änderung und rufe request_callback auf "
        "   (Änderungen können nur manuell vom Team vorgenommen werden).\n"
        "Sage nie, dass du direkt in die Bestellung eingreifen kannst."
        + SIE_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "request_callback", "transfer_to_tier2", "transfer_to_human", "end_call", "faq",
    ]),
)
