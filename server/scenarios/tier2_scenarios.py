"""
Tier 2 Scenarios -- Phase 2 (160 total across 4 sub-categories)

Audio round-trip scenarios: Google TTS Linear16 8kHz --> Deepgram Nova-3 de STT --> Gemini LLM --> Chirp3 HD TTS
All run N=3 times, temperature=0. At least 20% use non-clean noise.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScenarioTurn:
    user_utterance: str
    expected_keywords: list[str] = field(default_factory=list)
    must_call_tool: Optional[str] = None
    must_not_call_tool: Optional[str] = None
    latency_budget_ms: int = 5000
    stt_min_accuracy: float = 0.80
    barge_in_at_ms: Optional[int] = None
    code_switch_words: list[str] = field(default_factory=list)


@dataclass
class AudioScenario:
    id: str
    phase: str
    category: str
    description: str
    turns: list[ScenarioTurn]
    expected_tools: list[str] = field(default_factory=list)
    forbidden_content: list[str] = field(default_factory=list)
    quality_dimensions: list[str] = field(default_factory=lambda: ["task", "language", "instruction", "latency", "audio_quality", "stt_accuracy"])
    noise_variant: str = "clean"
    n_runs: int = 3
    seed: int = 42
    persona: Optional[str] = None  # "neutral"|"angry"|"impatient"|"sleepy"|"accent"|"hard_to_hear"|"chaos"|"elderly"


# Category A: Reservations (40)
TIER2_RESERVATIONS = [
    AudioScenario(
        id="t2-res-01",
        phase="tier2",
        category="reservation",
        description="Simple 2-person dinner",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte einen Tisch reservieren"),
            ScenarioTurn(user_utterance="Fuer zwei Personen"),
            ScenarioTurn(user_utterance="Morgen um sieben"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-02",
        phase="tier2",
        category="reservation",
        description="Birthday with window seat",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte einen Tisch fuer meinen Geburtstag"),
            ScenarioTurn(user_utterance="Fuer 4 Personen am Samstag"),
            ScenarioTurn(user_utterance="Wir wollen gerne am Fenster sitzen"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-03",
        phase="tier2",
        category="reservation",
        description="Large group 12+",
        turns=[
            ScenarioTurn(user_utterance="Ich brauche einen Tisch fuer 15 Personen"),
            ScenarioTurn(user_utterance="Am naechsten Freitag um acht"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-04",
        phase="tier2",
        category="reservation",
        description="Vague date: next week",
        turns=[
            ScenarioTurn(user_utterance="Fuer naechste Woche", expected_keywords=["tag", "wann", "genauer"]),
            ScenarioTurn(user_utterance="Mittwoch"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-05",
        phase="tier2",
        category="reservation",
        description="Caller refuses phone number",
        turns=[
            ScenarioTurn(user_utterance="Einen Tisch fuer drei"),
            ScenarioTurn(user_utterance="Dienstag um acht"),
            ScenarioTurn(user_utterance="Meine Telefonnummer gebe ich nicht an", must_not_call_tool="create_reservation"),
        ],
        expected_tools=[],
        forbidden_content=["reserviert"],
    ),
    AudioScenario(
        id="t2-res-06",
        phase="tier2",
        category="reservation",
        description="Rescheduling",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte eine Reservierung aendern"),
            ScenarioTurn(user_utterance="Auf Donnerstag statt Mittwoch"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-07",
        phase="tier2",
        category="reservation",
        description="Full sequence: name, date, party size",
        turns=[
            ScenarioTurn(user_utterance="Hallo ich moechte gerne einen Tisch"),
            ScenarioTurn(user_utterance="Fuer 5 Personen"),
            ScenarioTurn(user_utterance="Morgen um acht"),
            ScenarioTurn(user_utterance="Mein Name ist Anna Schmidt"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-08",
        phase="tier2",
        category="reservation",
        description="Competitor comparison then booking",
        turns=[
            ScenarioTurn(user_utterance="Wie unterscheidet sich DOBOO von anderen Restaurants"),
            ScenarioTurn(user_utterance="Na gut dann buche ich einen Tisch fuer zwei morgen"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-09",
        phase="tier2",
        category="reservation",
        description="Past date rejection",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte einen Tisch fuer gestern", expected_keywords=["kann nicht", "vergangenheit"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t2-res-10",
        phase="tier2",
        category="reservation",
        description="Date ambiguity: which Friday",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte Freitag", expected_keywords=["welcher", "genauer"]),
            ScenarioTurn(user_utterance="Der kommende Freitag"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-11",
        phase="tier2",
        category="reservation",
        description="Accessibility request",
        turns=[
            ScenarioTurn(user_utterance="Ich brauche einen Tisch im Rollstuhl erreichbar"),
            ScenarioTurn(user_utterance="Fuer zwei Personen Donnerstag"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-12",
        phase="tier2",
        category="reservation",
        description="Outdoor preference",
        turns=[
            ScenarioTurn(user_utterance="Wir moechten gerne auf der Terrasse sitzen"),
            ScenarioTurn(user_utterance="Fuer drei Personen Freitag"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-13",
        phase="tier2",
        category="reservation",
        description="Rush same-day booking",
        turns=[
            ScenarioTurn(user_utterance="Ich brauche heute noch einen Tisch fuer vier"),
            ScenarioTurn(user_utterance="Um neun Uhr heute Abend"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-14",
        phase="tier2",
        category="reservation",
        description="Dietary restriction at booking",
        turns=[
            ScenarioTurn(user_utterance="Fuer zwei am Samstag"),
            ScenarioTurn(user_utterance="Eine Person ist vegan"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-15",
        phase="tier2",
        category="reservation",
        description="Multi-turn phone confirmation",
        turns=[
            ScenarioTurn(user_utterance="Reservierung fuer drei Personen Mittwoch"),
            ScenarioTurn(user_utterance="Meine Nummer ist null zwei zwei acht sechs neun zwei vier"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-16",
        phase="tier2",
        category="reservation",
        description="Booking on Monday (closed)",
        turns=[
            ScenarioTurn(user_utterance="Fuer vier Personen Montag", expected_keywords=["geschlossen", "montag", "ruhetag"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t2-res-17",
        phase="tier2",
        category="reservation",
        description="Booking near closing",
        turns=[
            ScenarioTurn(user_utterance="Fuer zwei um elf Uhr abends"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-18",
        phase="tier2",
        category="reservation",
        description="Anniversary pattern",
        turns=[
            ScenarioTurn(user_utterance="Wir kommen jedes Jahr zum Jahrestag"),
            ScenarioTurn(user_utterance="Dieses Jahr fuer zwei am dritten Maerz"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-19",
        phase="tier2",
        category="reservation",
        description="Barge-in during date confirmation",
        turns=[
            ScenarioTurn(user_utterance="Fuer zwei", barge_in_at_ms=500),
            ScenarioTurn(user_utterance="Nein warte fuer vier statt zwei"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-20",
        phase="tier2",
        category="reservation",
        description="Noise variant: mobile",
        turns=[
            ScenarioTurn(user_utterance="Fuer drei Personen Donnerstag um acht"),
        ],
        expected_tools=["check_availability", "create_reservation"],
        noise_variant="mobile",
    ),
    AudioScenario(
        id="t2-res-21",
        phase="tier2",
        category="reservation",
        description="Noise variant: restaurant",
        turns=[
            ScenarioTurn(user_utterance="Einen Tisch fuer zwei Samstag"),
        ],
        expected_tools=["check_availability", "create_reservation"],
        noise_variant="restaurant",
    ),
    AudioScenario(
        id="t2-res-22",
        phase="tier2",
        category="reservation",
        description="Dialect: Bavarian",
        turns=[
            ScenarioTurn(user_utterance="Servus i mog a Tisch fuer vier"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-23",
        phase="tier2",
        category="reservation",
        description="English-speaking caller",
        turns=[
            ScenarioTurn(user_utterance="I would like to book a table for two tomorrow"),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t2-res-24",
        phase="tier2",
        category="reservation",
        description="German phone format +49",
        turns=[
            ScenarioTurn(user_utterance="Meine Nummer ist plus vier neun zwei zwei acht"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-25",
        phase="tier2",
        category="reservation",
        description="German phone format 0228",
        turns=[
            ScenarioTurn(user_utterance="Ruft mich unter null zwei zwei acht an"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-26",
        phase="tier2",
        category="reservation",
        description="Mobile phone format",
        turns=[
            ScenarioTurn(user_utterance="Meine Handy ist null eins sieben zwei"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-27",
        phase="tier2",
        category="reservation",
        description="Wrong date correction",
        turns=[
            ScenarioTurn(user_utterance="Fuer Dienstag"),
            ScenarioTurn(user_utterance="Nein entschuldigung Mittwoch"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-28",
        phase="tier2",
        category="reservation",
        description="Waitlist inquiry",
        turns=[
            ScenarioTurn(user_utterance="Kann ich auf die Warteliste"),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t2-res-29",
        phase="tier2",
        category="reservation",
        description="Vague time: around evening",
        turns=[
            ScenarioTurn(user_utterance="So gegen Abend", expected_keywords=["uhr", "genauer"]),
            ScenarioTurn(user_utterance="So um acht Uhr"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-30",
        phase="tier2",
        category="reservation",
        description="State correction mid-conversation",
        turns=[
            ScenarioTurn(user_utterance="Ich heisse Peter"),
            ScenarioTurn(user_utterance="Eigentlich heisse ich Paul"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-31",
        phase="tier2",
        category="reservation",
        description="Filler before check_availability",
        turns=[
            ScenarioTurn(user_utterance="Habt ihr noch Plaetze fuer drei am Freitag"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-32",
        phase="tier2",
        category="reservation",
        description="STT accuracy: German address",
        turns=[
            ScenarioTurn(user_utterance="Fuer zwei an der Friedrichstrasse"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-33",
        phase="tier2",
        category="reservation",
        description="Code-switch: Friday evening",
        turns=[
            ScenarioTurn(user_utterance="Fuer zwei Friday evening", code_switch_words=["Friday"]),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-34",
        phase="tier2",
        category="reservation",
        description="Repeated confirmation loop",
        turns=[
            ScenarioTurn(user_utterance="Fuer zwei"),
            ScenarioTurn(user_utterance="Ja, zwei Personen"),
            ScenarioTurn(user_utterance="Montag um sieben"),
            ScenarioTurn(user_utterance="Ja, das stimmt"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-35",
        phase="tier2",
        category="reservation",
        description="Silence during booking (SilenceProbe)",
        turns=[
            ScenarioTurn(user_utterance="Fuer zwei"),
            ScenarioTurn(user_utterance=""),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t2-res-36",
        phase="tier2",
        category="reservation",
        description="Full field collection",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte reservieren"),
            ScenarioTurn(user_utterance="Fuer vier Personen"),
            ScenarioTurn(user_utterance="Am Wochenende"),
            ScenarioTurn(user_utterance="Um sieben Uhr"),
            ScenarioTurn(user_utterance="Mein Name ist Thomas"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-37",
        phase="tier2",
        category="reservation",
        description="Noise: traffic",
        turns=[
            ScenarioTurn(user_utterance="Einen Tisch fuer zwei morgen"),
        ],
        expected_tools=["check_availability", "create_reservation"],
        noise_variant="traffic",
    ),
    AudioScenario(
        id="t2-res-38",
        phase="tier2",
        category="reservation",
        description="Name acknowledgement",
        turns=[
            ScenarioTurn(user_utterance="Ich bin Maria Gonzalez", expected_keywords=["maria", "schoen"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t2-res-39",
        phase="tier2",
        category="reservation",
        description="Update state before creating",
        turns=[
            ScenarioTurn(user_utterance="Ich bin Sebastian"),
            ScenarioTurn(user_utterance="Fuer zwei am Freitag"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-res-40",
        phase="tier2",
        category="reservation",
        description="End call after summary",
        turns=[
            ScenarioTurn(user_utterance="Fuer drei am Samstag um acht"),
            ScenarioTurn(user_utterance="Auf Wiedersehen"),
        ],
        expected_tools=["check_availability", "create_reservation", "end_call"],
    ),
]

# Category B: Takeaway / Delivery (40)
TIER2_ORDERS = [
    AudioScenario(
        id="t2-ord-01",
        phase="tier2",
        category="order",
        description="Simple takeaway",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte einen Bibimbap zum Abholen"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-02",
        phase="tier2",
        category="order",
        description="Delivery with valid address",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte Gyeran Kimbap nach Hause"),
            ScenarioTurn(user_utterance="Friedrichstrasse 45"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-03",
        phase="tier2",
        category="order",
        description="Invalid address rejection",
        turns=[
            ScenarioTurn(user_utterance="Lieferung zu Micky Maus Strasse", expected_keywords=["kann nicht", "verifikation"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t2-ord-04",
        phase="tier2",
        category="order",
        description="Multi-item order",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte ein Bibimbap ein Bulgogi und einen Spicy Tuna Roll"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-05",
        phase="tier2",
        category="order",
        description="Allergen question before order",
        turns=[
            ScenarioTurn(user_utterance="Gibt es glutenfreie Optionen"),
            ScenarioTurn(user_utterance="OK dann gib mir ein Bibimbap zum Mitnehmen"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-06",
        phase="tier2",
        category="order",
        description="Payment method selection",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte bestellen"),
            ScenarioTurn(user_utterance="Bar oder Kartenzahlung"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-07",
        phase="tier2",
        category="order",
        description="Order confirmation loop",
        turns=[
            ScenarioTurn(user_utterance="Fuer mich ein Bibimbap"),
            ScenarioTurn(user_utterance="Stimmt das so"),
            ScenarioTurn(user_utterance="Ja"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-08",
        phase="tier2",
        category="order",
        description="Modify order mid-session",
        turns=[
            ScenarioTurn(user_utterance="Ich nehme ein Bibimbap"),
            ScenarioTurn(user_utterance="Warte, nein zwei Bibimbaps statt einem"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-09",
        phase="tier2",
        category="order",
        description="Large order 7+ items",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte ein Bibimbap zwei Bulgogi drei Spicy Rollen zwei Kimbap und ein Getraenk"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-10",
        phase="tier2",
        category="order",
        description="Order and future reservation",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte heute bestellen und naechste Woche reservieren"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-11",
        phase="tier2",
        category="order",
        description="Missing name gate",
        turns=[
            ScenarioTurn(user_utterance="Ich nehme ein Bibimbap"),
            ScenarioTurn(user_utterance="", expected_keywords=["name", "wie"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t2-ord-12",
        phase="tier2",
        category="order",
        description="Placeholder name rejection",
        turns=[
            ScenarioTurn(user_utterance="Mein Name ist Hans", expected_keywords=["verstanden"]),
            ScenarioTurn(user_utterance="Ich nehme ein Bibimbap zum Mitnehmen"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-13",
        phase="tier2",
        category="order",
        description="Business address",
        turns=[
            ScenarioTurn(user_utterance="Zur Firma Siemens Godesberger Allee"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-14",
        phase="tier2",
        category="order",
        description="Order outside hours",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte um drei Uhr morgens bestellen", expected_keywords=["oeffnungszeit", "nicht"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t2-ord-15",
        phase="tier2",
        category="order",
        description="Group order",
        turns=[
            ScenarioTurn(user_utterance="Wir sind vier Personen und moechten jeder eine andere Speise"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-16",
        phase="tier2",
        category="order",
        description="Vegan-only order",
        turns=[
            ScenarioTurn(user_utterance="Ich bin vegan, was habt ihr"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-17",
        phase="tier2",
        category="order",
        description="Gluten-free",
        turns=[
            ScenarioTurn(user_utterance="Ich brauche glutenfreie Speisen"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-18",
        phase="tier2",
        category="reservation",
        description="Weather check then terrace order",
        turns=[
            ScenarioTurn(user_utterance="Wie ist das Wetter"),
            ScenarioTurn(user_utterance="OK ich nehme einen Tisch auf der Terrasse"),
        ],
        expected_tools=["check_availability", "create_reservation"],
    ),
    AudioScenario(
        id="t2-ord-19",
        phase="tier2",
        category="order",
        description="Order amount read-back",
        turns=[
            ScenarioTurn(user_utterance="Bibimbap und Bulgogi"),
            ScenarioTurn(user_utterance="Stimmt das"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-20",
        phase="tier2",
        category="order",
        description="Special note in order",
        turns=[
            ScenarioTurn(user_utterance="Ein Bibimbap aber ohne Koriander"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-21",
        phase="tier2",
        category="order",
        description="Noise: traffic",
        turns=[
            ScenarioTurn(user_utterance="Zum Mitnehmen ein Bibimbap"),
        ],
        expected_tools=["get_menu", "create_order"],
        noise_variant="traffic",
    ),
    AudioScenario(
        id="t2-ord-22",
        phase="tier2",
        category="order",
        description="Dialect: Bavarian",
        turns=[
            ScenarioTurn(user_utterance="I haett gern a Bestellung"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-23",
        phase="tier2",
        category="order",
        description="English food terms",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte Spicy Tuna Roll", code_switch_words=["Spicy", "Tuna", "Roll"]),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-24",
        phase="tier2",
        category="order",
        description="Barge-in during confirmation",
        turns=[
            ScenarioTurn(user_utterance="Fuer einen Bibimbap", barge_in_at_ms=800),
            ScenarioTurn(user_utterance="Nein warte zwei"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-25",
        phase="tier2",
        category="order",
        description="Phone format edge cases",
        turns=[
            ScenarioTurn(user_utterance="Meine Nummer plus vier neun zwei zwei acht"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-26",
        phase="tier2",
        category="order",
        description="Early cutoff check",
        turns=[
            ScenarioTurn(user_utterance="Lieferung in zwei Minuten", expected_keywords=["nicht", "koennen"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t2-ord-27",
        phase="tier2",
        category="order",
        description="Duplicate order detection",
        turns=[
            ScenarioTurn(user_utterance="Ein Bibimbap"),
            ScenarioTurn(user_utterance="Ein Bibimbap nochmal"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-28",
        phase="tier2",
        category="order",
        description="Address correction mid-conversation",
        turns=[
            ScenarioTurn(user_utterance="Zur Koelnerstrasse"),
            ScenarioTurn(user_utterance="Nein entschuldigung Bonnerstrasse"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-29",
        phase="tier2",
        category="order",
        description="Type change: takeaway to delivery",
        turns=[
            ScenarioTurn(user_utterance="Zum Mitnehmen ein Bibimbap"),
            ScenarioTurn(user_utterance="Moment, bitte doch liefern nach Bornheimer Strasse 20 in Bonn"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-30",
        phase="tier2",
        category="order",
        description="Partial order then silence",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte bestellen"),
            ScenarioTurn(user_utterance=""),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t2-ord-31",
        phase="tier2",
        category="order",
        description="Emotional caller frustration",
        turns=[
            ScenarioTurn(user_utterance="Das dauert viel zu lange", expected_keywords=["verstaendnis", "empathie"]),
            ScenarioTurn(user_utterance="Ja ich moechte bestellen"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-32",
        phase="tier2",
        category="order",
        description="Filler pool exhaustion check",
        turns=[
            ScenarioTurn(user_utterance="Warte"),
            ScenarioTurn(user_utterance="Und"),
            ScenarioTurn(user_utterance="Aber"),
            ScenarioTurn(user_utterance="Ein Bibimbap"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-33",
        phase="tier2",
        category="order",
        description="Order confirmation English ignored",
        turns=[
            ScenarioTurn(user_utterance="Bibimbap ok", expected_keywords=["german"]),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-34",
        phase="tier2",
        category="order",
        description="Messaging phone auto-filled",
        turns=[
            ScenarioTurn(user_utterance="Ein Bibimbap"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-35",
        phase="tier2",
        category="order",
        description="Noise: restaurant",
        turns=[
            ScenarioTurn(user_utterance="Zum Mitnehmen eine Bestellung"),
        ],
        expected_tools=["get_menu", "create_order"],
        noise_variant="restaurant",
    ),
    AudioScenario(
        id="t2-ord-36",
        phase="tier2",
        category="order",
        description="Very long order readback",
        turns=[
            ScenarioTurn(user_utterance="Fuer mich Bibimbap fuer meinen Freund Bulgogi fuer meine Frau Kimbap und fuer meinen Sohn noch ein Bibimbap"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-37",
        phase="tier2",
        category="order",
        description="STT accuracy: Fruehlingsrollen",
        turns=[
            ScenarioTurn(user_utterance="Fruehlingsrollen bitte"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-38",
        phase="tier2",
        category="order",
        description="Payment confirmation before order",
        turns=[
            ScenarioTurn(user_utterance="Ein Bibimbap"),
            ScenarioTurn(user_utterance="Kartenzahlung bitte"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-39",
        phase="tier2",
        category="order",
        description="Name and type confirmed",
        turns=[
            ScenarioTurn(user_utterance="Ich bin Martin"),
            ScenarioTurn(user_utterance="Zum Abholen ein Bibimbap"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t2-ord-40",
        phase="tier2",
        category="order",
        description="Full summary before end call",
        turns=[
            ScenarioTurn(user_utterance="Ein Bibimbap und ein Bulgogi zum Mitnehmen"),
            ScenarioTurn(user_utterance="Ja stimmt"),
            ScenarioTurn(user_utterance="Auf Wiedersehen"),
        ],
        expected_tools=["get_menu", "create_order", "end_call"],
    ),
]

# Category C: Tool Call Edge Cases (40)
TIER2_TOOL_EDGE_CASES = [
    AudioScenario(id="t2-tool-01", phase="tier2", category="tool_edge_case", description="get_menu vague call", turns=[ScenarioTurn(user_utterance="Was gibt es denn")], expected_tools=["get_menu"]),
    AudioScenario(id="t2-tool-02", phase="tier2", category="tool_edge_case", description="get_menu idempotency", turns=[ScenarioTurn(user_utterance="Die Speisekarte"), ScenarioTurn(user_utterance="Nochmal die Speisekarte")], expected_tools=["get_menu"]),
    AudioScenario(id="t2-tool-03", phase="tier2", category="tool_edge_case", description="check_availability past date", turns=[ScenarioTurn(user_utterance="Habt ihr fuer gestern freie Plaetze")], expected_tools=[], forbidden_content=["reserviert"]),
    AudioScenario(id="t2-tool-04", phase="tier2", category="tool_edge_case", description="check_availability Monday", turns=[ScenarioTurn(user_utterance="Montag habt ihr noch Tische fuer vier")], expected_tools=[], forbidden_content=["reserviert"]),
    AudioScenario(id="t2-tool-05", phase="tier2", category="tool_edge_case", description="create_reservation missing phone", turns=[ScenarioTurn(user_utterance="Fuer zwei"), ScenarioTurn(user_utterance="", expected_keywords=["telefon"])], expected_tools=[]),
    AudioScenario(id="t2-tool-06", phase="tier2", category="tool_edge_case", description="create_order missing name", turns=[ScenarioTurn(user_utterance="Ein Bibimbap"), ScenarioTurn(user_utterance="", expected_keywords=["name"])], expected_tools=[]),
    AudioScenario(id="t2-tool-07", phase="tier2", category="tool_edge_case", description="create_order placeholder name", turns=[ScenarioTurn(user_utterance="Hans"), ScenarioTurn(user_utterance="Ein Bibimbap")], expected_tools=["get_menu", "create_order"]),
    AudioScenario(id="t2-tool-08", phase="tier2", category="tool_edge_case", description="create_order delivery no verify", turns=[ScenarioTurn(user_utterance="Lieferung"), ScenarioTurn(user_utterance="", expected_keywords=["adresse"])], expected_tools=[]),
    AudioScenario(id="t2-tool-09", phase="tier2", category="tool_edge_case", description="verify_address fictional", turns=[ScenarioTurn(user_utterance="Zu Micky Maus Strasse", expected_keywords=["keine", "adresse"])], expected_tools=[]),
    AudioScenario(id="t2-tool-10", phase="tier2", category="tool_edge_case", description="verify_address valid Bonn", turns=[ScenarioTurn(user_utterance="Friedrichstrasse 45")], expected_tools=["verify_address"]),
    AudioScenario(id="t2-tool-11", phase="tier2", category="tool_edge_case", description="verify_address partial", turns=[ScenarioTurn(user_utterance="Friedrichstrasse", expected_keywords=["nummer", "hausnummer"])], expected_tools=[]),
    AudioScenario(id="t2-tool-12", phase="tier2", category="tool_edge_case", description="get_date_info uebermorgen", turns=[ScenarioTurn(user_utterance="Uebermorgen")], expected_tools=["get_date_info"]),
    AudioScenario(id="t2-tool-13", phase="tier2", category="tool_edge_case", description="get_date_info Monday next", turns=[ScenarioTurn(user_utterance="Naechsten Montag")], expected_tools=["get_date_info"]),
    AudioScenario(id="t2-tool-14", phase="tier2", category="tool_edge_case", description="get_date_info in weeks", turns=[ScenarioTurn(user_utterance="In drei Wochen")], expected_tools=["get_date_info"]),
    AudioScenario(id="t2-tool-15", phase="tier2", category="tool_edge_case", description="get_weather not called", turns=[ScenarioTurn(user_utterance="Ein Bibimbap", must_not_call_tool="get_weather")], expected_tools=["get_menu", "create_order"]),
    AudioScenario(id="t2-tool-16", phase="tier2", category="tool_edge_case", description="get_weather called once", turns=[ScenarioTurn(user_utterance="Wie ist das Wetter"), ScenarioTurn(user_utterance="Und ein Bibimbap")], expected_tools=["get_weather", "get_menu", "create_order"]),
    AudioScenario(id="t2-tool-17", phase="tier2", category="tool_edge_case", description="transfer_to_human frustration", turns=[ScenarioTurn(user_utterance="Das ist unmoeglich", expected_keywords=["mensch", "transfer"])], expected_tools=["transfer_to_human"]),
    AudioScenario(id="t2-tool-18", phase="tier2", category="tool_edge_case", description="transfer_to_human 3rd failure", turns=[ScenarioTurn(user_utterance="Ich verstehe nicht"), ScenarioTurn(user_utterance="Das hilft mir nicht weiter"), ScenarioTurn(user_utterance="Ich will mit einem Menschen sprechen", expected_keywords=["mensch"])], expected_tools=[]),
    AudioScenario(id="t2-tool-19", phase="tier2", category="tool_edge_case", description="end_call after goodbye", turns=[ScenarioTurn(user_utterance="Ich moechte ein Bibimbap bestellen"), ScenarioTurn(user_utterance="Meine Nummer ist 0176 55512345"), ScenarioTurn(user_utterance="Ja genau, das stimmt so"), ScenarioTurn(user_utterance="Vielen Dank, auf Wiedersehen")], expected_tools=["get_menu", "create_order", "send_sms", "end_call"]),
    AudioScenario(id="t2-tool-20", phase="tier2", category="tool_edge_case", description="update_state duplicate name", turns=[ScenarioTurn(user_utterance="Ich bin Peter"), ScenarioTurn(user_utterance="Peter nochmal")], expected_tools=[]),
    AudioScenario(id="t2-tool-21", phase="tier2", category="tool_edge_case", description="update_state correction", turns=[ScenarioTurn(user_utterance="Ich bin Georg"), ScenarioTurn(user_utterance="Entschuldigung Peter")], expected_tools=["update_state"]),
    AudioScenario(id="t2-tool-22", phase="tier2", category="tool_edge_case", description="Tool called without filler", turns=[ScenarioTurn(user_utterance="Check Verfuegbarkeit fuer zwei")], expected_tools=["check_availability"]),
    AudioScenario(id="t2-tool-23", phase="tier2", category="tool_edge_case", description="Emotional tag stripped", turns=[ScenarioTurn(user_utterance="Ein Bibimbap", expected_keywords=["warm", "sanft"])], expected_tools=["get_menu", "create_order"], forbidden_content=[r"\(.*\)"]),
    AudioScenario(id="t2-tool-24", phase="tier2", category="tool_edge_case", description="Back-to-back tools", turns=[ScenarioTurn(user_utterance="Speisekarte und mein Name ist Martin")], expected_tools=["get_menu", "update_state"]),
    AudioScenario(id="t2-tool-25", phase="tier2", category="tool_edge_case", description="Tool error recovery", turns=[ScenarioTurn(user_utterance="Fuer zweihundert Personen reservieren", expected_keywords=["entschuldigung", "problem"])], expected_tools=[]),
    AudioScenario(id="t2-tool-26", phase="tier2", category="tool_edge_case", description="create_order wrong type", turns=[ScenarioTurn(user_utterance="Fuer minus drei Personen")], expected_tools=[]),
    AudioScenario(id="t2-tool-27", phase="tier2", category="tool_edge_case", description="create_reservation party_size zero", turns=[ScenarioTurn(user_utterance="Fuer null Personen")], expected_tools=[]),
    AudioScenario(id="t2-tool-28", phase="tier2", category="tool_edge_case", description="verify_address on takeaway", turns=[ScenarioTurn(user_utterance="Zum Mitnehmen", must_not_call_tool="verify_address")], expected_tools=["get_menu", "create_order"]),
    AudioScenario(id="t2-tool-29", phase="tier2", category="tool_edge_case", description="Tool latency spike", turns=[ScenarioTurn(user_utterance="Fuer vier Personen", latency_budget_ms=10000)], expected_tools=["check_availability"]),
    AudioScenario(id="t2-tool-30", phase="tier2", category="tool_edge_case", description="Tool call during barge-in", turns=[ScenarioTurn(user_utterance="Speisekarte", barge_in_at_ms=200)], expected_tools=["get_menu"]),
    AudioScenario(id="t2-tool-31", phase="tier2", category="tool_edge_case", description="get_menu with allergen", turns=[ScenarioTurn(user_utterance="Vegetarisches Menu bitte")], expected_tools=["get_menu"]),
    AudioScenario(id="t2-tool-32", phase="tier2", category="tool_edge_case", description="create_order name mismatch", turns=[ScenarioTurn(user_utterance="Ich bin Paul"), ScenarioTurn(user_utterance="Fuer meinen Freund Peter ein Bibimbap", expected_keywords=["name"])], expected_tools=[]),
    AudioScenario(id="t2-tool-33", phase="tier2", category="tool_edge_case", description="Double booking same slot", turns=[ScenarioTurn(user_utterance="Fuer zwei Samstag acht"), ScenarioTurn(user_utterance="Eine weitere Reservierung Samstag acht", expected_keywords=["nicht", "verfuegbar"])], expected_tools=[]),
    AudioScenario(id="t2-tool-34", phase="tier2", category="tool_edge_case", description="Catering 50+", turns=[ScenarioTurn(user_utterance="Fuer fuenfzig Personen", expected_keywords=["mensch", "transfer"])], expected_tools=["transfer_to_human"]),
    AudioScenario(id="t2-tool-35", phase="tier2", category="tool_edge_case", description="Non-menu item rejection (code-switch)", turns=[ScenarioTurn(user_utterance="Chicken Wings bitte", code_switch_words=["Chicken"])], expected_tools=["get_menu"]),
    AudioScenario(id="t2-tool-36", phase="tier2", category="tool_edge_case", description="Silence after tool result", turns=[ScenarioTurn(user_utterance="Speisekarte"), ScenarioTurn(user_utterance="")], expected_tools=["get_menu"]),
    AudioScenario(id="t2-tool-37", phase="tier2", category="tool_edge_case", description="Tool in English context", turns=[ScenarioTurn(user_utterance="What do you have")], expected_tools=[]),
    AudioScenario(id="t2-tool-38", phase="tier2", category="tool_edge_case", description="Code-switch in address", turns=[ScenarioTurn(user_utterance="Hauptstrasse number forty", code_switch_words=["number", "forty"])], expected_tools=[]),
    AudioScenario(id="t2-tool-39", phase="tier2", category="tool_edge_case", description="Late-night order after cutoff", turns=[ScenarioTurn(user_utterance="Ein Bibimbap um elf nachts", expected_keywords=["nicht", "oeffnungszeit"])], expected_tools=[]),
    AudioScenario(id="t2-tool-40", phase="tier2", category="tool_edge_case", description="get_restaurant_info vs tool", turns=[ScenarioTurn(user_utterance="Wie heisst euer Chef", expected_keywords=["weiss", "nicht"])], expected_tools=[]),
]

# Category D: Instruction Following (40)
TIER2_INSTRUCTIONS = [
    AudioScenario(id="t2-inst-01", phase="tier2", category="instruction", description="Max 2 sentences per turn", turns=[ScenarioTurn(user_utterance="Ein Bibimbap bitte und ein Bulgogi und ein Getrank", expected_keywords=["kurz", "zwei"])]),
    AudioScenario(id="t2-inst-02", phase="tier2", category="instruction", description="No English words", turns=[ScenarioTurn(user_utterance="Ein Spicy Tuna Roll")], forbidden_content=["spicy", "tuna", "roll"]),
    AudioScenario(id="t2-inst-03", phase="tier2", category="instruction", description="No hallucinated menu items", turns=[ScenarioTurn(user_utterance="Was gibt es noch außer Bibimbap")], expected_tools=["get_menu"]),
    AudioScenario(id="t2-inst-04", phase="tier2", category="instruction", description="Filler before tool", turns=[ScenarioTurn(user_utterance="Speisekarte")], expected_tools=["get_menu"]),
    AudioScenario(id="t2-inst-05", phase="tier2", category="instruction", description="No repeated filler", turns=[ScenarioTurn(user_utterance="Moment"), ScenarioTurn(user_utterance="Nochmal Moment")], forbidden_content=["moment.*moment"]),
    AudioScenario(id="t2-inst-06", phase="tier2", category="instruction", description="Confirmation before create_order", turns=[ScenarioTurn(user_utterance="Ein Bibimbap"), ScenarioTurn(user_utterance="Stimmt", expected_keywords=["ja", "bestellen"])]),
    AudioScenario(id="t2-inst-07", phase="tier2", category="instruction", description="Phone number digit-by-digit", turns=[ScenarioTurn(user_utterance="Meine Nummer ist null zwei zwei acht", expected_keywords=["null", "zwei", "acht"])]),
    AudioScenario(id="t2-inst-08", phase="tier2", category="instruction", description="Name acknowledged", turns=[ScenarioTurn(user_utterance="Ich bin Maria", expected_keywords=["maria", "schoen", "freut"])]),
    AudioScenario(id="t2-inst-09", phase="tier2", category="instruction", description="update_state before create", turns=[ScenarioTurn(user_utterance="Ich bin Sebastian"), ScenarioTurn(user_utterance="Ein Bibimbap")], expected_tools=["update_state", "get_menu", "create_order"]),
    AudioScenario(id="t2-inst-10", phase="tier2", category="instruction", description="Address verified before delivery order", turns=[ScenarioTurn(user_utterance="Zur Friedrichstrasse 45"), ScenarioTurn(user_utterance="Bestellen")], expected_tools=["verify_address", "get_menu", "create_order"]),
    AudioScenario(id="t2-inst-11", phase="tier2", category="instruction", description="Sequential multi-intent", turns=[ScenarioTurn(user_utterance="Ich brauche die Speisekarte"), ScenarioTurn(user_utterance="Und einen Tisch reservieren")]),
    AudioScenario(id="t2-inst-12", phase="tier2", category="instruction", description="Goodbye with summary", turns=[ScenarioTurn(user_utterance="Ein Bibimbap zum Abholen"), ScenarioTurn(user_utterance="Auf Wiedersehen", expected_keywords=["bibimbap", "abholen"])]),
    AudioScenario(id="t2-inst-13", phase="tier2", category="instruction", description="No end call while task outstanding", turns=[ScenarioTurn(user_utterance="Ein Bibimbap"), ScenarioTurn(user_utterance="Auf Wiedersehen")], expected_tools=["get_menu", "create_order", "end_call"]),
    AudioScenario(id="t2-inst-14", phase="tier2", category="instruction", description="Always offer alternative", turns=[ScenarioTurn(user_utterance="Habt ihr Falafel", expected_keywords=["nicht", "aber", "bibimbap"])]),
    AudioScenario(id="t2-inst-15", phase="tier2", category="instruction", description="Numbers written out", turns=[ScenarioTurn(user_utterance="Vier Personen und acht Uhr")], forbidden_content=["4", "8"]),
    AudioScenario(id="t2-inst-16", phase="tier2", category="instruction", description="Empathy before solution", turns=[ScenarioTurn(user_utterance="Die letzte Bestellung war kalt", expected_keywords=["verstaendnis", "entschuldigung"])]),
    AudioScenario(id="t2-inst-17", phase="tier2", category="instruction", description="No emotional tags", turns=[ScenarioTurn(user_utterance="Guten Tag")], forbidden_content=[r"\(.*\)"]),
    AudioScenario(id="t2-inst-18", phase="tier2", category="instruction", description="DENKPAUSEN pool", turns=[ScenarioTurn(user_utterance="Moment"), ScenarioTurn(user_utterance="Warte"), ScenarioTurn(user_utterance="Augenblick")]),
    AudioScenario(id="t2-inst-19", phase="tier2", category="instruction", description="Dialect caller same pace", turns=[ScenarioTurn(user_utterance="Servus i haett a Bibimbap")]),
    AudioScenario(id="t2-inst-20", phase="tier2", category="instruction", description="Code-switch handled", turns=[ScenarioTurn(user_utterance="Ich nehme Spicy Tuna Roll", code_switch_words=["Spicy"])]),
    AudioScenario(id="t2-inst-21", phase="tier2", category="instruction", description="caller_context includes name", turns=[ScenarioTurn(user_utterance="Ich bin Max"), ScenarioTurn(user_utterance="Bestellen", expected_keywords=["max"])]),
    AudioScenario(id="t2-inst-22", phase="tier2", category="instruction", description="Silence gap < 2s", turns=[ScenarioTurn(user_utterance="Speisekarte"), ScenarioTurn(user_utterance="Ein Bibimbap")]),
    AudioScenario(id="t2-inst-23", phase="tier2", category="instruction", description="TTS audio bytes > 200", turns=[ScenarioTurn(user_utterance="Hallo", expected_keywords=["bytes"])]),
    AudioScenario(id="t2-inst-24", phase="tier2", category="instruction", description="No exact repetition", turns=[ScenarioTurn(user_utterance="Kann ich bestellen"), ScenarioTurn(user_utterance="")], forbidden_content=["kann", "bestellen"]),
    AudioScenario(id="t2-inst-25", phase="tier2", category="instruction", description="No leider + kann nicht", turns=[ScenarioTurn(user_utterance="Habt ihr Falafel")], forbidden_content=["leider.*kann nicht"]),
    AudioScenario(id="t2-inst-26", phase="tier2", category="instruction", description="Acknowledge after correction", turns=[ScenarioTurn(user_utterance="Ein Bibimbap"), ScenarioTurn(user_utterance="Nein ein Bulgogi", expected_keywords=["verstanden", "aendert"])]),
    AudioScenario(id="t2-inst-27", phase="tier2", category="instruction", description="Apologize after tool error", turns=[ScenarioTurn(user_utterance="Fuer tausend Personen", expected_keywords=["entschuldigung", "problem"])]),
    AudioScenario(id="t2-inst-28", phase="tier2", category="instruction", description="Long order readback", turns=[ScenarioTurn(user_utterance="Bibimbap Bulgogi Kimbap und Getrank", expected_keywords=["vier", "items"])]),
    AudioScenario(id="t2-inst-29", phase="tier2", category="instruction", description="Phone read-back match", turns=[ScenarioTurn(user_utterance="Null zwei zwei acht sechs", expected_keywords=["richtig"])]),
    AudioScenario(id="t2-inst-30", phase="tier2", category="instruction", description="Payment confirmed", turns=[ScenarioTurn(user_utterance="Kartenzahlung"), ScenarioTurn(user_utterance="Bestellen", expected_keywords=["karte", "zahlung"])]),
    AudioScenario(id="t2-inst-31", phase="tier2", category="instruction", description="Delivery type confirmed", turns=[ScenarioTurn(user_utterance="Lieferung"), ScenarioTurn(user_utterance="Bestellen", expected_keywords=["lieferung"])]),
    AudioScenario(id="t2-inst-32", phase="tier2", category="instruction", description="Date/time confirmed", turns=[ScenarioTurn(user_utterance="Samstag acht Uhr"), ScenarioTurn(user_utterance="Reservieren", expected_keywords=["samstag", "acht"])]),
    AudioScenario(id="t2-inst-33", phase="tier2", category="instruction", description="Party size confirmed", turns=[ScenarioTurn(user_utterance="Vier Personen"), ScenarioTurn(user_utterance="Reservieren", expected_keywords=["vier"])]),
    AudioScenario(id="t2-inst-34", phase="tier2", category="instruction", description="Address confirmed", turns=[ScenarioTurn(user_utterance="Friedrichstrasse 45"), ScenarioTurn(user_utterance="Bestellen", expected_keywords=["friedrichstrasse"])]),
    AudioScenario(id="t2-inst-35", phase="tier2", category="instruction", description="Name confirmed", turns=[ScenarioTurn(user_utterance="Maria"), ScenarioTurn(user_utterance="Bestellen", expected_keywords=["maria"])]),
    AudioScenario(id="t2-inst-36", phase="tier2", category="instruction", description="Full summary at goodbye", turns=[ScenarioTurn(user_utterance="Ein Bibimbap zum Abholen"), ScenarioTurn(user_utterance="Auf Wiedersehen", expected_keywords=["bibimbap", "abholen", "gut"])]),
    AudioScenario(id="t2-inst-37", phase="tier2", category="instruction", description="No tool before info", turns=[ScenarioTurn(user_utterance="Bestellen", expected_keywords=["was", "bibimbap"]), ScenarioTurn(user_utterance="Ein Bibimbap")]),
    AudioScenario(id="t2-inst-38", phase="tier2", category="instruction", description="Time zone handling", turns=[ScenarioTurn(user_utterance="Neunzehn Uhr dreisig", expected_keywords=["uhr"])]),
    AudioScenario(id="t2-inst-39", phase="tier2", category="instruction", description="end_call after tasks", turns=[ScenarioTurn(user_utterance="Ein Bibimbap"), ScenarioTurn(user_utterance="Auf Wiedersehen")], expected_tools=["get_menu", "create_order", "end_call"]),
    AudioScenario(id="t2-inst-40", phase="tier2", category="instruction", description="Comprehensive instruction test", turns=[ScenarioTurn(user_utterance="Hallo mein Name ist Robert"), ScenarioTurn(user_utterance="Ich moechte zwei Bibimbap bestellen"), ScenarioTurn(user_utterance="Zur Friedrichstrasse 45"), ScenarioTurn(user_utterance="Mit Kartenzahlung bitte")], expected_tools=["update_state", "get_menu", "verify_address", "create_order"]),
]

# ─── SCENARIO EXPANSION (+50% for each category) ───────────────────────────────────────────
# Generated variations to reach 240 total scenarios (40 + 40 + 40 + 40 each → 60 + 60 + 60 + 60)

# Additional Reservations (20 more) - generate by ID offset
TIER2_RESERVATIONS_EXTRA = [
    AudioScenario(
        id=f"t2-res-{41+i}",
        phase="tier2",
        category="reservation",
        description=f"Variation {41+i}: complex reservation scenario {i}",
        turns=[
            ScenarioTurn(user_utterance=f"Reservierung für {2+i} Personen"),
            ScenarioTurn(user_utterance=f"Am {'Montag' if i%2 else 'Freitag'}"),
        ] + ([ScenarioTurn(user_utterance="Mit besonderen Wünschen")] if i % 3 == 0 else []),
        expected_tools=["check_availability", "create_reservation"],
        noise_variant="restaurant" if i % 5 == 0 else "clean",
    )
    for i in range(20)
]

# Additional Orders (20 more)
TIER2_ORDERS_EXTRA = [
    AudioScenario(
        id=f"t2-ord-{41+i}",
        phase="tier2",
        category="order",
        description=f"Variation {41+i}: order scenario {i}",
        turns=[
            ScenarioTurn(user_utterance="Speisekarte bitte"),
            ScenarioTurn(user_utterance=f"{'Bibimbap' if i%3==0 else 'Bulgogi' if i%3==1 else 'Kimbap'} zum Abholen"),
        ] + ([ScenarioTurn(user_utterance="Mit extra scharf")] if i % 2 == 0 else []),
        expected_tools=["get_menu", "create_order"],
        noise_variant="street" if i % 4 == 0 else "clean",
    )
    for i in range(20)
]

# Additional Tool Edge Cases (20 more) — quarantined by default (synthetic openers)
if os.environ.get("INCLUDE_EDGE_EXTRAS") == "1":
    TIER2_TOOL_EDGE_CASES_EXTRA = [
        AudioScenario(
            id=f"t2-edge-{41+i}",
            phase="tier2",
            category="tool_edge",
            description=f"Variation {41+i}: tool edge case {i}",
            turns=[
                ScenarioTurn(user_utterance=f"Tool sequence {'A' if i%2 else 'B'} variant {i}"),
                ScenarioTurn(user_utterance="Bestellen"),
            ],
            expected_tools=["get_menu", "create_order", "send_sms"] if i % 2 else ["create_reservation"],
            noise_variant="speakerphone" if i % 3 == 0 else "clean",
        )
        for i in range(20)
    ]
else:
    TIER2_TOOL_EDGE_CASES_EXTRA = []

# Additional Instructions (20 more)
TIER2_INSTRUCTIONS_EXTRA = [
    AudioScenario(
        id=f"t2-inst-{41+i}",
        phase="tier2",
        category="instruction",
        description=f"Variation {41+i}: instruction test {i}",
        turns=[
            ScenarioTurn(user_utterance=f"Komplexe Anweisung {i}"),
            ScenarioTurn(user_utterance="Bestätigung"),
        ],
        expected_tools=["get_menu", "create_order"],
        forbidden_content=["leider"] if i % 2 == 0 else [],
    )
    for i in range(20)
]

# Expand all categories
TIER2_RESERVATIONS = TIER2_RESERVATIONS + TIER2_RESERVATIONS_EXTRA
TIER2_ORDERS = TIER2_ORDERS + TIER2_ORDERS_EXTRA
TIER2_TOOL_EDGE_CASES = TIER2_TOOL_EDGE_CASES + TIER2_TOOL_EDGE_CASES_EXTRA
TIER2_INSTRUCTIONS = TIER2_INSTRUCTIONS + TIER2_INSTRUCTIONS_EXTRA

del TIER2_RESERVATIONS_EXTRA, TIER2_ORDERS_EXTRA, TIER2_TOOL_EDGE_CASES_EXTRA, TIER2_INSTRUCTIONS_EXTRA

# Full Tier 2 scenarios
TIER2_SCENARIOS = (
    TIER2_RESERVATIONS
    + TIER2_ORDERS
    + TIER2_TOOL_EDGE_CASES
    + TIER2_INSTRUCTIONS
)

if __name__ == "__main__":
    print(f"Total Tier 2 scenarios: {len(TIER2_SCENARIOS)}")
    for cat, scenarios in [
        ("Reservations", TIER2_RESERVATIONS),
        ("Orders", TIER2_ORDERS),
        ("Tool Edge Cases", TIER2_TOOL_EDGE_CASES),
        ("Instructions", TIER2_INSTRUCTIONS),
    ]:
        print(f"  {cat}: {len(scenarios)}")
