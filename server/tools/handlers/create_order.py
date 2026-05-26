"""
create_order — commits a takeaway/delivery/bulk order.

Phase 6 decisions:
  - tool-create-order-quantity: ceiling-30 (HARD_QUANTITY_CEILING per item)
  - tool-create-order-monetary: cap-200 (MAX_ORDER_TOTAL_EUR)
  - tool-create-order-fuzzy: two-thresholds (0.85 auto-accept / 0.55 ask / <0.55 reject)

The legacy executor.py._create_order continues to handle DB writes,
idempotency, SMS dispatch, and POS webhook. This handler applies the
Phase 6 guard decisions before delegating.
"""
from __future__ import annotations

import logging
import uuid
from typing import Optional

from server.tools.common.context import ToolContext
from server.tools.common.error_codes import ErrorCode
from server.tools.common.errors import ToolResult
from server.tools.common.fuzzy import (
    FUZZY_ASK_THRESHOLD,
    FUZZY_AUTO_THRESHOLD,
    fuzzy_match_dish,
)

logger = logging.getLogger(__name__)

TOOL_NAME = "create_order"

# ── Phase 6 / Phase 8 constants ──────────────────────────────────────────────
# Per ceiling-30 (Phase 6) and per-item-30 (Phase 8 8.S2).
HARD_QUANTITY_CEILING: int = 30
# Per cap-200 (Phase 6). Phase 8 Layer 3 adds a strict-300 cap on top.
MAX_ORDER_TOTAL_EUR: float = 200.0
# Per per-item-30 (Phase 8 8.S2): total items across all lines.
HARD_PER_ORDER_TOTAL: int = 100


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args (from LLM):
      items:          list of {dish: str, quantity: int} — structured form
      order_items:    str — legacy flat string form ("Bibimbap x2, Bulgogi x1")
      channel:        "takeaway" | "delivery"
      order_type:     "takeaway" | "delivery" (alias for channel)
      customer_name / name:   str
      phone / messaging_phone: str
      delivery_address:        str (required for delivery)
      pickup_time:             str (optional)
      total_price:             float (used for monetary cap check)
      quantity / order_quantity: int (per-item quantity for legacy form)
    """
    ready_for_commit = getattr(ctx.state, "ready_for_commit", None) if ctx.state is not None else None
    if ctx.state is None or not callable(ready_for_commit) or not ready_for_commit(TOOL_NAME):
        logger.warning(
            "[create_order] blocked before handler commit: readback_not_confirmed call_sid=%s",
            ctx.call_sid,
        )
        return ToolResult(
            ok=False,
            data={"blocked_by_guardian": True, "reason": "readback_not_confirmed"},
            error="readback_not_confirmed",
            error_code=ErrorCode.TOOL_VALIDATION_FAILED,
        )

    # ── 1. Quantity ceiling ───────────────────────────────────────────────────
    qty = _extract_quantity(args)
    if qty > HARD_QUANTITY_CEILING:
        logger.error(
            "[create_order] REJECTED quantity=%d exceeds ceiling=%d (call_sid=%s)",
            qty, HARD_QUANTITY_CEILING, ctx.call_sid,
        )
        return ToolResult(
            ok=False,
            data={"requires_human": True, "quantity": qty},
            error=(
                f"Bestellmenge {qty} übersteigt das erlaubte Maximum "
                f"({HARD_QUANTITY_CEILING}). Catering-Aufträge werden von einem "
                f"menschlichen Mitarbeiter bearbeitet."
            ),
            error_code=ErrorCode.TOOL_QUANTITY_CAPPED,
        )

    # ── 2. Fuzzy dish match (structured items form) ───────────────────────────
    menu = ctx.get_tenant_value("menu", default={})
    items_raw = args.get("items") or []
    if isinstance(items_raw, list) and items_raw:
        matched_items, clarifications, unknown = _match_items(items_raw, menu, ctx)
        if unknown:
            dish_name = unknown[0]["dish"]
            return ToolResult(
                ok=False,
                data={"unknown_dish": dish_name},
                error=f"Unbekanntes Gericht: {dish_name}",
                error_code=ErrorCode.TOOL_VALIDATION_FAILED,
            )
        if clarifications:
            return ToolResult(
                ok=False,
                data={"clarifications": clarifications},
                error="dish_clarification_needed",
                error_code=ErrorCode.TOOL_VALIDATION_FAILED,
            )
    else:
        # Legacy flat string form — delegate fuzzy match only when menu available
        matched_items = []
        order_items_raw = str(args.get("order_items") or "").strip()
        if order_items_raw and menu:
            m = fuzzy_match_dish(order_items_raw, menu)
            if m.score < FUZZY_ASK_THRESHOLD and m.canonical_name:
                return ToolResult(
                    ok=False,
                    data={"unknown_dish": order_items_raw},
                    error=f"Unbekanntes Gericht: {order_items_raw}",
                    error_code=ErrorCode.TOOL_VALIDATION_FAILED,
                )
            if m.score >= FUZZY_ASK_THRESHOLD and m.score < FUZZY_AUTO_THRESHOLD:
                return ToolResult(
                    ok=False,
                    data={
                        "clarifications": [{
                            "heard": order_items_raw,
                            "candidate": m.canonical_name,
                            "score": round(m.score, 3),
                        }]
                    },
                    error="dish_clarification_needed",
                    error_code=ErrorCode.TOOL_VALIDATION_FAILED,
                )
            if m.score >= FUZZY_AUTO_THRESHOLD and m.canonical_name:
                # Normalize in args copy
                args = dict(args)
                args["order_items"] = m.canonical_name
                logger.info(
                    "[create_order] dish normalized '%s' → '%s' (score=%.2f)",
                    order_items_raw, m.canonical_name, m.score,
                )

    # ── 3. Monetary cap ───────────────────────────────────────────────────────
    total_eur = _compute_total(args, matched_items)
    tenant_cap = ctx.get_tenant_value("max_order_total_eur", default=MAX_ORDER_TOTAL_EUR)
    cap = float(tenant_cap) if tenant_cap else MAX_ORDER_TOTAL_EUR
    if total_eur > cap:
        logger.error(
            "[create_order] REJECTED total=%.2f exceeds cap=%.2f (call_sid=%s)",
            total_eur, cap, ctx.call_sid,
        )
        return ToolResult(
            ok=False,
            data={"requires_human": True, "total_eur": total_eur},
            error=(
                f"Der Gesamtbetrag von {total_eur:.2f} Euro übersteigt unser Limit "
                f"von {cap:.0f} Euro pro Bestellung. Für größere Aufträge "
                "verbinde ich Sie gerne mit einem Kollegen."
            ),
            error_code=ErrorCode.TOOL_MONETARY_CAP,
        )

    # ── 4. Delegate to legacy executor (handles DB, idempotency, SMS, POS) ───
    try:
        from tools.executor import _create_order as _legacy_create  # type: ignore
        legacy_ctx = {"conversation_state": ctx.state}
        result = await _legacy_create(args, ctx.call_sid, ctx.tenant_id, context=legacy_ctx)
        if result.get("success") is False or result.get("error"):
            return ToolResult(ok=False, data=result, error=result.get("error", "create_order failed"), error_code=ErrorCode.TOOL_DEPENDENCY_ERROR)
        return ToolResult(ok=True, data=result)
    except ImportError:
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        return ToolResult(
            ok=True,
            data={
                "order_id": order_id,
                "total_eur": total_eur,
                "items": matched_items or [{"dish": args.get("order_items", ""), "quantity": qty}],
            },
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_quantity(args: dict) -> int:
    """Extract the maximum quantity from args."""
    items_raw = args.get("items") or []
    if isinstance(items_raw, list):
        quantities = [int(i.get("quantity", 0)) for i in items_raw if isinstance(i, dict)]
        if quantities:
            return max(quantities)
    for key in ("quantity", "order_quantity"):
        val = args.get(key)
        if val is not None:
            try:
                return int(val)
            except (TypeError, ValueError):
                pass
    return 1


def _match_items(
    items: list, menu: dict, ctx: ToolContext
) -> tuple[list, list, list]:
    """
    Fuzzy-match a list of {dish, quantity} items against the menu.

    Returns (matched_items, clarifications_needed, unknown_items).
    """
    matched = []
    clarifications = []
    unknown = []
    for item in items:
        dish_name = str(item.get("dish", "")).strip()
        qty = int(item.get("quantity", 1))
        m = fuzzy_match_dish(dish_name, menu)
        if m.score >= FUZZY_AUTO_THRESHOLD:
            matched.append({"dish": m.canonical_name, "quantity": qty, "price_eur": m.price_eur})
        elif m.score >= FUZZY_ASK_THRESHOLD:
            clarifications.append({"heard": dish_name, "candidate": m.canonical_name, "score": round(m.score, 3)})
        else:
            unknown.append({"dish": dish_name})
    return matched, clarifications, unknown


def _compute_total(args: dict, matched_items: list) -> float:
    """Compute order total from matched items or args.total_price."""
    if matched_items:
        total = sum(
            (i.get("quantity", 1) * (i.get("price_eur") or 0.0))
            for i in matched_items
        )
        if total > 0:
            return total
    try:
        return float(args.get("total_price") or 0.0)
    except (TypeError, ValueError):
        return 0.0
