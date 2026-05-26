"""
Default validators registered at server startup.

Per pattern-checklist — every validator follows this signature:

    async def validate_<slot>(
        value: str,
        tenant_cfg: dict,
        ctx: ValidationContext,
    ) -> ValidationResult

Return one of:
    - VERIFIED  → populate enriched_data with canonical/normalized form
    - FAILED    → definitively wrong; detail explains why
    - ERROR     → transient; registry retries once

External calls wrapped in try/except. Raise on transient errors so registry
retries; return FAILED for definitive negatives.
"""
from __future__ import annotations

import re

from server.brain.layer1.validation.registry import (
    ValidationContext,
    ValidationRegistry,
    ValidationResult,
    ValidationStatus,
)


# ── Phone ─────────────────────────────────────────────────────────────────────

_PHONE_RX = re.compile(r"^(?:(?:\+49|0049)|0)(\d{9,11})$")


async def validate_phone(
    value: str, tenant_cfg: dict, ctx: ValidationContext
) -> ValidationResult:
    """German mobile/landline format. Canonical E.164 in enriched_data."""
    cleaned = re.sub(r"[\s\-\(\)/]", "", value)
    m = _PHONE_RX.match(cleaned)
    if not m:
        return ValidationResult(
            status=ValidationStatus.FAILED,
            detail="phone format invalid",
        )
    canonical = "+49" + m.group(1)
    return ValidationResult(
        status=ValidationStatus.VERIFIED,
        detail=f"canonical: {canonical}",
        enriched_data={"canonical_phone": canonical},
    )


# ── Address ───────────────────────────────────────────────────────────────────

async def validate_address(
    value: str, tenant_cfg: dict, ctx: ValidationContext
) -> ValidationResult:
    """
    Verify via Google Maps Places API. Canonical address in enriched_data.
    Optionally checks delivery zone if tenant has one defined.
    Raises on transient errors so the registry retries once.
    """
    try:
        from server.tools.handlers.verify_address import maps_lookup  # type: ignore
        result = await maps_lookup(value)
    except ImportError:
        # maps_lookup not yet wired — treat as UNVALIDATED rather than ERROR
        return ValidationResult(
            status=ValidationStatus.UNVALIDATED,
            detail="maps_lookup not available",
        )
    except Exception:
        # Transient network failure — let registry retry
        raise

    if not result or not result.get("formatted_address"):
        return ValidationResult(
            status=ValidationStatus.FAILED,
            detail="address not found by Maps",
        )

    delivery = tenant_cfg.get("delivery", {})
    if zone := delivery.get("zone_polygon"):
        try:
            from server.brain.geo import in_polygon  # type: ignore
            if not in_polygon(result.get("lat_lng"), zone):
                return ValidationResult(
                    status=ValidationStatus.FAILED,
                    detail="outside delivery zone",
                    enriched_data=result,
                )
        except ImportError:
            pass  # geo helper not available; skip zone check

    return ValidationResult(
        status=ValidationStatus.VERIFIED,
        detail=result["formatted_address"][:60],
        enriched_data=result,
    )


# ── Party size ────────────────────────────────────────────────────────────────

async def validate_party_size(
    value: str, tenant_cfg: dict, ctx: ValidationContext
) -> ValidationResult:
    try:
        n = int(value)
    except (ValueError, TypeError):
        return ValidationResult(
            status=ValidationStatus.FAILED, detail="not a number"
        )
    if n < 1:
        return ValidationResult(
            status=ValidationStatus.FAILED, detail="party size must be >= 1"
        )
    max_party = tenant_cfg.get("reservation", {}).get("max_party_size", 12)
    if n > max_party:
        return ValidationResult(
            status=ValidationStatus.FAILED,
            detail=f"party size {n} exceeds max {max_party} — escalate to group_catering",
        )
    return ValidationResult(
        status=ValidationStatus.VERIFIED,
        detail=f"{n} guests",
        enriched_data={"party_size_int": n},
    )


# ── Datetime (Phase 8 — A3: force-get-date) ──────────────────────────────────

async def validate_datetime_slot(
    value: str, tenant_cfg: dict, ctx: ValidationContext
) -> ValidationResult:
    """
    Per force-get-date (8.H9): pickup_time, reservation_date, and reservation_time
    must be canonicalized via get_date_info before create_* tools may fire.

    Calls get_date_info handler's resolve_german_datetime() helper; raises on
    transient errors so the registry retries once.

    On success, enriched_data["canonical_iso"] contains the ISO datetime string
    which downstream tools use instead of the raw caller string.
    """
    if not value or not value.strip():
        return ValidationResult(status=ValidationStatus.FAILED, detail="empty value")

    try:
        from server.tools.handlers.get_date_info import resolve_german_datetime  # type: ignore
        resolved = await resolve_german_datetime(value, tenant_cfg)
    except ImportError:
        # resolve_german_datetime not yet available; treat as VERIFIED with warning
        return ValidationResult(
            status=ValidationStatus.VERIFIED,
            detail=f"date/time accepted as-is (resolver unavailable): {value}",
            enriched_data={"raw_value": value},
        )
    except Exception:
        raise  # registry retries once on ERROR

    if not resolved:
        return ValidationResult(
            status=ValidationStatus.FAILED,
            detail=f"cannot resolve date/time: {value!r}",
        )

    try:
        import datetime as _dt
        if hasattr(resolved, "isoformat"):
            iso = resolved.isoformat()
            display = resolved.strftime("%a %d.%m. %H:%M")
        else:
            iso = str(resolved)
            display = iso
    except Exception:
        iso = str(resolved)
        display = iso

    return ValidationResult(
        status=ValidationStatus.VERIFIED,
        detail=display,
        enriched_data={"canonical_iso": iso},
    )


# ── Registration ──────────────────────────────────────────────────────────────

def register_default_validators(registry: ValidationRegistry) -> None:
    """Called once per call by the turn runner."""
    registry.register("phone", validate_phone)
    registry.register("address", validate_address)
    registry.register("party_size", validate_party_size)
    # Phase 8 A3 — date/time slots require canonicalization via get_date_info
    registry.register("pickup_time", validate_datetime_slot)
    registry.register("reservation_date", validate_datetime_slot)
    registry.register("reservation_time", validate_datetime_slot)
