"""server/brain/pipeline_helpers.py — Shared helpers for v4_pipeline_* modules.

These functions were originally in v4_pipeline_legacy and are extracted for
reuse by v4_pipeline_clean and other pipeline implementations.

Functions:
- format_address_for_speech: Remove country suffixes for local speech
- _state_snapshot_for_gate: Snapshot state fields for commit gate
- _default_menu_price_label: Get (price, label) for menu item with size preference
"""

from typing import Optional, Tuple, Dict, Any


def format_address_for_speech(address: str) -> str:
    """Remove country suffixes that are unnecessary in local restaurant speech."""
    text = (address or "").strip()
    for suffix in (", Germany", ", Deutschland", ", DE"):
        if text.endswith(suffix):
            return text[: -len(suffix)].strip().rstrip(",")
    return text


def _state_snapshot_for_gate(state: Any) -> Dict[str, Any]:
    """Subset of ConversationState fields used by the universal commit gate.

    Maps the canonical state field names onto the slot names declared in
    COMMIT_TOOLS_REQUIRED_SLOTS so the gate's slot-filled check works
    transparently for both reservation and order intents.
    """
    items = getattr(state, "selected_items", None)
    if not items:
        # Fall back to single dish as a one-element list so the gate sees it.
        sd = getattr(state, "selected_dish", None)
        items = [sd] if sd else None
    return {
        "party_size": getattr(state, "party_size", None),
        "reservation_date": getattr(state, "reservation_date", None),
        "reservation_time": getattr(state, "reservation_time", None),
        "customer_name": getattr(state, "customer_name", None) or getattr(state, "first_name", None),
        "phone_number": getattr(state, "phone_number", None),
        "order_items": items,
    }


def _default_menu_price_label(
    item: Dict[str, Any],
    preferred_size: Optional[str] = None
) -> Tuple[Optional[float], str]:
    """Return (price, label) for a menu item, respecting caller-stated size preference.

    If ``preferred_size`` is given (e.g. "0.5L", "groß"), prefer the variant
    whose ``size`` field contains that string (case-insensitive). Falls back to
    the first delivery-eligible catalog variant, not the cheapest.
    """
    name = str(item.get("name") or "").strip()
    price = item.get("price") or item.get("preis")
    if price is not None:
        return float(price), name
    variants = item.get("variants") or []
    candidates = []
    if isinstance(variants, list):
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            variant_price = variant.get("price") or variant.get("preis")
            if variant_price is None:
                continue
            eligible = variant.get("delivery_eligible", True) is not False
            size = str(variant.get("size") or "").strip()
            candidates.append((not eligible, float(variant_price), size))
    if not candidates:
        return None, name
    # P2_11: prefer caller-stated size over cheapest variant
    if preferred_size:
        _pref = preferred_size.lower().replace(",", ".")
        for _not_eligible, _vp, _vs in candidates:
            if not _not_eligible and _pref in _vs.lower().replace(",", "."):
                label = f"{name} {_vs}".strip() if _vs else name
                return _vp, label
    _not_eligible, selected_price, selected_size = next(
        (row for row in candidates if not row[0]),
        candidates[0],
    )
    label = f"{name} {selected_size}".strip() if selected_size else name
    return selected_price, label
