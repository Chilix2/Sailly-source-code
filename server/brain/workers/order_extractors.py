"""Fast regex order extractors for speculative restaurant order turns."""
from __future__ import annotations

import re
import time
from typing import Optional

from server.brain.workers import Worker, WorkerContext, WorkerKind, WorkerOutput

_STATIC_DISHES = (
    "bibimbap", "bulgogi", "kimchi", "mandu", "japchae", "tteokbokki",
    "ramen", "tofu", "wasser", "cola", "sake",
)
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s()/.-]{6,}\d)")
_ADDRESS_RE = re.compile(
    r"\b((?:[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\-]+(?:\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\-]+){0,3}\s+"
    r"(?:straße|strasse|weg|allee|platz|gasse|ring|damm|ufer)"
    r"|[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\-]*(?:straße|strasse|weg|allee|platz|gasse|ring|damm|ufer))"
    r"\s+\d{1,4}[a-zA-Z]?(?:\s*,?\s*(?:in\s+)?[A-ZÄÖÜ][A-Za-zÄÖÜäöüß.\- ]{2,30})?)\b",
    re.I,
)


def _tenant_dishes(tenant_id: str) -> list[str]:
    try:
        from server.core.tenant_config import load_tenant_config

        cfg = load_tenant_config(tenant_id or "doboo")
        items = getattr(cfg, "items", None) or []
        return [str(item).strip().lower() for item in items if str(item).strip()]
    except Exception:
        return []


class OrderDishExtractor(Worker):
    name = "order_dish_extractor"
    kind = WorkerKind.OPTIONAL
    estimated_latency_ms = 3
    timeout_ms = 80

    async def run(self, ctx: WorkerContext) -> WorkerOutput:
        t0 = time.monotonic()
        lower = ctx.user_text.lower()
        dishes = []
        for dish in _tenant_dishes(ctx.tenant_id) + list(_STATIC_DISHES):
            if dish and dish in lower and dish not in dishes:
                dishes.append(dish.title())
        return WorkerOutput(
            worker_name=self.name,
            success=True,
            data={"selected_items": dishes} if dishes else {},
            confidence=0.85 if dishes else 1.0,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )


class OrderAddressExtractor(Worker):
    name = "order_address_extractor"
    kind = WorkerKind.OPTIONAL
    estimated_latency_ms = 4
    timeout_ms = 80

    async def run(self, ctx: WorkerContext) -> WorkerOutput:
        t0 = time.monotonic()
        address: Optional[str] = None
        match = _ADDRESS_RE.search(ctx.user_text)
        if match and re.search(r"\d", match.group(1)):
            address = " ".join(match.group(1).split())
            address = re.sub(r"^(?:bitte\s+)?(?:nach|an)\s+", "", address, flags=re.I)
            address = re.sub(r"\s+(?:liefern|geliefert|bringen)$", "", address, flags=re.I)
        return WorkerOutput(
            worker_name=self.name,
            success=True,
            data={"delivery_address": address} if address else {},
            confidence=0.8 if address else 1.0,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )


class OrderPhoneExtractor(Worker):
    name = "order_phone_extractor"
    kind = WorkerKind.OPTIONAL
    estimated_latency_ms = 2
    timeout_ms = 80

    async def run(self, ctx: WorkerContext) -> WorkerOutput:
        t0 = time.monotonic()
        phone = None
        match = _PHONE_RE.search(ctx.user_text)
        if match:
            digits = re.sub(r"\D+", "", match.group(0))
            if len(digits) >= 7:
                phone = digits
        return WorkerOutput(
            worker_name=self.name,
            success=True,
            data={"phone_number": phone} if phone else {},
            confidence=0.9 if phone else 1.0,
            latency_ms=int((time.monotonic() - t0) * 1000),
        )


order_dish_extractor = OrderDishExtractor()
order_address_extractor = OrderAddressExtractor()
order_phone_extractor = OrderPhoneExtractor()
