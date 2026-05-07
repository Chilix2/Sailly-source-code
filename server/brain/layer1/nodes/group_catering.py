from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE, PERSONA

# Phase 4 C4: capture catering lead — requires name, phone, AND callback window.
GROUP_CATERING = Node(
    id=NodeId.GROUP_CATERING_NODE,
    description="Group order / catering (>20 pax): collect lead details incl. callback window, fire capture_catering_lead.",
    prompt=(
        PERSONA
        + "\nDer Anrufer plant eine Gruppenbestellung oder Catering für mehr als 20 Personen.\n"
        "\n"
        "SCHRITTE:\n"
        "1. Bestätige das Anliegen: 'Für Gruppen und Catering planen wir persönlich — gerne rufen wir Sie zurück!'\n"
        "2. Erfasse in dieser Reihenfolge (EINE Frage pro Turn):\n"
        "   a) Name des Ansprechpartners\n"
        "   b) Telefonnummer (Rückrufnummer)\n"
        "   c) catering_callback_availability — WANN passt ein Rückruf?\n"
        "      Frage: 'Wann wäre ein guter Zeitpunkt für unseren Rückruf — heute Nachmittag, morgen Vormittag, oder ein anderer Termin?'\n"
        "   d) Optional: ungefähre Personenzahl und Datum des Events\n"
        "3. Sobald Name + Telefon + catering_callback_availability erfasst: rufe [capture_catering_lead] auf.\n"
        "4. Bestätige: 'Ich habe Ihre Anfrage notiert — unser Team meldet sich bei Ihnen.'\n"
        "\n"
        "NIEMALS versprechen, dass der Rückruf zu einem exakten Zeitpunkt erfolgt."
        + SIE_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "capture_catering_lead",
        "request_callback",
        "transfer_to_tier2",
        "end_call",
    ]),
)
