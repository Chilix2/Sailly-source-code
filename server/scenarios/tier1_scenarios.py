"""
Tier 1 Scenarios -- Phase 1 (60 total, +50%)

Text-mode Gemini scenarios for greeting, FAQ, handoff triggers, and edge cases.
All run through GoogleVertexLLMService with tier1_prompt, temperature=0, N=3 runs.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScenarioTurn:
    user_utterance: str
    expected_keywords: list[str] = field(default_factory=list)
    must_call_tool: Optional[str] = None
    must_not_call_tool: Optional[str] = None
    latency_budget_ms: int = 3000
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
    quality_dimensions: list[str] = field(default_factory=lambda: ["task", "language", "instruction", "latency", "audio_quality"])
    noise_variant: str = "clean"
    n_runs: int = 3
    seed: int = 42
    persona: Optional[str] = None  # "neutral"|"angry"|"impatient"|"sleepy"|"accent"|"hard_to_hear"|"chaos"|"elderly"


# Category 1: Greeting variants (10)
TIER1_GREETING_VARIANTS = [
    AudioScenario(
        id="t1-greeting-01",
        phase="tier1",
        category="greeting",
        description="Simple greeting",
        turns=[
            ScenarioTurn(
                user_utterance="Hallo",
                expected_keywords=["willkommen", "doboo", "helfen", "sally"],
            )
        ],
        expected_tools=[],
        forbidden_content=[],
    ),
    AudioScenario(
        id="t1-greeting-02",
        phase="tier1",
        category="greeting",
        description="Formal greeting",
        turns=[
            ScenarioTurn(
                user_utterance="Guten Tag",
                expected_keywords=["willkommen", "doboo", "helfen"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-greeting-03",
        phase="tier1",
        category="greeting",
        description="Dialect greeting Servus",
        turns=[
            ScenarioTurn(
                user_utterance="Servus",
                expected_keywords=["willkommen", "helfen"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-greeting-04",
        phase="tier1",
        category="greeting",
        description="Greeting after silence",
        turns=[
            ScenarioTurn(user_utterance="", expected_keywords=[]),
            ScenarioTurn(
                user_utterance="Hallo",
                expected_keywords=["willkommen"],
            ),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-greeting-05",
        phase="tier1",
        category="greeting",
        description="Immediate order intent with greeting",
        turns=[
            ScenarioTurn(
                user_utterance="Hallo ich haette gerne bestellen",
                expected_keywords=["transfer", "ordering", "bestellen"],
                must_call_tool="transfer_to_ordering",
            )
        ],
        expected_tools=["transfer_to_ordering"],
    ),
    AudioScenario(
        id="t1-greeting-06",
        phase="tier1",
        category="greeting",
        description="Caller self-introduces",
        turns=[
            ScenarioTurn(
                user_utterance="Ich bin Thomas Mueller",
                expected_keywords=["thomas", "mueller", "helfen"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-greeting-07",
        phase="tier1",
        category="greeting",
        description="Greeting with FAQ",
        turns=[
            ScenarioTurn(
                user_utterance="Hallo seid ihr geoeffnet",
                expected_keywords=["oeffnung", "stunden", "montag"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-greeting-08",
        phase="tier1",
        category="greeting",
        description="Greeting with complaint",
        turns=[
            ScenarioTurn(
                user_utterance="Hallo ich hatte ein Problem mit meiner letzten Bestellung",
                expected_keywords=["verstaendnis", "leid", "empathie"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-greeting-09",
        phase="tier1",
        category="greeting",
        description="English-only greeting",
        turns=[
            ScenarioTurn(
                user_utterance="Hello is this DOBOO",
                expected_keywords=["deutsch", "german"],
            )
        ],
        expected_tools=[],
        forbidden_content=["english", "english only"],
    ),
    AudioScenario(
        id="t1-greeting-10",
        phase="tier1",
        category="greeting",
        description="Wrong number inquiry",
        turns=[
            ScenarioTurn(
                user_utterance="Bin ich bei der Pizzeria Napoli",
                expected_keywords=["doboo", "not", "different"],
            )
        ],
        expected_tools=[],
    ),
]

# Additional greeting variants (5 more)
TIER1_GREETING_VARIANTS_EXTRA = [
    AudioScenario(
        id="t1-greeting-11",
        phase="tier1",
        category="greeting",
        description="Casual morning greeting",
        turns=[
            ScenarioTurn(
                user_utterance="Guten Morgen, ich habe eine Frage",
                expected_keywords=["willkommen", "helfen"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-greeting-12",
        phase="tier1",
        category="greeting",
        description="Evening greeting",
        turns=[
            ScenarioTurn(
                user_utterance="Guten Abend, sind Sie noch offen",
                expected_keywords=["ja", "offen", "helfen"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-greeting-13",
        phase="tier1",
        category="greeting",
        description="Greeting with context",
        turns=[
            ScenarioTurn(
                user_utterance="Hallo, ich bin ein neuer Kunde",
                expected_keywords=["willkommen", "doboo"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-greeting-14",
        phase="tier1",
        category="greeting",
        description="Greeting with name",
        turns=[
            ScenarioTurn(
                user_utterance="Hallo, mein Name ist Schmidt",
                expected_keywords=["willkommen", "schmidt"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-greeting-15",
        phase="tier1",
        category="greeting",
        description="Brief greeting pause",
        turns=[
            ScenarioTurn(
                user_utterance="Hallo... bin ich verbunden",
                expected_keywords=["ja", "verbunden", "doboo"],
            )
        ],
        expected_tools=[],
    ),
]

# Combine all greetings
TIER1_GREETING_ALL = TIER1_GREETING_VARIANTS + TIER1_GREETING_VARIANTS_EXTRA

TIER1_GREETING_VARIANTS = TIER1_GREETING_ALL
del TIER1_GREETING_VARIANTS_EXTRA
del TIER1_GREETING_ALL

# Now continue with original FAQ list (add 5 more)
TIER1_FAQ_QUESTIONS = [
    AudioScenario(
        id="t1-faq-01",
        phase="tier1",
        category="faq",
        description="Opening hours",
        turns=[
            ScenarioTurn(
                user_utterance="Wann habt ihr geoeffnet",
                expected_keywords=["oeffnungszeiten", "montag", "ruhetag"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-faq-02",
        phase="tier1",
        category="faq",
        description="Address and parking",
        turns=[
            ScenarioTurn(
                user_utterance="Wo seid ihr und gibt es Parkplaetze",
                expected_keywords=["friedrichstrasse", "parkplatz"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-faq-03",
        phase="tier1",
        category="faq",
        description="Cuisine type",
        turns=[
            ScenarioTurn(
                user_utterance="Was fuer Speisen habt ihr",
                expected_keywords=["koreanisch", "japanisch", "sushi"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-faq-04",
        phase="tier1",
        category="faq",
        description="Price range",
        turns=[
            ScenarioTurn(
                user_utterance="Wie teuer ist das Restaurant",
                expected_keywords=["tier2", "menu", "nicht", "erfunden"],
            )
        ],
        expected_tools=[],
        forbidden_content=["12.50", "15 euro", "20 euro"],
    ),
    AudioScenario(
        id="t1-faq-05",
        phase="tier1",
        category="faq",
        description="Allergen info",
        turns=[
            ScenarioTurn(
                user_utterance="Habt ihr vegetarische Optionen",
                expected_keywords=["tier2", "allergen", "transfer"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-faq-06",
        phase="tier1",
        category="faq",
        description="Delivery radius",
        turns=[
            ScenarioTurn(
                user_utterance="Liefert ihr zu mir",
                expected_keywords=["lieferung", "adresse"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-faq-07",
        phase="tier1",
        category="faq",
        description="Takeaway wait time",
        turns=[
            ScenarioTurn(
                user_utterance="Wie lange dauert eine Takeaway-Bestellung",
                expected_keywords=["wartezeit", "tier2"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-faq-08",
        phase="tier1",
        category="faq",
        description="Reservations availability",
        turns=[
            ScenarioTurn(
                user_utterance="Nehmt ihr Reservierungen an",
                expected_keywords=["reservierungen", "ja", "gerne"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-faq-09",
        phase="tier1",
        category="faq",
        description="Contact details",
        turns=[
            ScenarioTurn(
                user_utterance="Wie kann ich euch erreichen",
                expected_keywords=["telefon", "adresse"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-faq-10",
        phase="tier1",
        category="faq",
        description="Terrace seating",
        turns=[
            ScenarioTurn(
                user_utterance="Habt ihr eine Terrasse",
                expected_keywords=["terrasse", "draussen"],
            )
        ],
        expected_tools=[],
    ),
]

# Additional FAQ questions (5 more)
TIER1_FAQ_EXTRA = [
    AudioScenario(
        id="t1-faq-11",
        phase="tier1",
        category="faq",
        description="Dietary restrictions inquiry",
        turns=[
            ScenarioTurn(
                user_utterance="Habt ihr auch vegetarische Optionen",
                expected_keywords=["vegetarisch", "vegan", "menu"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-faq-12",
        phase="tier1",
        category="faq",
        description="Allergy information request",
        turns=[
            ScenarioTurn(
                user_utterance="Können Sie mir Informationen zu Allergenen geben",
                expected_keywords=["allergen", "information", "menu"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-faq-13",
        phase="tier1",
        category="faq",
        description="Parking availability",
        turns=[
            ScenarioTurn(
                user_utterance="Ist Parken bei euch kostenlos",
                expected_keywords=["parken", "kosten", "verfuegbar"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-faq-14",
        phase="tier1",
        category="faq",
        description="Children menu inquiry",
        turns=[
            ScenarioTurn(
                user_utterance="Habt ihr ein Kindermenü",
                expected_keywords=["kinder", "menu", "klein"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-faq-15",
        phase="tier1",
        category="faq",
        description="Loyalty program question",
        turns=[
            ScenarioTurn(
                user_utterance="Habt ihr ein Treueprogramm oder Rabatte",
                expected_keywords=["treue", "rabatt", "angebot"],
            )
        ],
        expected_tools=[],
    ),
]

# Combine all FAQ
TIER1_FAQ_ALL = TIER1_FAQ_QUESTIONS + TIER1_FAQ_EXTRA
TIER1_FAQ_QUESTIONS = TIER1_FAQ_ALL
del TIER1_FAQ_EXTRA
del TIER1_FAQ_ALL

# Category 3: Handoff triggers (10 + 5 = 15)
TIER1_HANDOFF_TRIGGERS = [
    AudioScenario(
        id="t1-handoff-01",
        phase="tier1",
        category="handoff",
        description="Order request",
        turns=[
            ScenarioTurn(
                user_utterance="Ich moechte bestellen",
                expected_keywords=["transfer", "ordering"],
                must_call_tool="transfer_to_ordering",
            )
        ],
        expected_tools=["transfer_to_ordering"],
    ),
    AudioScenario(
        id="t1-handoff-02",
        phase="tier1",
        category="handoff",
        description="Reservation request",
        turns=[
            ScenarioTurn(
                user_utterance="Ich moechte reservieren",
                expected_keywords=["transfer", "ordering"],
                must_call_tool="transfer_to_ordering",
            )
        ],
        expected_tools=["transfer_to_ordering"],
    ),
    AudioScenario(
        id="t1-handoff-03",
        phase="tier1",
        category="handoff",
        description="Table for tonight",
        turns=[
            ScenarioTurn(
                user_utterance="Einen Tisch fuer heute Abend",
                expected_keywords=["transfer", "reservation"],
                must_call_tool="transfer_to_ordering",
            )
        ],
        expected_tools=["transfer_to_ordering"],
    ),
    AudioScenario(
        id="t1-handoff-04",
        phase="tier1",
        category="handoff",
        description="Takeaway order",
        turns=[
            ScenarioTurn(
                user_utterance="Kann ich etwas zum Abholen bestellen",
                expected_keywords=["transfer", "order"],
                must_call_tool="transfer_to_ordering",
            )
        ],
        expected_tools=["transfer_to_ordering"],
    ),
    AudioScenario(
        id="t1-handoff-05",
        phase="tier1",
        category="handoff",
        description="Delivery order",
        turns=[
            ScenarioTurn(
                user_utterance="Lieferung nach Hause",
                expected_keywords=["transfer", "order"],
                must_call_tool="transfer_to_ordering",
            )
        ],
        expected_tools=["transfer_to_ordering"],
    ),
    AudioScenario(
        id="t1-handoff-06",
        phase="tier1",
        category="handoff",
        description="Takeaway request",
        turns=[
            ScenarioTurn(
                user_utterance="Takeaway bitte",
                expected_keywords=["transfer", "order"],
                must_call_tool="transfer_to_ordering",
            )
        ],
        expected_tools=["transfer_to_ordering"],
    ),
    AudioScenario(
        id="t1-handoff-07",
        phase="tier1",
        category="handoff",
        description="Specific dish order",
        turns=[
            ScenarioTurn(
                user_utterance="Ich nehme das Bibimbap",
                expected_keywords=["transfer", "order"],
                must_call_tool="transfer_to_ordering",
            )
        ],
        expected_tools=["transfer_to_ordering"],
    ),
    AudioScenario(
        id="t1-handoff-08",
        phase="tier1",
        category="handoff",
        description="Implicit reservation",
        turns=[
            ScenarioTurn(
                user_utterance="Fuer 4 Personen naechste Woche",
                expected_keywords=["transfer", "reservation"],
                must_call_tool="transfer_to_ordering",
            )
        ],
        expected_tools=["transfer_to_ordering"],
    ),
    AudioScenario(
        id="t1-handoff-09",
        phase="tier1",
        category="handoff",
        description="Dual intent FAQ then handoff",
        turns=[
            ScenarioTurn(
                user_utterance="Habt ihr geoeffnet",
                expected_keywords=["oeffnungszeiten"],
            ),
            ScenarioTurn(
                user_utterance="Und ich moechte dann einen Tisch reservieren",
                expected_keywords=["transfer", "reservation"],
                must_call_tool="transfer_to_ordering",
            ),
        ],
        expected_tools=["transfer_to_ordering"],
    ),
    AudioScenario(
        id="t1-handoff-10",
        phase="tier1",
        category="handoff",
        description="Delayed handoff after FAQ",
        turns=[
            ScenarioTurn(user_utterance="Wann habt ihr auf", expected_keywords=["oeffnungszeiten"]),
            ScenarioTurn(user_utterance="Und Preise", expected_keywords=["tier2"]),
            ScenarioTurn(user_utterance="Ach uebrigens ich moechte bestellen", expected_keywords=["transfer"], must_call_tool="transfer_to_ordering"),
        ],
        expected_tools=["transfer_to_ordering"],
    ),
]

# Additional handoff triggers (5 more)
TIER1_HANDOFF_EXTRA = [
    AudioScenario(
        id="t1-handoff-11",
        phase="tier1",
        category="handoff",
        description="Reservation complexity handoff",
        turns=[
            ScenarioTurn(
                user_utterance="Ich brauche eine komplexe Reservierung mit besonderen Wünschen",
                expected_keywords=["reservierung", "komplexe", "tier2"],
                must_call_tool="transfer_to_tier2",
            )
        ],
        expected_tools=["transfer_to_tier2"],
    ),
    AudioScenario(
        id="t1-handoff-12",
        phase="tier1",
        category="handoff",
        description="Event catering inquiry handoff",
        turns=[
            ScenarioTurn(
                user_utterance="Wir planen eine Veranstaltung, könnt ihr Catering machen",
                expected_keywords=["veranstaltung", "catering", "tier2"],
                must_call_tool="transfer_to_tier2",
            )
        ],
        expected_tools=["transfer_to_tier2"],
    ),
    AudioScenario(
        id="t1-handoff-13",
        phase="tier1",
        category="handoff",
        description="Private event request",
        turns=[
            ScenarioTurn(
                user_utterance="Könnt ihr einen privaten Raum für eine Firmenfeier zur Verfügung stellen",
                expected_keywords=["privat", "firmen", "tier2"],
                must_call_tool="transfer_to_tier2",
            )
        ],
        expected_tools=["transfer_to_tier2"],
    ),
    AudioScenario(
        id="t1-handoff-14",
        phase="tier1",
        category="handoff",
        description="Technical support transfer",
        turns=[
            ScenarioTurn(
                user_utterance="Ich habe ein technisches Problem mit der Bestellung",
                expected_keywords=["technisch", "problem", "support"],
                must_call_tool="transfer_to_human",
            )
        ],
        expected_tools=["transfer_to_human"],
    ),
    AudioScenario(
        id="t1-handoff-15",
        phase="tier1",
        category="handoff",
        description="Complaint escalation",
        turns=[
            ScenarioTurn(
                user_utterance="Ich möchte eine Beschwerde einreichen",
                expected_keywords=["beschwerde", "manager", "tier2"],
                must_call_tool="transfer_to_human",
            )
        ],
        expected_tools=["transfer_to_human"],
    ),
]

# Combine all handoff
TIER1_HANDOFF_ALL = TIER1_HANDOFF_TRIGGERS + TIER1_HANDOFF_EXTRA
TIER1_HANDOFF_TRIGGERS = TIER1_HANDOFF_ALL
del TIER1_HANDOFF_EXTRA
del TIER1_HANDOFF_ALL

# Category 4: Edge cases (10 + 5 = 15) -- EXCLUDED FROM PHASE GATE
TIER1_EDGE_CASES = [
    AudioScenario(
        id="t1-edge-01",
        phase="tier1",
        category="edge_case",
        description="Off-topic weather question",
        turns=[
            ScenarioTurn(
                user_utterance="Wie ist das Wetter",
                expected_keywords=["restaurant", "doboo", "redirect"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-edge-02",
        phase="tier1",
        category="edge_case",
        description="Aggressive/rude caller",
        turns=[
            ScenarioTurn(
                user_utterance="Das ist eine Abzocke",
                expected_keywords=["verstaendnis", "empathie", "helfen"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-edge-03",
        phase="tier1",
        category="edge_case",
        description="English-only caller",
        turns=[
            ScenarioTurn(
                user_utterance="Can you help me in English",
                expected_keywords=["deutsch", "german"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-edge-04",
        phase="tier1",
        category="edge_case",
        description="Long monologue",
        turns=[
            ScenarioTurn(
                user_utterance="Also ich bin in der Gegend und dachte ich schau mal vorbei aber ich weiss nicht ob ich alleine komme oder mit Freunden und ausserdem bin ich nicht sicher ob ich Fleisch essen kann",
                expected_keywords=["verstanden", "intent"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-edge-05",
        phase="tier1",
        category="edge_case",
        description="Self-introduction before handoff",
        turns=[
            ScenarioTurn(user_utterance="Ich bin Max Schmidt"),
            ScenarioTurn(
                user_utterance="Ich moechte einen Tisch reservieren",
                expected_keywords=["max", "schmidt", "transfer"],
                must_call_tool="transfer_to_ordering",
            ),
        ],
        expected_tools=["transfer_to_ordering"],
    ),
    AudioScenario(
        id="t1-edge-06",
        phase="tier1",
        category="edge_case",
        description="AI identity question",
        turns=[
            ScenarioTurn(
                user_utterance="Bist du eine KI",
                expected_keywords=["ja", "ki", "kuenstlich"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-edge-07",
        phase="tier1",
        category="edge_case",
        description="Human request in Tier 1",
        turns=[
            ScenarioTurn(
                user_utterance="Ich moechte mit einer echten Person sprechen",
                expected_keywords=["tier2", "verbinden"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-edge-08",
        phase="tier1",
        category="edge_case",
        description="Empty utterance",
        turns=[
            ScenarioTurn(
                user_utterance="",
                expected_keywords=["verstaendnis", "frage"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-edge-09",
        phase="tier1",
        category="edge_case",
        description="Competitor mention",
        turns=[
            ScenarioTurn(
                user_utterance="Bei McDonalds ist das viel billiger",
                expected_keywords=["qualitaet", "doboo"],
            )
        ],
        expected_tools=[],
        forbidden_content=["zustimm", "recht"],
    ),
    AudioScenario(
        id="t1-edge-10",
        phase="tier1",
        category="edge_case",
        description="Code-switch English food term",
        turns=[
            ScenarioTurn(
                user_utterance="Ich moechte Chicken Wings bestellen",
                expected_keywords=["wings", "transfer"],
                must_call_tool="transfer_to_ordering",
            )
        ],
        expected_tools=["transfer_to_ordering"],
    ),
]

# Additional edge cases (5 more)
TIER1_EDGE_EXTRA = [
    AudioScenario(
        id="t1-edge-11",
        phase="tier1",
        category="edge_case",
        description="Rapid consecutive questions",
        turns=[
            ScenarioTurn(
                user_utterance="Öffnungszeiten? Preise? Adresse? Alles gleichzeitig",
                expected_keywords=["offen", "preis", "adresse"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-edge-12",
        phase="tier1",
        category="edge_case",
        description="Heavy background noise scenario",
        turns=[
            ScenarioTurn(
                user_utterance="Hallo, KANNST DU MICH HÖRENNN",
                expected_keywords=["ja", "höre"],
            )
        ],
        expected_tools=[],
        noise_variant="heavy_traffic",
    ),
    AudioScenario(
        id="t1-edge-13",
        phase="tier1",
        category="edge_case",
        description="Accented German speaker",
        turns=[
            ScenarioTurn(
                user_utterance="Hallooo, ich hätte gerne Informationen",
                expected_keywords=["informationen", "doboo"],
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-edge-14",
        phase="tier1",
        category="edge_case",
        description="Elderly caller very slow",
        turns=[
            ScenarioTurn(
                user_utterance="Hallo...äh...ich...ich möchte",
                expected_keywords=["helfen", "geduld"],
                latency_budget_ms=5000,
            )
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t1-edge-15",
        phase="tier1",
        category="edge_case",
        description="Conflicting requests",
        turns=[
            ScenarioTurn(
                user_utterance="Ich will kein Kimchi aber Bibimbap mit viel Kimchi",
                expected_keywords=["kimchi", "bibimbap"],
            )
        ],
        expected_tools=[],
    ),
]

# Combine all edge cases
TIER1_EDGE_ALL = TIER1_EDGE_CASES + TIER1_EDGE_EXTRA
TIER1_EDGE_CASES = TIER1_EDGE_ALL
del TIER1_EDGE_EXTRA
del TIER1_EDGE_ALL

# Full Tier 1 scenarios list
TIER1_SCENARIOS = (
    TIER1_GREETING_VARIANTS
    + TIER1_FAQ_QUESTIONS
    + TIER1_HANDOFF_TRIGGERS
    + TIER1_EDGE_CASES
)

# Phase gate scenarios: only greeting + FAQ + handoff (30 total, exclude edge cases)
TIER1_CORE_SCENARIOS = (
    TIER1_GREETING_VARIANTS
    + TIER1_FAQ_QUESTIONS
    + TIER1_HANDOFF_TRIGGERS
)

if __name__ == "__main__":
    print(f"Total Tier 1 scenarios: {len(TIER1_SCENARIOS)}")
    print(f"Core scenarios (for phase gate): {len(TIER1_CORE_SCENARIOS)}")
    for cat, scenarios in [
        ("Greeting", TIER1_GREETING_VARIANTS),
        ("FAQ", TIER1_FAQ_QUESTIONS),
        ("Handoff", TIER1_HANDOFF_TRIGGERS),
        ("Edge Case", TIER1_EDGE_CASES),
    ]:
        print(f"  {cat}: {len(scenarios)}")
