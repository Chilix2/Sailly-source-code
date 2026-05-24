from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE, PERSONA

DIETARY_INQUIRY = Node(
    id=NodeId.DIETARY_INQUIRY_NODE,
    description="Allergy/dietary questions: answer from menu, always caveat life-threatening allergies.",
    prompt=(
        PERSONA
        + "Der Anrufer fragt nach Allergenen oder Ernährungseinschränkungen.\n"
        "Beantworte soweit möglich aus dem Menü (get_menu).\n"
        "WICHTIG: Bei lebensbedrohlichen Allergien (Erdnüsse, Nüsse, Gluten):\n"
        "  'Das kann ich nicht mit 100% Sicherheit bestätigen — bitte ruf uns direkt an\n"
        "   oder sprich beim Besuch direkt mit unserem Team.'\n"
        "NIEMALS: 'Das Gericht ist garantiert allergen-frei.'"
        + SIE_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "get_menu", "faq", "end_call", "transfer_to_tier2", "request_callback",
    ]),
)
