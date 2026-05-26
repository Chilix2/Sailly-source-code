"""
verify_address — validate a delivery address via Google Maps.

Phase 6 decision:
  - tool-verify-address: ask-caller-confirm
    When Maps confidence is below MAPS_AUTO_ACCEPT_CONFIDENCE (0.90), return
    the canonical address plus a readback prompt so the LLM asks the caller
    to confirm. Validation registry marks the slot PENDING until confirmed.

Also exported: maps_lookup() so the Phase 5.5 validate_address validator
can share the same geocoding logic.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from server.tools.common.context import ToolContext
from server.tools.common.error_codes import ErrorCode
from server.tools.common.errors import ToolResult

logger = logging.getLogger(__name__)

TOOL_NAME = "verify_address"

MAPS_AUTO_ACCEPT_CONFIDENCE = 0.90


def _format_address_for_speech(address: str) -> str:
    text = (address or "").strip()
    for suffix in (", Germany", ", Deutschland", ", DE"):
        if text.endswith(suffix):
            return text[: -len(suffix)].strip().rstrip(",")
    return text


async def handle(args: dict, ctx: ToolContext) -> ToolResult:
    """
    Args:
      address: str — street address (may include city)
      city:    str — optional city for disambiguation
    """
    raw_address = str(args.get("address") or "").strip()
    if not raw_address:
        return ToolResult(ok=False, error="Keine Adresse angegeben", error_code=ErrorCode.MISSING_REQUIRED_SLOT)

    maps_result = await maps_lookup(raw_address, city=args.get("city", ""))
    if maps_result is None:
        return ToolResult(
            ok=False,
            data={"address": raw_address},
            error="maps_lookup_failed",
            error_code=ErrorCode.MAPS_NOT_FOUND,
        )

    delivery = ctx.get_tenant_value("delivery", default={})
    in_zone = _check_delivery_zone(maps_result, delivery)
    confidence = maps_result.get("confidence", 1.0)

    if confidence >= MAPS_AUTO_ACCEPT_CONFIDENCE:
        canonical = _format_address_for_speech(maps_result.get("formatted_address", raw_address))
        return ToolResult(
            ok=True,
            data={
                "canonical_address": canonical,
                "in_delivery_zone": in_zone,
                "confidence": confidence,
                "needs_caller_confirm": False,
                "latitude": maps_result.get("latitude"),
                "longitude": maps_result.get("longitude"),
            },
        )

    # Low confidence — ask caller to confirm canonical form
    canonical = _format_address_for_speech(maps_result.get("formatted_address", raw_address))
    return ToolResult(
        ok=True,
        data={
            "canonical_address": canonical,
            "in_delivery_zone": in_zone,
            "confidence": confidence,
            "needs_caller_confirm": True,
            "readback_text": f"Habe ich Sie richtig verstanden — {canonical}?",
        },
    )


async def maps_lookup(address: str, city: str = "") -> Optional[dict]:
    """
    Geocode an address via Google Maps Geocoding API directly, protected by circuit breaker.

    Returns a dict with at minimum:
      formatted_address: str
      confidence:        float (derived from location_type)
      latitude:          float | None
      longitude:         float | None

    Returns None on hard failure. Raises on transient errors (caller retries).
    """
    import aiohttp
    import os
    import re
    from server.core.resilience import with_breaker, BreakerOpenError, MAPS_BREAKER
    from server.configs.secrets import get_secret

    maps_api_key = get_secret("maps-api-key", default="") or os.environ.get("GOOGLE_MAPS_API_KEY", "")
    
    # Dev fallback: if no API key, use simple geocoding cache for known Bonn addresses
    if not maps_api_key:
        logger.info("[verify_address] maps-api-key not configured; using dev fallback")
        return _dev_fallback_geocode(address, city)

    search_query = f"{address}, {city}".strip() if city else address

    async def call_geocoding():
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": search_query,
            "key": maps_api_key,
            "region": "de",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if data.get("status") != "OK":
                    return None
                results = data.get("results", [])
                if not results:
                    return None
                return results[0]

    try:
        result = await with_breaker(MAPS_BREAKER, call_geocoding())
        if not result:
            return None
        
        formatted_address = result.get("formatted_address", address)
        location = result.get("geometry", {}).get("location", {})
        location_type = result.get("geometry", {}).get("location_type", "")
        
        # Derive confidence from location_type
        raw_confidence = _infer_confidence({"location_type": location_type})
        
        return {
            "formatted_address": formatted_address,
            "confidence": raw_confidence,
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
            "valid": True,
        }
    except Exception as e:
        logger.warning("[verify_address] maps_lookup raised: %s", e)
        return None  # Return None instead of raising, to let the tool gracefully degrade


def _infer_confidence(geocode_result: dict) -> float:
    """
    Map Google's location_type strings to a 0-1 confidence score.

    ROOFTOP = exact match → 0.98
    RANGE_INTERPOLATED = address range → 0.80
    GEOMETRIC_CENTER = centroid → 0.60
    APPROXIMATE → 0.40
    """
    lt = (geocode_result.get("location_type") or "").upper()
    mapping = {
        "ROOFTOP": 0.98,
        "RANGE_INTERPOLATED": 0.80,
        "GEOMETRIC_CENTER": 0.60,
        "APPROXIMATE": 0.40,
    }
    return mapping.get(lt, 0.85 if geocode_result.get("valid") else 0.30)


def _check_delivery_zone(maps_result: dict, delivery_cfg: dict) -> Optional[bool]:
    """True if within zone polygon, None if no zone configured."""
    zone = delivery_cfg.get("zone_polygon")
    if not zone:
        return None
    try:
        from server.brain.geo import in_polygon  # type: ignore
        lat = maps_result.get("latitude")
        lng = maps_result.get("longitude")
        if lat is None or lng is None:
            return None
        return in_polygon((lat, lng), zone)
    except ImportError:
        return None


def _dev_fallback_geocode(address: str, city: str = "") -> Optional[dict]:
    """
    Dev mode fallback geocoding for known addresses in Bonn.
    
    This allows demos and testing without a valid Google Maps API key.
    Maps real-world addresses to approximate Bonn coordinates.
    """
    import re
    
    # Normalize address (remove extra whitespace, lowercase)
    search = f"{address} {city}".lower().strip()
    
    # Known addresses in Bonn (approximate coordinates)
    known_addresses = {
        "bonner bogen": {
            "formatted_address": "Bonner Bogen 20, 53227 Bonn",
            "confidence": 0.90,
            "latitude": 50.7376,
            "longitude": 7.1111,
            "location_type": "RANGE_INTERPOLATED",
        },
        "bogen": {
            "formatted_address": "Bonner Bogen 20, 53227 Bonn",
            "confidence": 0.85,
            "latitude": 50.7376,
            "longitude": 7.1111,
            "location_type": "GEOMETRIC_CENTER",
        },
        "friedrich-ebert": {
            "formatted_address": "Friedrich-Ebert-Allee 69, 53113 Bonn",
            "confidence": 0.95,
            "latitude": 50.7323,
            "longitude": 7.0954,
            "location_type": "ROOFTOP",
        },
        "hauptbahnhof": {
            "formatted_address": "Hauptbahnhof, 53111 Bonn",
            "confidence": 0.92,
            "latitude": 50.7408,
            "longitude": 7.0993,
            "location_type": "RANGE_INTERPOLATED",
        },
    }
    
    # Try to match known addresses
    for key, data in known_addresses.items():
        if key in search:
            logger.info(f"[verify_address] dev fallback matched '{key}' in '{address}'")
            return data
    
    # Default fallback: accept if it mentions Bonn
    if "bonn" in search or city.lower() == "bonn":
        logger.info(f"[verify_address] dev fallback: generic Bonn address '{address}'")
        # Extract street and number if possible
        match = re.search(r"(\w[\w\s]*)\s+(\d+)", address)
        street = match.group(1).strip() if match else address
        number = match.group(2) if match else ""
        return {
            "formatted_address": f"{street} {number}, Bonn".strip(),
            "confidence": 0.75,
            "latitude": 50.7323,
            "longitude": 7.0954,
            "location_type": "GEOMETRIC_CENTER",
            "valid": True,
        }
    
    return None

