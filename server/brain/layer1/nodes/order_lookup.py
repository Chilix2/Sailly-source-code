from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import (
    PERSONA, NO_GREETING_RULE, SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE,
)

ORDER_LOOKUP = Node(
    id=NodeId.ORDER_LOOKUP,
    description="Anchor capture: asks for order/reservation identifier before modify/cancel/status operations.",
    prompt=(
        PERSONA
        + "Der Anrufer möchte eine bestehende Bestellung oder Reservierung verwalten.\n"
        "Bevor du fortfahren kannst, benötigst du eine eindeutige Kennung:\n"
        "\n"
        "Frage nach EINER der folgenden Angaben:\n"
        "- Telefonnummer, mit der die Bestellung aufgegeben wurde\n"
        "- Bestellnummer (falls per SMS erhalten)\n"
        "- Reservierungsname + Datum\n"
        "\n"
        "Sobald die Kennung vorliegt → antworte kurz und fahre mit dem eigentlichen Anliegen fort.\n"
        "Maximal 2 Versuche; beim 3. Versuch → request_callback."
        + SIE_RULE
        + NO_GREETING_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "request_callback", "transfer_to_tier2", "transfer_to_human",
        "end_call", "faq",
    ]),
)
