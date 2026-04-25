from server.brain.layer1.nodes.base import Node, NodeId, MENU_FETCHED_PREREQ
from server.brain.layer1.nodes._prompts import (
    PERSONA, NO_GREETING_RULE, SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE,
)

ESCALATION = Node(
    id=NodeId.ESCALATION,
    description="Escalation hub: routes tech issues, abuse, catering, callbacks.",
    prompt=(
        PERSONA
        + "Du bist Sailly vom DOBOO Korean Soulfood. Der Kunde hat ein Problem.\n"
        "Technisch ('App kaputt', 'Fehler'): → [TOOL:technical_issues_callback].\n"
        "Beleidigung/Drohung: Einmal → [TOOL:transfer_to_tier2].\n"
        "Catering/Gruppen >20 Personen: → [TOOL:transfer_to_human].\n"
        "Rückrufwunsch: → [TOOL:request_callback].\n"
        "Bei Frustration: Empathie zeigen, Lösung anbieten. KEIN Transfer.\n"
        "Maximal 2 Sätze.\n"
        "ABSOLUT PFLICHT: Antworte NUR auf Deutsch. Niemals Englisch.\n"
        "Format: [TOOL:name] für alle Werkzeuge — kein anderes Format.\n"
        "Nach 2 Turns ohne Lösung: immer [TOOL:transfer_to_tier2] setzen."
        + SIE_RULE
        + NO_GREETING_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "technical_issues_callback", "transfer_to_tier2",
        "transfer_to_human", "request_callback", "end_call",
        "create_order", "create_reservation",
        "get_menu", "get_date_info", "check_availability",
        "get_weather", "faq", "send_sms", "ai_greeting", "get_restaurant_info",
    ]),
    prerequisites=(MENU_FETCHED_PREREQ,),
)
