from server.brain.layer1.nodes.base import Node, NodeId
from server.brain.layer1.nodes._prompts import SIE_RULE, PLAIN_TEXT_RULE, WORD_CAP_RULE, PERSONA

MODIFY_RESERVATION = Node(
    id=NodeId.MODIFY_RESERVATION_NODE,
    description="Caller wants to change an existing reservation; checks availability then hands to team.",
    prompt=(
        PERSONA
        + "Der Anrufer möchte eine Reservierung ändern.\n"
        "Erfasse: altes Datum/Uhrzeit (zur Identifikation), neues Datum, neue Uhrzeit.\n"
        "Prüfe Verfügbarkeit mit check_availability.\n"
        "Rufe dann request_callback auf — Team bestätigt die Änderung."
        + SIE_RULE
        + PLAIN_TEXT_RULE
        + WORD_CAP_RULE
    ),
    tools=frozenset([
        "check_availability", "request_callback", "transfer_to_tier2", "end_call",
    ]),
)
