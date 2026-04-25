from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import (
    PERSONA, NO_GREETING_RULE, SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE,
    OFF_TOPIC_RULE, CONFIRM_DATA_RULE,
)

RESERVATION = Node(
    id=NodeId.RESERVATION,
    description="Reservation flow: date, time, party size, name, then create_reservation.",
    prompt=(
        PERSONA
        + "Du bist Sailly vom DOBOO Korean Soulfood. Der Kunde möchte reservieren.\n"
        "Erfrage nacheinander (nicht alles auf einmal): 1) Datum 2) Uhrzeit 3) Personenzahl 4) Name.\n"
        "Prüfe Verfügbarkeit mit [TOOL:check_availability] sobald Datum+Uhrzeit bekannt.\n"
        "Sobald alle 4 Angaben vorliegen: [TOOL:create_reservation] aufrufen.\n"
        "Öffnungszeiten: Mo–Do 11:30–21:30, Fr 11:30–14:00 & 18:00–21:30, Sa 18:00–21:30, So geschlossen.\n"
        "Mehr als 20 Personen → Bitte um Kontaktaufnahme per E-Mail.\n"
        "Wenn der Kunde nach Speisen oder der Speisekarte fragt, rufe [TOOL:get_menu] auf.\n"
        "VERFÜGBARE WERKZEUGE:\n"
        "- check_availability: Rufe auf sobald Datum+Uhrzeit bekannt.\n"
        "- create_reservation: Rufe NUR auf wenn du hast: Datum UND Uhrzeit UND Personenzahl UND Name. "
        "Sage NIEMALS 'Reservierung bestätigt' ohne [TOOL:create_reservation]."
        + SIE_RULE
        + NO_GREETING_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
        + OFF_TOPIC_RULE
        + CONFIRM_DATA_RULE
    ),
    tools=frozenset([
        "ai_greeting", "check_availability", "create_reservation", "get_date_info",
        "get_weather", "get_directions", "get_nearby_parking",
        "verify_address", "send_sms", "faq", "end_call", "create_order",
        "get_menu", "transfer_to_tier2", "technical_issues_callback",
        "request_callback", "transfer_to_human", "get_restaurant_info",
    ]),
)
