"""Consolidated slot extraction layer for FSM-driven conversation pipeline.

This module replaces 5 duplicate phone extractors, 3 date extractors, and 4 menu
item fuzzy matchers with a single, TenantConfig-driven source of truth.

All extraction functions:
1. Use phonenumbers, dateparser, rapidfuzz for robust parsing
2. Read from ctx (TenantConfig) for locale, menu, address patterns
3. Return typed candidates for FSM phases (slot validation happens separately)
"""

from __future__ import annotations

import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import phonenumbers
from dateparser import parse as parse_date
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class MenuItem:
    """Menu item candidate extracted from text."""
    name: str
    quantity: int = 1
    category: Optional[str] = None
    price: Optional[float] = None
    aliases: List[str] = field(default_factory=list)


@dataclass
class Address:
    """Delivery address candidate extracted from text."""
    street: str
    city: str
    postcode: Optional[str] = None
    country: str = "Deutschland"


# ── Helper: German date formatting ────────────────────────────────────────────

_GERMAN_MONTHS = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April", 5: "Mai", 6: "Juni",
    7: "Juli", 8: "August", 9: "September", 10: "Oktober", 11: "November", 12: "Dezember"
}

_GERMAN_WEEKDAYS = {
    0: "Montag", 1: "Dienstag", 2: "Mittwoch", 3: "Donnerstag",
    4: "Freitag", 5: "Samstag", 6: "Sonntag"
}


def _iso_to_spoken_german(iso_date: str, locale: str = "de-DE") -> str:
    """Convert ISO date (2026-01-15) to German spoken format (Mittwoch, 15. Januar 2026)."""
    try:
        dt = datetime.fromisoformat(iso_date)
        weekday = _GERMAN_WEEKDAYS[dt.weekday()]
        month = _GERMAN_MONTHS[dt.month]
        return f"{weekday}, {dt.day}. {month} {dt.year}"
    except (ValueError, KeyError):
        return iso_date


# ── Phone extraction ──────────────────────────────────────────────────────────

_PHONE_PATTERN_RELAXED = re.compile(r"(?:\+?49|0)[1-9]\d{1,14}")


def extract_phone(text: str, ctx: Any) -> Optional[str]:
    """
    Extract and normalize German phone number from text.
    
    Args:
        text: User utterance or extracted value
        ctx: TenantConfig with locale info
    
    Returns:
        E.164 format phone (e.g. "+491234567890") or None if not found/invalid.
    """
    if not text or not isinstance(text, str):
        return None
    
    text = text.strip()
    
    try:
        # Try to match German phone patterns first (0xxx or +49xxx)
        match = _PHONE_PATTERN_RELAXED.search(text)
        if match:
            raw_phone = match.group(0)
            try:
                parsed = phonenumbers.parse(raw_phone, "DE")
                if phonenumbers.is_valid_number(parsed):
                    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            except phonenumbers.NumberParseException:
                pass
        
        # Fallback: try parsing as-is (phonenumbers is forgiving with context)
        parsed = phonenumbers.parse(text, "DE")
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    
    except Exception as e:
        logger.debug(f"Phone extraction failed for '{text}': {e}")
    
    return None


# ── Date extraction ──────────────────────────────────────────────────────────

_PAST_DATE_KEYWORDS = {"gestern", "yesterday", "letzten", "vorige", "voriger"}


def extract_date(text: str, ctx: Any) -> Optional[str]:
    """
    Extract and validate reservation date from German text.
    
    Args:
        text: User utterance (e.g. "Ich möchte für Mittwoch, den 15. Januar reservieren")
        ctx: TenantConfig with timezone/locale info
    
    Returns:
        ISO format date (YYYY-MM-DD) or None if invalid/past.
    """
    if not text or not isinstance(text, str):
        return None
    
    text = text.strip().lower()
    
    # Guard: reject explicit past-date markers
    if any(kw in text for kw in _PAST_DATE_KEYWORDS):
        logger.debug(f"Date extraction rejected past date indicator in '{text}'")
        return None
    
    try:
        # Parse with German locale and lenient settings
        settings = {
            "PREFER_DATES_FROM": "current_period",
            "RELATIVE_BASE": datetime.utcnow(),
            "RETURN_AS_TIMEZONE_AWARE": False,
        }
        parsed_dt = parse_date(text, languages=["de"], settings=settings)
        
        if not parsed_dt:
            logger.debug(f"dateparser could not parse '{text}'")
            return None
        
        # Guard: reject dates in the past (up to 5 min tolerance for server/TTS skew)
        now = datetime.utcnow()
        if parsed_dt < now - timedelta(minutes=5):
            logger.debug(f"Date extraction rejected past date: {parsed_dt} < {now}")
            return None
        
        # Convert to ISO format
        iso_date = parsed_dt.strftime("%Y-%m-%d")
        logger.debug(f"Extracted date: '{text}' -> {iso_date}")
        return iso_date
    
    except Exception as e:
        logger.debug(f"Date extraction failed for '{text}': {e}")
        return None


# ── Menu item extraction ──────────────────────────────────────────────────────

_QUANTITY_KEYWORDS = {
    "ein": 1, "eins": 1, "eine": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5,
    "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12,
    "dreizehn": 13, "vierzehn": 14, "fünfzehn": 15, "sechzehn": 16, "siebzehn": 17,
    "achtzehn": 18, "neunzehn": 19, "zwanzig": 20,
}


def extract_menu_items(
    text: str,
    ctx: Any,
    category: Optional[str] = None,
    fuzzy_threshold: float = 0.75
) -> List[MenuItem]:
    """
    Extract menu items from user utterance using fuzzy matching.
    
    Args:
        text: User utterance (e.g. "Ich hätte gerne zwei Bibimbap und ein Kimchi")
        ctx: TenantConfig with menu items
        category: Filter by category (e.g. "hauptgerichte") or None for all
        fuzzy_threshold: Rapifuzz token_set_ratio threshold (0.0-1.0)
    
    Returns:
        List of MenuItem objects with matched names and quantities.
    """
    if not text or not ctx or not hasattr(ctx, 'tool_data'):
        return []
    
    items = []
    menu_data = ctx.tool_data.menu if hasattr(ctx.tool_data, 'menu') else None
    
    if not menu_data:
        logger.debug("No menu data in context")
        return []
    
    # Flatten menu into a list of (name, price, category, aliases)
    menu_items_flat: List[Dict[str, Any]] = []
    
    if isinstance(menu_data, dict):
        for cat_name, cat_items in menu_data.items():
            if category and cat_name != category:
                continue
            
            if isinstance(cat_items, list):
                for item in cat_items:
                    if isinstance(item, dict):
                        menu_items_flat.append({
                            'name': item.get('name', ''),
                            'price': item.get('price'),
                            'category': cat_name,
                            'aliases': item.get('aliases', []) if isinstance(item.get('aliases'), list) else [],
                        })
    
    if not menu_items_flat:
        logger.debug(f"No menu items found for category={category}")
        return []
    
    # Extract quantities from text using German number keywords
    text_lower = text.lower()
    quantities: Dict[str, int] = {}
    
    for kw, qty in _QUANTITY_KEYWORDS.items():
        if kw in text_lower:
            quantities[kw] = qty
    
    # If no quantity keywords, default to 1
    default_qty = 1
    
    # Fuzzy match menu items against text
    for menu_item in menu_items_flat:
        item_name = menu_item['name']
        aliases = [item_name] + menu_item['aliases']
        
        best_ratio = 0
        best_alias = None
        
        for alias in aliases:
            ratio = fuzz.token_set_ratio(alias.lower(), text_lower) / 100.0
            if ratio > best_ratio:
                best_ratio = ratio
                best_alias = alias
        
        if best_ratio >= fuzzy_threshold:
            # Determine quantity: use any quantity keyword found, else default to 1
            qty = next(iter(quantities.values())) if quantities else default_qty
            
            extracted_item = MenuItem(
                name=item_name,
                quantity=qty,
                category=menu_item['category'],
                price=menu_item.get('price'),
                aliases=menu_item['aliases']
            )
            items.append(extracted_item)
            logger.debug(f"Matched menu item: {item_name} x{qty} (ratio={best_ratio:.2f})")
    
    return items


# ── Address extraction ────────────────────────────────────────────────────────

def extract_address(text: str, ctx: Any) -> Optional[Address]:
    """
    Extract delivery address from user utterance.
    
    Args:
        text: User utterance (e.g. "Friedrich-Ebert-Allee 69, 53113 Bonn")
        ctx: TenantConfig with default city and postcode pattern
    
    Returns:
        Address object or None if no street/city detected.
    """
    if not text or not isinstance(text, str):
        return None
    
    text = text.strip()
    
    # Default values from context
    default_city = "Bonn"  # fallback
    postcode_pattern = r"53\d{3}"  # fallback for DOBOO (Bonn area)
    
    if ctx and hasattr(ctx, 'location'):
        if isinstance(ctx.location, dict):
            default_city = ctx.location.get('city', default_city)
            postcode_prefix = ctx.location.get('postcode_prefix', '53')
            postcode_pattern = rf"{re.escape(postcode_prefix)}\d{{3,4}}"
        elif hasattr(ctx.location, 'city'):
            default_city = ctx.location.city
    
    # Extract postcode if present
    postcode_match = re.search(postcode_pattern, text)
    postcode = postcode_match.group(0) if postcode_match else None
    
    # Extract street address (everything before postcode, or entire text)
    if postcode_match:
        street_part = text[:postcode_match.start()].strip()
        city_part = text[postcode_match.end():].strip() or default_city
    else:
        street_part = text
        city_part = default_city
    
    # Parse city + country
    city = city_part.split(',')[0].strip() if ',' in city_part else city_part.strip()
    if not city:
        city = default_city
    
    # Ensure we have a street
    if not street_part:
        logger.debug(f"Address extraction: no street found in '{text}'")
        return None
    
    return Address(street=street_part, city=city, postcode=postcode, country="Deutschland")


# ── Slot confirmation ─────────────────────────────────────────────────────────

def is_slot_confirmed(slots: Any, threshold: float = 0.75) -> bool:
    """
    Check if a slot has been confirmed by user (two-pass gate).
    
    Args:
        slots: ConversationSlots object or dict with 'confirmed' field
        threshold: Confidence threshold (for future LLM scoring)
    
    Returns:
        True if slots.confirmed is True, False otherwise.
    """
    if hasattr(slots, 'confirmed'):
        return slots.confirmed is True
    elif isinstance(slots, dict):
        return slots.get('confirmed', False) is True
    return False
