"""
server/brain/stt/keyterm_loader.py
------------------------------------
Canonical source for Deepgram ASR keyterm hints.

Replaces the ad-hoc ``TenantConfig.asr_keywords()`` call in ``main.py`` with a
dedicated module that:
  - Reads ``menu.categories[].items[].name`` from tenant config (primary source)
  - Falls back to ``TenantConfig.asr_keywords()`` for backwards-compatibility
  - Caches results for 60 seconds (TTL) to avoid repeated YAML parses
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

_CACHE: Dict[str, Tuple[float, List[str]]] = {}
_TTL_SECONDS: float = 60.0


def _extract_menu_names(tenant_cfg) -> List[str]:
    """Walk ``menu.categories[].items[].name`` from tenant YAML tool_data or audio."""
    names: List[str] = []

    # Try tool_data.menu first (ToolData model)
    try:
        tool_data = getattr(tenant_cfg, "tool_data", None)
        if tool_data is not None:
            menu = getattr(tool_data, "menu", None) or {}
            if isinstance(menu, dict):
                for cat in menu.get("categories", []):
                    for item in cat.get("items", []):
                        name = item.get("name") if isinstance(item, dict) else None
                        if name and isinstance(name, str):
                            names.append(name)
    except Exception:
        pass

    return names


def get_keyterms_for_tenant(tenant_id: str) -> List[str]:
    """Return deduplicated ASR keyterm list for *tenant_id* with 60s TTL cache.

    Resolution order:
      1. menu.categories[].items[].name from ``tool_data.menu``
      2. ``TenantConfig.asr_keywords()`` (items + extra_*_keywords)

    Results are deduplicated (case-insensitive) and cached for 60 seconds.
    """
    now = time.monotonic()
    cached = _CACHE.get(tenant_id)
    if cached is not None:
        ts, terms = cached
        if now - ts < _TTL_SECONDS:
            return list(terms)

    terms: List[str] = []
    try:
        from server.core.tenant_config import TenantRegistry
        tc = TenantRegistry().load_tenant(tenant_id)

        # Primary: menu item names from structured menu data
        menu_names = _extract_menu_names(tc)
        terms.extend(menu_names)

        # Secondary: asr_keywords() covers extra keyword lists + items field
        for kw in tc.asr_keywords():
            if kw not in terms:
                terms.append(kw)
    except Exception:
        pass

    # Deduplicate case-insensitively, preserving first occurrence
    seen: set = set()
    deduped: List[str] = []
    for t in terms:
        lower = t.lower()
        if lower not in seen:
            seen.add(lower)
            deduped.append(t)

    _CACHE[tenant_id] = (now, deduped)
    return list(deduped)


def invalidate_cache(tenant_id: Optional[str] = None) -> None:
    """Invalidate cache for a specific tenant or all tenants."""
    if tenant_id is None:
        _CACHE.clear()
    else:
        _CACHE.pop(tenant_id, None)
