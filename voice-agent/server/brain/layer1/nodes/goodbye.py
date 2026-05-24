from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import (
    PERSONA, NO_GREETING_RULE, SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE,
)

GOODBYE = Node(
    id=NodeId.GOODBYE,
    description="End-of-call farewell; must fire end_call tool.",
    prompt=(
        PERSONA
        + "Du bist Sailly vom DOBOO Korean Soulfood.\n"
        "'Vielen Dank für Ihren Anruf bei DOBOO! Auf Wiedersehen.'\n"
        "Rufe [TOOL:end_call] auf."
        + SIE_RULE
        + NO_GREETING_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "end_call", "create_order", "create_reservation",
        "ai_greeting", "get_menu", "verify_address", "faq", "get_date_info",
        "check_availability", "get_weather", "transfer_to_tier2",
        "technical_issues_callback", "request_callback", "transfer_to_human",
        "get_restaurant_info",
    ]),
)
