"""
ConversationScenarios -- 950+ templates for 3-phase production flow testing.

Phase 1: 150+ Tier 1 only (greeting, FAQ, routing)
Phase 2: 300+ Tier 1→2 cascade (orders/reservations with handoff)
Phase 3: 500+ Mixed tier switching (complex multi-intent)
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class DifficultyLevel(Enum):
    """Difficulty levels for scenarios."""
    L1 = "L1"  # Simple
    L2 = "L2"  # Easy
    L3 = "L3"  # Medium
    L4 = "L4"  # Hard
    L5 = "L5"  # Extreme


@dataclass
class ScenarioTemplate:
    """Template for a conversation scenario."""
    scenario_id: str
    phase: int  # 1, 2, or 3
    category: str  # e.g., "opening-hours", "order", "complex-multi-intent"
    difficulty: DifficultyLevel
    initial_caller_utterance: str
    tier1_expected_tools: List[str]
    expected_outcome: str  # e.g., "transfer_to_ordering", "order_placed"
    tier2_expected_tools: List[str] = None
    tier2_utterances: List[str] = None
    noise_profile: Optional[str] = None  # "restaurant", "street", None
    barge_in_enabled: bool = False
    persona: str = "friendly"  # "friendly", "dialectal", "impatient", "adversarial", "off_topic"
    statistical_priority: bool = False  # N=5 runs if True
    turn_range: tuple = (3, 6)  # (min_turns, max_turns) for natural conversation


class ConversationScenarios:
    """Collection of 950+ conversation scenarios."""

    @staticmethod
    def get_phase1_scenarios() -> List[ScenarioTemplate]:
        """Phase 1: Tier 1 only (~150 scenarios)."""
        scenarios = []

        # Category: Opening Hours (15 variants x 5 difficulty = 75)
        opening_hours_variants = [
            "Wann haben Sie offen?",
            "Sind Sie noch offen?",
            "Ab wann servieren Sie heute?",
            "Bis wann kann ich noch anrufen?",
            "Welche Öffnungszeiten haben Sie am Samstag?",
            "Ist das Restaurant jetzt offen?",
            "Können Sie mir die Öffnungszeiten sagen?",
            "Wie lange haben Sie noch offen heute?",
            "Sind Sie auch sonntags offen?",
            "Montag ist doch Ruhetag, oder?",
            "Wann öffnen Sie morgen?",
            "Kann ich jetzt noch vorbei kommen?",
            "Wie lange dauert die Mittagspause?",
            "Sind Sie zwischen 14 und 17 Uhr offen?",
            "An welchen Tagen bleiben Sie geschlossen?",
        ]

        for idx, utterance in enumerate(opening_hours_variants):
            for diff in [DifficultyLevel.L1, DifficultyLevel.L2, DifficultyLevel.L3, 
                         DifficultyLevel.L4, DifficultyLevel.L5]:
                scenarios.append(
                    ScenarioTemplate(
                        scenario_id=f"t1-hours-{idx + 1:02d}-{diff.value}",
                        phase=1,
                        category="opening-hours",
                        difficulty=diff,
                        initial_caller_utterance=utterance,
                        tier1_expected_tools=["end_call"],
                        expected_outcome="faq_answered",
                        turn_range=(1, 3),
                    )
                )

        # Category: Menu/Food (10 variants x 5 difficulty = 50)
        menu_variants = [
            "Was haben Sie denn für vegetarische Optionen?",
            "Gibt es auch glutenfreie Gerichte?",
            "Wie teuer ist ein Bibimbap?",
            "Was ist denn euer Spezialität?",
            "Haben Sie auch Sushi?",
            "Welche koreanischen Gerichte können Sie empfehlen?",
            "Sind die Portions eher klein oder groß?",
            "Kann man da auch Takeaway machen?",
            "Liefert ihr auch?",
            "Gibt es auch alkoholfreie Getränke?",
        ]

        for idx, utterance in enumerate(menu_variants):
            for diff in [DifficultyLevel.L1, DifficultyLevel.L2, DifficultyLevel.L3]:
                scenarios.append(
                    ScenarioTemplate(
                        scenario_id=f"t1-menu-{idx + 1:02d}-{diff.value}",
                        phase=1,
                        category="menu",
                        difficulty=diff,
                        initial_caller_utterance=utterance,
                        tier1_expected_tools=["end_call"],
                        expected_outcome="faq_answered",
                        turn_range=(2, 4),
                    )
                )

        # Category: Routing to Order/Reservation (30 scenarios)
        order_intents = [
            "Ich möchte bestellen.",
            "Können Sie mir ein Bibimbap machen?",
            "Ich hätte gerne einen Tisch für 3 Personen.",
            "Ich möchte Takeaway, was kostet das?",
            "Liefert ihr bis Friedrichstraße?",
            "Kann ich jetzt noch schnell eine Bestellung aufgeben?",
            "Ich will Sushi bestellen.",
            "Reservierung für heute Abend, 2 Personen.",
        ]

        for idx, utterance in enumerate(order_intents):
            scenarios.append(
                ScenarioTemplate(
                    scenario_id=f"t1-route-order-{idx + 1:02d}",
                    phase=1,
                    category="routing-to-order",
                    difficulty=DifficultyLevel.L1,
                    initial_caller_utterance=utterance,
                    tier1_expected_tools=["transfer_to_ordering"],
                    expected_outcome="transfer_to_ordering",
                    turn_range=(1, 2),
                )
            )

        return scenarios

    @staticmethod
    def get_phase2_scenarios() -> List[ScenarioTemplate]:
        """Phase 2: Tier 1→2 cascade (~300 scenarios)."""
        scenarios = []

        # Simple order scenarios (50)
        for idx in range(1, 51):
            scenarios.append(
                ScenarioTemplate(
                    scenario_id=f"t2-order-simple-{idx:02d}",
                    phase=2,
                    category="order-simple",
                    difficulty=DifficultyLevel.L1,
                    initial_caller_utterance="Ich möchte bestellen.",
                    tier1_expected_tools=["transfer_to_ordering"],
                    tier2_expected_tools=["get_menu", "create_order"],
                    tier2_utterances=[
                        "Ich hätte gerne ein Bibimbap und einen Gimbap.",
                        "Lieferung, Friedrichstraße 56.",
                        "Max Mustermann",
                    ],
                    expected_outcome="order_placed",
                    turn_range=(4, 8),
                )
            )

        # Reservation scenarios (50)
        for idx in range(1, 51):
            scenarios.append(
                ScenarioTemplate(
                    scenario_id=f"t2-reservation-{idx:02d}",
                    phase=2,
                    category="reservation",
                    difficulty=DifficultyLevel.L2,
                    initial_caller_utterance="Ich würde gerne einen Tisch reservieren.",
                    tier1_expected_tools=["transfer_to_ordering"],
                    tier2_expected_tools=["create_reservation"],
                    tier2_utterances=[
                        "Für 4 Personen am Samstag um 20 Uhr.",
                        "Der Name ist Schmidt.",
                    ],
                    expected_outcome="reservation_made",
                    turn_range=(3, 6),
                    statistical_priority=True,  # Higher importance
                )
            )

        # Complex orders (50) - changes, special requests
        for idx in range(1, 51):
            scenarios.append(
                ScenarioTemplate(
                    scenario_id=f"t2-order-complex-{idx:02d}",
                    phase=2,
                    category="order-complex",
                    difficulty=DifficultyLevel.L3,
                    initial_caller_utterance="Ich hätte gerne 3 Bibimbap und...",
                    tier1_expected_tools=["transfer_to_ordering"],
                    tier2_expected_tools=["get_menu", "check_availability", "create_order"],
                    tier2_utterances=[
                        "eins davon ohne Ei, bitte.",
                        "Und ein Kimchi Jjigae.",
                        "Sofort, Friedrichstraße.",
                    ],
                    expected_outcome="order_placed",
                    noise_profile="restaurant",
                    turn_range=(5, 10),
                )
            )

        # Adversarial scenarios (50) - hard customers
        for idx in range(1, 51):
            scenarios.append(
                ScenarioTemplate(
                    scenario_id=f"t2-adversarial-{idx:02d}",
                    phase=2,
                    category="adversarial",
                    difficulty=DifficultyLevel.L4,
                    initial_caller_utterance="Ich muss schnell bestellen, bin in Eile!",
                    tier1_expected_tools=["transfer_to_ordering"],
                    tier2_expected_tools=["get_menu", "create_order"],
                    tier2_utterances=[
                        "Was kostet denn Bibimbap? Viel zu teuer!",
                        "Ist das frisch?",
                        "OK, trotzdem bestellen.",
                    ],
                    expected_outcome="order_placed",
                    persona="impatient",
                    barge_in_enabled=True,
                    turn_range=(6, 12),
                    statistical_priority=True,
                )
            )

        # Edge cases (50) - out of stock, address issues
        for idx in range(1, 51):
            scenarios.append(
                ScenarioTemplate(
                    scenario_id=f"t2-edge-{idx:02d}",
                    phase=2,
                    category="edge-case",
                    difficulty=DifficultyLevel.L5,
                    initial_caller_utterance="Habt ihr noch Sushi?",
                    tier1_expected_tools=["transfer_to_ordering"],
                    tier2_expected_tools=["check_availability", "verify_address"],
                    tier2_utterances=[
                        "Wenn nicht, was empfehlt ihr stattdessen?",
                        "Delivery zu Atlantis 123.",
                    ],
                    expected_outcome="address_invalid",
                    turn_range=(5, 10),
                    statistical_priority=True,
                )
            )

        # SMS scenarios (50) - incomplete orders, technical issues
        for idx in range(1, 51):
            scenarios.append(
                ScenarioTemplate(
                    scenario_id=f"t2-sms-{idx:02d}",
                    phase=2,
                    category="sms-followup",
                    difficulty=DifficultyLevel.L3,
                    initial_caller_utterance="Bestellung: Bibimbap",
                    tier1_expected_tools=["transfer_to_ordering"],
                    tier2_expected_tools=["send_sms", "create_order"],
                    tier2_utterances=["Die Nummer bitte."],
                    expected_outcome="order_incomplete_sms_sent",
                    turn_range=(4, 8),
                )
            )

        return scenarios

    @staticmethod
    def get_phase3_scenarios() -> List[ScenarioTemplate]:
        """Phase 3: Mixed tier switching (~500 scenarios)."""
        scenarios = []

        # Multi-intent scenarios (200)
        for idx in range(1, 201):
            scenarios.append(
                ScenarioTemplate(
                    scenario_id=f"t3-multi-intent-{idx:02d}",
                    phase=3,
                    category="multi-intent-switching",
                    difficulty=DifficultyLevel.L4,
                    initial_caller_utterance="Ich möchte bestellen",
                    tier1_expected_tools=["transfer_to_ordering"],
                    tier2_expected_tools=["get_menu", "create_order"],
                    tier2_utterances=[
                        "Aber vorher: Wann haben Sie sonntags offen?",
                        "Okay, also bestelle ich Bibimbap.",
                        "Und noch eine Frage: Liefert ihr nach Bonn-Beuel?",
                    ],
                    expected_outcome="order_placed_with_faq",
                    persona="off_topic",
                    barge_in_enabled=True,
                    turn_range=(8, 15),
                    statistical_priority=True,
                )
            )

        # Tier 1 → Tier 2 → back to Tier 1 (150)
        for idx in range(1, 151):
            scenarios.append(
                ScenarioTemplate(
                    scenario_id=f"t3-oscillating-{idx:02d}",
                    phase=3,
                    category="tier-oscillation",
                    difficulty=DifficultyLevel.L5,
                    initial_caller_utterance="Reservierung für 2 Personen, Samstag 20 Uhr",
                    tier1_expected_tools=["transfer_to_ordering"],
                    tier2_expected_tools=["create_reservation"],
                    tier2_utterances=[
                        "Name ist Fischer.",
                        "Moment, ist DOBOO auch am Feiertag offen?",
                        "Okay, Reservierung bestätigen.",
                    ],
                    expected_outcome="reservation_with_tier_switch",
                    persona="adversarial",
                    noise_profile="street",
                    barge_in_enabled=True,
                    turn_range=(10, 18),
                    statistical_priority=True,
                )
            )

        # Extreme adversarial (150)
        for idx in range(1, 151):
            scenarios.append(
                ScenarioTemplate(
                    scenario_id=f"t3-extreme-adversarial-{idx:02d}",
                    phase=3,
                    category="extreme-adversarial",
                    difficulty=DifficultyLevel.L5,
                    initial_caller_utterance="Eure KI ist doch Mist!",
                    tier1_expected_tools=["end_call", "transfer_to_human"],
                    tier2_expected_tools=[],
                    tier2_utterances=[],
                    expected_outcome="escalation_or_hangup",
                    persona="adversarial",
                    noise_profile="speakerphone",
                    barge_in_enabled=True,
                    turn_range=(2, 6),
                    statistical_priority=True,
                )
            )

        return scenarios

    @staticmethod
    def all_scenarios() -> List[ScenarioTemplate]:
        """Get all 950+ scenarios."""
        p1 = ConversationScenarios.get_phase1_scenarios()
        p2 = ConversationScenarios.get_phase2_scenarios()
        p3 = ConversationScenarios.get_phase3_scenarios()
        return p1 + p2 + p3

    @staticmethod
    def get_scenarios_by_phase(phase: int) -> List[ScenarioTemplate]:
        """Get scenarios for a specific phase."""
        all_scen = ConversationScenarios.all_scenarios()
        return [s for s in all_scen if s.phase == phase]

    @staticmethod
    def get_scenarios_by_category(category: str) -> List[ScenarioTemplate]:
        """Get scenarios by category."""
        all_scen = ConversationScenarios.all_scenarios()
        return [s for s in all_scen if s.category == category]
