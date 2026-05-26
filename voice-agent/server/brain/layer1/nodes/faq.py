from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import (
    PERSONA, NO_GREETING_RULE, SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE, OFF_TOPIC_RULE,
)

FAQ = Node(
    id=NodeId.FAQ,
    description="General FAQ: address, hours, delivery time, menu questions.",
    prompt=(
        PERSONA
        + "Du bist Sailly vom DOBOO Korean Soulfood.\n"
        "Adresse: Friedrich-Ebert-Allee 69, 53113 Bonn (Eingang Adalbert-Stifter-Straße).\n"
        "Öffnungszeiten: Mo–Do 11:30–21:30, Fr 11:30–14:00 & 18:00–21:30, Sa 18:00–21:30, So geschlossen.\n"
        "Lieferzeit: ca. 30-60 Minuten.\n"
        "Beantworte kurz und frage ob du noch helfen kannst."
        + SIE_RULE
        + NO_GREETING_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
        + OFF_TOPIC_RULE
    ),
    tools=frozenset([
        "ai_greeting", "faq", "end_call", "get_weather", "get_menu",
        "get_date_info", "get_directions", "get_nearby_parking", "check_availability",
        "create_order", "request_callback", "create_reservation",
        "transfer_to_tier2", "technical_issues_callback", "transfer_to_human",
        "get_restaurant_info",
    ]),
)
