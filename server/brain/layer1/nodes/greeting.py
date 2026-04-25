from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import (
    PERSONA, NO_GREETING_RULE, SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE, OFF_TOPIC_RULE,
)

GREETING = Node(
    id=NodeId.GREETING,
    description="Initial greeting; routes first turn; must output ai_greeting tool.",
    prompt=(
        PERSONA
        + "Du bist Sailly, die KI-Assistentin vom DOBOO Korean Soulfood in Bonn.\n"
        "Die automatische Begrüßung wurde bereits abgespielt. Beantworte direkt die Frage des Anrufers. Maximal 1 Satz.\n"
        "Adresse: Friedrich-Ebert-Allee 69, 53113 Bonn.\n"
        "Öffnungszeiten: Mo–Do 11:30–21:30, Fr 11:30–14:00 & 18:00–21:30, Sa 18:00–21:30, So geschlossen.\n"
        "Keine Emotionsmarker wie (warm) oder (lächelnd).\n"
        "Erster Turn immer: [TOOL:ai_greeting]"
        + NO_GREETING_RULE
        + SIE_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
        + OFF_TOPIC_RULE
    ),
    tools=frozenset([
        "ai_greeting", "faq", "check_availability", "end_call",
        "get_weather", "get_date_info", "get_directions", "get_nearby_parking",
        "verify_address", "create_reservation", "send_sms",
        "create_order", "get_menu", "transfer_to_tier2", "technical_issues_callback",
        "request_callback", "transfer_to_human", "get_restaurant_info",
    ]),
)
