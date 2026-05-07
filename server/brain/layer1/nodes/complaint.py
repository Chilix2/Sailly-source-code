from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE, PERSONA

COMPLAINT = Node(
    id=NodeId.COMPLAINT_NODE,
    description="Complaint handling: listen, apologise, escalate to team.",
    prompt=(
        PERSONA
        + "Der Anrufer hat eine Beschwerde.\n"
        "1. Höre aufmerksam zu — kein Unterbrechen.\n"
        "2. Entschuldige dich aufrichtig: 'Das tut mir sehr leid, das sollte nicht passieren.'\n"
        "3. Erfasse: Art der Beschwerde, betroffenes Gericht/Datum.\n"
        "4. Verbinde sofort mit dem Team (transfer_to_tier2) oder biete Rückruf an.\n"
        "KEIN Anbieten von Rabatten oder Gutscheinen ohne Teamgenehmigung."
        + SIE_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "transfer_to_tier2", "transfer_to_human", "request_callback", "end_call",
    ]),
)
