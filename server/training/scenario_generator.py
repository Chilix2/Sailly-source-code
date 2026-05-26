"""
Demo Training Loop — Unified Scenario Generator

Generates realistic, persona-driven test scenarios for all 4 phases using GPT-4o-mini.
Scenarios are written as static Python files importable by ab_test_loop.py.

Phase definitions:
  Phase 1 (40)  — FAQ, greetings, simple routing
  Phase 2 (100) — Tool-call inquiries (order, reservation, delivery)
  Phase 3 (100) — Chaos / multi-intent (caller jumps, changes mind, contradicts)
  Phase 4 (40)  — Adversarial edge cases

Usage:
  python -m server.training.scenario_generator --phase 1 --count 40 \\
      --out server/scenarios/phase1_scenarios.py

  # Generate all phases at once:
  python -m server.training.scenario_generator --all \\
      --out-dir server/scenarios/
"""

import argparse
import asyncio
import json
import logging
import os
import re
import textwrap
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Persona catalogue
# --------------------------------------------------------------------------- #

PERSONAS = {
    "neutral": "Normaler, höflicher Kunde. Klare Sätze, wartet geduldig.",
    "angry": "Frustrierter, unzufriedener Anrufer. Beschwert sich, hebt die Stimme, unterbricht.",
    "impatient": "Ungeduldiger Anrufer. Kurze abrupte Sätze, verlangt schnelle Antworten, wird ungeduldig bei Rückfragen.",
    "sleepy": "Schläfriger Anrufer. Langsame, undeutliche Sprache, Sätze enden nicht, lange Pausen.",
    "accent": "Anrufer mit starkem nicht-deutschen Akzent. Mischt gelegentlich Englisch oder andere Sprachen ein, Aussprache variiert.",
    "hard_to_hear": "Anrufer kaum hörbar. Hintergrundgeräusche (Straße, Restaurant), spricht leise, nuschelt.",
    "chaos": "Chaotischer Anrufer. Ändert mehrfach die Meinung, startet neue Themen mittendrin, widerspricht sich selbst.",
    "elderly": "Älterer Anrufer. Spricht langsam, wiederholt sich, braucht Bestätigung, verwechselt Details.",
}

# --------------------------------------------------------------------------- #
# Phase-specific system prompts & persona distributions
# --------------------------------------------------------------------------- #

PHASE_CONFIGS = {
    1: {
        "name": "Phase 1 — FAQ & Greeting",
        "description": (
            "Einfache Anrufe: Begrüßung, allgemeine Fragen (Öffnungszeiten, Adresse, Speisekarte), "
            "Weiterleitung, einfache Handoffs. KEINE Bestellungen oder Reservierungen."
        ),
        "categories": [
            "greeting",
            "faq_hours",
            "faq_address",
            "faq_menu_info",
            "faq_payment",
            "faq_parking",
            "handoff",
            "simple_routing",
        ],
        "expected_tools_pool": [
            [],
            [],
            [],
            ["transfer_to_tier2"],
            ["end_call"],
        ],
        "persona_weights": {
            "neutral": 0.35,
            "elderly": 0.20,
            "accent": 0.15,
            "impatient": 0.15,
            "hard_to_hear": 0.15,
        },
        "id_prefix": "p1",
        "turns_range": (5, 8),
    },
    2: {
        "name": "Phase 2 — Tool-Call Inquiries",
        "description": (
            "Bestellungen, Reservierungen, Lieferanfragen. Der Anrufer hat ein KLARES Ziel. "
            "Tools werden in typischer Reihenfolge aufgerufen: check_availability → create_reservation "
            "oder get_menu → create_order → send_sms."
        ),
        "categories": [
            "order_delivery",
            "order_takeaway",
            "reservation_small",
            "reservation_large",
            "check_menu",
            "sms_confirmation",
            "callback_request",
        ],
        "expected_tools_pool": [
            ["get_menu", "create_order", "send_sms"],
            ["check_availability", "create_reservation"],
            ["check_availability", "create_reservation", "send_sms"],
            ["create_order", "send_sms"],
            ["get_menu"],
            ["technical_issues_callback"],
            ["request_callback"],
        ],
        "persona_weights": {
            "neutral": 0.25,
            "impatient": 0.25,
            "accent": 0.20,
            "sleepy": 0.15,
            "hard_to_hear": 0.15,
        },
        "id_prefix": "p2",
        "turns_range": (7, 12),
    },
    3: {
        "name": "Phase 3 — Chaos & Multi-Intent",
        "description": (
            "Der Anrufer ist unsicher, ändert mehrfach seine Meinung, springt zwischen Themen, "
            "stellt widersprüchliche Anforderungen, fragt FAQ mitten in einer Bestellung. "
            "Mindestens 3 Themenwechsel oder Gesprächsabzweigungen pro Szenario."
        ),
        "categories": [
            "order_to_reservation_switch",
            "reservation_to_order_switch",
            "faq_during_order",
            "faq_during_reservation",
            "multiple_dish_changes",
            "date_time_changes",
            "party_size_changes",
            "address_changes",
            "intent_flip_multiple",
            "escalation_mid_conversation",
        ],
        "expected_tools_pool": [
            ["get_menu", "create_order", "send_sms"],
            ["check_availability", "create_reservation"],
            ["get_menu", "check_availability", "create_order"],
            ["get_menu", "create_order", "send_sms", "end_call"],
            [],
        ],
        "persona_weights": {
            "chaos": 0.35,
            "impatient": 0.25,
            "angry": 0.20,
            "accent": 0.10,
            "sleepy": 0.10,
        },
        "id_prefix": "p3",
        "turns_range": (6, 16),
    },
    4: {
        "name": "Phase 4 — Adversarial Edge Cases",
        "description": (
            "Extreme Grenzfälle: KI-feindliche Anrufer, technische Probleme, Sprachbarrieren, "
            "sehr lange Gespräche, Stille-Tests, Gesprächsabbrüche, Missverständnisse, "
            "unpassende Anfragen, Eskalationen."
        ),
        "categories": [
            "ai_hostile",
            "very_hard_to_hear",
            "language_barrier",
            "long_silence",
            "abrupt_hangup_attempt",
            "repeated_misunderstanding",
            "out_of_scope_request",
            "escalation_demand",
            "dialect_extreme",
            "contradictory_info",
        ],
        "expected_tools_pool": [
            [],
            ["end_call"],
            ["transfer_to_tier2"],
            ["technical_issues_callback"],
            ["request_callback"],
        ],
        "persona_weights": {
            "angry": 0.30,
            "hard_to_hear": 0.25,
            "chaos": 0.20,
            "accent": 0.15,
            "elderly": 0.10,
        },
        "id_prefix": "p4",
        "turns_range": (5, 10),
    },
}

# --------------------------------------------------------------------------- #
# OpenAI generation
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT_TEMPLATE = """\
Du generierst realistische Test-Szenarien für "Sailly", den deutschsprachigen \
KI-Sprachassistenten des Restaurants DOBOO in Bonn (koreanische Küche).

RESTAURANT-KONTEXT:
- Name: DOBOO, Friedrich-Ebert-Allee 69, 53113 Bonn (Eingang Adalbert-Stifter-Straße)
- Spezialitäten: Bibimbap, Bulgogi, Kimchi, Kimbap, Ramyeon, Tteokbokki
- Öffnungszeiten: Di-So 12:00-22:00, Mo geschlossen
- Lieferung: nur Bonn Innenstadt, min. 15€
- Zahlung: Bar, EC, Kreditkarte (kein PayPal)
- Parkplatz: Rheinufer-Parkhaus 200m entfernt

VERFÜGBARE TOOLS:
- ai_greeting — Begrüßung durch KI
- end_call — Gespräch beenden
- transfer_to_tier2 — Weiterleiten zu Tier-2-Agenten
- create_reservation — Reservierung erstellen
- check_availability — Verfügbarkeit prüfen
- create_order — Bestellung aufnehmen
- send_sms — SMS-Bestätigung senden
- get_menu — Speisekarte abrufen
- technical_issues_callback — Technischen Rückruf vereinbaren
- request_callback — Allgemeinen Rückruf anfordern
- verify_address — Lieferadresse prüfen
- get_date_info — Datums-/Zeitinformationen abfragen

PHASE: {phase_name}
BESCHREIBUNG: {phase_description}

PERSONA-TYPEN (verwende ausschließlich diese):
{persona_list}

FORMAT — antworte NUR mit einem JSON-Array, kein anderer Text:
[
  {{
    "id": "{id_prefix}-<kategorie>-<nr>",
    "category": "<kategorie>",
    "description": "<20-60 Zeichen Beschreibung>",
    "persona": "<persona-schlüssel>",
    "noise_variant": "clean|restaurant_bg|street|speakerphone",
    "turns": [
      {{"user": "<Anrufer-Aussage auf Deutsch>"}},
      ...
    ],
    "expected_tools": ["<tool1>", ...]
  }},
  ...
]

PFLICHT-GESPRÄCHSSTRUKTUR (JEDES Szenario MUSS diese Phasen als eigene Turns durchlaufen):
1. BEGRÜSSUNG: Der Anrufer ruft an und sagt Hallo / meldet sich
2. ANLIEGEN: Der Anrufer nennt konkret sein Ziel (bestellen, reservieren, fragen etc.)
3. INFORMATIONSAUSTAUSCH: Mehrere Turns — Bot fragt nach Details, Anrufer antwortet vollständig
   - Bei Bestellung: Gericht nennen → Lieferung oder Abholung? → Adresse (bei Lieferung) → Name → Mobilnummer
   - Bei Reservierung: Datum/Uhrzeit → Personenanzahl → Name → Telefonnummer
   - Bei FAQ: konkrete Frage stellen → Antwort empfangen → ggf. Nachfrage
4. BESTÄTIGUNG: Bot fasst zusammen, Anrufer bestätigt ("Ja, genau") oder korrigiert einen Detail
5. ABSCHLUSS/VERABSCHIEDUNG: Anrufer bedankt sich und sagt Tschüss / Auf Wiederhören

VERBOTEN — diese Szenarien werden abgelehnt:
- Szenarien mit weniger als {min_turns} Turns
- Szenarien die mitten in einem Gespräch beginnen (kein "Hallo" am Anfang)
- Szenarien ohne Verabschiedung am Ende
- Szenarien wo der Anrufer alle Infos im ersten Turn nennt ohne auf Bot-Fragen zu warten

ANFORDERUNGEN:
1. Alle Anrufer-Aussagen auf Deutsch (außer accent-Persona: leichtes Code-Switching erlaubt)
2. Jedes Szenario hat min {min_turns} und max {max_turns} Turns — vollständiger Anruf von Anfang bis Ende
3. Persona muss sich in den Aussagen widerspiegeln (chaos → Meinungsänderungen, angry → Beschwerden etc.)
4. expected_tools nur mit Tools aus der obigen Liste
5. {extra_requirements}
6. Generiere exakt {count} Szenarien
"""

PHASE3_EXTRA = (
    "Jedes Szenario MUSS mindestens 3 Themenwechsel oder Gesprächsabzweigungen haben — "
    "aber trotzdem vollständig von Begrüßung bis Verabschiedung. "
    "Der Anrufer soll sich mindestens 2× umentscheiden, dann aber zum Abschluss kommen."
)
PHASE4_EXTRA = (
    "Szenarien müssen extreme Grenzfälle darstellen — aber trotzdem vollständig von Begrüßung bis Ende. "
    "Mindestens 30% der Szenarien: expected_tools=[]. "
    "Auch bei Abbrüchen: der Anrufer verabschiedet sich oder hängt genervt ein."
)
DEFAULT_EXTRA = (
    "Szenarien müssen realistische, vollständige Telefongespräche sein — "
    "von der Begrüßung bis zur Verabschiedung, so wie ein echter Anrufer beim Restaurant anrufen würde."
)


async def _call_openai(
    messages: List[Dict],
    openai_key: str,
    model: str = "gpt-4o",
    temperature: float = 0.9,
    max_tokens: int = 16000,
) -> str:
    """Call OpenAI chat completions and return the raw response text."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=openai_key)
    resp = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""


def _build_system_prompt(phase: int, count: int) -> str:
    cfg = PHASE_CONFIGS[phase]
    persona_list = "\n".join(
        f'  "{k}": {v}' for k, v in PERSONAS.items()
        if k in cfg["persona_weights"]
    )
    min_t, max_t = cfg["turns_range"]
    extra = {3: PHASE3_EXTRA, 4: PHASE4_EXTRA}.get(phase, DEFAULT_EXTRA)
    return SYSTEM_PROMPT_TEMPLATE.format(
        phase_name=cfg["name"],
        phase_description=cfg["description"],
        persona_list=persona_list,
        id_prefix=cfg["id_prefix"],
        min_turns=min_t,
        max_turns=max_t,
        extra_requirements=extra,
        count=count,
    )


async def _generate_batch(
    phase: int,
    count: int,
    openai_key: str,
    batch_num: int = 1,
) -> List[Dict]:
    """Generate one batch of scenario specs via OpenAI."""
    system = _build_system_prompt(phase, count)
    user = (
        f"Generiere exakt {count} Szenarien für Phase {phase}. "
        f"Batch {batch_num}. Antworte NUR mit dem JSON-Array."
    )
    logger.info(f"  OpenAI batch {batch_num}: generating {count} phase-{phase} scenarios...")
    raw = await _call_openai(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        openai_key=openai_key,
    )
    # Extract JSON array from response, with partial-recovery fallback
    m = re.search(r"\[[\s\S]*\]", raw)
    if not m:
        logger.warning(f"  Batch {batch_num}: no JSON array found in response")
        return []
    raw_json = m.group(0)
    try:
        specs = json.loads(raw_json)
        logger.info(f"  Batch {batch_num}: parsed {len(specs)} specs")
        return specs
    except json.JSONDecodeError as e:
        # Truncated response: salvage complete objects before the error
        logger.warning(f"  Batch {batch_num}: JSON parse error at char {e.pos}, attempting partial recovery")
        partial = raw_json[: e.pos]
        # Find last complete '},' or '}' followed by ']'
        last_brace = max(partial.rfind("},"), partial.rfind("}"))
        if last_brace > 0:
            salvage = partial[: last_brace + 1] + "]"
            try:
                specs = json.loads(salvage)
                logger.info(f"  Batch {batch_num}: partial recovery: {len(specs)} specs")
                return specs
            except json.JSONDecodeError:
                pass
        logger.warning(f"  Batch {batch_num}: partial recovery failed, skipping batch")
        return []


# --------------------------------------------------------------------------- #
# Spec → AudioScenario conversion
# --------------------------------------------------------------------------- #

_VALID_TOOLS = {
    "ai_greeting", "end_call", "transfer_to_tier2",
    "create_reservation", "check_availability",
    "create_order", "send_sms", "get_menu",
    "technical_issues_callback", "request_callback",
    "verify_address", "get_date_info",
}


def _spec_to_scenario_code(spec: Dict, phase: int, idx: int) -> str:
    """Convert a raw GPT spec dict to Python AudioScenario constructor code."""
    cfg = PHASE_CONFIGS[phase]
    sid = spec.get("id") or f"{cfg['id_prefix']}-gen-{idx:03d}"
    category = spec.get("category", "generated")
    description = spec.get("description", "Generated scenario")[:80]
    persona = spec.get("persona", "neutral")
    if persona not in PERSONAS:
        persona = "neutral"
    noise = spec.get("noise_variant", "clean")
    if noise not in ("clean", "restaurant_bg", "street", "speakerphone"):
        noise = "clean"

    raw_tools = spec.get("expected_tools", [])
    tools = [t for t in raw_tools if t in _VALID_TOOLS]

    turns_raw = spec.get("turns", [])
    if not turns_raw:
        return ""

    turns_code_parts = []
    for t in turns_raw:
        utterance = t.get("user", "").replace('"', '\\"').replace("\\", "\\\\")
        if not utterance.strip():
            continue
        keywords_raw = t.get("expected_keywords", [])
        if keywords_raw:
            kw_str = ", ".join(f'"{k}"' for k in keywords_raw[:5])
            turns_code_parts.append(
                f'        ScenarioTurn(user_utterance="{utterance}", '
                f'expected_keywords=[{kw_str}]),'
            )
        else:
            turns_code_parts.append(
                f'        ScenarioTurn(user_utterance="{utterance}"),'
            )

    if not turns_code_parts:
        return ""

    turns_code = "\n".join(turns_code_parts)
    tools_code = ", ".join(f'"{t}"' for t in tools)

    return textwrap.dedent(f'''\
    AudioScenario(
        id="{sid}",
        phase="phase{phase}",
        category="{category}",
        description="{description}",
        persona="{persona}",
        noise_variant="{noise}",
        turns=[
{turns_code}
        ],
        expected_tools=[{tools_code}],
    ),''')


# --------------------------------------------------------------------------- #
# Main generation pipeline
# --------------------------------------------------------------------------- #

async def generate_phase(
    phase: int,
    count: int,
    openai_key: str,
    batch_size: int = 50,
) -> List[Dict]:
    """Generate `count` scenario specs for the given phase.

    Splits into batches of `batch_size` to stay within token limits.
    Returns raw spec dicts (not AudioScenario objects).
    """
    all_specs: List[Dict] = []
    batch_num = 0
    while len(all_specs) < count:
        remaining = count - len(all_specs)
        batch_count = min(batch_size, remaining)
        batch_num += 1
        specs = await _generate_batch(phase, batch_count, openai_key, batch_num)
        all_specs.extend(specs)
        if not specs:
            logger.warning(f"  Empty batch {batch_num}, stopping early")
            break

    logger.info(f"Phase {phase}: generated {len(all_specs)} raw specs (target {count})")
    return all_specs[:count]


def write_scenario_file(
    specs: List[Dict],
    phase: int,
    output_path: str,
    append: bool = False,
) -> int:
    """Write scenario specs as a static Python file. Returns scenario count written.

    If append=True and the file exists, new scenarios are appended to the existing list.
    """
    cfg = PHASE_CONFIGS[phase]
    out = Path(output_path)
    const_name = f"PHASE{phase}_SCENARIOS"

    existing_count = 0
    if append and out.exists():
        # Count existing entries to continue numbering
        existing_count = out.read_text(encoding="utf-8").count("AudioScenario(")

    new_code_parts = []
    count = 0
    for idx, spec in enumerate(specs):
        code = _spec_to_scenario_code(spec, phase, existing_count + idx + 1)
        if code:
            new_code_parts.append(code)
            count += 1

    if not count:
        logger.warning(f"No valid scenarios to write")
        return 0

    if append and out.exists():
        # Insert new scenarios before the closing ']'
        existing = out.read_text(encoding="utf-8")
        insert_point = existing.rfind("]")
        new_block = "\n" + "\n".join(new_code_parts) + "\n"
        updated = existing[:insert_point] + new_block + existing[insert_point:]
        # Update the scenario count comment
        updated = re.sub(r"# \d+ scenarios in this file", f"# {existing_count + count} scenarios in this file", updated)
        out.write_text(updated, encoding="utf-8")
        logger.info(f"Appended {count} scenarios to {output_path} (total: {existing_count + count})")
        return count

    lines = []
    lines.append(f'"""')
    lines.append(f'{cfg["name"]} — Generated Scenarios')
    lines.append(f'')
    lines.append(f'Auto-generated by server/training/scenario_generator.py')
    lines.append(f'DO NOT EDIT BY HAND — re-run the generator with --append to add more.')
    lines.append(f'"""')
    lines.append('')
    lines.append('from server.scenarios.base import AudioScenario, ScenarioTurn')
    lines.append('')
    lines.append(f'{const_name} = [')
    lines.extend(new_code_parts)
    lines.append(']')
    lines.append('')
    lines.append(f'# {count} scenarios in this file')
    lines.append('')

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Wrote {count} scenarios to {output_path}")
    return count


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

async def _main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Demo Training Loop — Scenario Generator")
    parser.add_argument(
        "--phase", type=int, choices=[1, 2, 3, 4],
        help="Generate scenarios for a single phase",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Generate all 4 phases (40+100+100+40)",
    )
    parser.add_argument(
        "--count", type=int, default=None,
        help="Number of scenarios (overrides phase default)",
    )
    parser.add_argument(
        "--out", type=str, default=None,
        help="Output file path (single phase only)",
    )
    parser.add_argument(
        "--out-dir", type=str, default="server/scenarios",
        help="Output directory for --all mode",
    )
    parser.add_argument(
        "--batch-size", type=int, default=50,
        help="Scenarios per OpenAI call (default 50)",
    )
    parser.add_argument(
        "--openai-key", type=str, default=os.environ.get("OPENAI_API_KEY"),
        help="OpenAI API key (default: OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--append", action="store_true",
        help="Append new scenarios to existing output file instead of overwriting",
    )
    args = parser.parse_args()

    if not args.openai_key:
        parser.error("OpenAI API key required (--openai-key or OPENAI_API_KEY env var)")

    phase_counts = {1: 40, 2: 100, 3: 100, 4: 40}

    if args.all:
        for p in [1, 2, 3, 4]:
            count = phase_counts[p]
            out_path = Path(args.out_dir) / f"phase{p}_scenarios.py"
            specs = await generate_phase(p, count, args.openai_key, args.batch_size)
            written = write_scenario_file(specs, p, str(out_path), append=args.append)
            print(f"Phase {p}: {written} scenarios → {out_path}")
    elif args.phase:
        count = args.count or phase_counts[args.phase]
        out_path = args.out or f"server/scenarios/phase{args.phase}_scenarios.py"
        specs = await generate_phase(args.phase, count, args.openai_key, args.batch_size)
        written = write_scenario_file(specs, args.phase, out_path, append=args.append)
        print(f"Phase {args.phase}: {written} scenarios → {out_path}")
    else:
        parser.error("Specify --phase N or --all")


if __name__ == "__main__":
    asyncio.run(_main())
