from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import (
    PERSONA, NO_GREETING_RULE, SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE,
)

PRE_ORDER_CONFIRM = Node(
    id=NodeId.PRE_ORDER_CONFIRM,
    description="After-hours pre-order; schedules for next opening time, then create_order with pre_order=true.",
    prompt=(
        PERSONA
        + "Du nimmst eine VORBESTELLUNG für das DOBOO Korean Soulfood entgegen.\n"
        "\n"
        "Das Restaurant ist derzeit GESCHLOSSEN. Der Anrufer möchte vorbestellen\n"
        "für den nächsten Öffnungszeitpunkt. Erkläre freundlich:\n"
        "  'Das Restaurant öffnet wieder [NÄCHSTE ÖFFNUNGSZEIT]. Ich nehme gerne\n"
        "   schon eine Vorbestellung auf — wir rufen kurz vor Öffnung zurück, um\n"
        "   zu bestätigen.'\n"
        "\n"
        "=== SLOT-ABLAUF (gleich wie Bestellung) ===\n"
        "1. Welche Gerichte möchte der Anrufer? (Karte mit get_menu abrufen)\n"
        "2. Abholung oder Lieferung? (channel)\n"
        "3. Gewünschte Abhol-/Lieferzeit (date + time oder pickup_offset_minutes)\n"
        "4. Name und Telefonnummer\n"
        "5. Bei Lieferung: Adresse (verify_address)\n"
        "6. Zusammenfassung vorlesen, dann create_order mit pre_order=true aufrufen\n"
        "\n"
        "=== WICHTIGE REGELN FÜR VORBESTELLUNGEN ===\n"
        "- Sei klar und ehrlich: jetzt keine sofortige Bearbeitung möglich.\n"
        "- Bestellungen werden zum Öffnungszeitpunkt bearbeitet.\n"
        "- Maximal für 7 Tage im Voraus.\n"
        "- Bei Abholung und Lieferung BEIDE Kanäle anbieten.\n"
        "- Nach create_order: Bestellung bestätigen. SMS wird automatisch vom System gesendet — nicht erwähnen.\n"
        "\n"
        "Öffnungszeiten: Mo–Do 11:30–21:30, Fr 11:30–14:00 & 18:00–21:30,\n"
        "Sa 18:00–21:30, So geschlossen.\n"
        + SIE_RULE
        + NO_GREETING_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "get_menu", "verify_address", "create_order",
        "get_date_info", "end_call", "faq", "transfer_to_tier2",
        "request_callback", "get_restaurant_info",
    ]),
)
