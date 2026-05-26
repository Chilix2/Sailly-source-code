"""
Tier Switch Scenarios -- Phase 3 (40 total)

Tests Tier 2 behavior when callers ask Tier-1-type questions, try to go back, or create ambiguous routing.
Includes FAQ-in-Tier2 (20), Re-handoff/back-transfer (10), Ambiguous routing (10).
"""

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


# Category A: FAQ-in-Tier2 (20)
TIER3_FAQ_IN_TIER2 = [
    AudioScenario(
        id="t3-faq-01",
        phase="switch",
        category="faq_in_tier2",
        description="Mid-order: opening hours",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte ein Bibimbap"),
            ScenarioTurn(user_utterance="Wann habt ihr eigentlich auf", expected_keywords=["oeffnungszeit"]),
            ScenarioTurn(user_utterance="OK und ein Bulgogi auch"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t3-faq-02",
        phase="switch",
        category="faq_in_tier2",
        description="Where are we",
        turns=[
            ScenarioTurn(user_utterance="Wo seid ihr", expected_keywords=["friedrichstrasse", "bonn"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-faq-03",
        phase="switch",
        category="faq_in_tier2",
        description="Tomorrow open hours",
        turns=[
            ScenarioTurn(user_utterance="Seid ihr morgen auch auf", expected_keywords=["ja", "auf"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-faq-04",
        phase="switch",
        category="faq_in_tier2",
        description="Parking question",
        turns=[
            ScenarioTurn(user_utterance="Gibt es Parkplaetze", expected_keywords=["parkplatz"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-faq-05",
        phase="switch",
        category="faq_in_tier2",
        description="Can we look inside",
        turns=[
            ScenarioTurn(user_utterance="Kann ich direkt reinschauen", expected_keywords=["ja", "willkommen"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-faq-06",
        phase="switch",
        category="faq_in_tier2",
        description="WiFi availability",
        turns=[
            ScenarioTurn(user_utterance="Habt ihr WLAN", expected_keywords=["weiss", "nicht", "vor", "ort"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-faq-07",
        phase="switch",
        category="faq_in_tier2",
        description="Accessibility info",
        turns=[
            ScenarioTurn(user_utterance="Ist das Restaurant barrierefrei", expected_keywords=["rollstuhl"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-faq-08",
        phase="switch",
        category="faq_in_tier2",
        description="Chef information",
        turns=[
            ScenarioTurn(user_utterance="Wie heisst euer Chef", expected_keywords=["weiss", "nicht"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-faq-09",
        phase="switch",
        category="faq_in_tier2",
        description="Hours mid-delivery",
        turns=[
            ScenarioTurn(user_utterance="Ein Bibimbap zur Lieferung"),
            ScenarioTurn(user_utterance="Wie lange macht ihr noch auf", expected_keywords=["oeffnungszeit"]),
            ScenarioTurn(user_utterance="OK bestellen wir trotzdem"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t3-faq-10",
        phase="switch",
        category="faq_in_tier2",
        description="Address mid-reservation",
        turns=[
            ScenarioTurn(user_utterance="Fuer zwei Personen"),
            ScenarioTurn(user_utterance="Wo genau seid ihr nochmal", expected_keywords=["friedrichstrasse"]),
            ScenarioTurn(user_utterance="OK reservieren wir"),
        ],
        expected_tools=["create_reservation"],
    ),
    AudioScenario(
        id="t3-faq-11",
        phase="switch",
        category="faq_in_tier2",
        description="FAQ interleaved with name",
        turns=[
            ScenarioTurn(user_utterance="Ich bin Martin"),
            ScenarioTurn(user_utterance="Gibt es auch vegetarisch", expected_keywords=["ja", "bibimbap"]),
            ScenarioTurn(user_utterance="Ein Bibimbap dann"),
        ],
        expected_tools=["update_state", "get_menu", "create_order"],
    ),
    AudioScenario(
        id="t3-faq-12",
        phase="switch",
        category="faq_in_tier2",
        description="FAQ after tool error",
        turns=[
            ScenarioTurn(user_utterance="Fuer tausend Personen", expected_keywords=["entschuldigung"]),
            ScenarioTurn(user_utterance="Wie teuer ist das Restaurant", expected_keywords=["menu"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-faq-13",
        phase="switch",
        category="faq_in_tier2",
        description="KI confirmation in Tier 2",
        turns=[
            ScenarioTurn(user_utterance="Bist du eine KI", expected_keywords=["ja", "sally"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-faq-14",
        phase="switch",
        category="faq_in_tier2",
        description="Same person Sally continuity",
        turns=[
            ScenarioTurn(user_utterance="Ich dachte ich spreche mit Sally", expected_keywords=["ja", "sally"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-faq-15",
        phase="switch",
        category="faq_in_tier2",
        description="Topic switch during multi-intent",
        turns=[
            ScenarioTurn(user_utterance="Speisekarte und Reservierung"),
            ScenarioTurn(user_utterance="Wie viele Tische habt ihr", expected_keywords=["kapazitaet"]),
            ScenarioTurn(user_utterance="Fuer zwei Samstag"),
        ],
        expected_tools=["get_menu", "create_reservation"],
    ),
    AudioScenario(
        id="t3-faq-16",
        phase="switch",
        category="faq_in_tier2",
        description="FAQ dialect mid-order",
        turns=[
            ScenarioTurn(user_utterance="I mog bestellen"),
            ScenarioTurn(user_utterance="Wann macht's z'uas auf", expected_keywords=["oeffnungszeit"]),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t3-faq-17",
        phase="switch",
        category="faq_in_tier2",
        description="FAQ English mid-German",
        turns=[
            ScenarioTurn(user_utterance="Ein Bibimbap"),
            ScenarioTurn(user_utterance="What are your opening hours", expected_keywords=["deutsch"]),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t3-faq-18",
        phase="switch",
        category="faq_in_tier2",
        description="Terrace and weather",
        turns=[
            ScenarioTurn(user_utterance="Habt ihr eine Terrasse"),
            ScenarioTurn(user_utterance="Wie ist das Wetter", expected_keywords=["wetter"]),
            ScenarioTurn(user_utterance="OK Terrasse fuer zwei"),
        ],
        expected_tools=["get_weather", "create_reservation"],
    ),
    AudioScenario(
        id="t3-faq-19",
        phase="switch",
        category="faq_in_tier2",
        description="Price range mid-order",
        turns=[
            ScenarioTurn(user_utterance="Wie viel kostet das Menu", expected_keywords=["speisekarte", "menu"]),
            ScenarioTurn(user_utterance="Ein Bibimbap"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t3-faq-20",
        phase="switch",
        category="faq_in_tier2",
        description="Restaurant info noise",
        turns=[
            ScenarioTurn(user_utterance="Seid ihr neu hier", expected_keywords=["doboo", "restaurant"]),
        ],
        expected_tools=[],
        noise_variant="restaurant",
    ),
]

# Category B: Re-handoff / back-transfer (10)
TIER3_REHANDOFF = [
    AudioScenario(
        id="t3-rehand-01",
        phase="switch",
        category="rehandoff",
        description="Request to speak with person",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte mit einer echten Person sprechen", expected_keywords=["mensch", "transfer"]),
        ],
        expected_tools=["transfer_to_human"],
    ),
    AudioScenario(
        id="t3-rehand-02",
        phase="switch",
        category="rehandoff",
        description="Give me the reception",
        turns=[
            ScenarioTurn(user_utterance="Gebt mir nochmal den Empfang", expected_keywords=["mensch"]),
        ],
        expected_tools=["transfer_to_human"],
    ),
    AudioScenario(
        id="t3-rehand-03",
        phase="switch",
        category="rehandoff",
        description="Too complicated, will call back",
        turns=[
            ScenarioTurn(user_utterance="Das ist zu kompliziert ich rufe nochmal an", expected_keywords=["verstanden", "auf", "wiedersehen"]),
        ],
        expected_tools=["end_call"],
    ),
    AudioScenario(
        id="t3-rehand-04",
        phase="switch",
        category="rehandoff",
        description="Silence 45s escalation",
        turns=[
            ScenarioTurn(user_utterance="Ein Bibimbap"),
            ScenarioTurn(user_utterance="", expected_keywords=["stille", "callback"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-rehand-05",
        phase="switch",
        category="rehandoff",
        description="Technical error recovery",
        turns=[
            ScenarioTurn(user_utterance="Ein Bibimbap", expected_keywords=["technisch", "problem"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-rehand-06",
        phase="switch",
        category="rehandoff",
        description="Returning with context",
        turns=[
            ScenarioTurn(user_utterance="Ich bin Maria"),
            ScenarioTurn(user_utterance="Ein Bibimbap bitte"),
        ],
        expected_tools=["update_state", "get_menu", "create_order"],
    ),
    AudioScenario(
        id="t3-rehand-07",
        phase="switch",
        category="rehandoff",
        description="No duplicate handoff",
        turns=[
            ScenarioTurn(user_utterance="Bestellen"),
            ScenarioTurn(user_utterance="Nochmal bestellen", expected_keywords=["bereits"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-rehand-08",
        phase="switch",
        category="rehandoff",
        description="Human transfer not answered",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte mit jemand sprechen"),
        ],
        expected_tools=["transfer_to_human"],
    ),
    AudioScenario(
        id="t3-rehand-09",
        phase="switch",
        category="rehandoff",
        description="Long wait empathy",
        turns=[
            ScenarioTurn(user_utterance="Ich bin schon seit 5 Minuten dran", expected_keywords=["verstaendnis", "sorry"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-rehand-10",
        phase="switch",
        category="rehandoff",
        description="Transfer mid-order with context",
        turns=[
            ScenarioTurn(user_utterance="Ein Bibimbap und ein Bulgogi"),
            ScenarioTurn(user_utterance="Ich moechte jetzt mit einer Person sprechen"),
        ],
        expected_tools=["transfer_to_human"],
    ),
]

# Category C: Ambiguous routing (10)
TIER3_AMBIGUOUS_ROUTING = [
    AudioScenario(
        id="t3-ambig-01",
        phase="switch",
        category="ambiguous_routing",
        description="Caller mentions Sally from before",
        turns=[
            ScenarioTurn(user_utterance="Ich war gerade bei Sally", expected_keywords=["ja", "weiter"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-ambig-02",
        phase="switch",
        category="ambiguous_routing",
        description="Voice change Tier1 to Tier2",
        turns=[
            ScenarioTurn(user_utterance="Eure Stimme klingt anders", expected_keywords=["sally", "service"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-ambig-03",
        phase="switch",
        category="ambiguous_routing",
        description="Repeat same order intent",
        turns=[
            ScenarioTurn(user_utterance="Ich will bestellen", expected_keywords=["weiter"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-ambig-04",
        phase="switch",
        category="ambiguous_routing",
        description="Interrupts handoff TwiML",
        turns=[
            ScenarioTurn(user_utterance="Warte nein", expected_keywords=["verstanden", "weiter"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-ambig-05",
        phase="switch",
        category="ambiguous_routing",
        description="Very fast handoff coherence",
        turns=[
            ScenarioTurn(user_utterance="Bestellen", expected_keywords=["gut", "speisekarte"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-ambig-06",
        phase="switch",
        category="ambiguous_routing",
        description="Missing caller_context",
        turns=[
            ScenarioTurn(user_utterance="Was kann ich tun", expected_keywords=["help", "bestellen"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-ambig-07",
        phase="switch",
        category="ambiguous_routing",
        description="caller_context has name",
        turns=[
            ScenarioTurn(user_utterance="Ein Bibimbap", expected_keywords=["name", "caller"]),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
    AudioScenario(
        id="t3-ambig-08",
        phase="switch",
        category="ambiguous_routing",
        description="Reason order but wants reservation",
        turns=[
            ScenarioTurn(user_utterance="Ich moechte lieber reservieren", expected_keywords=["reservation"]),
        ],
        expected_tools=["create_reservation"],
    ),
    AudioScenario(
        id="t3-ambig-09",
        phase="switch",
        category="ambiguous_routing",
        description="Ambiguous intent clarification",
        turns=[
            ScenarioTurn(user_utterance="Ein Tisch oder nein lieber zum Abholen", expected_keywords=["was", "welche"]),
        ],
        expected_tools=[],
    ),
    AudioScenario(
        id="t3-ambig-10",
        phase="switch",
        category="ambiguous_routing",
        description="Handoff during Tier1 FAQ answer",
        turns=[
            ScenarioTurn(user_utterance="Wann habt ihr auf"),
            ScenarioTurn(user_utterance="Und ich moechte jetzt bestellen"),
        ],
        expected_tools=["get_menu", "create_order"],
    ),
]

# ─── SCENARIO EXPANSION (+50% for Phase 3) ────────────────────────────────────────────────
# Generate additional tier-switch scenarios to reach 60 total (20 original → 30 per category)

TIER3_FAQ_EXTRA = [
    AudioScenario(
        id=f"t3-faq-{11+i}",
        phase="switch",
        category="faq_in_tier2",
        description=f"Additional FAQ during ordering {i}",
        turns=[
            ScenarioTurn(user_utterance=f"Speisekarte"), 
            ScenarioTurn(user_utterance=f"Öffnungszeiten" if i%2 else "Preise"),
            ScenarioTurn(user_utterance=f"Ich möchte {'Bibimbap' if i%2 else 'Bulgogi'}"),
        ],
        expected_tools=["get_menu", "create_order"],
    )
    for i in range(7)  # 7 + 10 = 17, but we only need ~6 more per category
]

TIER3_REHANDOFF_EXTRA = [
    AudioScenario(
        id=f"t3-rehnd-{11+i}",
        phase="switch",
        category="rehandoff",
        description=f"Re-handoff scenario {i}",
        turns=[
            ScenarioTurn(user_utterance="Öffnungszeiten"),
            ScenarioTurn(user_utterance="Ich möchte reservieren"),
            ScenarioTurn(user_utterance=f"{'Für vier' if i%2 else 'Für zwei'} Personen"),
        ],
        expected_tools=["create_reservation"],
    )
    for i in range(7)
]

TIER3_AMBIGUOUS_EXTRA = [
    AudioScenario(
        id=f"t3-ambig-{11+i}",
        phase="switch",
        category="ambiguous_routing",
        description=f"Complex routing case {i}",
        turns=[
            ScenarioTurn(user_utterance="Hallo Speisekarte"),
            ScenarioTurn(user_utterance=f"{'Und reservieren' if i%2 else 'Und bestellen'}"),
        ],
        expected_tools=["create_reservation"] if i%2 else ["get_menu", "create_order"],
    )
    for i in range(6)
]

# Expand all categories
TIER3_FAQ_IN_TIER2 = TIER3_FAQ_IN_TIER2 + TIER3_FAQ_EXTRA
TIER3_REHANDOFF = TIER3_REHANDOFF + TIER3_REHANDOFF_EXTRA
TIER3_AMBIGUOUS_ROUTING = TIER3_AMBIGUOUS_ROUTING + TIER3_AMBIGUOUS_EXTRA

del TIER3_FAQ_EXTRA, TIER3_REHANDOFF_EXTRA, TIER3_AMBIGUOUS_EXTRA

# Full Tier Switch scenarios
TIER3_SCENARIOS = (
    TIER3_FAQ_IN_TIER2
    + TIER3_REHANDOFF
    + TIER3_AMBIGUOUS_ROUTING
)

if __name__ == "__main__":
    print(f"Total Tier Switch scenarios: {len(TIER3_SCENARIOS)}")
    for cat, scenarios in [
        ("FAQ-in-Tier2", TIER3_FAQ_IN_TIER2),
        ("Re-handoff", TIER3_REHANDOFF),
        ("Ambiguous Routing", TIER3_AMBIGUOUS_ROUTING),
    ]:
        print(f"  {cat}: {len(scenarios)}")
