#!/usr/bin/env python3
"""
Convert phase2 and phase3 scripted scenarios to goal-driven reactive mode.

- order / reservation / chaos → ReactiveCallerLLM (goal + caller details)
- faq / opening_hours / menu  → keep scripted turns (deterministic, no tool gates)

Run with:  python -m server.training.convert_to_reactive
"""
import ast
import os
import re
import sys
import textwrap
from pathlib import Path

# ── regex helpers ──────────────────────────────────────────────────────────────

_NAME_RE  = re.compile(
    r"(?:Name ist|Ich hei[ßs]e|Mein Name ist|name is)\s+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)",
    re.I,
)
_PHONE_RE = re.compile(r"((?:\+49|0)\d[\d\s]{7,})")
_ADDR_RE  = re.compile(
    r"([A-ZÄÖÜ][a-zäöüß-]+(?: \d+)?(?:straße|allee|weg|gasse|platz|ring|ufer|damm|[Ss]tr\.?)"
    r"[^,\n]*,\s*(?:\d{5}\s+)?[A-ZÄÖÜ][a-zA-Zäöüß ]+)",
    re.I,
)
# Also pick up bare "Straße 1, Bonn" without the street-type in the first match
_ADDR_RE2 = re.compile(r"([A-ZÄÖÜ][a-zäöüß-]+ \d+,\s*[A-ZÄÖÜ][a-zA-Zäöüß ]+)", re.I)

_FOOD_RE  = re.compile(
    r"(Bibimbap|Bulgogi|Kimchi(?:suppe)?|Tteokbokki|Ramen|Japchae|Pajeon|Galbi|Sundubu|Naengmyeon)",
    re.I,
)
_FOOD_DESC_RE = re.compile(
    r"(Bibimbap|Bulgogi|Kimchi|Tteokbokki|Ramen|Japchae|Pajeon|Galbi|Sundubu|Naengmyeon)",
    re.I,
)
_DELIVERY_RE = re.compile(r"\b(lieferung|liefer|delivery|geliefert|liefern)\b", re.I)
_PICKUP_RE   = re.compile(r"\b(abholung|abhol|abholen|pickup|pick.?up)\b", re.I)

_PARTY_RE = re.compile(r"(?:für\s+)?(\w+)\s+(?:Personen?|persons?)", re.I)
_TIME_RE  = re.compile(r"(\d{1,2}(?::\d{2})?\s*Uhr|\d{1,2}(?::\d{2})\s*h)", re.I)
_DAY_RE   = re.compile(
    r"(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag"
    r"|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
    r"|heute|morgen|übermorgen|Wochenende)", re.I
)


def _all_text(turns_text: str) -> str:
    """Concatenate all user_utterance strings from a turns block."""
    return " ".join(re.findall(r'user_utterance="([^"]+)"', turns_text))


def _extract_caller_info(turns_text: str, category: str = "") -> dict:
    blob = _all_text(turns_text)
    info: dict = {}

    m = _NAME_RE.search(blob)
    if m:
        info["caller_name"] = m.group(1).strip()

    m = _PHONE_RE.search(blob)
    if m:
        info["caller_phone"] = re.sub(r"\s+", "", m.group(1)).strip()

    # Only extract delivery address for order scenarios
    # (reservation/chaos callers don't have addresses — they're picked up in-call)
    if category == "order":
        m = _ADDR_RE.search(blob) or _ADDR_RE2.search(blob)
        if m:
            addr = m.group(1).strip()
            # Sanity-check: must be short and not contain question-word noise
            if len(addr) < 60 and "?" not in addr and "weit" not in addr.lower():
                info["caller_address"] = addr

    return info


def _build_goal(category: str, description: str, turns_text: str) -> str:
    blob = _all_text(turns_text)

    if category in ("order",):
        # Try to find food in both the scripted turns and the description
        food = _FOOD_RE.findall(blob) or _FOOD_DESC_RE.findall(description)
        food_str = " and ".join(dict.fromkeys(food)) if food else "a meal"
        delivery = bool(_DELIVERY_RE.search(blob)) or bool(_DELIVERY_RE.search(description))
        pickup   = bool(_PICKUP_RE.search(blob)) or bool(_PICKUP_RE.search(description))
        mode = "for delivery" if delivery else ("for pickup" if pickup else "")
        return f"Order {food_str} {mode}".strip() + "."

    if category in ("reservation",):
        party = _PARTY_RE.search(blob)
        day   = _DAY_RE.search(blob)
        time  = _TIME_RE.search(blob)
        parts = ["Book a table"]
        if party:
            parts.append(f"for {party.group(1)} people")
        if day:
            parts.append(f"on {day.group(1)}")
        if time:
            parts.append(f"at {time.group(1)}")
        return " ".join(parts) + "."

    if category in ("chaos", "edge_case"):
        return f"{description}. The caller is confused and may change their mind."

    # fallback
    return description + "."


_WORD_TO_NUM = {
    "ein": "1", "eine": "1", "zwei": "2", "drei": "3", "vier": "4",
    "fünf": "5", "sechs": "6", "sieben": "7", "acht": "8", "neun": "9",
    "zehn": "10",
}

# ── source file rewriter ───────────────────────────────────────────────────────

_REACTIVE_CATEGORIES = {"order", "reservation", "chaos", "edge_case"}
_SCRIPTED_CATEGORIES = {"faq", "opening_hours", "menu", "smoke"}

_SCENARIO_RE = re.compile(r"AudioScenario\s*\(.*?\n\)", re.DOTALL)


def _rewrite_scenario(match_text: str) -> str:
    """Rewrite a single AudioScenario block to goal-based if needed."""

    # Extract key fields via regex (faster than ast.parse on snippets)
    def _field(name: str) -> str:
        m = re.search(rf'{name}="([^"]+)"', match_text)
        return m.group(1) if m else ""

    category    = _field("category")
    description = _field("description")
    sid         = _field("id")
    persona     = _field("persona") or "neutral"
    noise_v     = _field("noise_variant") or "clean"
    phase       = _field("phase") or "phase2"

    # Extract expected_tools
    tools_m = re.search(r"expected_tools=\[(.*?)\]", match_text, re.DOTALL)
    tools_str = tools_m.group(0) if tools_m else "expected_tools=[]"

    # Extract turns block
    turns_m = re.search(r"turns=\[(.*?)\],", match_text, re.DOTALL)
    turns_str = turns_m.group(0) if turns_m else "turns=[],"

    if category.lower() in _SCRIPTED_CATEGORIES:
        return match_text  # keep as-is

    # Build goal + caller info
    goal   = _build_goal(category, description, turns_str)
    caller = _extract_caller_info(turns_str, category)

    # Determine max_turns by category
    max_turns = 10 if category in ("chaos", "edge_case") else 8

    # Build reactive scenario block
    caller_lines = []
    if caller.get("caller_name"):
        caller_lines.append(f'    caller_name="{caller["caller_name"]}",')
    if caller.get("caller_phone"):
        caller_lines.append(f'    caller_phone="{caller["caller_phone"]}",')
    if caller.get("caller_address"):
        caller_lines.append(f'    caller_address="{caller["caller_address"]}",')

    block = f"""\
AudioScenario(
    id="{sid}",
    phase="{phase}",
    category="{category}",
    description="{description}",
    persona="{persona}",
    noise_variant="{noise_v}",
    goal="{goal}",
{chr(10).join(caller_lines)}
    max_turns={max_turns},
    turns=[],
    {tools_str},
)"""
    return block


def rewrite_file(src: Path) -> None:
    text = src.read_text()
    new_text = _SCENARIO_RE.sub(lambda m: _rewrite_scenario(m.group(0)), text)
    src.write_text(new_text)
    print(f"[convert] Rewrote {src} ({text.count('AudioScenario(')} scenarios)")


def main() -> None:
    base = Path(__file__).parent.parent / "scenarios"
    targets = [
        base / "phase2_scenarios.py",
        base / "phase3_scenarios.py",
    ]
    for f in targets:
        if f.exists():
            rewrite_file(f)
        else:
            print(f"[convert] SKIP (not found): {f}")
    print("[convert] Done. FAQ/smoke scenarios kept scripted; order/reservation/chaos converted to reactive.")


if __name__ == "__main__":
    main()
