"""
Scenario Generator — Dynamically create test scenarios from difficulty × persona matrix.

Instead of static YAML files, this generates ValidationScenario objects at runtime
by combining base scripts with persona overlays.

Reference: Sailly Test Call Script Matrix v1.0 (difficulty D1-D5, personas × 7)
Total: ~32 base scripts × 7 personas = 224 scenarios per phase
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Realistic German caller identities ────────────────────────────────────────
# Assigned deterministically per scenario_id so re-runs get the same identity.
_CALLER_IDENTITIES = [
    {"name": "Markus Bauer",      "phone": "+49 89 4521 8834",  "address": "Schillerstraße 12, 80336 München"},
    {"name": "Sabine Hoffmann",   "phone": "+49 30 7791 2243",  "address": "Kastanienallee 47, 10119 Berlin"},
    {"name": "Thomas Schneider",  "phone": "+49 221 3384 9901", "address": "Venloer Str. 201, 50823 Köln"},
    {"name": "Claudia Müller",    "phone": "+49 711 6623 4410", "address": "Tübinger Str. 55, 70178 Stuttgart"},
    {"name": "Andreas Fischer",   "phone": "+49 40 3398 7712",  "address": "Eppendorfer Weg 88, 20259 Hamburg"},
    {"name": "Julia Wagner",      "phone": "+49 69 2445 6631",  "address": "Berger Str. 139, 60385 Frankfurt"},
    {"name": "Stefan Weber",      "phone": "+49 351 4412 9087", "address": "Bautzner Str. 34, 01099 Dresden"},
    {"name": "Petra Schmidt",     "phone": "+49 911 7823 5500", "address": "Königstr. 72, 90402 Nürnberg"},
    {"name": "Michael Richter",   "phone": "+49 621 8831 4427", "address": "Mannheimer Str. 18, 68165 Mannheim"},
    {"name": "Monika Braun",      "phone": "+49 251 9934 6615", "address": "Promenade 23, 48143 Münster"},
    {"name": "Hans-Peter Koch",   "phone": "+49 89 6671 2280",  "address": "Nymphenburger Str. 64, 80335 München"},
    {"name": "Ursula Klein",      "phone": "+49 341 5523 8843", "address": "Karl-Liebknecht-Str. 11, 04107 Leipzig"},
    {"name": "Ralf Schulz",       "phone": "+49 711 4482 0034", "address": "Schlossplatz 3, 70173 Stuttgart"},
    {"name": "Ingrid Wolf",       "phone": "+49 40 5591 3367",  "address": "Altonaer Str. 102, 22769 Hamburg"},
    {"name": "Günter Zimmermann", "phone": "+49 30 4478 9912",  "address": "Prenzlauer Allee 58, 10405 Berlin"},
    {"name": "Heike Krause",      "phone": "+49 421 8843 2201", "address": "Sögestr. 44, 28195 Bremen"},
    {"name": "Bernd Lehmann",     "phone": "+49 511 3397 6654", "address": "Georgstr. 29, 30159 Hannover"},
    {"name": "Karin Hartmann",    "phone": "+49 201 6612 5543", "address": "Rüttenscheider Str. 97, 45130 Essen"},
    {"name": "Dieter Lange",      "phone": "+49 911 2234 8876", "address": "Marienplatz 7, 90402 Nürnberg"},
    {"name": "Renate Schäfer",    "phone": "+49 221 9987 3310", "address": "Hohenstaufenring 12, 50674 Köln"},
]


def _pick_identity(scenario_id: str) -> Dict[str, str]:
    """Deterministically pick a caller identity based on scenario_id hash."""
    idx = int(hashlib.md5(scenario_id.encode()).hexdigest(), 16) % len(_CALLER_IDENTITIES)
    return dict(_CALLER_IDENTITIES[idx])


class Difficulty(Enum):
    """Difficulty scale for scenarios."""
    D1 = "D1"  # Clean, structured, cooperative
    D2 = "D2"  # Minor ambiguity
    D3 = "D3"  # Multi-slot / corrections
    D4 = "D4"  # Interruptions / friction
    D5 = "D5"  # Chaos / failure handling


class Persona(Enum):
    """Persona overlays for realistic human behavior simulation."""
    NEUTRAL = "neutral"          # cooperative, clear
    BUSY = "busy"                # short, rushed
    ELDERLY = "elderly"          # slow, unsure, pauses
    SKEPTICAL = "skeptical"      # questions AI
    IMPATIENT = "impatient"      # interrupts, pushes
    RUDE = "rude"                # aggressive tone
    INDECISIVE = "indecisive"    # changes mind often


@dataclass
class PersonaTraits:
    """Traits for persona mutations."""
    pace_multiplier: float          # 0.5=slow, 1.0=normal, 2.0=fast
    interrupts: bool                # does user interrupt?
    pauses: bool                    # adds hesitation?
    tone: str                       # "neutral", "aggressive", "questioning", "rushed"
    repetitions: int                # how many times to ask same thing?
    correction_tendency: float      # 0.0-1.0 probability of mid-message correction


PERSONA_TRAITS_MAP: Dict[Persona, PersonaTraits] = {
    Persona.NEUTRAL: PersonaTraits(
        pace_multiplier=1.0,
        interrupts=False,
        pauses=False,
        tone="neutral",
        repetitions=1,
        correction_tendency=0.0,
    ),
    Persona.BUSY: PersonaTraits(
        pace_multiplier=2.0,
        interrupts=False,
        pauses=False,
        tone="rushed",
        repetitions=1,
        correction_tendency=0.1,
    ),
    Persona.ELDERLY: PersonaTraits(
        pace_multiplier=0.5,
        interrupts=False,
        pauses=True,
        tone="neutral",
        repetitions=2,
        correction_tendency=0.2,
    ),
    Persona.SKEPTICAL: PersonaTraits(
        pace_multiplier=1.0,
        interrupts=True,
        pauses=False,
        tone="questioning",
        repetitions=2,
        correction_tendency=0.4,
    ),
    Persona.IMPATIENT: PersonaTraits(
        pace_multiplier=1.5,
        interrupts=True,
        pauses=False,
        tone="aggressive",
        repetitions=1,
        correction_tendency=0.3,
    ),
    Persona.RUDE: PersonaTraits(
        pace_multiplier=1.5,
        interrupts=True,
        pauses=False,
        tone="aggressive",
        repetitions=1,
        correction_tendency=0.2,
    ),
    Persona.INDECISIVE: PersonaTraits(
        pace_multiplier=0.8,
        interrupts=False,
        pauses=True,
        tone="questioning",
        repetitions=3,
        correction_tendency=0.8,
    ),
}


@dataclass
class BaseScript:
    """A base script template before persona overlay."""
    id: str                         # e.g., "A1.1"
    phase: int                      # 0 (A), 1 (B), 2 (C), 3 (D)
    category: str                   # "reservation", "faq", "order", "delivery", etc.
    difficulty: Difficulty
    script: str                     # German text
    expectations: Dict[str, Any] = field(default_factory=dict)
    required_data: Dict[str, Any] = field(default_factory=dict)  # slot values needed to pass this scenario


# ============================================================================
# BASE SCRIPTS FROM REFERENCE 1
# ============================================================================

BASE_SCRIPTS: List[BaseScript] = [
    # PHASE A — FOUNDATION (Reservation + FAQs)

    # A1 — Reservation (Single Intent)
    BaseScript(
        id="A1.1",
        phase=0,
        category="reservation",
        difficulty=Difficulty.D1,
        script="Ich möchte heute Abend einen Tisch für zwei Personen um 19 Uhr reservieren. Name ist Müller.",
        expectations={
            "must_detect": "reservation",
            "must_capture": ["party_size", "time", "date", "name"],
            "must_not_contain": ["technisches problem"],
        },
        required_data={"party_size": 2, "reservation_date": "heute Abend", "reservation_time": "19:00"},
    ),
    BaseScript(
        id="A1.2",
        phase=0,
        category="reservation",
        difficulty=Difficulty.D2,
        script="Nächsten Samstag, vier Personen, 20 Uhr, Schmidt.",
        expectations={
            "must_detect": "reservation",
            "must_capture": ["party_size", "time", "date"],
            "resolve_future_date": True,
        },
        required_data={"party_size": 4, "reservation_time": "20:00"},
    ),
    BaseScript(
        id="A1.3",
        phase=0,
        category="reservation",
        difficulty=Difficulty.D3,
        script="Also… ich wollte vielleicht… einen Tisch reservieren… für drei Personen… heute… ich glaube um halb acht…",
        expectations={
            "must_detect": "reservation",
            "tone": "patient",
            "must_not_contain": ["interruption"],
        },
        required_data={"party_size": 3, "reservation_date": "heute", "reservation_time": "19:30"},
    ),
    BaseScript(
        id="A1.4",
        phase=0,
        category="reservation_modify",
        difficulty=Difficulty.D3,
        script="Ich habe schon reserviert auf Weber, heute 19 Uhr. Können wir das auf 20 Uhr ändern?",
        expectations={
            "must_detect": "modification",
            "must_not_contain": ["duplicate_booking"],
        },
        required_data={"reservation_time": "20:00", "reservation_date": "heute"},
    ),
    BaseScript(
        id="A1.5",
        phase=0,
        category="reservation_cancel",
        difficulty=Difficulty.D2,
        script="Reservierung auf Becker heute 20 Uhr bitte stornieren.",
        expectations={
            "must_detect": "cancellation",
        },
        required_data={"reservation_date": "heute", "reservation_time": "20:00"},
    ),

    # A2 — FAQs (Single Intent)
    BaseScript(
        id="A2.1",
        phase=0,
        category="faq",
        difficulty=Difficulty.D1,
        script="Wann habt ihr heute geöffnet?",
        expectations={
            "must_detect": "faq",
            "must_call": ["get_date_info"],
            "must_not_contain": ["technisches problem"],
        },
    ),
    BaseScript(
        id="A2.2",
        phase=0,
        category="faq",
        difficulty=Difficulty.D2,
        script="Was habt ihr denn so?",
        expectations={
            "must_detect": "faq",
            "must_call": ["get_menu"],
        },
    ),
    BaseScript(
        id="A2.3",
        phase=0,
        category="faq",
        difficulty=Difficulty.D2,
        script="Habt ihr Bibimbap?",
        expectations={
            "must_detect": "faq",
            "must_call": ["get_menu"],
        },
    ),
    BaseScript(
        id="A2.4",
        phase=0,
        category="faq",
        difficulty=Difficulty.D2,
        script="Habt ihr Pizza?",
        expectations={
            "must_detect": "faq",
            "must_not_contain": ["hallucination"],
        },
    ),
    BaseScript(
        id="A2.5",
        phase=0,
        category="faq_allergen",
        difficulty=Difficulty.D4,
        script="Ist da Gluten drin? Ich habe eine Unverträglichkeit.",
        expectations={
            "must_detect": "faq_allergen",
            "tone": "safety_critical",
        },
    ),
    BaseScript(
        id="A2.6",
        phase=0,
        category="faq_ai",
        difficulty=Difficulty.D3,
        script="Bist du überhaupt ein Mensch oder ein Bot?",
        expectations={
            "must_detect": "faq_ai",
            "tone": "honest_answer",
        },
    ),

    # PHASE B — ORDERING (Single Intent)

    # B1 — Takeaway
    BaseScript(
        id="B1.1",
        phase=1,
        category="order_takeaway",
        difficulty=Difficulty.D1,
        script="Einmal Bibimbap zum Mitnehmen, Name Schulz, 19 Uhr.",
        expectations={
            "must_detect": "order",
            "must_capture": ["dish", "name", "time"],
            "must_call": ["create_order"],
        },
    ),
    BaseScript(
        id="B1.2",
        phase=1,
        category="order_takeaway_multi",
        difficulty=Difficulty.D2,
        script="Zwei Bibimbap, ein Kimchi, eine Cola, Abholung 18 Uhr, Name Meier.",
        expectations={
            "must_detect": "order",
            "must_capture": ["dishes", "name", "time"],
        },
    ),
    BaseScript(
        id="B1.3",
        phase=1,
        category="order_correction",
        difficulty=Difficulty.D3,
        script="Drei Bibimbap… nein zwei.",
        expectations={
            "must_detect": "order_correction",
            "must_not_contain": ["duplicate_items"],
        },
    ),
    BaseScript(
        id="B1.4",
        phase=1,
        category="order_impatient",
        difficulty=Difficulty.D4,
        script="Ja komm, zwei Bibimbap, schnell, 19 Uhr, Müller.",
        expectations={
            "must_detect": "order",
            "tone": "fast_processing",
        },
    ),

    # B2 — Delivery
    BaseScript(
        id="B2.1",
        phase=1,
        category="order_delivery",
        difficulty=Difficulty.D2,
        script="Lieferung bitte, ein Bibimbap, Aachener Straße 10, Köln.",
        expectations={
            "must_detect": "order_delivery",
            "must_capture": ["address"],
        },
    ),
    BaseScript(
        id="B2.2",
        phase=1,
        category="order_address_correction",
        difficulty=Difficulty.D3,
        script="Venloer Straße 20… nein 22.",
        expectations={
            "must_detect": "address_correction",
            "must_not_contain": ["wrong_address"],
        },
    ),
    BaseScript(
        id="B2.3",
        phase=1,
        category="order_outside_zone",
        difficulty=Difficulty.D3,
        script="Lieferung nach Düsseldorf.",
        expectations={
            "must_detect": "delivery_outside_zone",
        },
    ),

    # PHASE C — MULTI-INTENT
    BaseScript(
        id="C1",
        phase=2,
        category="multi_order_question",
        difficulty=Difficulty.D3,
        script="Ein Bibimbap bitte. Ist das scharf?",
        expectations={
            "must_detect": "multi_intent",
        },
    ),
    BaseScript(
        id="C2",
        phase=2,
        category="multi_reservation_order",
        difficulty=Difficulty.D4,
        script="Ich möchte einen Tisch reservieren und zwei Bibimbap bestellen.",
        expectations={
            "must_detect": "multi_intent",
            "must_not_contain": ["loss_of_state"],
        },
    ),
    BaseScript(
        id="C3",
        phase=2,
        category="multi_long_input",
        difficulty=Difficulty.D3,
        script="Hallo, ich bin Tim, Nummer 0176123456, ich möchte um 19 Uhr zwei Bibimbap bestellen.",
        expectations={
            "must_detect": "order",
            "must_extract_info": True,
        },
    ),
    BaseScript(
        id="C4",
        phase=2,
        category="multi_indecisive",
        difficulty=Difficulty.D4,
        script="Ein Bibimbap… nein doch Kimchi… ach doch Bibimbap.",
        expectations={
            "must_detect": "order_indecision",
            "must_handle_corrections": True,
        },
    ),
    BaseScript(
        id="C5",
        phase=2,
        category="multi_interrupt",
        difficulty=Difficulty.D4,
        script="Ja, ich möchte—",  # User interrupts bot mid-response
        expectations={
            "must_handle": "mid_response_interrupt",
        },
    ),

    # PHASE D — EDGE + FAILURE
    BaseScript(
        id="D1",
        phase=3,
        category="edge_silence",
        difficulty=Difficulty.D3,
        script="[SILENCE_10S]",  # No response for 10s
        expectations={
            "must_handle": "silence",
            "must_not_hang": True,
        },
    ),
    BaseScript(
        id="D2",
        phase=3,
        category="edge_rude",
        difficulty=Difficulty.D4,
        script="Hör zu, ich will einfach bestellen, mach hin.",
        expectations={
            "tone": "professional_despite_rudeness",
        },
    ),
    BaseScript(
        id="D3",
        phase=3,
        category="edge_unrealistic",
        difficulty=Difficulty.D5,
        script="Ich nehme tausend Bibimbap.",
        expectations={
            "must_handle": "unrealistic_order",
        },
    ),
    BaseScript(
        id="D4",
        phase=3,
        category="edge_chaos",
        difficulty=Difficulty.D5,
        script="Ich weiß nicht… vielleicht bestellen… oder reservieren… keine Ahnung.",
        expectations={
            "must_handle": "indecisive_chaos",
        },
    ),
    BaseScript(
        id="D5",
        phase=3,
        category="edge_long_call",
        difficulty=Difficulty.D5,
        script="[MULTI_TURN_EXTENDED]",  # Simulate extended conversation
        expectations={
            "must_not_timeout": True,
        },
    ),
    BaseScript(
        id="D6",
        phase=3,
        category="edge_after_hours",
        difficulty=Difficulty.D3,
        script="Ich möchte jetzt bestellen.",  # restaurant closed
        expectations={
            "must_detect": "after_hours",
        },
    ),
    BaseScript(
        id="D7",
        phase=3,
        category="edge_escalation",
        difficulty=Difficulty.D5,
        script="[USER_LOOPS_5_TURNS]",  # User confused for 5+ turns
        expectations={
            "must_escalate": True,
            "must_not_loop": True,
        },
    ),

    # ── ADDITIONAL PHASE A — German date/time expressions ─────────────────────

    BaseScript(
        id="A1.6",
        phase=0,
        category="reservation",
        difficulty=Difficulty.D2,
        script="Nächste Woche Samstag für zwei Personen um 19 Uhr bitte. Auf den Namen Fischer.",
        expectations={
            "must_detect": "reservation",
            "must_capture": ["party_size", "time", "date", "name"],
            "resolve_future_date": True,
        },
    ),
    BaseScript(
        id="A1.7",
        phase=0,
        category="reservation",
        difficulty=Difficulty.D2,
        script="Übernächste Woche Freitag, drei Personen, abends so gegen acht. Name Bauer.",
        expectations={
            "must_detect": "reservation",
            "resolve_future_date": True,
        },
    ),
    BaseScript(
        id="A1.8",
        phase=0,
        category="reservation",
        difficulty=Difficulty.D3,
        script="Ich möchte am ersten April reservieren, vier Personen um 20 Uhr, Name Wagner.",
        expectations={
            "must_detect": "reservation",
            "must_capture": ["date"],
            "resolve_future_date": True,
        },
    ),
    BaseScript(
        id="A1.9",
        phase=0,
        category="reservation",
        difficulty=Difficulty.D3,
        script="Morgen Abend, zwei Personen, halb sieben. Geht das? Name ist Klein.",
        expectations={
            "must_detect": "reservation",
            "resolve_future_date": True,
        },
    ),
    BaseScript(
        id="A2.7",
        phase=0,
        category="faq",
        difficulty=Difficulty.D2,
        script="Habt ihr heute noch auf? Ich komme so gegen halb neun.",
        expectations={
            "must_detect": "faq",
            "must_call": ["get_date_info"],
        },
    ),
    BaseScript(
        id="A2.8",
        phase=0,
        category="faq",
        difficulty=Difficulty.D2,
        script="Ist übermorgen geöffnet? Ich wollte zum Mittagessen kommen.",
        expectations={
            "must_detect": "faq",
            "must_call": ["get_date_info"],
        },
    ),

    # ── ADDITIONAL PHASE B — Time-sensitive orders ─────────────────────────────

    BaseScript(
        id="B1.5",
        phase=1,
        category="order_takeaway",
        difficulty=Difficulty.D3,
        script="Ich brauche das bis 12 Uhr mittags, geht das noch? Einmal Bibimbap, Name Hoffmann.",
        expectations={
            "must_detect": "order",
            "must_capture": ["dish", "name", "time"],
        },
    ),
    BaseScript(
        id="B1.6",
        phase=1,
        category="order_takeaway",
        difficulty=Difficulty.D2,
        script="Abholung für heute Abend 18 Uhr, zweimal Bibimbap, einmal Kimchi. Name Lehmann.",
        expectations={
            "must_detect": "order",
            "must_capture": ["dishes", "name", "time"],
        },
    ),
    BaseScript(
        id="B2.4",
        phase=1,
        category="order_delivery",
        difficulty=Difficulty.D2,
        script="Lieferung für heute Abend 19 Uhr bitte, Venloer Straße 10 in Köln, zwei Bibimbap.",
        expectations={
            "must_detect": "order_delivery",
            "must_capture": ["address", "time"],
        },
    ),
]


# Persona opener phrases — prepended to the base script to create authentic German caller tone
_PERSONA_OPENERS: Dict[Persona, List[str]] = {
    Persona.NEUTRAL:    [],  # no prefix, clean delivery
    Persona.BUSY:       ["Kurz gesagt:", "Also schnell —", "Ich hab wenig Zeit,"],
    Persona.ELDERLY:    ["Ach wissen Sie,", "Einen Moment bitte —", "Ja also,", "Guten Tag, ich wollte sagen:"],
    Persona.SKEPTICAL:  ["Ich frage mich,", "Mal sehen ob das klappt —", "Ich bin etwas skeptisch, aber:"],
    Persona.IMPATIENT:  ["Los,", "Beeilung bitte,", "Kurz und gut:"],
    Persona.RUDE:       ["Hören Sie mal,", "Das ist doch nicht so schwer,", "Ich sage Ihnen:"],
    Persona.INDECISIVE: ["Also eigentlich wollte ich…", "Nein, warten Sie,", "Hmm, ich bin mir nicht sicher, aber"],
}

# Persona suffix phrases — appended to signal uncertainty/urgency/etc.
_PERSONA_SUFFIXES: Dict[Persona, List[str]] = {
    Persona.NEUTRAL:    [],
    Persona.BUSY:       ["— und bitte schnell.", "Danke, ich muss weiter."],
    Persona.ELDERLY:    ["Wissen Sie, ich bin nicht so fit mit dem Telefon.", "Ich hoffe das war verständlich."],
    Persona.SKEPTICAL:  [" Stimmt das so?", " Können Sie das bestätigen?"],
    Persona.IMPATIENT:  [" Geht das?", " Ja oder nein?"],
    Persona.RUDE:       [" Das sollte doch klar sein.", ""],
    Persona.INDECISIVE: ["… oder vielleicht doch was anderes.", "… ich weiß noch nicht genau."],
}


def apply_persona_mutations(script: str, persona: Persona) -> str:
    """Apply persona traits to mutate a script with authentic German phrasing."""
    import random

    # Skip special placeholder scripts
    if script.startswith("[") and script.endswith("]"):
        return script

    # Pick opener for this persona
    openers = _PERSONA_OPENERS.get(persona, [])
    opener = random.choice(openers) if openers else ""

    # Pick suffix for this persona
    suffixes = _PERSONA_SUFFIXES.get(persona, [])
    suffix = random.choice(suffixes) if suffixes else ""

    # Elderly: insert a hesitation pause mid-sentence
    if persona == Persona.ELDERLY and "…" not in script:
        words = script.split()
        if len(words) > 4:
            insert_pos = len(words) // 2
            words.insert(insert_pos, "…")
            script = " ".join(words)

    # Skeptical: append doubt about being automated
    if persona == Persona.SKEPTICAL and not script.endswith("?"):
        script = script.rstrip(".") + ", falls das hier wirklich automatisch funktioniert."

    # Indecisive: insert a self-correction
    if persona == Persona.INDECISIVE:
        script = script.rstrip(".") + "… nein, warten Sie, ich meine:"

    # Rude: strip politeness markers
    script = script.replace("bitte ", "") if persona == Persona.RUDE else script

    # Build final mutated script
    parts = [p for p in [opener, script, suffix] if p]
    return " ".join(parts)


def generate_scenario_id(base_id: str, difficulty: Difficulty, persona: Persona) -> str:
    """Generate unique scenario ID from base + difficulty + persona."""
    return f"{base_id}_{difficulty.value}_{persona.value}"


class ScenarioMatrix:
    """Generates ValidationScenario objects from difficulty × persona matrix."""

    def __init__(self):
        self.base_scripts = BASE_SCRIPTS
        self.personas = list(Persona)

    def generate_phase(
        self,
        phase: int,
        difficulty_filter: Optional[Difficulty] = None,
        persona_filter: Optional[Persona] = None,
    ) -> List[dict]:
        """
        Generate all scenarios for a phase.

        Args:
            phase: 0 (A), 1 (B), 2 (C), 3 (D)
            difficulty_filter: filter to specific difficulty (None = all)
            persona_filter: filter to specific persona (None = all)

        Returns:
            List of scenario dicts suitable for ValidationScenario creation
        """
        scenarios = []

        for base_script in self.base_scripts:
            if base_script.phase != phase:
                continue

            for persona in self.personas:
                if persona_filter and persona != persona_filter:
                    continue

                if difficulty_filter and base_script.difficulty != difficulty_filter:
                    continue

                # Apply persona mutations
                mutated_script = apply_persona_mutations(base_script.script, persona)

                scenario_id = generate_scenario_id(
                    base_script.id, base_script.difficulty, persona
                )

                identity = _pick_identity(scenario_id)
                scenario_dict = {
                    "id": scenario_id,
                    "phase": base_script.phase,
                    "description": f"{base_script.id} ({base_script.difficulty.value}) — {persona.value}",
                    "caller_goal": mutated_script,  # Use the actual script as the goal (what customer says)
                    "caller_identity": identity,
                    "caller_patience_turns": 5,
                    "tenant_id": "doboo",
                    "confirmation_phrases": ["ja", "ja genau", "ja bitte", "passt so"],
                    "expectations": base_script.expectations,
                    # All required slot data for this scenario — caller bot uses these to answer Sailly
                    "required_data": {
                        **base_script.required_data,
                        "customer_name": identity.get("name", ""),
                        "phone_number": identity.get("phone", ""),
                    },
                    # Custom fields for stress test
                    "difficulty": base_script.difficulty.value,
                    "persona": persona.value,
                    "base_id": base_script.id,
                    "category": base_script.category,  # Keep category for reference
                    "mutated_script": mutated_script,
                }

                scenarios.append(scenario_dict)

        logger.info(
            f"Generated {len(scenarios)} scenarios for phase {phase} "
            f"(difficulty_filter={difficulty_filter}, persona_filter={persona_filter})"
        )
        return scenarios

    def get_all_scenarios_for_phase(self, phase: int) -> List[dict]:
        """Get all 224 scenarios (32 scripts × 7 personas) for a phase."""
        return self.generate_phase(phase)

    def get_scenarios_by_difficulty(self, phase: int, difficulty: Difficulty) -> List[dict]:
        """Get scenarios filtered by difficulty (32 scripts × 7 personas / 5 difficulties ≈ 45 per difficulty)."""
        return self.generate_phase(phase, difficulty_filter=difficulty)

    def get_statistics(self, phase: int) -> dict:
        """Get generation statistics for a phase."""
        all_scenarios = self.generate_phase(phase)
        by_difficulty = {d: len(self.generate_phase(phase, difficulty_filter=d)) for d in Difficulty}
        by_persona = {p: len(self.generate_phase(phase, persona_filter=p)) for p in Persona}

        return {
            "total_scenarios": len(all_scenarios),
            "base_scripts": len([s for s in self.base_scripts if s.phase == phase]),
            "personas": len(self.personas),
            "by_difficulty": {d.value: count for d, count in by_difficulty.items()},
            "by_persona": {p.value: count for p, count in by_persona.items()},
        }
