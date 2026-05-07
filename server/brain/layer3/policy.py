"""
Layer 3 — Policy / validation filter.

Phase 8 complete chain. Sits between Layer 2 (LLM output) and tool dispatch.
Deterministic and side-effect free (except logging + critical-alert log entries).

Guard execution order (highest priority first):

  SAFETY (cheapest / most damaging first):
    B1  check_tech_problem         — "technisches Problem" hard-block
    B2  check_quantity_in_tools    — per-item 30, per-order 100 ceiling
    B3  check_monetary_cap         — €300 hard cap
    B8  check_after_hours_orders   — belt-and-braces after-hours block
    B4  filter_bot_profanity        — bot output profanity filter

  HALLUCINATION (after safety so blacklist/price checks see cleaned text):
    A4  strip_blacklisted          — GLOBAL_BLACKLIST + tenant extension
    A2  check_prices_in_text       — regex price-must-match
    A5  check_length_cap           — hard 5-sentence ceiling

Each guard returns (text_or_tools, warnings_list). Warnings accumulate
and are returned in PolicyResult.warnings for google_turn_metrics.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── Phase 8 constants ──────────────────────────────────────────────────────────
HARD_PER_ITEM_CEILING: int = 30       # per safe-quantity-ceiling: per-item-30
HARD_PER_ORDER_TOTAL: int = 100       # per safe-quantity-ceiling: per-item-30 doc
HARD_MONETARY_CAP_EUR: float = 300.0  # per safe-monetary: strict-300
MAX_RESPONSE_SENTENCES: int = 5       # hard ceiling; soft target is 3 (prompt)


# ── Shared types ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict


@dataclass(frozen=True)
class PolicyWarning:
    code: str           # e.g. "TECH_PROBLEM_BLOCKED", "HALLUCINATED_PRICE"
    detail: str
    original: str = ""  # original content before rewrite (first 200 chars)


@dataclass(frozen=True)
class PolicyResult:
    """Return value of the policy filter."""
    text: str
    tools: List[ToolCall]
    warnings: List[PolicyWarning] = field(default_factory=list)


# ── Sentence splitter (shared) ─────────────────────────────────────────────────

def _split_sentences(text: str) -> list[str]:
    """German-aware sentence splitter. Handles . ! ? separators."""
    return re.split(r"(?<=[.!?])\s+", text.strip())


# ── Tenant helpers ─────────────────────────────────────────────────────────────

def _tenant_id_from_tp(turn_package) -> str:
    return getattr(turn_package, "call_sid", "").split("_")[0] or "doboo"


def _get_tenant_cfg(turn_package) -> dict:
    try:
        from server.core.tenant_config import get_tenant_config
        tenant_id = _tenant_id_from_tp(turn_package)
        cfg = get_tenant_config(tenant_id)
        return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def _menu_prices(tenant_cfg: dict) -> set[str]:
    """All valid menu prices as 'XX.YY' normalized strings."""
    prices: set[str] = set()
    for category in tenant_cfg.get("menu", {}).get("categories", []):
        for item in category.get("items", []):
            for key in ("price_eur", "price"):
                p = item.get(key)
                if p is not None:
                    try:
                        prices.add(f"{float(p):.2f}")
                        prices.add(f"{float(p):.2f}".replace(".", ","))
                    except (ValueError, TypeError):
                        pass
    return prices


def _menu_prices_dict(tenant_cfg: dict) -> dict[str, float]:
    """name (lower) → price_eur for monetary cap calculation."""
    result: dict[str, float] = {}
    for category in tenant_cfg.get("menu", {}).get("categories", []):
        for item in category.get("items", []):
            name = (item.get("name") or "").lower().strip()
            for key in ("price_eur", "price"):
                p = item.get(key)
                if p is not None and name:
                    try:
                        result[name] = float(p)
                    except (ValueError, TypeError):
                        pass
    return result


# ── B1: "Technisches Problem" hard-block ───────────────────────────────────────

_TECH_PROBLEM_PATTERNS: list[re.Pattern] = [
    re.compile(r"technisch(?:es|er|e|en)\s+problem", re.IGNORECASE),
    re.compile(r"funktioniert\s+(?:gerade|aktuell|im\s+Moment)\s+nicht", re.IGNORECASE),
    re.compile(r"entschuldigung,?\s+ich\s+kann\s+das\s+(?:gerade|aktuell)\s+nicht", re.IGNORECASE),
    re.compile(r"system\s+ist\s+(?:down|nicht\s+verf[uü]gbar)", re.IGNORECASE),
    re.compile(r"ein(?:en)?\s+(?:technisch|server|system)(?:er|en)?\s+fehler", re.IGNORECASE),
]
_TRANSFER_SUBSTITUTION_DE = "Einen Moment, ich verbinde Sie mit einem Mitarbeiter."


def check_tech_problem(
    text: str,
    tools: List[ToolCall],
) -> tuple[str, List[ToolCall], list[PolicyWarning]]:
    """
    Per hard-block (8.S1): replace any tech-problem admission with a
    transfer-to-human handoff phrase and inject transfer_to_human tool.
    Emits a critical-level log to trigger alerting (Phase 9 wires to Slack).
    """
    matched = any(p.search(text) for p in _TECH_PROBLEM_PATTERNS)
    if not matched:
        return text, tools, []

    has_transfer = any(t.name == "transfer_to_human" for t in tools)
    new_tools = list(tools)
    if not has_transfer:
        new_tools.append(ToolCall(
            name="transfer_to_human",
            args={"reason": "tech_problem_admission_blocked"},
        ))

    logger.critical(  # critical → Phase 9 alert hook
        "[POLICY:TECH_PROBLEM_BLOCKED] bot admitted technical issue — "
        "replaced with transfer. original=%r",
        text[:200],
    )
    # Phase 9 A4 — fire Slack alert asynchronously (never blocks policy chain)
    try:
        import asyncio as _asyncio
        from server.brain.observability.alerts import alert_tech_problem_blocked as _alert_tp
        _loop = _asyncio.get_event_loop()
        if _loop and _loop.is_running():
            _asyncio.ensure_future(_alert_tp(call_sid="", tenant_id=""))
    except Exception:
        pass  # alerting must never break the policy chain

    return _TRANSFER_SUBSTITUTION_DE, new_tools, [PolicyWarning(
        code="TECH_PROBLEM_BLOCKED",
        detail="bot admission of technical issue replaced with human handoff",
        original=text[:200],
    )]


# ── B2: Quantity ceiling ───────────────────────────────────────────────────────

def check_quantity_in_tools(
    tools: List[ToolCall],
) -> tuple[List[ToolCall], list[PolicyWarning]]:
    """
    Per safe-quantity-ceiling: per-item-30 (8.S2).
    Caps per-item at 30; drops create_order when total exceeds 100.
    """
    warnings: list[PolicyWarning] = []
    new_tools: list[ToolCall] = []

    for tc in tools:
        if tc.name == "create_order":
            raw_items: list[dict] = list(tc.args.get("items") or [])
            capped_items: list[dict] = []
            modified = False

            for item in raw_items:
                qty = item.get("quantity", 0)
                if isinstance(qty, (int, float)) and qty > HARD_PER_ITEM_CEILING:
                    warnings.append(PolicyWarning(
                        code="QUANTITY_CEILING",
                        detail=(
                            f"{item.get('name', '?')} qty {qty} "
                            f"capped to {HARD_PER_ITEM_CEILING}"
                        ),
                    ))
                    item = {**item, "quantity": HARD_PER_ITEM_CEILING}
                    modified = True
                capped_items.append(item)

            total = sum(
                item.get("quantity", 0) for item in capped_items
                if isinstance(item.get("quantity"), (int, float))
            )
            if total > HARD_PER_ORDER_TOTAL:
                warnings.append(PolicyWarning(
                    code="ORDER_TOTAL_CEILING",
                    detail=f"order total {total} items > {HARD_PER_ORDER_TOTAL} — escalating",
                ))
                logger.warning("[POLICY] order_total_ceiling %d > %d — dropping create_order", total, HARD_PER_ORDER_TOTAL)
                continue  # drop the tool call

            if modified:
                tc = ToolCall(name=tc.name, args={**tc.args, "items": capped_items})
        new_tools.append(tc)

    return new_tools, warnings


# ── B3: Monetary cap ──────────────────────────────────────────────────────────

def check_monetary_cap(
    tools: List[ToolCall],
    turn_package,
) -> tuple[List[ToolCall], list[PolicyWarning]]:
    """
    Per safe-monetary: strict-300 (8.S3).
    Drops create_order when computed total exceeds €300.
    """
    tenant_cfg = _get_tenant_cfg(turn_package)
    menu_prices = _menu_prices_dict(tenant_cfg)

    warnings: list[PolicyWarning] = []
    new_tools: list[ToolCall] = []

    for tc in tools:
        if tc.name == "create_order":
            items = tc.args.get("items") or []
            total_eur = sum(
                menu_prices.get((item.get("name") or "").lower().strip(), 0.0)
                * item.get("quantity", 0)
                for item in items
                if isinstance(item, dict)
            )
            if total_eur > HARD_MONETARY_CAP_EUR:
                warnings.append(PolicyWarning(
                    code="MONETARY_CAP",
                    detail=f"order total €{total_eur:.2f} > €{HARD_MONETARY_CAP_EUR:.2f} — escalating",
                ))
                logger.warning("[POLICY] monetary_cap €%.2f > €%.2f — dropping create_order", total_eur, HARD_MONETARY_CAP_EUR)
                continue  # drop the tool call
        new_tools.append(tc)

    return new_tools, warnings


# ── B8: After-hours order block (belt-and-braces) ─────────────────────────────

_ORDER_TOOLS: frozenset = frozenset({"create_order", "create_delivery"})


def check_after_hours_orders(
    text: str,
    tools: List[ToolCall],
    warnings: List[PolicyWarning],
    turn_package,
) -> tuple[str, List[ToolCall], List[PolicyWarning]]:
    """
    Belt-and-braces after-hours block per hard-block-orders (8.S10).

    Pre-orders (channel='pre_order') are allowed outside hours.
    Verification that Phase 2 after_hours.py still active:
    this guard fires independently of the Phase 2 gate.
    """
    if not tools:
        return text, tools, warnings

    try:
        from server.brain.layer1.after_hours import is_within_hours, earliest_pre_order_time
        if is_within_hours():
            return text, tools, warnings

        blocked: list[ToolCall] = []
        allowed: list[ToolCall] = []
        for t in tools:
            if t.name in _ORDER_TOOLS and t.args.get("channel") != "pre_order":
                blocked.append(t)
            else:
                allowed.append(t)

        if not blocked:
            return text, tools, warnings

        next_open = earliest_pre_order_time()
        next_open_str = (
            next_open.strftime("%A %d.%m. ab %H:%M Uhr") if next_open else "bei Öffnung"
        )
        new_warnings = list(warnings) + [PolicyWarning(
            code="AFTER_HOURS_BLOCKED",
            detail=f"blocked {[t.name for t in blocked]} — kitchen closed",
            original=text[:200],
        )]
        redirect_text = (
            f"Das Restaurant ist gerade geschlossen. "
            f"Die nächste Bestellung ist möglich ab {next_open_str}. "
            f"Möchten Sie eine Vorbestellung aufgeben?"
        )
        logger.warning("[POLICY] after_hours blocked %s", [t.name for t in blocked])
        return redirect_text, allowed, new_warnings

    except Exception as exc:
        logger.debug("[Policy.check_after_hours_orders] non-fatal: %s", exc)
        return text, tools, warnings


# ── B4: Bot profanity filter ──────────────────────────────────────────────────

def _filter_bot_profanity(text: str) -> tuple[str, list[PolicyWarning]]:
    """Delegates to profanity.py; local wrapper to keep cycle clean."""
    try:
        from server.brain.layer3.profanity import filter_bot_profanity
        return filter_bot_profanity(text)
    except ImportError:
        return text, []


# ── A4: Hallucination blacklist ───────────────────────────────────────────────

def _strip_blacklisted(
    text: str, turn_package,
) -> tuple[str, list[PolicyWarning]]:
    from server.brain.layer3.blacklist import strip_blacklisted
    tenant_id = _tenant_id_from_tp(turn_package)
    cleaned, removed = strip_blacklisted(text, tenant_id)
    warnings = [
        PolicyWarning(code="BLACKLIST", detail=f"stripped term: '{t}'", original=text[:200])
        for t in removed
    ]
    if removed:
        logger.warning("[POLICY] blacklist stripped %s terms from bot response", len(removed))
    return cleaned, warnings


# ── A2: Price regex check ─────────────────────────────────────────────────────

_PRICE_RE = re.compile(
    r"(?:€|EUR\s*)\s*(\d+[.,]\d{1,2})"     # €14,90 or EUR 14.90
    r"|(\d+[.,]\d{1,2})\s*(?:Euro|EUR|€)",  # 14,90 Euro
    re.IGNORECASE,
)


def check_prices_in_text(
    text: str,
    turn_package,
) -> tuple[str, list[PolicyWarning]]:
    """
    Per regex-price-check + prices-must-match (8.H6 + 8.H8).

    Scan text for price mentions; strip any sentence containing a price not
    in the tenant menu. Append a clarification phrase when sentences are stripped.
    """
    tenant_cfg = _get_tenant_cfg(turn_package)
    valid_prices = _menu_prices(tenant_cfg)

    if not valid_prices:
        return text, []  # no menu data — skip to avoid false positives

    sentences = _split_sentences(text)
    kept: list[str] = []
    warnings: list[PolicyWarning] = []

    for sentence in sentences:
        matches = _PRICE_RE.findall(sentence)
        if not matches:
            kept.append(sentence)
            continue

        flagged = False
        for m in matches:
            raw = (m[0] or m[1]).replace(",", ".")
            try:
                normalized = f"{float(raw):.2f}"
            except ValueError:
                continue
            if normalized not in {p.replace(",", ".") for p in valid_prices}:
                flagged = True
                warnings.append(PolicyWarning(
                    code="HALLUCINATED_PRICE",
                    detail=f"price {raw}€ not in menu",
                    original=sentence[:200],
                ))
                logger.warning("[POLICY] hallucinated_price %.2f stripped", float(raw))
                break

        if not flagged:
            kept.append(sentence)

    cleaned = " ".join(kept).strip()
    if warnings:
        cleaned += " Den genauen Preis schaue ich Ihnen kurz nach."
    return cleaned, warnings


# ── A5: Length cap ────────────────────────────────────────────────────────────

def check_length_cap(text: str) -> tuple[str, list[PolicyWarning]]:
    """
    Hard ceiling of 5 sentences per cap-3-sentences (8.H7) belt-and-braces.
    Soft target (3 sentences) is enforced via prompt instruction in system_prompt.py.
    """
    sentences = _split_sentences(text)
    if len(sentences) <= MAX_RESPONSE_SENTENCES:
        return text, []
    truncated = " ".join(sentences[:MAX_RESPONSE_SENTENCES])
    logger.info(
        "[POLICY] length_cap_truncated from %d to %d sentences",
        len(sentences), MAX_RESPONSE_SENTENCES,
    )
    return truncated, [PolicyWarning(
        code="LENGTH_CAP_TRUNCATED",
        detail=f"truncated from {len(sentences)} to {MAX_RESPONSE_SENTENCES} sentences",
        original=text[:200],
    )]


# ── Main check function ───────────────────────────────────────────────────────

def check(
    text: str,
    tools: List[ToolCall],
    turn_package,  # server.brain.contracts.turn_package.TurnPackage
) -> PolicyResult:
    """
    The Layer 3 filter. Order is fixed — see module docstring.

    Phase 8 full chain:
      Safety  → B1 tech-problem, B2 quantity, B3 monetary, B8 after-hours, B4 profanity
      Halluc. → A4 blacklist, A2 price-check, A5 length-cap
    """
    warnings: List[PolicyWarning] = []

    # ── SAFETY ────────────────────────────────────────────────────────────────
    # B1 — "technisches Problem" hard-block (never event, runs first)
    text, tools, w = check_tech_problem(text, tools)
    warnings.extend(w)

    # B2 — quantity ceiling
    tools, w = check_quantity_in_tools(tools)
    warnings.extend(w)

    # B3 — monetary cap
    tools, w = check_monetary_cap(tools, turn_package)
    warnings.extend(w)

    # B8 — after-hours order block (belt-and-braces over Phase 2 A6)
    text, tools, warnings = check_after_hours_orders(text, tools, warnings, turn_package)

    # B4 — bot profanity filter (caller input never passes through here)
    text, w = _filter_bot_profanity(text)
    warnings.extend(w)

    # ── HALLUCINATION ─────────────────────────────────────────────────────────
    # A4 — blacklist (runs before price check so blacklisted+price sentence is caught once)
    text, w = _strip_blacklisted(text, turn_package)
    warnings.extend(w)

    # A2 — price regex check
    text, w = check_prices_in_text(text, turn_package)
    warnings.extend(w)

    # A5 — hard length cap
    text, w = check_length_cap(text)
    warnings.extend(w)

    return PolicyResult(text=text, tools=tools, warnings=warnings)
