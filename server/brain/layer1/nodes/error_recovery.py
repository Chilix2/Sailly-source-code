from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import (
    PERSONA, NO_GREETING_RULE, SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE,
)

ERROR_RECOVERY = Node(
    id=NodeId.ERROR_RECOVERY,
    description="Tool failure recovery: acknowledge the issue, offer alternatives, never pretend the tool succeeded.",
    prompt=(
        PERSONA
        + "Ein Tool hat soeben einen Fehler zurückgegeben oder ist nicht verfügbar.\n"
        "1. Teile dem Anrufer mit, dass es ein technisches Problem gibt.\n"
        "   Beispiel: 'Entschuldigung, gerade gibt es ein kleines technisches Problem.'\n"
        "2. Biete eine Alternative an:\n"
        "   - Rückruf: [TOOL:request_callback]\n"
        "   - Weiterleitung: [TOOL:transfer_to_tier2]\n"
        "   - Einfache Fragen beantworte direkt ohne Tool.\n"
        "3. NIEMALS so tun, als wäre die Aktion erfolgreich gewesen.\n"
        "4. NIEMALS mehrfach dasselbe fehlgeschlagene Tool aufrufen."
        + SIE_RULE
        + NO_GREETING_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "request_callback", "transfer_to_tier2", "transfer_to_human",
        "end_call", "faq", "get_date_info",
    ]),
)
