"""
layer2/system_prompt.py — System-prompt construction for Sailly's main LLM.

Exports:
  SAILLY_PERSONA  — core persona text (imported from node _prompts for DRY)
  FEW_SHOT_EXAMPLES — 3 canonical turn pairs (German, voice-optimised)
  build_system_prompt(node_prompt, menu_text, tenant_cfg) → str
  render_compact_menu(menu_dict_or_cfg) → str  — names + prices only, no details
  render_standard_facts(tenant_cfg) → str      — address, hours, phone, parking

Phase 8 grounding additions (per decisions):
  - inline-names-prices: compact menu inlined every turn
  - all-standard-facts: address, hours, phone, parking, delivery zones
  - explicit-uncertainty: "Das weiß ich nicht genau" pattern
  - cap-3-sentences: soft length cap as prompt instruction
"""
from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

from server.brain.layer1.nodes._prompts import (
    CONFIRM_DATA_RULE,
    NO_GREETING_RULE,
    OFF_TOPIC_RULE,
    PERSONA,
    PLAIN_TEXT_RULE,
    SIE_RULE,
    WORD_CAP_RULE,
)

# Re-export for callers that import from here
SAILLY_PERSONA = PERSONA

# ── Phase 8 grounding instructions ────────────────────────────────────────────

UNCERTAINTY_INSTRUCTION_DE = (
    "Wenn du dir bei einer Tatsache unsicher bist (Preis, Verfügbarkeit, "
    "ein Detail das nicht in der Karte steht), sage: "
    "'Das weiß ich nicht genau, ich verbinde Sie mit einem Mitarbeiter.' "
    "Spekuliere nicht. Erfinde keine Preise, Zeiten oder Details."
)

LENGTH_CAP_INSTRUCTION_DE = (
    "Halte deine Antworten kurz: maximal drei Sätze pro Turn. "
    "Bei Read-back-Bestätigungen darf es etwas länger sein."
)

# ── Three canonical few-shot examples ────────────────────────────────────────
FEW_SHOT_EXAMPLES: List[Dict[str, str]] = [
    {
        "label": "Simple order (pickup)",
        "user":  "Ich hätte gerne ein Bibimbap zum Abholen.",
        "sailly": (
            "Gerne — ein Bibimbap zum Abholen. "
            "Auf welchen Namen darf ich die Bestellung aufnehmen?"
        ),
    },
    {
        "label": "Reservation request",
        "user":  "Ich möchte einen Tisch für vier Personen reservieren, Freitag um 19 Uhr.",
        "sailly": (
            "Klar — vier Personen, Freitagabend um 19 Uhr. "
            "Und auf welchen Namen soll ich reservieren?"
        ),
    },
    {
        "label": "Allergy question (liability rule)",
        "user":  "Ist das Bulgogi-Bowl glutenfrei?",
        "sailly": (
            "Für verbindliche Allergen- und Zutateninformationen verweise ich Sie gerne an unser Team vor Ort — "
            "dort kann das jemand persönlich prüfen. Soll ich Sie kurz verbinden?"
        ),
    },
]


def _format_few_shots() -> str:
    """Render FEW_SHOT_EXAMPLES as a prompt block."""
    lines = ["BEISPIELE (Vorlage — bitte ähnlichen Stil verwenden):"]
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, 1):
        lines.append(f"\nBeispiel {i} — {ex['label']}:")
        lines.append(f"  Anrufer: {ex['user']}")
        lines.append(f"  Sailly:  {ex['sailly']}")
    return "\n".join(lines)


def render_standard_facts(tenant_cfg: dict) -> str:
    """
    Per all-standard-facts: address, hours today, phone, parking, delivery zones.

    Inlined every turn so the LLM never has to guess factual restaurant details.
    """
    if not tenant_cfg:
        return ""

    location = tenant_cfg.get("location", {})
    lines: List[str] = [
        f"Restaurant: {tenant_cfg.get('restaurant_name', 'Restaurant')}",
        f"Adresse: {location.get('address', 'unbekannt')}",
    ]
    if phone := location.get("phone"):
        lines.append(f"Telefon: {phone}")

    # Today's hours from tenant YAML
    opening = tenant_cfg.get("opening_hours", {})
    formatted = opening.get("formatted")
    if formatted:
        lines.append(f"Öffnungszeiten: {formatted}")
    else:
        try:
            day_key = datetime.datetime.now().strftime("%A").lower()
            day_hours = opening.get(day_key)
            if day_hours:
                lines.append(f"Heutige Öffnungszeiten: {day_hours}")
        except Exception:
            pass

    if parking := location.get("parking"):
        lines.append(f"Parken: {parking}")

    delivery = tenant_cfg.get("delivery", {})
    if zone_desc := delivery.get("description"):
        lines.append(f"Lieferzone: {zone_desc}")

    return "\n".join(lines)


def build_system_prompt(
    node_prompt: str = "",
    menu_text: str = "",
    *,
    include_few_shots: bool = True,
    voice_mood: str = "NEUTRAL",
    voice_situation: str = "INFO_NEUTRAL",
    tenant_cfg: Optional[dict] = None,
) -> str:
    """
    Assemble the full system prompt for a turn.

    Args:
        node_prompt:       Current node's focused instruction (from Node.prompt).
        menu_text:         Pre-rendered compact menu string (optional). If not
                           provided and tenant_cfg is given, render_compact_menu()
                           is called automatically.
        include_few_shots: Inject FEW_SHOT_EXAMPLES (default True).
        voice_mood:        Caller mood key from CALLER_MIRRORS (Phase 7).
        voice_situation:   Situation key from SITUATION_STYLES (Phase 7).
        tenant_cfg:        Full tenant config dict for Phase 8 grounding.
                           When present, standard facts + menu are inlined.

    Returns a single string suitable for GenerativeModel(system_instruction=...).
    """
    from server.brain.tts.situation_styles import SITUATION_STYLES
    from server.brain.tts.caller_mirrors import CALLER_MIRRORS

    parts: List[str] = [
        PERSONA,
        SIE_RULE,
        PLAIN_TEXT_RULE,
        WORD_CAP_RULE,
        NO_GREETING_RULE,
        OFF_TOPIC_RULE,
        CONFIRM_DATA_RULE,
    ]

    # Phase 8 — uncertainty + length cap instructions (grounding)
    parts.append(f"\n{UNCERTAINTY_INSTRUCTION_DE}")
    parts.append(LENGTH_CAP_INSTRUCTION_DE)

    # Phase 8 — standard facts (address, hours, phone, parking)
    if tenant_cfg:
        facts = render_standard_facts(tenant_cfg)
        if facts:
            parts.append(f"\nINFORMATIONEN ZUM RESTAURANT:\n{facts}")

    # Phase 7 — voice conditioning fragments injected into system prompt
    sit_style = SITUATION_STYLES.get(voice_situation)
    if sit_style and sit_style.get("prompt_add"):
        parts.append(f"\nSTILHINWEIS: {sit_style['prompt_add']}")

    mirror = CALLER_MIRRORS.get(voice_mood)
    if mirror:
        if mirror.get("prompt_add"):
            parts.append(f"\nSTIMMUNG DES ANRUFERS: {mirror['prompt_add']}")
        if mirror.get("skip_chitchat"):
            parts.append(
                "\nWICHTIG: Der Anrufer ist ungeduldig. Beginne NICHT mit "
                "Höflichkeitsphrasen wie «Sehr gerne!», «Natürlich!» oder "
                "«Selbstverständlich!». Antworte direkt und knapp."
            )

    # Menu — prefer explicit menu_text; auto-render from tenant_cfg if absent
    effective_menu = menu_text
    if not effective_menu and tenant_cfg:
        effective_menu = render_compact_menu(tenant_cfg.get("menu", {}))
    if effective_menu:
        parts.append(f"\nKARTE (Namen und Preise — nutze nur diese Werte):\n{effective_menu}")

    if include_few_shots:
        parts.append(_format_few_shots())

    if node_prompt:
        parts.append(f"\nAKTUELLE AUFGABE (überschreibt Allgemeines):\n{node_prompt}")

    return "\n".join(parts)


def render_compact_menu(menu: Any) -> str:
    """
    Produce a compact menu string (name + price only) from a menu dict or list.

    Accepts several shapes:
      - list of {"name": str, "price": float, ...}
      - dict of {"items": [...]}
      - dict of {"categories": {cat: [...]}}

    Unknown shapes are serialised with str() as a last resort.
    """
    if not menu:
        return ""

    items: List[Dict] = []

    if isinstance(menu, list):
        items = menu
    elif isinstance(menu, dict):
        if "items" in menu:
            items = menu["items"]
        elif "categories" in menu:
            categories = menu["categories"]
            # categories may be a list [{"name": ..., "items": [...]}]
            # or a dict {"category_name": [...]} — handle both
            if isinstance(categories, list):
                for cat in categories:
                    if isinstance(cat, dict):
                        items.extend(cat.get("items") or [])
            elif isinstance(categories, dict):
                for cat_items in categories.values():
                    if isinstance(cat_items, list):
                        items.extend(cat_items)
        else:
            # Flat dict: {name: price}
            lines = []
            for name, price in menu.items():
                if isinstance(price, (int, float)):
                    lines.append(f"  {name} — {price:.2f} Euro")
                else:
                    lines.append(f"  {name}")
            return "\n".join(lines) if lines else str(menu)

    lines: List[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("title") or str(item)
        price = item.get("price") or item.get("preis")
        if price is not None:
            try:
                lines.append(f"  {name} — {float(price):.2f} Euro")
            except (ValueError, TypeError):
                lines.append(f"  {name} — {price}")
        else:
            lines.append(f"  {name}")

    return "\n".join(lines)
