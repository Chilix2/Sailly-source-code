"""
Fuzzy dish matching — Phase 6, create_order two-thresholds decision.

Per tool-create-order-fuzzy: two-thresholds
  - score >= FUZZY_AUTO_THRESHOLD (0.85) → auto-accept, normalize name
  - FUZZY_ASK_THRESHOLD (0.55) <= score < 0.85 → return for clarification
  - score < FUZZY_ASK_THRESHOLD → reject (unknown dish)

Extracted from tools/executor.py._fuzzy_match_dish so it can be shared
between the new handler and the legacy executor bridge.
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

FUZZY_AUTO_THRESHOLD = 0.85
FUZZY_ASK_THRESHOLD = 0.55


@dataclass
class FuzzyMatchResult:
    canonical_name: str
    price_eur: Optional[float]
    score: float
    matched: bool  # True if above FUZZY_ASK_THRESHOLD


def _extract_menu_dishes(menu: dict) -> list[dict]:
    """
    Walk the tenant menu dict and extract {name, price} pairs.

    Handles both flat `{category: [items]}` and nested category dicts.
    """
    dishes: list[dict] = []
    if not isinstance(menu, dict):
        return dishes

    categories = menu.get("categories") or menu
    if isinstance(categories, list):
        for cat in categories:
            for item in cat.get("items", []):
                dishes.append({
                    "name": item.get("name", ""),
                    "price": item.get("price"),
                })
    elif isinstance(categories, dict):
        for _cat_name, items in categories.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        dishes.append({
                            "name": item.get("name", ""),
                            "price": item.get("price"),
                        })

    return [d for d in dishes if d["name"]]


def fuzzy_match_dish(
    user_said: str,
    menu: dict,
    canonical_list: Optional[list[str]] = None,
) -> FuzzyMatchResult:
    """
    Return the best fuzzy match for user_said against the tenant menu.

    Args:
        user_said:      What the caller said (raw string).
        menu:           Tenant menu dict from tenant_cfg["menu"].
        canonical_list: Optional pre-built list of canonical dish names
                        (skips menu extraction if provided).

    Returns:
        FuzzyMatchResult with the best match. If no dishes found, returns
        a result with score=0 and matched=False.
    """
    if not user_said:
        return FuzzyMatchResult(canonical_name="", price_eur=None, score=0.0, matched=False)

    if canonical_list is not None:
        dishes = [{"name": n, "price": None} for n in canonical_list]
    else:
        dishes = _extract_menu_dishes(menu)

    if not dishes:
        return FuzzyMatchResult(canonical_name="", price_eur=None, score=0.0, matched=False)

    user_lower = user_said.lower().strip()
    best_score = 0.0
    best_dish: dict = {"name": "", "price": None}

    for dish in dishes:
        name = dish["name"].lower().strip()
        if not name:
            continue
        # Exact match wins immediately
        if user_lower == name:
            return FuzzyMatchResult(
                canonical_name=dish["name"],
                price_eur=_safe_float(dish.get("price")),
                score=1.0,
                matched=True,
            )
        # Substring wins with high score
        if user_lower in name or name in user_lower:
            score = 0.9
        else:
            score = SequenceMatcher(None, user_lower, name).ratio()

        if score > best_score:
            best_score = score
            best_dish = dish

    matched = best_score >= FUZZY_ASK_THRESHOLD
    return FuzzyMatchResult(
        canonical_name=best_dish["name"],
        price_eur=_safe_float(best_dish.get("price")),
        score=best_score,
        matched=matched,
    )


def _safe_float(value: object) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
