"""
get_menu — return the restaurant menu.

Phase 6 task 6.7 (verification):
  Phase 4 added state.cached_menu. This handler implements the caching policy:
    - First call: fetch from executor + cache in state.cached_menu
    - Subsequent calls: return from state.cached_menu (no network request)
    - Cache scoped to the call (cleared on call end)

Decision: tool-get-menu: cached-in-state
"""
from __future__ import annotations

import logging

from server.tools.common.context import ToolContext
from server.tools.common.error_codes import ErrorCode
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "get_menu"


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args:
      category: str — optional category filter ("mains", "drinks", etc.)
      lang:     str — language ("de" | "en"), default "de"
    """
    state = ctx.state

    # ── Return from cache (Phase 4 decision) ─────────────────────────────────
    cached_menu = getattr(state, "cached_menu", None) if state else None
    if cached_menu:
        logger.debug("[get_menu] returning from state.cached_menu (call_sid=%s)", ctx.call_sid)
        menu = _filter_category(cached_menu, args.get("category"))
        return ToolResult(
            ok=True,
            data={
                "menu": menu,
                "from_cache": True,
                "cached_at_turn": getattr(state, "cached_menu_at_turn", None),
            },
        )

    # ── Fetch from executor and cache ─────────────────────────────────────────
    try:
        from tools.executor import _get_menu as _legacy  # type: ignore
        result = await _legacy(args, ctx.call_sid, ctx.tenant_id)

        if result.get("error"):
            return ToolResult(ok=False, data=result, error=result["error"], error_code=ErrorCode.TOOL_DEPENDENCY_ERROR)

        # Cache on state per Phase 4 policy
        if state is not None:
            raw_menu = result.get("menu") or result
            state.cached_menu = raw_menu
            state.cached_menu_at_turn = getattr(state, "turn_idx", 0)
            state.menu_fetched = True
            logger.debug("[get_menu] menu cached (call_sid=%s)", ctx.call_sid)

        menu = _filter_category(result.get("menu") or result, args.get("category"))
        return ToolResult(
            ok=True,
            data={"menu": menu, "from_cache": False},
        )
    except ImportError:
        # Fallback: try to load from tenant YAML
        tenant_menu = ctx.get_tenant_value("menu", default={})
        if tenant_menu and state is not None:
            state.cached_menu = tenant_menu
        menu = _filter_category(tenant_menu, args.get("category"))
        return ToolResult(
            ok=True,
            data={"menu": menu, "from_cache": bool(tenant_menu), "source": "tenant_yaml"},
        )


def _filter_category(menu: dict, category: str | None) -> dict:
    """Filter menu to a specific category if requested."""
    if not category or not isinstance(menu, dict):
        return menu
    # Try exact key
    if category in menu:
        return {category: menu[category]}
    # Try case-insensitive
    cat_lower = category.lower()
    for k, v in menu.items():
        if k.lower() == cat_lower:
            return {k: v}
    return menu  # return full menu if category not found
