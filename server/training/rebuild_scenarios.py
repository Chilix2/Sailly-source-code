#!/usr/bin/env python3
"""
Rebuild phase2_scenarios.py and phase3_scenarios.py:
  1. Deduplicate by ID (keep first occurrence).
  2. Add caller_name, caller_phone, caller_address to every reactive scenario.
  3. Fix goals to name exact DOBOO menu items and give specific reservation details.

Run from repo root:
  python3 -m server.training.rebuild_scenarios
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, "/home/charles2/sailly-google-fork")

from server.scenarios.phase2_scenarios import PHASE2_SCENARIOS
from server.scenarios.phase3_scenarios import PHASE3_SCENARIOS
from server.scenarios.base import AudioScenario

# ── Caller pool (rotate through scenarios) ────────────────────────────────────
_CALLERS = [
    ("Thomas Mueller",   "+49 176 12345678", "Berliner Str. 42, 10115 Berlin"),
    ("Anna Schmidt",     "+49 152 98765432", "Friedrichstr. 18, 10117 Berlin"),
    ("Marcus Weber",     "+49 160 55551234", "Kastanienallee 7, 10435 Berlin"),
    ("Julia Hoffmann",   "+49 170 33334444", "Karl-Marx-Allee 101, 10243 Berlin"),
    ("Stefan Bauer",     "+49 151 22223333", "Schönhauser Allee 55, 10437 Berlin"),
    ("Laura Fischer",    "+49 172 66667777", "Prenzlauer Allee 12, 10405 Berlin"),
]

# Known DOBOO dishes (must match KNOWN_DISHES in conversation_state.py exactly)
_DISHES = [
    "Bibimbap", "Bulgogi", "Kimchi Jjigae", "Tteokbokki",
    "Japchae", "Mandu", "Tofu Jjigae", "Tofu Bibimbap",
]

# ── Specific goal templates by category ───────────────────────────────────────
_ORDER_GOALS = [
    "Order {dish} for delivery to your home address. When asked, provide your name, address, and phone number.",
    "Order {dish} for home delivery. Give your delivery address and contact details only when the agent asks.",
    "Order {dish} to take away. Confirm your order clearly when asked.",
    "Order {dish} for delivery. You are in a hurry but provide all required details when asked.",
    "Order {dish} for delivery. Be polite but brief.",
]

_RESERVATION_GOALS = [
    "Reserve a table for 4 people this Saturday at 7 PM. Provide your name and phone when asked.",
    "Book a table for 2 people tonight at 8 PM. Give your contact details when the agent asks.",
    "Make a reservation for 3 people on Friday at 6:30 PM. Confirm when asked.",
    "Reserve a table for 6 people on Sunday at 1 PM. Provide name and phone number when asked.",
    "Book a table for 2 for tomorrow evening at 7:30 PM. Answer all questions clearly.",
]

_CHAOS_GOALS = [
    "First try to order {dish}, then change your mind and want {dish2} instead, then finally decide to order {dish} for delivery. Provide details only when asked.",
    "Start by asking about the menu, then order {dish} for delivery. Be indecisive but eventually commit to the order.",
    "First want to order {dish}, then ask if you can reserve a table for 2 tonight instead. Then change back to ordering. Provide details when the agent asks.",
    "Order {dish} for delivery but first ask about opening hours. Be somewhat confused but cooperative.",
    "Try to reserve a table for 4 on Saturday, then change to ordering {dish} for delivery. Provide your details when asked.",
]

_FAQ_GOALS = [
    "Ask about opening hours. Be polite and confirm the information.",
    "Ask about the menu options and what Korean dishes are available.",
    "Ask about parking near the restaurant.",
    "Ask whether the restaurant offers vegetarian or vegan options.",
    "Ask about delivery areas and minimum order amounts.",
]


def _caller(idx: int):
    return _CALLERS[idx % len(_CALLERS)]


def _dish(idx: int):
    return _DISHES[idx % len(_DISHES)]


def _dish2(idx: int):
    return _DISHES[(idx + 3) % len(_DISHES)]


def _fix_goal(s: AudioScenario, idx: int) -> str:
    cat = (s.category or "").lower()
    dish = _dish(idx)
    dish2 = _dish2(idx)

    if cat in ("order", "bestellen", "lieferung", "takeaway", "delivery"):
        templates = _ORDER_GOALS
        goal = templates[idx % len(templates)].format(dish=dish)
    elif cat in ("reservation", "reservierung", "reservieren"):
        templates = _RESERVATION_GOALS
        goal = templates[idx % len(templates)]
    elif cat in ("chaos", "multi_intent", "bestellen"):
        templates = _CHAOS_GOALS
        goal = templates[idx % len(templates)].format(dish=dish, dish2=dish2)
    elif cat in ("faq", "opening_hours", "menu"):
        templates = _FAQ_GOALS
        goal = templates[idx % len(templates)]
    elif cat in ("sleepy", "impatient", "angry", "accent", "edge_case"):
        # Use order goal by default for these behavioral categories
        goal = _ORDER_GOALS[idx % len(_ORDER_GOALS)].format(dish=dish)
    elif cat in ("escalation", "complaint", "transfer"):
        goal = f"Try to order {dish} but become frustrated with the service. Eventually request to speak to a human or escalate the issue."
    else:
        # Generic fallback
        if s.goal and len(s.goal) > 20 and any(d.lower() in s.goal.lower() for d in _DISHES):
            # Goal already mentions a specific dish — keep but append detail instruction
            goal = s.goal.rstrip(".") + ". Provide your name, address and phone only when the agent explicitly asks."
        else:
            goal = _ORDER_GOALS[idx % len(_ORDER_GOALS)].format(dish=dish)
    return goal


def _enrich(s: AudioScenario, idx: int) -> AudioScenario:
    """Return a new AudioScenario with deduplication-safe data."""
    is_reactive = s.goal is not None and len(s.turns) == 0

    if not is_reactive:
        # Scripted (FAQ etc.) — keep as-is
        return s

    name, phone, addr = _caller(idx)
    cat = (s.category or "").lower()

    # Only order/delivery scenarios need an address
    needs_address = cat in (
        "order", "bestellen", "lieferung", "takeaway", "delivery",
        "chaos", "multi_intent", "edge_case", "sleepy", "impatient",
        "angry", "accent",
    )

    new_goal = _fix_goal(s, idx)

    return AudioScenario(
        id=s.id,
        phase=s.phase,
        category=s.category,
        description=s.description,
        persona=s.persona,
        noise_variant=s.noise_variant,
        goal=new_goal,
        caller_name=name,
        caller_phone=phone,
        caller_address=addr if needs_address else None,
        max_turns=s.max_turns,
        turns=s.turns,
        expected_tools=s.expected_tools,
    )


def deduplicate(scenarios: list[AudioScenario]) -> list[AudioScenario]:
    seen: dict[str, AudioScenario] = {}
    for s in scenarios:
        if s.id not in seen:
            seen[s.id] = s
    return list(seen.values())


def _render_scenario(s: AudioScenario) -> str:
    lines = ["AudioScenario("]
    lines.append(f'    id="{s.id}",')
    lines.append(f'    phase="{s.phase}",')
    lines.append(f'    category="{s.category}",')
    lines.append(f'    description="{s.description}",')
    lines.append(f'    persona="{s.persona}",')
    lines.append(f'    noise_variant="{s.noise_variant}",')

    if s.goal is not None:
        # Escape any double-quotes in goal text
        goal_escaped = s.goal.replace('"', '\\"')
        lines.append(f'    goal="{goal_escaped}",')
    if s.caller_name:
        lines.append(f'    caller_name="{s.caller_name}",')
    if s.caller_phone:
        lines.append(f'    caller_phone="{s.caller_phone}",')
    if s.caller_address:
        lines.append(f'    caller_address="{s.caller_address}",')
    if s.goal is not None:
        lines.append(f'    max_turns={s.max_turns},')

    if s.turns:
        lines.append("    turns=[")
        for t in s.turns:
            utt = t.user_utterance.replace('"', '\\"')
            lines.append(f'        ScenarioTurn(user_utterance="{utt}"),')
        lines.append("    ],")
    else:
        lines.append("    turns=[],")

    if s.expected_tools:
        tools_str = ", ".join(f'"{t}"' for t in s.expected_tools)
        lines.append(f"    expected_tools=[{tools_str}],")
    else:
        lines.append("    expected_tools=[],")

    lines.append(")")
    return "\n".join(lines)


def write_file(path: str, var_name: str, scenarios: list[AudioScenario], docstring: str):
    rendered = [_render_scenario(s) for s in scenarios]
    body = ",\n".join(rendered)
    content = f'''\
"""
{docstring}
"""

from server.scenarios.base import AudioScenario, ScenarioTurn

{var_name} = [
{body},
]
'''
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote {len(scenarios)} unique scenarios to {path}")


def main():
    print(f"Phase 2: {len(PHASE2_SCENARIOS)} total scenarios")
    phase2_deduped = deduplicate(PHASE2_SCENARIOS)
    print(f"Phase 2: {len(phase2_deduped)} unique scenarios after dedup")

    print(f"Phase 3: {len(PHASE3_SCENARIOS)} total scenarios")
    phase3_deduped = deduplicate(PHASE3_SCENARIOS)
    print(f"Phase 3: {len(phase3_deduped)} unique scenarios after dedup")

    # Enrich with caller data and specific goals
    phase2_enriched = [_enrich(s, i) for i, s in enumerate(phase2_deduped)]
    phase3_enriched = [_enrich(s, i) for i, s in enumerate(phase3_deduped)]

    base = "/home/charles2/sailly-google-fork/server/scenarios"

    write_file(
        f"{base}/phase2_scenarios.py",
        "PHASE2_SCENARIOS",
        phase2_enriched,
        "Phase 2 — Tool-Call Inquiries — Scenarios\n\nRebuilt by server/training/rebuild_scenarios.py (deduplicated + enriched with caller data).",
    )
    write_file(
        f"{base}/phase3_scenarios.py",
        "PHASE3_SCENARIOS",
        phase3_enriched,
        "Phase 3 — Chaos & Multi-Intent — Scenarios\n\nRebuilt by server/training/rebuild_scenarios.py (deduplicated + enriched with caller data).",
    )

    print("\nDone. Run text validation next to check for regressions.")


if __name__ == "__main__":
    main()
