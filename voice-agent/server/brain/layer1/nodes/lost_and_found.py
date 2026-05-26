from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE, PERSONA

LOST_AND_FOUND = Node(
    id=NodeId.LOST_AND_FOUND_NODE,
    description="Lost item: collect description, visit date/time, callback number.",
    prompt=(
        PERSONA
        + "Der Anrufer hat etwas im Restaurant vergessen.\n"
        "1. Was wurde vergessen? (genaue Beschreibung)\n"
        "2. Wann war der Besuch? (Datum, Uhrzeit)\n"
        "3. Kontaktnummer für Rückruf?\n"
        "4. 'Ich notiere das für unser Team — wir melden uns, wenn der Gegenstand gefunden wurde.'\n"
        "5. Rufe request_callback auf."
        + SIE_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "request_callback", "end_call",
    ]),
)
