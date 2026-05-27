"""Tracks order/reservation intent across training conversation turns."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import Any, Optional, List

logger = logging.getLogger(__name__)


# FIX 3: End-of-call state machine for proper multi-intent conclusion
class EndOfCallState(Enum):
    """States for multi-intent call completion sequence."""
    NOT_READY = "not_ready"                    # More intents to confirm or not in multi-intent mode
    READY_FOR_SMS = "ready_for_sms"            # All intents confirmed, ready to send final SMS
    READY_FOR_FAREWELL = "ready_for_farewell"  # SMS sent, ready to speak goodbye
    FAREWELL_SPOKEN = "farewell_spoken"        # Goodbye TTS complete, safe to end_call

# CRITICAL FIX A2.8_D2: Split hours storage — restaurants with lunch/dinner breaks
# Store opening hours as a list of shifts with explicit break windows.
# This prevents hardcoded "11:30–21:30" from drowning out split-hour patterns.
from dataclasses import dataclass as _dc
@_dc
class OpeningShift:
    start: str  # "11:30"
    end: str    # "14:00" or "21:30"
    label: str  # "lunch" or "dinner"

# DEPRECATED: _FRIDAY_SPLIT_HOURS was hardcoded for DOBOO only.
# Now all opening hours come from ctx.opening_hours (TenantConfig).
# Kept here only for backward compatibility in legacy code paths.
def set_known_items(items: List[str]):
    """Called at startup to initialize known items from tenant config."""
    global _KNOWN_ITEMS
    _KNOWN_ITEMS = list(items) if items else list(KNOWN_DISHES)

ORDER_KEYWORDS = [
    "bestellen", "bestellung", "möchte bestellen", "moechte bestellen",
    "ich nehme", "zum mitnehmen", "liefern", "lieferung", "order",
    "ich hätte gerne", "ich haette gerne", "takeaway", "abholen",
    # Fix 3: Indirect order phrases for dual-intent scenarios
    "bestelle ich doch", "gleich was zu essen", "was zu essen",
    # Fix B: Delivery-related phrases
    "lieferung", "liefern", "delivery", "bestell", "essen bestellen",
    "zum mitnehmen", "abholen", "bring mir",
]

# CRITICAL: Availability-check keywords that explicitly NEGATE order intent
AVAILABILITY_CHECK_KEYWORDS = [
    "nur fragen", "nur wissen", "nur check", "nur verfügbarkeit",
    "haben sie", "gibt es", "ist das", "können sie mir sagen",
    "ob sie", "wollte wissen", "möchte wissen", "wollte nur fragen",
    "gefragt", "nicht bestellt", "keine bestellung",
]

NEGATE_ORDER = [
    "nicht bestellen", "keine bestellung", "doch nicht", "stornieren",
    "abbrechen", "verzichten", "kein interesse",
    # Inquiry phrases: caller asks ABOUT a dish, not ordering it
    "wollte wissen, was", "wollte wissen was", "möchte wissen, was",
    "möchte wissen was", "wissen, was", "was ist das", "was sind das",
    "was bedeutet", "können sie erklären", "was genau ist",
]

RESERVATION_KEYWORDS = [
    "reservieren", "reservierung", "tisch für", "tisch fuer", "buchen",
    "platz für", "platz fuer", "reservation", "terrasse",
    "tisch", "plaetze", "plätze", "einen tisch", "freie plätze",
    "freie plaetze",
]

PHONE_PATTERN = re.compile(r"(\+?\d[\d\s\-/]{6,18}\d)")


# === Bug B: German function words that must never be accepted as a name ===
_NAME_BLOCKLIST = {
    # verbs / auxiliaries
    "ist", "bin", "sind", "war", "hab", "habe", "haben", "hatte",
    "heiße", "heiss", "heisse", "heißt", "geht", "kann", "könnte", "koennte",
    "möchte", "moechte", "brauche", "brauch", "will",
    # pronouns / articles
    "ich", "du", "er", "sie", "es", "wir", "ihr",
    "mein", "meine", "dein", "deine", "sein", "seine",
    "der", "die", "das", "den", "dem", "des",
    # particles / common short words
    "ja", "nein", "ok", "okay", "gut", "klar", "doch", "also", "dann",
    "hallo", "tschüss", "tschuess", "danke", "bitte", "gern", "gerne",
    "entschuldigung", "moment",
    # German words that commonly look like names via STT
    "herr", "frau", "schon", "noch", "nur", "mal", "etwa",
    "name", "namen", "nachname", "vorname",
    # imperative / command words frequently spoken instead of a name
    "weiter", "los", "super", "prima", "genau", "stimmt", "richtig",
    "passt", "korrekt", "perfekt", "alles", "fertig", "bereit", "bitte",
    "stop", "stopp", "nochmal", "wieder", "zurück", "zurueck",
    # German verb infinitives that can follow "auf den Namen" in a sentence
    "reservieren", "buchen", "bestellen", "stornieren", "notieren",
    "anrufen", "anfragen", "machen", "sagen", "gehen", "kommen", "legen",
    # articles / determiners that can start false-positive 2-word phrases like "Ein Getränk"
    "ein", "eine", "einen", "einem", "einer", "eines",
    "kein", "keine", "keinen", "keinem", "keiner", "keines",
    "dieser", "diese", "diesen", "diesem", "jeder", "jede", "jeden",
    # pickup/delivery phrases must never be parsed as customer names
    "zur", "zum", "abholung", "lieferung", "lieferservice",
    # food/drink/order words that are not names
    "getränk", "getränke", "gericht", "gerichte", "speise", "speisen",
    "wasser", "bier", "wein", "saft", "tee", "kaffee",
    "pizza", "nudeln", "suppe", "salat", "dessert",
    # German day-of-week names (STT confusion: 'Montag' → customer_name)
    "montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag",
    # German month names (STT confusion: 'Mai' → customer_name)
    "januar", "februar", "märz", "maerz", "april", "mai", "juni",
    "juli", "august", "september", "oktober", "november", "dezember",
    # Bot's own identity — NEVER valid as customer_name
    "sailly", "ki-assistentin", "assistentin",
}


def _is_valid_name_candidate(candidate: str) -> bool:
    """Name validation: accept full names (first+last) OR single last names in reservation context.
    CRITICAL FIX A2.3_D2: Enforce temporal/function-word rejection.
    CRITICAL FIX H2.2_D3: Allow single capitalized surnames (≥3 chars) when extracted from direct name-question context.
    """
    if not candidate:
        return False
    
    _GERMAN_TEMPORAL_REJECT = {
        "montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag",
        "januar", "februar", "märz", "maerz", "april", "mai", "juni",
        "juli", "august", "september", "oktober", "november", "dezember",
    }
    _TEMPORAL_ADJECTIVES = {
        "nächsten", "naechsten", "kommenden", "kommender", "nächste", "naechste",
        "vorherigen", "vorigen", "letzten", "letzte", "heutigen", "morgigen",
        "übermorgen", "uebermorgen", "morgen", "heute",
    }
    
    candidate_lower = candidate.lower().strip()
    if candidate_lower in _GERMAN_TEMPORAL_REJECT or candidate_lower in _NAME_BLOCKLIST:
        return False
    if candidate_lower in _TEMPORAL_ADJECTIVES:
        return False
    
    parts = candidate.strip().split()
    # Accept: 2+ parts (first+last) OR single capitalized word ≥3 chars (last name only)
    # This allows "Claudia Müller" (2 parts) and "Müller" (1 part, surname) both as valid
    if len(parts) == 1:
        # Single word: only accept if ≥3 chars, starts with capital, not in blocklist
        single = parts[0]
        if len(single) < 3 or single in _NAME_BLOCKLIST:
            return False
        if not re.match(r"^[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]+$", single):
            return False
        return True
    elif len(parts) < 2:
        return False
    
    # Check each part independently
    for part in parts:
        if len(part) < 3:
            return False
        part_lower = part.lower()
        
        # Reject ALL temporal words and function words
        if part_lower in _GERMAN_TEMPORAL_REJECT:
            return False
        if part_lower in _TEMPORAL_ADJECTIVES:
            return False
        if part_lower in _NAME_BLOCKLIST:
            return False
        
        # Must start with capital German letter
        if not re.match(r"^[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]+$", part):
            return False
    
    return True


def _extract_name_from_utterance(utterance: str, reservation_context: bool = False) -> Optional[str]:
    """Extract a valid full name (first + last).

    Strategy 1: marker-based (mein name ist …, ich heiße …, ich bin …)
    Strategy 2: bare short utterance (user answering a direct name question)

    CRITICAL: In reservation_context (cancel/modify), ONLY accept names with explicit
    'auf den Namen' or 'name ist' markers. Reject caller names ("ich bin", "hier").
    Returns the full name string only (or None). For single first names use
    _extract_first_name_from_utterance instead.
    """
    if not utterance:
        return None

    # In cancel/reservation context, ONLY accept explicit reservation-name markers
    if reservation_context:
        markers = [
            r"auf\s+den\s+namen",
            r"name\s+ist",
            r"name\s+lautet",
            r"(?:der\s+)?name(?:\s+ist)?\s*[:]",
            r"reservierung\s+(?:auf|auf\s+den\s+namen)",
        ]
    else:
        markers = [
            r"mein\s+name\s+ist",
            r"ich\s+heiße",
            r"ich\s+heisse",
            r"ich\s+bin",
            r"hier\s+(?:ist|spricht)",
            r"(?:hallo[,.]?\s+)?hier",  # "Hallo, hier Philipp Schneider" (no ist/spricht)
            r"auf\s+den\s+namen",
            r"name\s+ist",
            r"name\s+lautet",
            r"(?:der\s+)?name(?:\s+ist)?\s*[:]",
        ]
    # EXTRA: handle bare 'Name <Word>' patterns (e.g. 'Name Braun').
    # Do not match "Name ist <First> <Last>" here; the marker loop below
    # preserves full names such as "Ursula Klein".
    _bare_name_pattern = r"\bname\s+(?!ist\b)([A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]{2,})\b"
    _bare_m = re.search(_bare_name_pattern, utterance, re.IGNORECASE)
    if _bare_m:
        token = _bare_m.group(1)
        if token[0].isupper() and token.lower() not in _NAME_BLOCKLIST:
            # Return as single last name — callers that need full name will use this as customer_name
            return token
    for marker in markers:
        # Support hyphenated first names like "Hans-Peter" (uppercase after hyphen is valid)
        _name_token = r"[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]{2,}"
        pattern = (
            rf"{marker}\s+"
            rf"(?:der\s+|die\s+|herr\s+|frau\s+)?"
            rf"({_name_token})(?:\s+({_name_token}))?"
        )
        m = re.search(pattern, utterance, re.IGNORECASE)
        if m:
            first_raw = m.group(1)
            last_raw = m.group(2)  # may be None for single-word names
            if not first_raw[0].isupper():
                continue
            if last_raw is None:
                # Single-word name after marker (e.g. "mein Name ist Koch")
                candidate = first_raw
            else:
                if not last_raw[0].isupper():
                    continue
                candidate = f"{first_raw} {last_raw}"
            if _is_valid_name_candidate(candidate):
                return candidate

    tokens = utterance.strip().strip(".,!?").split()
    if 2 <= len(tokens) <= 4:
        for i in range(len(tokens) - 1):
            a = tokens[i].strip(".,!?")
            b = tokens[i + 1].strip(".,!?")
            pair = f"{a} {b}"
            if _is_valid_name_candidate(pair):
                return pair
    # Compact reservation format: "..., 20 Uhr, Schmidt." or "vier Personen, ..., Schmidt."
    # When the utterance ends with ", [CapWord]." and contains reservation keywords,
    # the trailing capitalized word IS the customer's last name (e.g. A1.2 style inputs).
    _trailing_name_m = re.search(
        r",\s*([A-ZÄÖÜ][a-zäöüß\-]{2,})\.?\s*$",
        utterance.strip()
    )
    if _trailing_name_m:
        _trail = _trailing_name_m.group(1)
        _trail_lo = _trail.lower()
        _TEMPORAL_BLOCKLIST_TRAIL = {
            "montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag",
            "januar", "februar", "märz", "maerz", "april", "mai", "juni", "juli",
            "august", "september", "oktober", "november", "dezember",
            "nächsten", "naechsten", "morgen", "heute", "abend",
        }
        _HAS_RESERVATION_KW = any(
            kw in utterance.lower()
            for kw in ("uhr", "personen", "person", "reservier", "tisch")
        )
        if (_trail_lo not in _TEMPORAL_BLOCKLIST_TRAIL
                and _trail_lo not in _NAME_BLOCKLIST
                and _HAS_RESERVATION_KW):
            logger.debug(f"[NAME_EXTRACT] Compact reservation trailing name: {_trail!r}")
            return _trail.capitalize()
    # Final safeguards: reject temporal and function words even if earlier checks missed them
    _GERMAN_TEMPORAL_FINAL = {
        "montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag",
        "januar", "februar", "märz", "maerz", "april", "mai", "juni",
        "juli", "august", "september", "oktober", "november", "dezember",
    }
    if utterance.lower().strip() in _GERMAN_TEMPORAL_FINAL:
        logger.debug(f"[NAME_EXTRACT] Rejected temporal word as name: {utterance!r}")
        return None
    # CRITICAL: Reject any single-word utterance as a name
    if len(utterance.strip().split()) <= 1:
        return None
    return None


_NAME_CORRECTION_MARKERS = (
    "falsch", "falsch verstanden", "falsch geschrieben", "stimmt nicht",
    "nicht", "sondern", "eigentlich", "korrektur", "korrigieren", "ändern",
    "aendern", "ich meinte", "meinte",
)


def _is_name_correction_context(text: str) -> bool:
    lower = (text or "").lower()
    has_marker = any(marker in lower for marker in _NAME_CORRECTION_MARKERS)
    has_name_context = any(
        marker in lower
        for marker in ("name", "namen", "heiße", "heisse", "sondern")
    )
    return has_marker and has_name_context


def _extract_name_correction(utterance: str) -> Optional[str]:
    """Extract authoritative name corrections like 'nicht Müller, sondern Schmidt'."""
    if not utterance:
        return None
    name_token = r"[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]{2,}"
    patterns = [
        rf"(?:nicht|nein|nee)[^.!?]{{0,80}}\bsondern\s+(?:auf\s+den\s+namen\s+)?({name_token})(?:\s+({name_token}))?",
        rf"(?:mein\s+name\s+ist\s+eigentlich|der\s+name\s+ist\s+eigentlich|name\s+ist\s+eigentlich|ich\s+heiße\s+eigentlich|ich\s+heisse\s+eigentlich)\s+({name_token})(?:\s+({name_token}))?",
        rf"(?:sie\s+haben\s+(?:meinen\s+)?namen\s+falsch\s+verstanden[^.!?]{{0,40}}(?:ich\s+heiße|ich\s+heisse|name\s+ist)\s+)\s*({name_token})(?:\s+({name_token}))?",
    ]
    for pattern in patterns:
        m = re.search(pattern, utterance, re.IGNORECASE)
        if not m:
            continue
        first_raw = m.group(1)
        last_raw = m.group(2)
        if not first_raw or not first_raw[0].isupper():
            continue
        candidate = first_raw if not last_raw else f"{first_raw} {last_raw}"
        if _is_valid_name_candidate(candidate):
            return candidate
    return None


def _extract_first_name_from_utterance(utterance: str) -> Optional[str]:
    """Extract a single first name when a strong identity marker precedes it.

    Used as a fallback after _extract_name_from_utterance fails (i.e. caller
    gave only their first name like "Hier ist der Julius").

    Rules:
    - Must follow a strong marker (prevents false-positive matches on dish names
      or filler words mid-sentence).
    - Single token: capitalized, ≥ 3 chars, not in _NAME_BLOCKLIST.
    - NOT a single letter (the 'N' bug guard).
    - NOT a known dish name or German city.
    """
    if not utterance:
        return None

    # Strong markers that strongly imply the next token is a person's first name
    _FIRST_NAME_MARKERS = [
        r"ich\s+bin",
        r"hier\s+(?:ist|spricht)\s+(?:der\s+|die\s+)?",
        r"mein\s+name\s+ist",
        r"ich\s+heiße",
        r"ich\s+heisse",
        r"auf\s+den\s+namen",
        r"name\s+ist",
        r"hier\s+(?:ist|spricht)",
    ]
    # Words that should never be accepted as first names (extend the blocklist
    # with single-letter catch and known dish words).
    _DISH_LOWER = {d.lower() for d in _KNOWN_ITEMS}
    _CITY_LOWER = {"bonn", "köln", "koeln", "berlin", "münchen", "muenchen",
                   "frankfurt", "hamburg", "düsseldorf", "duesseldorf"}

    for marker in _FIRST_NAME_MARKERS:
        pattern = (
            rf"{marker}\s+"
            r"(?:der\s+|die\s+|herr\s+|frau\s+)?"
            r"([A-ZÄÖÜ][a-zäöüß\-]{2,})\b"
        )
        m = re.search(pattern, utterance, re.IGNORECASE)
        if m:
            token = m.group(1).strip(".,!?")
            # Must start with uppercase (after capitalize)
            candidate = token[0].upper() + token[1:]
            if len(candidate) < 3:
                continue
            if candidate.lower() in _NAME_BLOCKLIST:
                continue
            if candidate.lower() in _DISH_LOWER:
                continue
            if candidate.lower() in _CITY_LOWER:
                continue
            # Must look like a proper name: capital start + only letters/hyphens
            if not re.match(r"^[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]+$", candidate):
                continue
            return candidate

    return None


# === Bug C: German number words + strict address extractor ===
_GERMAN_NUMBER_WORDS = {
    "null": "0", "eins": "1", "ein": "1", "eine": "1",
    "zwei": "2", "drei": "3", "vier": "4", "fünf": "5", "fuenf": "5",
    "sechs": "6", "sieben": "7", "acht": "8", "neun": "9",
    "zehn": "10", "elf": "11", "zwölf": "12", "zwoelf": "12",
    "dreizehn": "13", "vierzehn": "14", "fünfzehn": "15", "fuenfzehn": "15",
    "sechzehn": "16", "siebzehn": "17", "achtzehn": "18", "neunzehn": "19",
    "zwanzig": "20", "dreißig": "30", "dreissig": "30",
    "vierzig": "40", "fünfzig": "50", "fuenfzig": "50",
    "sechzig": "60", "siebzig": "70", "achtzig": "80", "neunzig": "90",
    "hundert": "100",
}


def _convert_number_words(text: str) -> str:
    """Replace isolated German number-words with digits (word-by-word)."""
    out = []
    for w in text.split():
        low = w.lower().rstrip(".,!?;:")
        punct = w[len(w.rstrip(".,!?;:")):] if len(w.rstrip(".,!?;:")) < len(w) else ""
        if low in _GERMAN_NUMBER_WORDS:
            out.append(_GERMAN_NUMBER_WORDS[low] + punct)
        else:
            out.append(w)
    return " ".join(out)


_GARBAGE_CITIES = {
    "von", "bis", "nach", "zu", "an", "in", "auf", "und", "oder", "aber",
    "ja", "nein", "ist", "sind", "war", "gut", "okay", "danke",
    "bitte", "please", "thanks", "doch", "also",
}


def _address_looks_valid(addr: str) -> bool:
    """Quick structural check used by update_state_from_utterance."""
    if not addr or len(addr) < 8:
        return False
    if not re.search(r"\d", addr):
        return False
    if not re.search(
        r"(?:straße|strasse|str\.?|allee|ring|gasse|damm|weg|platz|ufer|chaussee|bogen)",
        addr.lower(),
    ):
        return False
    return True


def _extract_address_from_utterance(utterance: str) -> Optional[str]:
    """Extract street address from user utterance.

    Accepts word-form numbers ('zwanzig' → '20').
    Primary pattern: Street(suffix) + number + city.
    Fallback pattern: Street(suffix) + number only → defaults to Bonn.
    Returns None when no street suffix is found at all.
    """
    if not utterance:
        return None
    normalized = _convert_number_words(utterance)
    street_suffix = (
        r"(?:straße|strasse|str\.?|allee|ring|gasse|damm|weg|platz|ufer|chaussee|feld|berg|heim|bogen)"
    )
    def _clean_street_name(raw: str) -> str:
        street = raw.strip()
        # Keep the segment after the last delivery/address preposition so
        # "zur Lieferung nach Venloer Straße 10" does not keep "Lieferung nach".
        prep_matches = list(re.finditer(
            r"\b(?:zur|zum|zu|nach|an|in)\s+",
            street,
            flags=re.IGNORECASE,
        ))
        if prep_matches:
            street = street[prep_matches[-1].end():].strip()
        for _ in range(2):
            street = re.sub(
                r"^(?:bitte\s+)?(?:lieferung\s+)?(?:zur|zum|zu|nach|an|am|im|in|die|der|den)\s+",
                "",
                street,
                flags=re.IGNORECASE,
            ).strip()
            street = re.sub(r"^lieferung\s+", "", street, flags=re.IGNORECASE).strip()
            street = re.sub(r"^bitte\s+", "", street, flags=re.IGNORECASE).strip()
        return street

    street_name = (
        rf"(?:[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]*{street_suffix}"
        rf"|[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]*(?:\s+[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]*){{0,3}}\s+{street_suffix})"
    )
    # Primary: street + number + city
    pattern_full = (
        rf"({street_name})"
        r"\s+(\d{1,4}[a-z]?)"
        r"[,.\s]+(?:in\s+|nach\s+)?"
        r"([A-ZÄÖÜ][a-zäöüß\-]{2,})"
    )
    m = re.search(pattern_full, normalized, re.IGNORECASE)
    if m:
        street = _clean_street_name(m.group(1))
        number = m.group(2).strip()
        city = m.group(3).strip()
        if city.lower() not in _GARBAGE_CITIES and len(city) >= 3:
            street = "".join(c.upper() if i == 0 else c for i, c in enumerate(street))
            city = city[0].upper() + city[1:].lower()
            return f"{street} {number}, {city}"

    # Fallback: street + number only → default city Bonn
    pattern_partial = (
        rf"({street_name})"
        r"\s+(\d{1,4}[a-z]?)"
    )
    m2 = re.search(pattern_partial, normalized, re.IGNORECASE)
    if m2:
        street = _clean_street_name(m2.group(1))
        number = m2.group(2).strip()
        street = "".join(c.upper() if i == 0 else c for i, c in enumerate(street))
        return f"{street} {number}, Bonn"

    return None


# === Bug D: Digit-by-digit phone assembly from spoken German digits ===
_SPOKEN_DIGITS = {
    "null": "0", "eins": "1", "ein": "1", "zwei": "2", "drei": "3",
    "vier": "4", "fünf": "5", "fuenf": "5", "sechs": "6", "sieben": "7",
    "acht": "8", "neun": "9",
}
# Two-digit spoken numbers (useful at the *tail* of a phone number, e.g. "…zwei eins elf")
_SPOKEN_TEENS = {
    "zehn": "10", "elf": "11", "zwölf": "12", "zwoelf": "12",
    "dreizehn": "13", "vierzehn": "14", "fünfzehn": "15", "fuenfzehn": "15",
    "sechzehn": "16", "siebzehn": "17", "achtzehn": "18", "neunzehn": "19",
    "zwanzig": "20",
}
# German shorthand multipliers: "zweimal" / "dreimal" / ... → how many times to repeat
# Sprint B: added einmal/1mal + spaced forms normalised before pattern matching
_SPOKEN_MULTIPLIERS = {
    "einmal": 1, "1mal": 1,  # NEW
    "zweimal": 2, "dreimal": 3, "viermal": 4, "fünfmal": 5, "fuenfmal": 5,
    "sechsmal": 6, "siebenmal": 7, "achtmal": 8, "neunmal": 9, "zehnmal": 10,
    "2mal": 2, "3mal": 3, "4mal": 4, "5mal": 5, "6mal": 6, "7mal": 7,
    "8mal": 8, "9mal": 9,
}

# Sprint B: German plural digit noun forms — "drei Zweien" → three 2s, etc.
# Maps plural word to base digit string
_SPOKEN_DIGIT_PLURALS = {
    "einsen": "1", "einsens": "1",
    "zweien": "2", "zweis": "2",
    "dreien": "3",
    "vieren": "4",
    "fünfen": "5", "fuenfen": "5",
    "sechsen": "6",
    # "sieben" intentionally omitted — identical to the digit word "sieben" (7),
    # causes "sechs sieben" (digits 6,7) to be mis-expanded to six 7s.
    "achten": "8",
    "neunen": "9",
    "nullen": "0",
}

# Sprint B: compound tens/ones → two phone digits (achtundachtzig = 8,8 in phone context)
# Only covers the most common patterns to avoid false positives
_COMPOUND_TENS_TO_PAIRS: dict = {
    "achtundachtzig": ("8", "8"),
    "neunundneunzig": ("9", "9"),
    "einundzwanzig": ("2", "1"),
    "zweiundzwanzig": ("2", "2"),
    "dreiundzwanzig": ("2", "3"),
    "vierundzwanzig": ("2", "4"),
    "fünfundzwanzig": ("2", "5"),
    "sechsundzwanzig": ("2", "6"),
    "siebenundzwanzig": ("2", "7"),
    "achtundzwanzig": ("2", "8"),
    "neunundzwanzig": ("2", "9"),
    "einunddreißig": ("3", "1"), "einunddreissig": ("3", "1"),
    "zweiundvierzig": ("4", "2"),
    "dreiundvierzig": ("4", "3"),
    "vierundvierzig": ("4", "4"),
    "fünfundvierzig": ("4", "5"),
    "sechsundvierzig": ("4", "6"),
    "siebenundvierzig": ("4", "7"),
    "achtundvierzig": ("4", "8"),
    "neunundvierzig": ("4", "9"),
    "einundfünfzig": ("5", "1"), "einundfuenfzig": ("5", "1"),
    "zweiundfünfzig": ("5", "2"),
    "sechsundfünfzig": ("5", "6"),
    "siebenundfünfzig": ("5", "7"),
    "achtundfünfzig": ("5", "8"),
    "neunundfünfzig": ("5", "9"),
    "siebenundsechzig": ("6", "7"),
    "achtundsechzig": ("6", "8"),
    "neunundsechzig": ("6", "9"),
    "einundsiebzig": ("7", "1"),
    "zweiundsiebzig": ("7", "2"),
    "dreiundsiebzig": ("7", "3"),
    "siebenundsiebzig": ("7", "7"),
    "achtundsiebzig": ("7", "8"),
    "neunundsiebzig": ("7", "9"),
    "einundachtzig": ("8", "1"),
    "zweiundachtzig": ("8", "2"),
    "dreiundachtzig": ("8", "3"),
    "vierundachtzig": ("8", "4"),
    "fünfundachtzig": ("8", "5"),
    "sechsundachtzig": ("8", "6"),
    "siebenundachtzig": ("8", "7"),
    "neunundachtzig": ("8", "9"),
    "einundneunzig": ("9", "1"),
    "zweiundneunzig": ("9", "2"),
    "dreiundneunzig": ("9", "3"),
    "vierundneunzig": ("9", "4"),
    "fünfundneunzig": ("9", "5"),
    "sechsundneunzig": ("9", "6"),
    "siebenundneunzig": ("9", "7"),
    "achtundneunzig": ("9", "8"),
}


def _expand_spoken_shorthand(utterance: str) -> str:
    """Expand German spoken shorthand in phone contexts.

    Handles patterns callers commonly use:
      • "Xmal die Y" or "X mal die Y"  → repeat digit Y exactly X times
         e.g. "viermal die vier"  → "4 4 4 4"
              "dreimal acht"      → "8 8 8"
              "vier mal die 1"    → "1 1 1 1"   (spaced form)
      • "<count> <digit-plural>"   → repeat digit count times
         e.g. "drei Zweien"       → "2 2 2"
              "vier Einsen"       → "1 1 1 1"
      • "doppel <digit>"          → repeat digit twice
         e.g. "doppel acht"       → "8 8"
              "doppelvier"        → "4 4"
      • Compound tens in phone context → two digits
         e.g. "achtundachtzig"    → "8 8"
      • Teens at the end: "…zwei eins elf" → "…zwei eins eins eins"

    Returns the expanded lowercase utterance (spaces between tokens).
    """
    if not utterance:
        return utterance
    text = " " + utterance.lower() + " "

    # Step 0: Normalise spaced multipliers "vier mal" → "viermal" before pattern
    text = re.sub(
        r"\b(ein|zwei|drei|vier|fünf|fuenf|sechs|sieben|acht|neun|zehn|[1-9])\s+mal\b",
        r"\1mal",
        text,
    )

    # Step 1: "<multiplier> [die|der] <digit-word-or-number>"
    pat = re.compile(
        r"\b(" + "|".join(map(re.escape, sorted(_SPOKEN_MULTIPLIERS.keys(), key=len, reverse=True)))
        + r")\s+(?:die\s+|der\s+)?"
        r"(" + "|".join(list(_SPOKEN_DIGITS.keys()) + [r"\d"]) + r")\b"
    )

    def _expand(m: re.Match) -> str:
        count = _SPOKEN_MULTIPLIERS[m.group(1)]
        token = m.group(2)
        digit = _SPOKEN_DIGITS.get(token, token)
        return " ".join([digit] * count)

    text = pat.sub(_expand, text)

    # Step 2: "<count-word> <digit-plural>" e.g. "drei Zweien" → "2 2 2"
    # Count words that express quantity (use _SPOKEN_DIGITS keys as counts 1-9)
    _count_words = {
        "eine": 1, "ein": 1, "zwei": 2, "drei": 3, "vier": 4,
        "fünf": 5, "fuenf": 5, "sechs": 6, "sieben": 7, "acht": 8, "neun": 9,
    }
    for plural_word, digit in _SPOKEN_DIGIT_PLURALS.items():
        # Match "<count> <plural>" e.g. "drei zweien"
        for count_word, count_val in _count_words.items():
            pattern = rf"\b{re.escape(count_word)}\s+{re.escape(plural_word)}\b"
            replacement = " ".join([digit] * count_val)
            text = re.sub(pattern, replacement, text)

    # Step 3: "doppel <digit-word>" or "doppel<digit-word>" → repeat twice
    doppel_pat = re.compile(
        r"\bdoppel[\s\-]?(" + "|".join(_SPOKEN_DIGITS.keys()) + r")\b"
    )
    text = doppel_pat.sub(
        lambda m: f"{_SPOKEN_DIGITS[m.group(1)]} {_SPOKEN_DIGITS[m.group(1)]}", text
    )

    # Step 4: Compound tens → two phone digits (phone context ONLY)
    # BUG FIX: Only expand when the utterance contains an explicit phone-number signal word.
    # Without this guard, address words like "Friedrichstraße zwanzig" → "Friedrichstraße 2 0"
    # leak "20" into the phone digit scanner, corrupting the phone buffer.
    _HAS_PHONE_SIGNAL = any(
        w in utterance.lower()
        for w in ("telefonnummer", "handynummer", "nummer", "handy", "meine nummer",
                  "rufnummer", "mobilnummer", "mobilfunk", "anrufnummer")
    )
    if _HAS_PHONE_SIGNAL:
        for compound, (d1, d2) in _COMPOUND_TENS_TO_PAIRS.items():
            text = re.sub(rf"\b{re.escape(compound)}\b", f"{d1} {d2}", text)

    # Step 5: Teens → two phone digits (phone context ONLY — "neunzehn Uhr" must not leak "1 9")
    if _HAS_PHONE_SIGNAL:
        for word, two in _SPOKEN_TEENS.items():
            text = re.sub(rf"\b{re.escape(word)}\b", f"{two[0]} {two[1]}", text)

    return text.strip()


def _extract_phone_digits(utterance: str) -> Optional[str]:
    """Assemble a phone number from digits AND/OR spoken digits.

    Returns the full digit string (no formatting) if ≥ 9 digits found,
    else None. Rejects date/time patterns (YYYY, MM:MM, DD.MM.YYYY).
    CRITICAL FIX: Require minimum 9 digits (blocks truncated patterns like '18 2026').
    CRITICAL FIX G1.2_D3: Also reject patterns like '18 2026' → '182026' (6 digits = too short)
    and '19:00' → '1900' (4 digits = too short for German phone).
    """
    if not utterance:
        return None
    # Pre-expand spoken shorthand so the rest of the pipeline sees plain digits
    expanded = _expand_spoken_shorthand(utterance)
    # First attempt: look for ≥9 contiguous digits (with optional separators)
    m = re.search(r"(\+?\d[\d\s\-/\.]{7,}\d)", expanded)
    if m:
        digits = re.sub(r"\D", "", m.group(1))
        # CRITICAL FIX G1.2_D3: Reject date/time patterns FIRST before any length checks
        # This prevents '18 2026' (year fragment) from being accepted as a phone number
        if re.match(r"^20\d{2}$", digits):  # YYYY pattern (2000-2099)
            return None
        if re.match(r"^[012]\d[0-5]\d$", digits):  # HH:MM pattern (0000-2359)
            return None
        if re.match(r"^\d{1,2}\.\d{1,2}$", digits):  # DD.MM pattern (4 digits)
            return None
        if re.match(r"^\d{1,2}\d{1,2}$", digits) and len(digits) == 4:  # DDMM pattern (4 digits)
            return None
        if re.match(r"^\d{1,2}20\d{2}$", digits):  # DDYYYy pattern (6 digits like '182026')
            return None
        # CRITICAL: Also reject year fragments like '18 2026' (6 digits)
        # Check the RAW match string (with spaces) to catch "18 2026" before digit extraction
        if re.match(r"^\d{2}\s+20\d{2}$|^\d{2}20\d{2}$", m.group(1)):
            return None
        # CRITICAL FIX: Require minimum 9 digits BEFORE accepting
        if len(digits) < 9:
            return None
        # Additional sanity check: reject if looks like DDYYYY pattern (e.g. '182026' = 18.2026)
        if len(digits) == 6 and digits[0:2].isdigit() and digits[2:6] in ("2026", "2027", "2028", "2029"):
            return None
        if 9 <= len(digits) <= 13:
            return digits
    # Spoken-digit assembly: scan tokens, pick both numeric and spoken
    # Sprint B: extended connector/separator set to keep scanning through grouping words
    # BUG FIX: add address-related words as BREAK words so "Friedrichstraße 20" does not
    # contribute digits to a phone number scan — these cause buffer contamination.
    _PHONE_CONNECTORS = {
        "und", "komma", "pause", "dann", "strich", "bindestrich",
        "schrägstrich", "schraegstrich", "vorwahl", "durchwahl", "also", "so",
        "unter",  # German verbal separator in phone numbers ("026 unter 3457978")
    }
    _PHONE_BREAK_WORDS = {
        "straße", "strasse", "str", "gasse", "platz", "weg", "allee", "ring",
        "damm", "ufer", "chaussee", "boulevard", "promenade", "passage",
        "bonn", "köln", "berlin", "hamburg", "frankfurt", "münchen", "muenchen",
        "in", "bei", "nahe",
    }
    out_digits: list[str] = []
    for token in expanded.split():
        t = token.strip(".,!?;:-/")
        if not t:
            continue
        # Hard break on address words — they stop the digit scan immediately
        # so street numbers don't contaminate phone digit collection
        if t in _PHONE_BREAK_WORDS:
            if out_digits:
                break
            continue  # haven't started collecting yet, just skip
        if t.isdigit():
            out_digits.append(t)
        elif t in _SPOKEN_DIGITS:
            out_digits.append(_SPOKEN_DIGITS[t])
        else:
            if out_digits:
                if t in _PHONE_CONNECTORS:
                    continue
                break
    s = "".join(out_digits)
    if 9 <= len(s) <= 13:
        return s
    return None


# Public alias used by v4_pipeline.py module-level imports
_extract_phone_from_utterance = _extract_phone_digits


_FORBIDDEN_TTS_PATTERNS = [
    r"TOOL\s+CALL\s*:.*$",
    r"\[TOOL:\s*\w+\s*\]",
    r"`\[TOOL:\s*\w+\s*\]`",  # backtick-wrapped tool tags
    r"\bprint\s*\([^\)]*\)",
    r"\b(?:verify_address|create_order|create_reservation|send_sms|get_menu|"
    r"check_availability|ai_greeting|transfer_to_tier2|get_weather|"
    r"get_date_info|end_call|execute_tool|request_callback)\s*\([^\)]*\)",
    r"```[\s\S]*?```",
    r"```",
    r"<tool_call>[\s\S]*?</tool_call>",
    r"<function_call>[\s\S]*?</function_call>",
    r"<tool_call>",
    r"<function_call>",
    r'\{\s*"(?:name|tool|function)"\s*:\s*"[^"]+"',
    r"\[(?:TOOL_RESPONSE|TOOL_RESULT|TOOL_ERROR):\s*\w+\s*\]",  # tool response markers
    r"`\[(?:TOOL_RESPONSE|TOOL_RESULT|TOOL_ERROR):\s*\w+\s*\]`",  # backtick-wrapped responses
]
_FORBIDDEN_TTS_RE = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in _FORBIDDEN_TTS_PATTERNS]


def strip_tool_call_leakage(text: str) -> tuple[str, bool]:
    """Remove forbidden tool-call / code patterns from TTS text.

    Returns (cleaned_text, was_stripped). Never returns empty —
    substitutes a neutral filler if the result would be blank.
    Logs when tool tags are found and stripped for debugging.
    """
    if not text:
        return text or "", False
    original = text
    cleaned = text
    for pat in _FORBIDDEN_TTS_RE:
        before = cleaned
        cleaned = pat.sub("", cleaned)
        if cleaned != before:
            # Log detection of tool tag patterns
            import logging
            logger_local = logging.getLogger(__name__)
            logger_local.debug(
                f"[strip_tool_call_leakage] Found and stripped pattern: {pat.pattern[:60]}... "
                f"result_len={len(cleaned)}"
            )
    # Collapse residual whitespace
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    stripped = cleaned != original
    if stripped and not cleaned.strip():
        cleaned = "Einen Moment bitte."
    return cleaned, stripped

# OFF_TOPIC LOOP FIX: After 1 off-topic redirect, offer goodbye instead of re-asking
# Track consecutive off-topic rejections to trigger graceful exit
_OFF_TOPIC_REDIRECT_MAX = 1

# Keywords that trigger the delivery_address_mentioned flag (backward-compatible).
# Includes delivery intent words so forced order commits work even without explicit address text.
_ADDRESS_KW_STATE = [
    # Formal address vocabulary
    "adresse", "strasse", "straße", "hausnummer", "plz", "postleitzahl",
    "lieferadresse", "liefern an", "liefern nach", "lieferung an",
    "wohne in", "wohne auf", "meine adresse",
    "str.", "allee", "ring", "gasse", "markt",
    "hof", "graben", "damm", "ufer", "promenade",
    # Delivery intent words — also trigger the flag (backward compat with text validation)
    "lieferung", "geliefert", "liefern", "liefere", "zustellung",
    "delivery", "deliver", "delivered",
    "bring", "bringen", "gebracht",
    "mitnehmen", "zum mitnehmen", "takeaway", "take away",
    # Location mentions common in delivery scenarios
    "innenstadt", "altstadt", "stadtmitte", "zentrum",
    "bonn", "koeln", "köln", "berlin", "münchen", "muenchen",
    "hamburg", "düsseldorf", "duesseldorf", "frankfurt", "stuttgart",
    "dortmund", "essen", "leipzig", "dresden", "hannover",
]

# Subset of _ADDRESS_KW_STATE that indicates delivery INTENT specifically.
# Used to set delivery_intended flag separately from delivery_address_mentioned.
_DELIVERY_INTENT_KW = [
    "lieferung", "geliefert", "liefern", "liefere", "zustellung",
    "delivery", "deliver", "delivered",
    "bring", "bringen", "gebracht",
    "nach hause", "zu mir", "zu meiner",
]


# ============================================================================
# Quantity extraction (Sprint 0 — BLOCKING)
# ----------------------------------------------------------------------------
# MAX_ORDER_QUANTITY: soft cap — above this we ask the caller to verbally
# confirm the large order before create_order commits. Chosen high enough that
# family/group orders still commit in one turn ("acht Bibimbap").
#
# HARD_QUANTITY_CEILING: absolute cap enforced in tools/executor.py. Orders
# above this will NEVER commit — they are treated as catering events and
# escalated to a human. The floor between soft and hard is the "confirm zone".
# ============================================================================
MAX_ORDER_QUANTITY: int = 20
# Phase 6 ceiling-30 decision: reduced from 50 to 30. Orders above this are
# catering events routed to a human agent. The Phase 6 handler enforces this.
HARD_QUANTITY_CEILING: int = 30

# German number words we map to ints for dish-quantity parsing. Keep conservative
# — we ONLY accept words that unambiguously mean a count. Avoid "mal" / "paar"
# (too vague) and avoid ordinals for dish quantities.
_GERMAN_DISH_NUMBERS: dict[str, int] = {
    "ein": 1, "eine": 1, "einen": 1, "eins": 1,
    "zwei": 2, "zwo": 2,
    "drei": 3, "vier": 4,
    "fünf": 5, "fuenf": 5,
    "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10,
    "elf": 11, "zwölf": 12, "zwoelf": 12,
    "dreizehn": 13, "vierzehn": 14, "fünfzehn": 15, "fuenfzehn": 15,
    "sechzehn": 16, "siebzehn": 17, "achtzehn": 18, "neunzehn": 19,
    "zwanzig": 20, "dreißig": 30, "dreissig": 30,
    "vierzig": 40, "fünfzig": 50, "fuenfzig": 50,
    "hundert": 100, "einhundert": 100,
}

# Quantity triggers: we only accept a digit/word as a quantity when it appears
# next to one of these cues, so that "für vier Personen" (party size),
# "um 8 Uhr" (time) and phone digits do NOT get mistaken for a dish count.
_QTY_VERB_CUES = (
    "möchte", "moechte", "nehme", "bestelle", "hätte", "haette",
    "will", "brauche", "bitte", "gerne", "gern", "bekomme", "bekommen",
)
# Words that, if found in the utterance, disqualify it as a quantity utterance
# (unless a dish-count pattern is literally adjacent).
_QTY_NEGATIVE_CONTEXT = (
    "uhr", "personen", "person", "leute", "gäste", "gaeste",
    "minuten", "minute", "stunde", "stunden",
    "grad", "prozent",
)


def _extract_order_quantity(utterance: str) -> Optional[int]:
    """Extract a DISH count from the utterance.

    Returns None when no reliable count is found (→ callers should leave
    order_quantity at its current value, typically 1).

    Strategy:
      1. Look for "<digit|word> mal ..." → strong cue.
      2. Look for "<digit|word> Portion(en)" → strong cue.
      3. Look for digit/word adjacent to a dish name (same utterance) guarded
         by a verb cue and with no conflicting context (Uhr, Personen, …).
    """
    if not utterance:
        return None
    lower = utterance.lower().strip()

    def _parse_token(tok: str) -> Optional[int]:
        tok = tok.strip().lower()
        if tok.isdigit():
            try:
                n = int(tok)
            except ValueError:
                return None
            return n if n >= 1 else None
        return _GERMAN_DISH_NUMBERS.get(tok)

    # (1) "X mal ..." / "X Portionen ..."
    m = re.search(
        r"\b(\d{1,3}|[a-zäöüß]+)\s+(?:mal|portion(?:en)?)\b",
        lower,
    )
    if m:
        n = _parse_token(m.group(1))
        if n and 1 <= n <= HARD_QUANTITY_CEILING * 2:
            return n

    # (2) Digit followed directly by a known dish name.
    known = [d.lower() for d in _KNOWN_ITEMS]
    for dish_l in known:
        # Only consider the first word of the dish to keep the regex cheap.
        first = dish_l.split()[0]
        pat = rf"\b(\d{{1,3}}|[a-zäöüß]+)\s+(?:{re.escape(first)})\b"
        mm = re.search(pat, lower)
        if mm:
            n = _parse_token(mm.group(1))
            if n and 1 <= n <= HARD_QUANTITY_CEILING * 2:
                # Require a verb cue somewhere in the utterance or an explicit
                # "ich" so that declarative sentences ("Es gibt drei Bibimbap")
                # don't trigger. This is conservative by design.
                if any(cue in lower for cue in _QTY_VERB_CUES) or "ich " in lower:
                    return n

    return None


@dataclass
class CommitGateState:
    """Durable pre-commit gate for high-stakes write tools."""

    readback_shown: bool = False
    confirmed: bool = False
    committed: bool = False
    reset_cause: Optional[str] = None

    def mark_readback_shown(self) -> None:
        self.readback_shown = True
        self.confirmed = False
        self.reset_cause = None

    def mark_confirmed(self) -> None:
        if self.readback_shown:
            self.confirmed = True
            self.reset_cause = None

    def mark_committed(self) -> None:
        self.committed = True

    def reset(self, cause: str = "") -> None:
        self.readback_shown = False
        self.confirmed = False
        self.reset_cause = cause or None

    def ready(self) -> bool:
        return self.readback_shown and self.confirmed and not self.committed

    def to_dict(self) -> dict:
        return {
            "readback_shown": self.readback_shown,
            "confirmed": self.confirmed,
            "committed": self.committed,
            "reset_cause": self.reset_cause,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "CommitGateState":
        if not isinstance(data, dict):
            return cls()
        return cls(
            readback_shown=bool(data.get("readback_shown", False)),
            # Never infer confirmed from legacy restored blobs. Only trust the
            # explicit v6 field, which is written after a caller confirmation.
            confirmed=bool(data.get("confirmed", False)),
            committed=bool(data.get("committed", False)),
            reset_cause=data.get("reset_cause"),
        )


@dataclass
class ConversationState:
    # Phase 2: schema_version = 2 (CapturedIntent as primary storage; shared_slots added)
    # Phase 1 set this to 1; from_dict() handles the 0→1→2 migration chain.
    # Phase 5.5: schema_version = 5 (validation_entries added).
    schema_version: int = 6

    order_intent: bool = False
    selected_dish: Optional[str] = None
    # Extra items beyond primary selected_dish (upsells, sides, drinks).
    # Stored as list of canonical short names; prices resolved via get_cached_dish_price.
    order_items_extras: List[str] = field(default_factory=list)
    phone_number: Optional[str] = None
    phone_extracted: bool = False  # Issue 3: Set to True when phone is extracted from STT
    phone_prompt_sent: bool = False
    order_created: bool = False
    order_commit_state: CommitGateState = field(default_factory=CommitGateState)
    reservation_commit_state: CommitGateState = field(default_factory=CommitGateState)
    # Doorbell name notation if different from customer_name
    bell_name: Optional[str] = None

    # === Quantity sanity (Sprint 0 — blocking) ===
    # order_quantity applies to the PRIMARY selected_dish. Default 1.
    # Extras are single-unit each; bulk multi-unit extras route through the primary field.
    order_quantity: int = 1
    # Set when caller requests MAX_ORDER_QUANTITY < qty <= HARD_QUANTITY_CEILING
    # and must verbally confirm before create_order commits.
    pending_bulk_confirmation: bool = False
    # True once the caller has confirmed a large order within this turn.
    bulk_order_confirmed: bool = False

    # === Caller-ID prefill (Sprint 0 — piped in from Twilio `From`) ===
    # Raw caller ID as captured from telephony. Populated at call start (not from utterance).
    caller_id_phone: Optional[str] = None
    # True once the caller verbally confirms that the caller-ID number is the right
    # SMS destination. Until confirmed we do NOT use caller_id_phone as phone_number.
    caller_id_confirmed: bool = False

    # Back-reference to the canonical OrderSlots object managed by ADKTurnProcessor.
    # Not serialized to Redis — reconstructed on reconnect by ADKTurnProcessor.__init__.
    order_slots_ref: Optional[object] = None  # OrderSlots, typed as object to avoid circular import

    # Back-reference to ValidationRegistry (eager background validation).
    # Not serialized to Redis — reconstructed on reconnect by ADKTurnProcessor.__init__.
    validation_registry_ref: Optional[object] = None  # ValidationRegistry, typed as object to avoid circular import

    # Multi-intent capture — populated when extract_multi() returns >= 2 intents.
    # List of CapturedIntent (typed as list to avoid circular import from captured_intents.py).
    # Not serialized to Redis. current_intent_idx points at the active intent being confirmed.
    # Per-call identifier (populated at call start; used for TurnPackage.call_sid)
    call_sid: str = ""

    # CapturedIntent list — the primary state model (Phase 2+)
    captured_intents: list = field(default_factory=list)
    # Optional[int]: None when no intents yet; set to first intent index on first capture
    current_intent_idx: Optional[int] = None
    multi_intent_completed: bool = False

    # Slots shared across all intents (caller name, phone — asked once, used everywhere)
    # Dict[str, SlotValue] — populated in Phase 2 when intents are merged
    shared_slots: dict = field(default_factory=dict)

    # FIX 3: State machine for multi-intent conclusion sequence
    end_of_call_state: str = "not_ready"  # One of EndOfCallState values

    # Phase 3 Stream 1: end-of-call state machine (durable; safe defaults → no schema bump)
    call_ended: bool = False            # True once end_call tool fires
    caller_said_goodbye: bool = False   # True when caller explicitly signed off
    farewell_spoken: bool = False       # True once farewell TTS has fired
    end_call_stage: str = "idle"        # EndCallStage values; mirrors end_of_call_state
    disposition: Optional[str] = None  # Phase 9 A2 — set at CALL_ENDED by goodbye FSM

    # Phase 4 C2: failed-intent audit trail (list of human-readable German summaries)
    failed_intent_summaries: list = field(default_factory=list)

    # Phase 4 D4: abuse strike counter (0 = no abuse, 1 = first warning, 2+ = call ended)
    abuse_strikes: int = 0

    # Phase 4: transient extractor output for current turn (not serialized)
    last_extraction: dict = field(default_factory=dict)
    # B3: True when extraction task timed out (memory_manager uses this to note uncertainty)
    last_extraction_timed_out: bool = False

    # Phase 5.5 — validation entries persisted across reconnects.
    # The ValidationRegistry instance itself is rebuilt from this on resume.
    # Format: {slot_path: {"status": str, "value": str, "validator": str, "detail": str}}
    validation_entries: dict = field(default_factory=dict)

    # Phase 6 — send_sms strict gate: set to turn_idx when caller explicitly
    # confirms (e.g. "ja", "stimmt", "korrekt") within a turn. Cleared after
    # the confirmation turn is processed. None means not confirmed this turn.
    last_caller_confirmation_turn: Optional[int] = None

    # Smart-mix confirmation flags (set by utterance handler on affirmative responses).
    # phone_confirmed already exists below (line ~713); address/summary are new.
    address_confirmed: bool = False        # caller confirmed address readback
    order_summary_confirmed: bool = False  # caller confirmed batched items/name/delivery summary
    phone_readback_confirmed: bool = False # caller confirmed the phone number readback once

    # Sprint 1.5: per-slot confirmation flags — set on affirmative reply to a
    # readback. Read by memory_manager._compose_next_step_instruction so the
    # NÄCHSTER SCHRITT block never re-asks a slot the caller already confirmed
    # (fixes the demo-6cf65e58003d "danke, danke, danke" name-loop at T3/T4/T5).
    name_confirmed: bool = False
    items_confirmed: bool = False
    delivery_type_confirmed: bool = False

    # Sprint 2.5: phone-retry escalation decoupling.
    # Set when phone_attempts >= 3 → bot enters a phone-specific fallback
    # mode (slower readback, explicit digit-group instruction) instead of
    # general escalation. Only escalates to human at phone_attempts >= 5
    # or explicit request.
    phone_retry_mode: bool = False

    # Set when verify_address returns an error; order flow continues without ending the call.
    verify_address_failed: bool = False

    reservation_intent: bool = False
    party_size: Optional[int] = None
    reservation_date: Optional[str] = None
    reservation_time: Optional[str] = None
    reservation_created: bool = False

    menu_fetched: bool = False
    check_availability_called: bool = False
    get_date_info_called: bool = False
    verify_address_called: bool = False
    customer_confirmed: bool = False
    # Set when caller explicitly asks to have the menu sent (via SMS)
    sms_requested: bool = False

    # Set when caller explicitly mentions delivery intent (e.g. "Lieferung")
    delivery_intended: bool = False
    # Sticky flag — set once when an ACTUAL address is detected, never cleared
    delivery_address_mentioned: bool = False
    # Set once when get_weather is called
    get_weather_called: bool = False
    # Set once when ai_greeting is called (prevents double-call on node switch)
    ai_greeting_called: bool = False
    # Fix 1: One-shot flag to prevent transfer_to_tier2 from firing every turn
    transfer_to_tier2_called: bool = False
    # Fix D: Track escalation requests across turns
    escalation_requested: bool = False
    # Fix E: One-shot flag for request_callback
    request_callback_called: bool = False

    recent_responses: list[str] = field(default_factory=list)

    # Production fields — collected during live calls (not used in training scenarios)
    customer_name: Optional[str] = None  # full name: first + last (confirmed)
    first_name: Optional[str] = None      # partial: first name only, set before full name confirmed
    delivery_address: Optional[str] = None
    selected_items: Optional[List[str]] = None
    semantic_slot_values: dict = field(default_factory=dict)
    pending_readback_slots: dict = field(default_factory=dict)
    semantic_slot_metrics: dict = field(default_factory=dict)
    
    # Training: known items list (dishes, services, etc.) from tenant config
    known_items: List[str] = field(default_factory=lambda: list(_KNOWN_ITEMS))

    # Menu cache: populated when get_menu succeeds so create_order can look up prices
    cached_menu: Optional[dict] = field(default=None, repr=False)
    cached_menu_at_turn: Optional[int] = None
    cached_menu_metadata: dict = field(default_factory=dict)  # lunch_menu_available, current_time_cest, etc.

    # === ACTIVE COLLECTION & RETRY TRACKING (F-A Fix) ===
    # Field collection tracking - attempts only, no boolean flags
    field_attempts: dict[str, int] = field(default_factory=lambda: {
        "name": 0,
        "delivery_choice": 0,
        "address": 0,
        "address_verified": 0,
        "phone": 0,
    })
    
    # Which field was last asked (for turn-boundary increment logic)
    last_field_asked: Optional[str] = None
    
    # Phone-specific: is it a landline (validation issue, not refusal)?
    phone_is_landline: bool = False  # True = user gave 01x number, need mobile
    
    # Which fields have been confirmed/validated
    address_verified: bool = False   # verify_address tool returned valid
    name_confirmed: bool = False     # User said name matching extraction pattern
    delivery_confirmed: bool = False # User chose pickup or delivery explicitly
    phone_confirmed: bool = False    # Phone passed format check (and is mobile if required)
    
    # Last user utterance (for next-turn attempt increment logic)
    last_user_utterance: str = ""

    # Ring buffer of last 5 caller utterances — used by TTS conditioning
    # Phase 2 for mood detection (repetition, frustration, relaxed signals).
    recent_caller_utterances: list = field(default_factory=list)

    # Bug D follow-up: buffer for cross-turn phone digit assembly
    # When user speaks phone in fragments (T10: "eins fünf", T11: "zwei eins", etc.),
    # accumulate them here until threshold is met
    phone_digits_buffer: str = ""

    def __post_init__(self) -> None:
        # Compatibility shims for legacy code that still reads/writes flat flags.
        self._readback_already_shown = self.order_commit_state.readback_shown
        self._order_readback_confirmed = self.order_commit_state.confirmed
        self.order_pre_commit_shown = self.order_commit_state.readback_shown
        self._order_readback_shown = self.order_commit_state.readback_shown
        self.pre_commit_shown = self.reservation_commit_state.readback_shown

    def ready_for_order_commit(self) -> bool:
        """
        Single authoritative check for whether create_order can fire.

        With ValidationRegistry active: requires all required slots filled,
        all three confirmation gates passed (address/phone/summary), and
        phone format-verified. Address can be FAILED (Maps error) as long
        as the caller verbally confirmed it.

        Legacy fallback (no slots): intent + dish present.
        CRITICAL: Mandate readback with item names + prices BEFORE commit.
        """
        if self.order_created:
            return False
        # Initialize transient readback tracking fields (safe no-op if already set)
        if not hasattr(self, '_readback_already_shown'):
            self._readback_already_shown = False
        if not hasattr(self, '_order_readback_confirmed'):
            self._order_readback_confirmed = False
        # CRITICAL FIX H2.2_D3: NEVER commit order without mandatory readback shown + confirmed
        # This prevents KEIN_READBACK flag when order commits without showing items+prices
        if not self._readback_already_shown:
            logger.info("[ready_for_order_commit] Blocking: readback not yet shown")
            return False
        if not self._order_readback_confirmed:
            logger.info("[ready_for_order_commit] Blocking: readback shown but not confirmed")
            return False

        slots = self.order_slots_ref
        registry = self.validation_registry_ref

        # ── Slot-mode with validation registry ────────────────────────────
        if slots is not None and registry is not None:
            # All required fields filled
            if slots.missing_required():
                logger.info(
                    f"[ready_for_order_commit] slots-mode: False — missing={slots.missing_required()}"
                )
                return False

            # Confirmation gate: address (only for delivery)
            delivery_is_delivery = (
                slots.delivery_type.is_usable()
                and slots.delivery_type.value == "delivery"
            )
            if delivery_is_delivery and not self.address_confirmed:
                logger.info("[ready_for_order_commit] slots-mode: False — address not confirmed")
                return False

            # Confirmation gate: phone
            if not self.phone_confirmed:
                logger.info("[ready_for_order_commit] slots-mode: False — phone not confirmed")
                return False

            # Confirmation gate: order summary
            if not self.order_summary_confirmed:
                logger.info("[ready_for_order_commit] slots-mode: False — summary not confirmed")
                return False

            # Phone format must be verified (strict gate)
            phone_entry = registry.get("phone")
            # Import locally to avoid circular import
            try:
                from server.brain.validation_registry import ValidationStatus
                if phone_entry is None or phone_entry.status != ValidationStatus.VERIFIED:
                    logger.info(
                        f"[ready_for_order_commit] slots-mode: False — phone not yet validated "
                        f"(status={phone_entry.status.value if phone_entry else 'None'})"
                    )
                    return False

                # Address may be FAILED (Maps issue) — caller verbal confirmation is enough
                address_entry = registry.get("address")
                if address_entry and address_entry.status.value == "pending":
                    logger.info("[ready_for_order_commit] slots-mode: False — address validation still pending")
                    return False
            except ImportError:
                pass  # registry active but import failed; fall through to slot check

            logger.info("[ready_for_order_commit] slots-mode: True — all gates passed")
            return True

        # ── Slot-mode without registry (partial setup) ────────────────────
        if slots is not None:
            result = (
                slots.intent == "order"
                and not slots.missing_required()
            )
            logger.info(
                f"[TRACE-2026-04-20] ready_for_order_commit() [slot-mode-no-registry] returning {result} — "
                f"intent={slots.intent!r} missing={slots.missing_required()} "
                f"order_created={self.order_created}"
            )
            return result

        # ── Legacy fallback: intent + dish is sufficient ───────────────────
        result = (
            self.order_intent
            and self.selected_dish is not None
            and not self.order_created
        )
        logger.info(
            f"[TRACE-2026-04-20] ready_for_order_commit() returning {result} — "
            f"order_intent={self.order_intent} selected_dish={self.selected_dish!r} "
            f"order_created={self.order_created} customer_name={self.customer_name!r} "
            f"phone={self.phone_number!r} address={self.delivery_address!r}"
        )
        return result

    def ready_for_reservation_commit(self) -> bool:
        """Commit when all reservation data present. No explicit confirmation needed."""
        return (
            self.reservation_intent
            and self.party_size is not None
            and self.reservation_date is not None
            and self.reservation_time is not None
            and not self.reservation_created
        )

    def _commit_gate_for(self, tool_name: str) -> Optional[CommitGateState]:
        if tool_name == "create_order":
            return self.order_commit_state
        if tool_name == "create_reservation":
            return self.reservation_commit_state
        return None

    def ready_for_commit(self, tool_name: str) -> bool:
        """Hard gate for high-stakes write tools after explicit readback confirmation."""
        gate = self._commit_gate_for(tool_name)
        if gate is None:
            return True
        if tool_name == "create_order" and self.order_created:
            return False
        if tool_name == "create_reservation" and self.reservation_created:
            return False
        ready = gate.ready()
        if tool_name == "create_order":
            ready = (
                ready
                and bool(getattr(self, "_readback_already_shown", False))
                and bool(getattr(self, "_order_readback_confirmed", False))
            )
        elif tool_name == "create_reservation":
            ready = ready and bool(getattr(self, "pre_commit_shown", False))
        if not ready:
            logger.info(
                "[ready_for_commit] Blocking %s: readback_shown=%s confirmed=%s committed=%s cause=%s",
                tool_name,
                gate.readback_shown,
                gate.confirmed,
                gate.committed,
                gate.reset_cause,
            )
        return ready

    def mark_commit_readback_shown(self, tool_name: str) -> None:
        gate = self._commit_gate_for(tool_name)
        if gate is None:
            return
        gate.mark_readback_shown()
        if tool_name == "create_order":
            self._readback_already_shown = True
            self._order_readback_confirmed = False
            self.order_pre_commit_shown = True
        elif tool_name == "create_reservation":
            self.pre_commit_shown = True

    def mark_commit_readback_confirmed(self, tool_name: str) -> None:
        gate = self._commit_gate_for(tool_name)
        if gate is None:
            return
        gate.mark_confirmed()
        self.last_caller_confirmation_turn = getattr(self, "_current_turn_idx", None)
        if tool_name == "create_order":
            self._readback_already_shown = True
            self._order_readback_confirmed = gate.confirmed
            self.order_summary_confirmed = gate.confirmed
        elif tool_name == "create_reservation":
            self.pre_commit_shown = True

    def mark_commit_tool_succeeded(self, tool_name: str) -> None:
        gate = self._commit_gate_for(tool_name)
        if gate is not None:
            gate.mark_committed()

    def reset_commit_readback(self, tool_name: str, cause: str = "") -> None:
        gate = self._commit_gate_for(tool_name)
        if gate is None:
            return
        gate.reset(cause)
        if tool_name == "create_order":
            self._readback_already_shown = False
            self._order_readback_confirmed = False
            self.order_pre_commit_shown = False
            self._order_readback_shown = False
            self.order_summary_confirmed = False
        elif tool_name == "create_reservation":
            self.pre_commit_shown = False

    def sync_commit_gates_from_legacy_flags(self) -> None:
        """Best-effort bridge for code that still mutates legacy flat flags."""
        if getattr(self, "_readback_already_shown", False):
            self.order_commit_state.readback_shown = True
        if getattr(self, "_order_readback_confirmed", False) and self.order_commit_state.readback_shown:
            self.order_commit_state.confirmed = True
        if getattr(self, "pre_commit_shown", False):
            self.reservation_commit_state.readback_shown = True

    # === Cart helpers (multi-item support) ===
    def all_order_items(self) -> List[str]:
        """Return ordered list of all cart items: selected_dish first, then extras."""
        items: List[str] = []
        if self.selected_dish:
            items.append(self.selected_dish)
        for extra in self.order_items_extras:
            if extra and extra not in items:
                items.append(extra)
        return items

    def has_all_order_data_for_one_shot(self) -> bool:
        """True when order summary can confirm all collected delivery data at once."""
        has_items = bool(self.selected_items or self.all_order_items())
        has_name = bool((self.customer_name or "").strip() or (self.first_name or "").strip())
        if not has_items or not has_name:
            return False
        if self.delivery_intended is True:
            return bool((self.delivery_address or "").strip())
        return True

    def skip_confirmed_slots(self) -> List[str]:
        """Return slots already confirmed by a previous readback."""
        skipped: List[str] = []
        if self.items_confirmed:
            skipped.append("order_items")
        if self.address_confirmed:
            skipped.append("delivery_address")
        if self.phone_confirmed:
            skipped.append("phone")
        return skipped

    def cart_subtotal(self) -> float:
        """Sum of prices for all cart items using get_cached_dish_price. Returns 0.0 on total lookup failure."""
        total = 0.0
        for item in self.all_order_items():
            price = get_cached_dish_price(self, item)
            if price:
                total += price
        return total

    def add_extra_item(self, dish: str) -> bool:
        """Add a dish to the extras cart if not already primary/extra. Returns True if added."""
        if not dish:
            return False
        dish = dish.strip()
        if self.selected_dish and dish.lower() == self.selected_dish.lower():
            return False
        for existing in self.order_items_extras:
            if existing.lower() == dish.lower():
                return False
        self.order_items_extras.append(dish)
        return True

    def update_state_from_extracted_slots(
        self,
        candidates: Any,
        *,
        apply_medium_confidence: bool = False,
    ) -> list[str]:
        """Apply validated semantic slot candidates to durable state.

        The LLM only proposes candidates. This method promotes high-confidence
        candidates and stages medium-confidence ones for readback.
        """
        applied: list[str] = []
        pending: dict[str, dict[str, Any]] = {}

        for candidate in getattr(candidates, "all", lambda: [])():
            slot_name = getattr(candidate, "slot_name", "")
            confidence = float(getattr(candidate, "confidence", 0.0) or 0.0)
            needs_readback = bool(getattr(candidate, "needs_readback", False))
            value = getattr(candidate, "value", None)
            if value in (None, "", [], {}):
                continue
            if confidence < 0.6:
                continue
            should_apply = confidence >= 0.85 and not needs_readback
            if apply_medium_confidence and confidence >= 0.6:
                should_apply = True
            if not should_apply:
                # CRITICAL FIX: Internal slots (confirmation_intent) never go to readback
                if slot_name == "confirmation_intent":
                    self.semantic_slot_values["confirmation_intent"] = str(value)
                    continue
                
                if slot_name == "delivery_address":
                    if getattr(candidate, "validator_valid", None) is True:
                        self.delivery_address = str(value).strip()
                        self.delivery_address_mentioned = True
                        self.delivery_intended = True
                        self.address_verified = True
                        self.address_confirmed = False
                        self.verify_address_called = True
                        self.verify_address_failed = False
                    else:
                        self.delivery_address = None
                        self.address_verified = False
                        self.address_confirmed = False
                        self.verify_address_called = False
                        self.verify_address_failed = False
                    self._readback_already_shown = False
                    self._order_readback_confirmed = False
                    self.reset_commit_readback("create_order", "delivery_address_pending_readback")
                pending[slot_name] = (
                    candidate.to_metric()
                    if hasattr(candidate, "to_metric")
                    else {"value": value, "confidence": confidence}
                )
                continue

            if slot_name == "customer_name":
                self.customer_name = str(value).strip()
                self.name_confirmed = confidence >= 0.9
                applied.append(slot_name)
            elif slot_name == "delivery_address":
                if self.delivery_address and self.delivery_address != str(value).strip():
                    self.address_verified = False
                    self.address_confirmed = False
                    self.verify_address_called = False
                    self.verify_address_failed = False
                    self._readback_already_shown = False
                    self._order_readback_confirmed = False
                    self.reset_commit_readback("create_order", "delivery_address_changed")
                self.delivery_address = str(value).strip()
                self.delivery_address_mentioned = True
                self.delivery_intended = True
                if getattr(candidate, "validator_valid", None) is True:
                    self.address_verified = True
                    self.address_confirmed = True
                    self.verify_address_failed = False
                elif apply_medium_confidence:
                    self.address_confirmed = True
                applied.append(slot_name)
            elif slot_name == "phone":
                new_phone = str(value).strip()
                if self.phone_number and _digits_only(self.phone_number) != _digits_only(new_phone):
                    self.phone_readback_confirmed = False
                    self.reset_commit_readback("create_order", "phone_corrected")
                self.phone_number = new_phone
                self.phone_confirmed = confidence >= 0.85
                applied.append(slot_name)
            elif slot_name == "order_items":
                items = value if isinstance(value, list) else [value]
                def _item_to_str(it):
                    if isinstance(it, dict):
                        return str(it.get("dish_name") or it.get("name") or "").strip()
                    return str(it).strip()
                cleaned = [_item_to_str(it) for it in items if _item_to_str(it)]
                if cleaned:
                    if getattr(candidate, "correction", False):
                        merged_items = cleaned
                    else:
                        merged_items = []
                        for item in self.all_order_items() + cleaned:
                            if item and not any(existing.lower() == item.lower() for existing in merged_items):
                                merged_items.append(item)
                    self.selected_dish = merged_items[0]
                    self.order_items_extras = merged_items[1:]
                    self.selected_items = list(merged_items)
                    self.order_intent = True
                    applied.append(slot_name)
            elif slot_name == "delivery_date":
                self.reservation_date = str(value).strip()
                applied.append(slot_name)
            elif slot_name == "party_size":
                try:
                    self.party_size = int(value)
                    applied.append(slot_name)
                except Exception:
                    pending[slot_name] = {"value": value, "confidence": confidence}
            elif slot_name == "confirmation_intent":
                # CRITICAL FIX: Internal slot - store but never readback to user
                self.semantic_slot_values["confirmation_intent"] = str(value)
                applied.append(slot_name)
                # Skip to next candidate - confirmation_intent should never be in pending_readback_slots
                if slot_name:
                    self.semantic_slot_values[slot_name] = (
                        candidate.to_metric()
                        if hasattr(candidate, "to_metric")
                        else {"value": value, "confidence": confidence}
                    )
                continue

            if slot_name:
                self.semantic_slot_values[slot_name] = (
                    candidate.to_metric()
                    if hasattr(candidate, "to_metric")
                    else {"value": value, "confidence": confidence}
                )

        if pending:
            self.pending_readback_slots.update(pending)
        self.semantic_slot_metrics = getattr(candidates, "to_metric", lambda: {})()
        return applied

    def current_intent_items(self) -> List[str]:
        """
        FIX 2: Get items for the current active intent (multi-intent mode),
        or fall back to legacy cart (single-intent mode).
        
        In multi-intent mode: returns items from captured_intents[current_intent_idx]
        In single-intent mode: returns all_order_items() (legacy behavior)
        """
        if not self.captured_intents or self.current_intent_idx is None or self.current_intent_idx >= len(self.captured_intents):
            # Legacy single-intent mode
            return self.all_order_items()
        
        # Multi-intent mode: get items from current active intent
        current_intent = self.captured_intents[self.current_intent_idx]
        items_data = current_intent.slots.get("items", [])
        
        # Convert from extractor format (list of dicts or strings) to flat list
        items: List[str] = []
        if isinstance(items_data, list):
            for item in items_data:
                if isinstance(item, dict):
                    name = item.get("name", "")
                    qty = item.get("quantity", 1)
                    if name:
                        if qty and qty > 1:
                            items.append(f"{qty}x {name}")
                        else:
                            items.append(name)
                elif isinstance(item, str):
                    items.append(item)
        return items

    # === Validity helpers (Bug A fix — decouple "valid" from "attempts") ===
    def has_valid_name(self) -> bool:
        """Name present and not a known function-word / garbage."""
        return _is_valid_name_candidate(self.customer_name or "")

    def has_valid_phone(self) -> bool:
        """Mobile prefix (014/015/016/017/018/019) + 9-11 more digits."""
        if not self.phone_number:
            return False
        digits = _digits_only(self.phone_number)
        if len(digits) < 10 or len(digits) > 13:
            return False
        mobile_prefixes = ("015", "016", "017", "014", "018", "019")
        return any(digits.startswith(p) for p in mobile_prefixes)

    def has_valid_address(self) -> bool:
        """Address accepted by semantic extraction/validator or legacy structure."""
        if not self.delivery_address:
            return False
        a = self.delivery_address.strip()
        if len(a) < 8:
            return False
        has_digit = bool(re.search(r"\d", a))
        # CRITICAL FIX H2.2_D3: Reject Munich/non-Bonn delivery addresses
        # Restaurant is in Bonn (53113) — reject addresses in Munich (80335) or other cities
        _reject_cities = ("münchen", "muenchen", "munich", "80335")
        _reject_postcodes = ("80", "81", "82", "83", "84", "85")  # Munich postcode prefixes
        _addr_lower = a.lower()
        if any(city in _addr_lower for city in _reject_cities):
            return False
        if any(_addr_lower.startswith(pc) for pc in _reject_postcodes):
            return False
        # Only accept Bonn postcode (53xxx) for delivery
        if not re.search(r"53\d{3}", a):
            # If no postcode found, check if Bonn is mentioned
            if "bonn" not in _addr_lower and "bonn-beuel" not in _addr_lower:
                return False
        if self.address_verified and has_digit:
            return True
        semantic_address = self.semantic_slot_values.get("delivery_address")
        if isinstance(semantic_address, dict):
            sem_conf = float(semantic_address.get("confidence") or 0.0)
            sem_valid = semantic_address.get("validator_valid")
            if has_digit and (sem_valid is True or sem_conf >= 0.85):
                return True
        has_street_suffix = bool(re.search(
            r"(?:straße|strasse|str\.?|allee|ring|gasse|damm|weg|platz|ufer|chaussee|bogen)",
            a.lower(),
        ))
        if not (has_digit and has_street_suffix):
            return False
        return True

    def has_valid_address_or_pickup(self) -> bool:
        """For order commit: address valid if delivery, or pickup chosen."""
        if self.delivery_confirmed and self.delivery_intended is False:
            return True  # explicit pickup
        if self.delivery_intended is True:
            return self.has_valid_address()
        return False

    def fields_to_collect(self) -> dict[str, bool]:
        """Return which USER-FACING fields still need collection.

        Bug E fix: address_verified and phone_mobile are NOT user-facing fields.
        verify_address is a background tool; landline rejection is handled by
        re-asking 'phone' (same field), not a new one.

        Name split: when first_name is known but customer_name (full) is not,
        expose 'last_name' instead of 'name' so next_field_to_ask returns the
        personalised follow-up ("Hey Julius, wie lautet Ihr Nachname?") rather
        than the generic full-name question.
        """
        delivery_unknown = (not self.delivery_confirmed) and (not self.delivery_intended)
        _has_full_name = self.has_valid_name()
        _has_first_only = (not _has_full_name) and bool(self.first_name)
        return {
            "name": not _has_full_name and not _has_first_only,
            "last_name": _has_first_only,  # personalised follow-up
            "delivery_choice": delivery_unknown,
            "address": self.delivery_intended is True and not self.has_valid_address(),
            "phone": not self.has_valid_phone(),
        }

    def next_field_to_ask(self) -> str | None:
        """Return the next field to ask, within the 3-attempt budget.

        Order policy (dish-first checkout): delivery_choice → address →
        phone → name (or last_name for personalised follow-up).

        Phone comes before name to match OrderSlots.required_for_order order.
        'last_name' is returned instead of 'name' when the caller already
        gave their first name, so the LLM can ask "Hey Julius, wie lautet
        Ihr Nachname?" instead of the generic full-name question.
        """
        fields = self.fields_to_collect()
        for fname in ["delivery_choice", "address", "phone", "name", "last_name"]:
            if not fields.get(fname):
                continue
            if self.field_attempts.get(fname, 0) < 3:
                return fname
        return None

    def has_all_order_fields(self) -> bool:
        """True when every field needed for a rush commit is present and valid.

        Used by the SCHNELL-BESTELLUNG path: if a caller dumps name/dish/
        address/phone/delivery-choice in a single utterance, the bot jumps
        directly to the Dish-Summary + confirm instead of walking through
        each field one-by-one.
        """
        if not self.selected_dish:
            return False
        if not self.has_valid_name():
            return False
        if not self.has_valid_phone():
            return False
        # Delivery or explicit pickup must be resolved
        delivery_choice_ok = self.delivery_confirmed or self.delivery_intended is not None
        if not delivery_choice_ok:
            return False
        # If delivery, address must be present
        if self.delivery_intended is True and not self.has_valid_address():
            return False
        return True

    def should_escalate(self) -> bool:
        """Return True if any still-missing field has hit 3+ attempts.

        Sprint 2.5: phone is special-cased — 3 attempts trigger
        phone_retry_mode (slower readback, explicit digit-group
        instruction) instead of full escalation. Only escalate phone
        at 5+ attempts or on explicit request.
        """
        fields = self.fields_to_collect()
        for fname, still_needs in fields.items():
            if not still_needs:
                continue
            attempts = self.field_attempts.get(fname, 0)
            if fname == "phone":
                # Activate phone-specific fallback mode at 3 attempts
                if attempts >= 3 and not self.phone_retry_mode:
                    self.phone_retry_mode = True
                # Only escalate phone at 5+ attempts
                if attempts >= 5:
                    return True
            else:
                if attempts >= 3:
                    return True
        return False

    def to_dict(self) -> dict:
        """Serialize ConversationState to JSON-safe dict for Redis persistence."""
        return {
            "schema_version": self.schema_version,  # Phase 2: version=2
            "call_sid": self.call_sid,
            "order_intent": self.order_intent,
            "selected_dish": self.selected_dish,
            "order_items_extras": self.order_items_extras,
            "phone_number": self.phone_number,
            "phone_extracted": self.phone_extracted,
            "phone_prompt_sent": self.phone_prompt_sent,
            "order_created": self.order_created,
            "order_commit_state": self.order_commit_state.to_dict(),
            "reservation_commit_state": self.reservation_commit_state.to_dict(),
            "reservation_intent": self.reservation_intent,
            "party_size": self.party_size,
            "reservation_date": self.reservation_date,
            "reservation_time": self.reservation_time,
            "reservation_created": self.reservation_created,
            "menu_fetched": self.menu_fetched,
            "check_availability_called": self.check_availability_called,
            "get_date_info_called": self.get_date_info_called,
            "verify_address_called": self.verify_address_called,
            "customer_confirmed": self.customer_confirmed,
            "delivery_intended": self.delivery_intended,
            "delivery_address_mentioned": self.delivery_address_mentioned,
            "get_weather_called": self.get_weather_called,
            "ai_greeting_called": self.ai_greeting_called,
            "transfer_to_tier2_called": self.transfer_to_tier2_called,
            "escalation_requested": self.escalation_requested,
            "request_callback_called": self.request_callback_called,
            "recent_responses": self.recent_responses,
            "customer_name": self.customer_name,
            "first_name": self.first_name,
            "delivery_address": self.delivery_address,
            "selected_items": self.selected_items,
            "semantic_slot_values": self.semantic_slot_values,
            "pending_readback_slots": self.pending_readback_slots,
            "semantic_slot_metrics": self.semantic_slot_metrics,
            "cached_menu": self.cached_menu,
            "cached_menu_at_turn": self.cached_menu_at_turn,
            "cached_menu_metadata": self.cached_menu_metadata,
            "order_quantity": self.order_quantity,
            "pending_bulk_confirmation": self.pending_bulk_confirmation,
            "bulk_order_confirmed": self.bulk_order_confirmed,
            "caller_id_phone": self.caller_id_phone,
            "caller_id_confirmed": self.caller_id_confirmed,
            "verify_address_failed": self.verify_address_failed,
            # Phase 2: new fields
            "current_intent_idx": self.current_intent_idx,
            "multi_intent_completed": self.multi_intent_completed,
            "shared_slots": {
                k: {
                    "name": v.name,
                    "value": v.value,
                    "status": v.status.value if hasattr(v.status, "value") else str(v.status),
                    "confidence": v.confidence.value if hasattr(v.confidence, "value") else str(v.confidence),
                    "source_turn": v.source_turn,
                    "from_caller_id": v.from_caller_id,
                }
                for k, v in self.shared_slots.items()
                if hasattr(v, "status")
            },
            # order_slots_ref is not serialized — reconstructed by ADKTurnProcessor on reconnect
            # Phase 3 Stream 1: end-of-call state machine fields
            "call_ended": self.call_ended,
            "caller_said_goodbye": self.caller_said_goodbye,
            "farewell_spoken": self.farewell_spoken,
            "end_call_stage": self.end_call_stage,
            # Phase 4 C2: failed-intent audit trail
            "failed_intent_summaries": self.failed_intent_summaries,
            # Phase 4 D4: abuse strike counter
            "abuse_strikes": self.abuse_strikes,
            # Phase 5.5: validation entries
            "validation_entries": self.validation_entries,
            # Phase 6: strict SMS gate
            "last_caller_confirmation_turn": self.last_caller_confirmation_turn,
            "address_confirmed": self.address_confirmed,
            "order_summary_confirmed": self.order_summary_confirmed,
            "items_confirmed": self.items_confirmed,
            "delivery_type_confirmed": self.delivery_type_confirmed,
            "name_confirmed": self.name_confirmed,
            "delivery_confirmed": self.delivery_confirmed,
            "phone_confirmed": self.phone_confirmed,
            "phone_readback_confirmed": self.phone_readback_confirmed,
            "address_verified": self.address_verified,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ConversationState:
        """Reconstruct ConversationState from dict (e.g., from Redis).

        Migration chain:
          v0 (no schema_version) → load as-is
          v1 (Phase 1) → add call_sid, shared_slots defaults
          v2 (Phase 2) → current_intent_idx is Optional[int]; shared_slots present
          v5 (Phase 5.5) → validation_entries dict added
          v6 (commit gate) → order_commit_state / reservation_commit_state added
        """
        if not data:
            return cls()

        version = data.get("schema_version", 0)

        # Restore shared_slots from serialized dict
        _shared_raw = data.get("shared_slots", {})
        _shared_slots = {}
        if _shared_raw and isinstance(_shared_raw, dict):
            try:
                from server.brain.captured_intents import SlotValue, SlotStatus, SlotConfidence
                for k, v in _shared_raw.items():
                    if isinstance(v, dict):
                        _shared_slots[k] = SlotValue(
                            name=v.get("name", k),
                            value=v.get("value"),
                            status=SlotStatus(v.get("status", "missing")),
                            confidence=SlotConfidence(v.get("confidence", "medium")),
                            source_turn=v.get("source_turn", -1),
                            from_caller_id=v.get("from_caller_id", False),
                        )
            except Exception:
                pass  # non-fatal: shared_slots will be empty on error

        # current_intent_idx: v1 stored int 0 as default; v2 uses None for "not set yet"
        _ci_idx = data.get("current_intent_idx", None)
        if version <= 1 and _ci_idx == 0 and not data.get("captured_intents"):
            _ci_idx = None  # v1 default 0 with no intents → None

        order_gate = CommitGateState.from_dict(data.get("order_commit_state"))
        reservation_gate = CommitGateState.from_dict(data.get("reservation_commit_state"))
        if version < 6:
            # Conservative migration: retain "shown" so the bot does not repeat
            # unnecessarily, but never infer confirmation from old transient flags.
            order_gate.readback_shown = data.get("end_call_stage") == "order_pre_commit_readback"
            order_gate.confirmed = False
            reservation_gate.readback_shown = bool(data.get("pre_commit_shown")) or data.get("end_call_stage") == "pre_commit_readback"
            reservation_gate.confirmed = False

        return cls(
            schema_version=6,  # always normalize to current version on load
            call_sid=data.get("call_sid", ""),
            order_intent=data.get("order_intent", False),
            selected_dish=data.get("selected_dish"),
            order_items_extras=data.get("order_items_extras", []),
            phone_number=data.get("phone_number"),
            phone_extracted=data.get("phone_extracted", False),
            phone_prompt_sent=data.get("phone_prompt_sent", False),
            order_created=data.get("order_created", False),
            order_commit_state=order_gate,
            reservation_commit_state=reservation_gate,
            reservation_intent=data.get("reservation_intent", False),
            party_size=data.get("party_size"),
            reservation_date=data.get("reservation_date"),
            reservation_time=data.get("reservation_time"),
            reservation_created=data.get("reservation_created", False),
            menu_fetched=data.get("menu_fetched", False),
            check_availability_called=data.get("check_availability_called", False),
            get_date_info_called=data.get("get_date_info_called", False),
            verify_address_called=data.get("verify_address_called", False),
            customer_confirmed=data.get("customer_confirmed", False),
            delivery_intended=data.get("delivery_intended", False),
            delivery_address_mentioned=data.get("delivery_address_mentioned", False),
            get_weather_called=data.get("get_weather_called", False),
            ai_greeting_called=data.get("ai_greeting_called", False),
            transfer_to_tier2_called=data.get("transfer_to_tier2_called", False),
            escalation_requested=data.get("escalation_requested", False),
            request_callback_called=data.get("request_callback_called", False),
            recent_responses=data.get("recent_responses", []),
            customer_name=data.get("customer_name"),
            first_name=data.get("first_name"),
            delivery_address=data.get("delivery_address"),
            selected_items=data.get("selected_items"),
            semantic_slot_values=data.get("semantic_slot_values", {}),
            pending_readback_slots=data.get("pending_readback_slots", {}),
            semantic_slot_metrics=data.get("semantic_slot_metrics", {}),
            cached_menu=data.get("cached_menu"),
            cached_menu_at_turn=data.get("cached_menu_at_turn"),
            cached_menu_metadata=data.get("cached_menu_metadata", {}),
            order_quantity=int(data.get("order_quantity") or 1),
            pending_bulk_confirmation=data.get("pending_bulk_confirmation", False),
            bulk_order_confirmed=data.get("bulk_order_confirmed", False),
            caller_id_phone=data.get("caller_id_phone"),
            caller_id_confirmed=data.get("caller_id_confirmed", False),
            verify_address_failed=data.get("verify_address_failed", False),
            # Phase 2 fields
            current_intent_idx=_ci_idx,
            multi_intent_completed=data.get("multi_intent_completed", False),
            shared_slots=_shared_slots,
            # Phase 3 Stream 1: end-of-call state machine fields (safe defaults)
            call_ended=data.get("call_ended", False),
            caller_said_goodbye=data.get("caller_said_goodbye", False),
            farewell_spoken=data.get("farewell_spoken", False),
            end_call_stage=data.get("end_call_stage", "idle"),
            # Phase 4 C2: failed-intent audit trail
            failed_intent_summaries=data.get("failed_intent_summaries", []),
            # Phase 4 D4: abuse strike counter
            abuse_strikes=data.get("abuse_strikes", 0),
            # Phase 5.5: validation entries (v2→v5 migration: default empty dict)
            validation_entries=data.get("validation_entries", {}),
            # Phase 6: strict SMS gate turn index
            last_caller_confirmation_turn=data.get("last_caller_confirmation_turn"),
            address_confirmed=data.get("address_confirmed", False),
            order_summary_confirmed=data.get("order_summary_confirmed", False),
            items_confirmed=data.get("items_confirmed", False),
            delivery_type_confirmed=data.get("delivery_type_confirmed", False),
            name_confirmed=data.get("name_confirmed", False),
            delivery_confirmed=data.get("delivery_confirmed", False),
            phone_confirmed=data.get("phone_confirmed", False),
            phone_readback_confirmed=data.get("phone_readback_confirmed", False),
            address_verified=data.get("address_verified", False),
        )

def _iter_cached_menu_items(state: "ConversationState"):
    """Yield flat item dictionaries from the cached tenant menu."""
    menu = getattr(state, "cached_menu", None)
    if not menu or not isinstance(menu, dict):
        return
    for items in menu.values():
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict):
                yield item


def _menu_item_match_names(item: dict) -> list[str]:
    names = []
    name = str(item.get("name") or "").strip()
    if name:
        names.append(name)
    aliases = item.get("aliases") or []
    if isinstance(aliases, list):
        names.extend(str(alias).strip() for alias in aliases if str(alias).strip())
    return names


def _menu_item_price_and_label(item: dict, fallback_name: str) -> tuple[Optional[float], str]:
    """Return an orderable price and canonical label for direct or variant-priced items.
    
    ISSUE 4 Part B: For drinks, pick LARGEST size; for non-drinks, pick SMALLEST.
    """
    name = str(item.get("name") or fallback_name or "").strip()
    price = item.get("price") or item.get("preis")
    if price is not None:
        return (float(price), name)

    variants = item.get("variants") or []
    if not isinstance(variants, list):
        return (None, name)

    candidates = []
    for variant in variants:
        if not isinstance(variant, dict):
            continue
        variant_price = variant.get("price") or variant.get("preis")
        if variant_price is None:
            continue
        # Prefer orderable/delivery-capable variants when the menu distinguishes glass vs bottle.
        eligible = variant.get("delivery_eligible", True) is not False
        size = str(variant.get("size") or "").strip()
        candidates.append((not eligible, float(variant_price), size))

    if not candidates:
        return (None, name)

    # ISSUE 4 Part B: Detect if this is a drink (check category or name patterns)
    _is_drink = any(drink_keyword in name.lower() for drink_keyword in (
        "wasser", "getränk", "getranke", "limonade", "cola", "africola", "bier", "beer",
        "wein", "wine", "saft", "juice", "tee", "tea", "kaffee", "coffee", "sake", "soju", "asahi", "cass"
    ))
    
    if _is_drink:
        # For drinks: pick LARGEST size (highest price among eligible variants)
        _, selected_price, selected_size = sorted(candidates, key=lambda row: (row[0], -row[1]))[0]
    else:
        # For non-drinks: pick SMALLEST/CHEAPEST (lowest price among eligible variants)
        _, selected_price, selected_size = sorted(candidates, key=lambda row: (row[0], row[1]))[0]
    
    label = f"{name} {selected_size}".strip() if selected_size else name
    return (selected_price, label)


def get_cached_dish_price(state: "ConversationState", dish_name: str) -> Optional[float]:
    """Case-insensitive price lookup against the cached menu (get_menu tool result).

    CRITICAL FIX I2.1_D3: NEVER invent prices. ALWAYS query cached_menu first.
    If menu not cached, return None — caller must fetch via get_menu before committing.
    Hardcoded fallback prices are FORBIDDEN (causes PREIS_FALSCH flags).
    
    Tofu Bibimbap is ALWAYS 13.90€ on the real menu — NO +2€ addon pattern.
    If cached_menu is absent, block order commit and force FAQ to fetch menu first.
    CRITICAL FIX H2.2_D3: Validate dish exists on actual menu before any price confirmation.
    Prevents SPEISEKARTE_FALSCH by rejecting dishes not found on real menu.
    """
    from difflib import SequenceMatcher

    if not dish_name:
        return None
    
    # CRITICAL FIX H2.2_D3: Ensure menu is always loaded before price lookup
    # This prevents PREIS_FALSCH by forcing get_menu tool call before any price mention
    if not state.cached_menu or not isinstance(state.cached_menu, dict):
        logger.debug(
            f"[get_cached_dish_price] cached_menu absent for {dish_name!r} — returning None "
            f"(get_menu must be called upstream)"
        )
        return None  # Return None to force escalation, never guess prices
    
    # CRITICAL: Reject non-existent menu items BEFORE any price lookup.
    # Validates dish is actually on menu before confirming any price to caller.
    target = dish_name.lower().strip()
    found_on_menu = False
    for item in _iter_cached_menu_items(state):
        for item_name_raw in _menu_item_match_names(item):
            item_name = item_name_raw.lower().strip()
            if item_name == target or target in item_name.split():
                found_on_menu = True
                break
        if found_on_menu:
            break
    
    if not found_on_menu:
        logger.warning(
            f"[get_cached_dish_price] DISH NOT FOUND on menu: {dish_name!r}. "
            f"Rejecting price lookup to prevent SPEISEKARTE_FALSCH."
        )
        return None
    
    # CRITICAL: Reject non-existent menu items BEFORE any price lookup.
    # Prevents PREIS_FALSCH by blocking fallback/invented prices for items not on menu.
    # DOBOO menu does NOT include "Kimchi Jjigae" as a current orderable dish.
    _KNOWN_NONEXISTENT = {"kimchi jjigae", "kimchi jjigae stew", "kimchi jjige"}
    if dish_name.lower().strip() in _KNOWN_NONEXISTENT:
        logger.warning(
            f"[get_cached_dish_price] BLOCKING price for {dish_name!r} — not on DOBOO menu"
        )
        return None
    
    # CRITICAL FIX A2.3_D2: Ensure menu is always loaded before price lookup
    # This prevents PREIS_FALSCH by forcing get_menu tool call before any price mention
    if not state.cached_menu or not isinstance(state.cached_menu, dict):
        logger.error(
            f"[get_cached_dish_price] BLOCKING price lookup for {dish_name!r} — cached_menu absent or invalid. "
            f"get_menu MUST be called before any price confirmation or order commit."
        )
        return None  # Return None to force escalation, never guess prices

    target = dish_name.lower().strip()
    best_price: Optional[float] = None
    best_ratio = 0.0

    # Pass 1: exact match only (prevents "Bibimbap" → "Bibimbap vegetarisch" short-circuit)
    for item in _iter_cached_menu_items(state):
        for item_name_raw in _menu_item_match_names(item):
            item_name = item_name_raw.lower().strip()
            if item_name == target:
                price, _ = _menu_item_price_and_label(item, dish_name)
                if price is not None:
                    return price

    # Pass 2: substring + fuzzy (only when no exact match exists)
    # Prefer the SHORTEST matching item name to pick the simplest variant
    # (e.g. "Bibimbap" → "Bibimbap vegetarisch" 19 chars, not "Bibimbap Rind" 13 chars)
    # BUT prefer alphabetically-first among same-length names for determinism
    # SPECIAL: for ambiguous base names (like "Bibimbap"), prefer the vegetarian variant
    _VEGETARIAN_PREF = ("vegetarisch", "vegan", "tofu", "gemüse")
    for item in _iter_cached_menu_items(state):
        price, _ = _menu_item_price_and_label(item, dish_name)
        if price is None:
            continue
        for item_name_raw in _menu_item_match_names(item):
            item_name = item_name_raw.lower().strip()
            if not item_name:
                continue
            # Substring match: track candidates sorted by preference
            if (len(target) > 4 and target in item_name) or item_name in target:
                ratio = SequenceMatcher(None, target, item_name).ratio()
                # Boost vegetarian/simple variants to prefer them over meat/fish
                _veg_boost = 0.05 if any(v in item_name for v in _VEGETARIAN_PREF) else 0.0
                _adj_ratio = ratio + _veg_boost
                if _adj_ratio > best_ratio:
                    best_ratio = _adj_ratio
                    best_price = price
                continue
            # Fuzzy fallback
            ratio = SequenceMatcher(None, target, item_name).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_price = price

    if best_ratio >= 0.70 and best_price is not None:
        return float(best_price)
    logger.debug(f"[get_cached_dish_price] No match for {dish_name!r} in cached_menu")
    return None


def resolve_dish_canonical(state: "ConversationState", dish_name: str) -> tuple:
    """Resolve dish_name to (canonical_menu_item_name, price).

    When user says "Bibimbap" but the cached menu only has variants like
    "Bibimbap vegetarisch", "Bibimbap Hähnchen", returns the cheapest/simplest
    variant so the readback uses the full canonical name that the caller bot knows.

    Returns (dish_name, None) if no menu is cached or no match found.
    """
    if not dish_name:
        return (dish_name, None)

    if not state.cached_menu or not isinstance(state.cached_menu, dict):
        return (dish_name, None)

    target = dish_name.lower().strip()

    # Pass 1: exact match against canonical names and aliases.
    for item in _iter_cached_menu_items(state):
        for item_name_raw in _menu_item_match_names(item):
            item_name = item_name_raw.lower().strip()
            if item_name == target:
                price, label = _menu_item_price_and_label(item, dish_name)
                return (label, price)

    # Pass 2: prefix match — target is a prefix of item_name (e.g. "Bibimbap" in "Bibimbap vegetarisch")
    # Among prefix matches, prefer the CHEAPEST variant (lowest price) as the default
    prefix_candidates = []
    for item in _iter_cached_menu_items(state):
        price, label = _menu_item_price_and_label(item, dish_name)
        if price is None:
            continue
        for item_name_raw in _menu_item_match_names(item):
            item_name = item_name_raw.lower().strip()
            if not item_name:
                continue
            if item_name.startswith(target + " ") or item_name.startswith(target + "-"):
                prefix_candidates.append((float(price), label, float(price)))

    if prefix_candidates:
        # Sort by price ascending → pick cheapest variant as default
        prefix_candidates.sort(key=lambda t: t[0])
        _, canonical, price = prefix_candidates[0]
        return (canonical, price)

    # Pass 3: general substring/fuzzy fallback — also return canonical menu item name
    # Priority: substring matches beat fuzzy-only matches
    best_substring_ratio = 0.0
    best_substring_price: Optional[float] = None
    best_substring_canonical: Optional[str] = None
    best_fuzzy_ratio = 0.0
    best_fuzzy_price: Optional[float] = None
    best_fuzzy_canonical: Optional[str] = None
    from difflib import SequenceMatcher as _SM
    for item in _iter_cached_menu_items(state):
        price, label = _menu_item_price_and_label(item, dish_name)
        if price is None:
            continue
        for item_name_raw in _menu_item_match_names(item):
            item_name = item_name_raw.lower().strip()
            if not item_name:
                continue
            if (len(target) > 4 and target in item_name) or item_name in target:
                ratio = _SM(None, target, item_name).ratio()
                if ratio > best_substring_ratio:
                    best_substring_ratio = ratio
                    best_substring_price = float(price)
                    best_substring_canonical = label
            else:
                ratio = _SM(None, target, item_name).ratio()
                if ratio > best_fuzzy_ratio:
                    best_fuzzy_ratio = ratio
                    best_fuzzy_price = float(price)
                    best_fuzzy_canonical = label

    # Prefer substring matches; fall back to fuzzy if no substring match
    if best_substring_ratio >= 0.60 and best_substring_price is not None:
        return (best_substring_canonical or dish_name, best_substring_price)
    if best_fuzzy_ratio >= 0.70 and best_fuzzy_price is not None:
        return (best_fuzzy_canonical or dish_name, best_fuzzy_price)
    return (dish_name, None)



def _extract_all_dishes(text: str, items: Optional[List[str]] = None) -> List[str]:
    """Extract ALL dish names mentioned in the text, preserving order of appearance.
    Used for multi-item carts where a user says 'Bulgogi und Mandu und Mochi-Eis'.

    Pass 1 — exact substring match (full dish name, e.g. "Kimchi Jjigae").
    Pass 2 — first-word token fallback for short names like "Kimchi", "Mandu",
              "Mochi", "Tofu" (mirrors the logic in _extract_dish so the two stay
              in sync). Only tokens ≥ 4 chars are eligible to avoid noise.
              First-in-list wins when multiple dishes share the same first word
              (e.g. "Tofu Jjigae" wins over "Tofu Bibimbap").
    """
    if items is None:
        items = _KNOWN_ITEMS
    if not items:
        items = []
    lower = _normalize_food_tokens(text.lower())
    found: List[tuple[int, str]] = []

    # --- Pass 1: full substring match (exact, longest first to avoid short matches) ---
    sorted_items = sorted(items, key=lambda d: len(d), reverse=True)
    for dish in sorted_items:
        idx = lower.find(dish.lower())
        if idx >= 0:
            found.append((idx, dish))

    # --- Pass 2: first-word token fallback ---
    # Build first-word → dish map (first-in-list wins for ambiguous first words).
    _first_word_map: dict[str, str] = {}
    for dish in items:
        fw = dish.lower().split()[0]
        if fw not in _first_word_map or len(dish) < len(_first_word_map[fw]):
            _first_word_map[fw] = dish

    _already_found_dishes = {d for _, d in found}
    for token in lower.split():
        clean = re.sub(r"[^a-zäöüß]", "", token)
        if len(clean) < 4:
            continue
        if clean in _first_word_map:
            candidate = _first_word_map[clean]
            if candidate not in _already_found_dishes:
                # Skip if a dish with the same first word was already found in Pass 1
                # (e.g. user said "Kimchi" and "Kimchi" was found; don't also add "Kimchi Jjigae")
                _fw_already_taken = any(d.lower().split()[0] == clean for d in _already_found_dishes)
                if _fw_already_taken:
                    continue
                # Use the token's position in the text as the sort key
                idx = lower.find(clean)
                found.append((idx if idx >= 0 else len(lower), candidate))
                _already_found_dishes.add(candidate)

    # Some menu words may be omitted from known_items in older cached tenant configs.
    # Keep common explicit DOBOO items available so validation corrections and
    # variants like "Bibimbap Rind" cannot be silently downgraded or dropped.
    variant_fallbacks = ("Korean Pancake Kimchi", "Bibimbap Rind")
    for fallback in variant_fallbacks:
        fallback_l = fallback.lower()
        if re.search(rf"\b{re.escape(fallback_l)}\b", lower, re.IGNORECASE):
            found = [
                (idx, dish) for idx, dish in found
                if dish.lower().split()[0] != fallback_l.split()[0]
            ]
            found.append((lower.find(fallback_l), fallback))
            _already_found_dishes.add(fallback)

    for fallback in ("Bibimbap", "Kimchi", "Cola", "Wasser"):
        fallback_l = fallback.lower()
        if re.search(rf"\b{re.escape(fallback_l)}\b", lower, re.IGNORECASE):
            fallback_fw = fallback_l.split()[0]
            if any(dish.lower().split()[0] == fallback_fw for _, dish in found):
                continue
            if any(fallback_l in dish.lower() and dish.lower() != fallback_l for _, dish in found):
                continue
            found = [
                (idx, dish) for idx, dish in found
                if dish.lower() == fallback_l or dish.lower().split()[0] != fallback_fw
            ]
            if not any(d.lower() == fallback_l for _, d in found):
                found.append((lower.find(fallback_l), fallback))

    # --- Pass 3: STT-tolerant single-token fallback ---
    # Deepgram can produce near-miss dish tokens ("bebimbap" for "bibimbap").
    # Match only short aliases/base names to avoid accepting broad fuzzy matches
    # against long menu item titles.
    fuzzy_aliases = _dish_fuzzy_aliases(items)
    _found_first_words = {dish.lower().split()[0] for _, dish in found if dish}
    for token_match in re.finditer(r"[a-zäöüß]{4,}", lower, re.IGNORECASE):
        token = token_match.group(0).lower()
        if token in _found_first_words:
            continue
        best_alias = ""
        best_score = 0.0
        for alias in fuzzy_aliases:
            score = SequenceMatcher(None, token, alias.lower()).ratio()
            if score > best_score:
                best_score = score
                best_alias = alias
        if best_alias and best_score >= 0.84:
            alias_fw = best_alias.lower().split()[0]
            if alias_fw in _found_first_words:
                continue
            found.append((token_match.start(), best_alias))
            _found_first_words.add(alias_fw)

    # Sort by position in text, deduplicate, return names only
    found.sort(key=lambda t: t[0])
    result: List[str] = []
    for _, dish in found:
        dish_l = dish.lower()
        if any(
            other.lower() != dish_l and dish_l in other.lower() and len(other) > len(dish)
            for _, other in found
        ):
            continue
        if dish not in result:
            result.append(dish)
    return result


_FOOD_TOKEN_NORMALIZATIONS = {
    "bebimbap": "bibimbap",
    "bewimbap": "bibimbap",
    "bibimbab": "bibimbap",
    "bimbap": "bibimbap",
    "bimbab": "bibimbap",
}


def _normalize_food_tokens(text: str) -> str:
    normalized = text
    for heard, canonical in _FOOD_TOKEN_NORMALIZATIONS.items():
        normalized = re.sub(rf"\b{re.escape(heard)}\b", canonical, normalized, flags=re.IGNORECASE)
    return normalized


def _dish_fuzzy_aliases(items: Optional[List[str]]) -> List[str]:
    aliases = ["Bibimbap", "Kimchi", "Bulgogi", "Mandu", "Wasser", "Cola"]
    for dish in items or []:
        first = str(dish).strip().split()[0] if str(dish).strip() else ""
        if len(first) >= 4:
            aliases.append(first)
    result: List[str] = []
    for alias in aliases:
        if alias and alias not in result:
            result.append(alias)
    return result


def _extract_dish(text: str, items: Optional[List[str]] = None) -> Optional[str]:
    # F9: Exact substring match only — no hallucination of items not in real menu.
    # Uses provided items list or falls back to global _KNOWN_ITEMS
    # CRITICAL FIX I1.1_D3: Prefer exact-word matches ("Kimchi" as standalone token)
    # over substring matches ("Kimchi Jjigae") to prevent false positives.
    if items is None:
        items = _KNOWN_ITEMS
    
    lower = text.lower()
    best_match = None
    best_len = float('inf')
    best_is_exact = False
    
    for dish in items:
        dish_lower = dish.lower()
        # Check for exact word match first (e.g. "Kimchi" as standalone token, not substring of "Kimchi Jjigae")
        import re as _re_exact
        is_exact_word = bool(_re_exact.search(rf'\b{_re_exact.escape(dish_lower)}\b', lower))
        is_substring = dish_lower in lower
        
        if is_exact_word or is_substring:
            # Prefer exact word matches over substrings
            # Among exact matches, prefer shorter ("Kimchi" over "Kimchi Jjigae")
            # Among substrings, prefer shorter (fallback only)
            if is_exact_word and not best_is_exact:
                # Upgrade from substring to exact word match
                best_match = dish
                best_len = len(dish)
                best_is_exact = True
            elif is_exact_word and best_is_exact and len(dish) < best_len:
                # Both exact: prefer shorter
                best_match = dish
                best_len = len(dish)
            elif not is_exact_word and not best_is_exact and len(dish) < best_len:
                # Both substring: prefer shorter
                best_match = dish
                best_len = len(dish)
    
    return best_match


def _digits_only(s: str) -> str:
    return re.sub(r"\D", "", s)


def update_state_from_utterance(state: ConversationState, utterance: str) -> None:
    # FIX I1.1_D3: Initialize readback tracking fields
    if not hasattr(state, '_readback_confirmed_this_turn'):
        state._readback_confirmed_this_turn = False
    if not hasattr(state, '_order_items_for_readback'):
        state._order_items_for_readback = []
    if not hasattr(state, '_order_readback_confirmed'):
        state._order_readback_confirmed = False
    if not hasattr(state, '_readback_already_shown'):
        state._readback_already_shown = False
    lower = utterance.lower()
    state._name_corrected_this_turn = False
    
    # Initialize transient tracking fields before any reads
    if not hasattr(state, "_last_user_text"):
        state._last_user_text = ""
    if not hasattr(state, "_greeting_processed"):
        state._greeting_processed = False
    
    # FIX: Immediate post-greeting empathy (prevents repeated "Hallo" frustration)
    # Track greeting attempts to add empathetic confirmation on turn 1
    if "hallo" in lower and not state._greeting_processed:
        state._greeting_processed = True
        logger.debug("[update_state] First greeting detected — bot should respond empathetically")

    # === ATTEMPT INCREMENT LOGIC (Per-Turn) (F-A Fix) ===
    # Uses validity not presence: "Ist" populates customer_name but is invalid,
    # so we must still count it as an attempt that failed.
    if state.last_field_asked:
        field_name = state.last_field_asked
        still_invalid = {
            "name": not state.has_valid_name(),
            "phone": not state.has_valid_phone(),
            "address": not state.has_valid_address(),
            "delivery_choice": (not state.delivery_confirmed) and (not state.delivery_intended),
        }.get(field_name, False)
        if still_invalid:
            state.field_attempts[field_name] = state.field_attempts.get(field_name, 0) + 1
            logger.info(
                f"[Collection] {field_name} attempt "
                f"#{state.field_attempts[field_name]} (still invalid/missing)"
            )
    state.last_user_utterance = utterance
    # Maintain ring buffer for mood detection (TTS conditioning Phase 2)
    state.recent_caller_utterances.append(utterance)
    if len(state.recent_caller_utterances) > 5:
        state.recent_caller_utterances = state.recent_caller_utterances[-5:]

    if any(n in lower for n in NEGATE_ORDER):
        state.order_intent = False

    if any(kw in lower for kw in ORDER_KEYWORDS):
        state.order_intent = True

    _active_order_flow = bool(
        state.order_intent
        or state.selected_dish
        or state.selected_items
        or state.delivery_intended
        or state.delivery_confirmed
    )
    if any(kw in lower for kw in RESERVATION_KEYWORDS) and not _active_order_flow:
        state.reservation_intent = True

    # Fix 2: Extract dish BEFORE checking order_intent
    # This allows dishes in customer utterances to be captured even on the first turn
    # before order_intent is explicitly set
    # Multi-item support: extract ALL dishes mentioned, first becomes/stays primary,
    # subsequent ones are added to extras cart (unless user is negating them).
    # CRITICAL FIX I1.1_D3: Always re-extract on user correction to prevent stale prices.
    _neg_words = ("nein", "kein ", "keine ", "keinen ", "ohne ", "nicht ")
    _is_negation = any(nw in lower for nw in _neg_words)
    # Detect explicit correction patterns ('statt X, sondern Y' or 'nicht X, bitte Y')
    _correction_pattern = r"(?:nein|nicht|falsch|statt|anstatt)[^\w]*(?:sondern|bitte|nehme|möchte)\s+(.+?)(?:\.|,|$)"
    _correction_m = re.search(_correction_pattern, lower)
    _explicit_correction_signal = lower.strip().startswith("nein") or "stimmt nicht" in lower
    _dishes_in_utterance = _extract_all_dishes(utterance)
    _is_user_correction = bool(_correction_m) or (
        _explicit_correction_signal and bool(_dishes_in_utterance)
    )
    # Always re-extract on correction to override stale state
    all_dishes = _dishes_in_utterance if (not _is_negation or _is_user_correction) else []
    dish = all_dishes[0] if all_dishes else None
    # CRITICAL FIX I1.1_D3: Detect user corrections ("Nein, sondern X" or "statt X") and ALWAYS apply
    # Re-check for correction pattern even if not flagged above to catch late corrections
    _correction_pattern = r"(?:nein|nicht|falsch|das stimmt nicht)[^\w]*(?:sondern|statt|anstatt|bitte|nehme|möchte|wollte|hatte|bestellung)\s+(.+?)(?:\.|,|$)"
    _correction_m = re.search(_correction_pattern, lower)
    if _correction_m or (_explicit_correction_signal and _dishes_in_utterance):
        # User explicitly corrected: "Nein, sondern Kimchi" or "Nein, das stimmt nicht, ich hatte Bibimbap und Kimchi bestellt"
        # Extract CORRECTED dishes only; reset primary to first corrected item, clear extras
        corrected_dishes = _dishes_in_utterance
        if corrected_dishes:
            state.selected_dish = corrected_dishes[0]
            state.selected_items = list(corrected_dishes)
            state.order_items_extras = []  # Clear old extras
            for extra in corrected_dishes[1:]:
                state.add_extra_item(extra)
            state.items_confirmed = False  # Force readback with NEW items on next turn
            state._order_readback_confirmed = False  # CRITICAL: reset readback gate on correction
            state._readback_already_shown = False  # Force re-show readback with corrected items
            state.reset_commit_readback("create_order", "items_corrected")
            logger.info(f"[Correction] user corrected dish to: {corrected_dishes} (cleared extras, reset readback gates)")
    elif dish and not (dish.lower() == (state.selected_dish or "").lower()):  # Only set if not a repetition of current
        if state.selected_dish is None:
            state.selected_dish = dish
            state.selected_items = list(all_dishes)
            # Any additional dishes in the same utterance become extras
            for extra in all_dishes[1:]:
                state.add_extra_item(extra)
        else:
            # Primary already set — add ALL mentioned (new) dishes as extras.
            # This handles "und dann noch Mandu und Mochi-Eis" after a dish is already selected.
            before_items = state.all_order_items()
            for d in all_dishes:
                state.add_extra_item(d)
            state.selected_items = state.all_order_items()
            if state.selected_items != before_items:
                state.reset_commit_readback("create_order", "items_changed")
        # Fix 2: Implicit order_intent from dish mention.
        # Only if not an inquiry (e.g. "was ist Kimchi?") and not a reservation.
        if not state.reservation_intent and not any(n in lower for n in NEGATE_ORDER):
            state.order_intent = True

    # Quantity extraction (applies to primary selected_dish when the caller
    # explicitly names a count). Defaults to 1; only overwrite when a count is
    # detected THIS turn so a later "keine" doesn't zero it out.
    qty = _extract_order_quantity(utterance)
    if qty is not None and qty >= 1:
        state.order_quantity = qty
        logger.info(f"[Quantity] order_quantity={qty} extracted from utterance")

    # Bulk-order confirmation: if the caller previously triggered
    # pending_bulk_confirmation, any affirmative this turn clears the gate.
    if state.pending_bulk_confirmation:
        _affirm = ("ja", "genau", "richtig", "korrekt", "stimmt", "klar",
                   "bestätige", "bestaetige", "confirm", "yes", "passt")
        _deny = ("nein", "nicht", "falsch", "doch nicht", "stornieren", "kein")
        if any(w in lower for w in _deny):
            state.pending_bulk_confirmation = False
            state.bulk_order_confirmed = False
            state.order_quantity = 1
            logger.info("[Quantity] bulk confirmation DENIED — resetting qty to 1")
        elif any(w in lower.split() for w in _affirm) or any(a in lower for a in _affirm):
            state.bulk_order_confirmed = True
            state.pending_bulk_confirmation = False
            logger.info(
                f"[Quantity] bulk confirmation ACCEPTED qty={state.order_quantity}"
            )

    m = PHONE_PATTERN.search(utterance)
    if m:
        raw = m.group(1).strip()
        digits = _digits_only(raw)
        if len(digits) >= 8:
            if state.phone_number and _digits_only(state.phone_number) != digits:
                state.phone_readback_confirmed = False
                state.reset_commit_readback("create_order", "phone_corrected")
            state.phone_number = raw
            # A freshly spoken phone overrides an unconfirmed caller-ID prefill:
            # the caller explicitly picked a different number as SMS destination.
            if (
                getattr(state, "caller_id_phone", None)
                and not state.caller_id_confirmed
                and _digits_only(state.caller_id_phone or "") != digits
            ):
                logger.info(
                    f"[CALLER-ID] Spoken phone {raw!r} differs from caller_id "
                    f"{state.caller_id_phone!r} — using spoken"
                )

    # Sprint 0 — caller-ID confirmation: when we have an unconfirmed caller-ID
    # prefill and no phone_number yet, interpret a simple affirmative this turn
    # as confirmation ("ja, genau die Nummer"), and copy it to phone_number.
    if (
        getattr(state, "caller_id_phone", None)
        and not state.caller_id_confirmed
        and not state.phone_number
    ):
        _cid_affirm = (
            "ja", "genau", "richtig", "korrekt", "stimmt", "passt",
            "bestätige", "bestaetige", "bitte", "gerne", "gern",
            "diese nummer", "die nummer", "dieselbe", "dieselbe nummer",
        )
        _cid_deny = (
            "nein", "andere", "anderes", "nicht diese", "nicht die",
            "falsch",
        )
        _tokens = lower.split()
        if any(neg in lower for neg in _cid_deny):
            # explicit deny — we'll wait for the spoken number
            pass
        elif any(a in _tokens for a in _cid_affirm) or any(a in lower for a in _cid_affirm):
            state.caller_id_confirmed = True
            state.phone_number = state.caller_id_phone
            state.phone_readback_confirmed = True
            logger.info(
                f"[CALLER-ID] Confirmed by caller — "
                f"phone_number={state.phone_number!r}"
            )
            # Also promote the OrderSlots phone slot to CONFIRMED
            _slots = getattr(state, "order_slots_ref", None)
            if _slots is not None and _slots.phone.is_phone_from_caller_id():
                from server.brain.order_slots import SlotStatus as _SS
                _slots.phone.status = _SS.CONFIRMED
                logger.info("[CALLER-ID-SLOT] phone slot promoted to CONFIRMED")

    # Party size: "für vier", "4 personen", "zu dritt", "sechs leute"
    # CRITICAL FIX F2.3_D3: Only extract party_size on EXPLICIT user statement.
    # User correction ('Nein, ich habe keine Personenzahl genannt') must NOT extract a value.
    # Check for negation/correction markers FIRST before attempting extraction.
    # CRITICAL: Also reject date/address false positives FIRST (18 2026, 23. Mai, Friedrichstraße 20)
    _date_false_positives = (
        r'\d{1,2}\s+20\d{2}',  # "18 2026"
        r'\d{1,2}\.\s*\d{1,2}\.\s*\d{4}',  # "23.05.2026"
        r'\d{1,2}:\d{2}\s*uhr',  # "20:00 Uhr"
        r'straße|strasse|str\.|platz|weg|allee',  # street suffix
    )
    _has_date_context = any(re.search(ctx, lower) for ctx in _date_false_positives)
    if _has_date_context:
        # Utterance contains date/time/address context — reject bare number extraction
        logger.debug(f"[party_size] rejected due to date/address context")
    else:
        _negation_markers = (
            'nein, ich habe keine personenzahl',
            'habe ich nicht', 'personenzahl nicht genannt', 'noch nicht genannt',
            'keine personenzahl genannt', 'personenzahl falsch',
        )
        # Check if utterance contains explicit negation/correction of party_size.
        # If present, it signals user is DENYING/CORRECTING — do NOT extract.
        _has_explicit_negation = any(marker in lower for marker in _negation_markers)
        if _has_explicit_negation:
            # User is explicitly DENYING or CORRECTING party_size — clear it from state
            if state.party_size is not None:
                logger.warning(f'[Party_Size] User correction detected: {utterance[:60]!r} — CLEARING party_size')
                state.party_size = None
                state.reset_commit_readback("create_reservation", "party_size_cleared")
        else:
            # ONLY extract party_size on positive/affirmative utterances (no explicit negation present)
            _WORD_NUMS = {
                "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "fuenf": 5,
                "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10,
                "zwölf": 12, "zwoelf": 12, "zwanzig": 20,
                "dritt": 3, "viert": 4, "fünft": 5, "sechst": 6,
            }
            pm = re.search(
                r"(?:für|fuer|zu)\s+(\d{1,2}|[a-zäöü]+)\s*(?:person|pers\.?|leute|gäste)?",
                lower,
            )
        if pm:
            val = pm.group(1)
            try:
                n = int(val)
            except ValueError:
                n = _WORD_NUMS.get(val, 0)
            if 1 <= n <= 50:
                if state.party_size is not None and state.party_size != n:
                    state.reset_commit_readback("create_reservation", "party_size_corrected")
                state.party_size = n
                logger.info(f'[Party_Size] Extracted: {n} from {utterance[:60]!r}')

    # Also catch "21 Personen" / "25 Leute" without a für/zu prefix
    # CRITICAL FIX: Must have explicit "Personen" / "Person" / "Leute" / "Gäste" marker
    # to avoid false extraction from dates ("23. Mai" → "23") or addresses ("Friedrichstraße 20")
    if state.party_size is None:
        pm2 = re.search(
            r"\b(\d{1,2})\s+(?:person(?:en)?|pers\.?|leute|gäste|gaeste)\b",
            lower,
        )
        if pm2:
            try:
                n2 = int(pm2.group(1))
                # CRITICAL: Sanity check — party size should be 1-50, NOT 2026 (year) or >50 (catering)
                if 1 <= n2 <= 50:
                    if state.party_size is not None and state.party_size != n2:
                        state.reset_commit_readback("create_reservation", "party_size_corrected")
                    state.party_size = n2
            except ValueError:
                pass

    # German word-number + Personen: "drei Personen", "vier Leute" (no "für" prefix needed)
    if state.party_size is None:
        _WORD_NUMS_PARTY = {
            "eine": 1, "ein": 1, "zwei": 2, "drei": 3, "vier": 4,
            "fünf": 5, "fuenf": 5, "sechs": 6, "sieben": 7, "acht": 8,
            "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12, "zwoelf": 12,
        }
        pm3 = re.search(
            r"\b(" + "|".join(_WORD_NUMS_PARTY.keys()) + r")\s+(?:person(?:en)?|pers\.?|leute|gäste|gaeste)\b",
            lower,
        )
        if pm3:
            n3 = _WORD_NUMS_PARTY.get(pm3.group(1), 0)
            if 1 <= n3 <= 50:
                if state.party_size is not None and state.party_size != n3:
                    state.reset_commit_readback("create_reservation", "party_size_corrected")
                state.party_size = n3
                logger.info(f'[Party_Size] Word-number extracted: {n3} from {utterance[:60]!r}')

    # Reservation date: "morgen", "Samstag", "am 15.", "nächsten Freitag"
    # F3: Check "übermorgen" and other extended phrases FIRST because "morgen"
    # is a substring of "übermorgen" — order matters here.
    _DAY_NAMES = [
        "montag", "dienstag", "mittwoch", "donnerstag",
        "freitag", "samstag", "sonntag",
        # English day names (accent scenarios may use mixed language)
        "monday", "tuesday", "wednesday", "thursday",
        "friday", "saturday", "sunday",
    ]

    # Always store reservation_date as ISO date (YYYY-MM-DD) so commit tools can parse it.
    # Display-time conversion ("Heute" → "Donnerstag, dem 7. Mai") happens in v4_pipeline
    # via _iso_to_spoken_german(), NOT at storage time.
    _old_reservation_date = state.reservation_date
    _date_word_present = (
        "heute" in lower or "morgen" in lower or "übermorgen" in lower or "uebermorgen" in lower
        or "woche" in lower or any(d in lower for d in _DAY_NAMES)
        or bool(re.search(r"\b\d{1,2}\.\s*(januar|februar|märz|april|mai|juni|juli|august|september|oktober|november|dezember)\b", lower, re.I))
    )
    # Date corrections must overwrite stale state. The old guard only parsed
    # dates when empty, so "Nein, heute ist ..." could leave yesterday/next-week
    # values in place and poison availability/readbacks.
    _date_correction_requested = bool(_old_reservation_date and _date_word_present)
    _date_correction_applied = False
    if not state.reservation_date or _date_correction_requested:
        import datetime as _dt
        _today = _dt.date.today()
        if "übermorgen" in lower or "uebermorgen" in lower:
            state.reservation_date = (_today + _dt.timedelta(days=2)).isoformat()
        elif "2027" in lower:
            # User explicitly said 2027 (next year) — extract that year
            _year_m = re.search(r'\b(202[7-9]|203\d)\b', lower)
            _explicit_year = int(_year_m.group(1)) if _year_m else _today.year
            # Check if user also mentioned a month+day
            _month_day_m = re.search(r'(\d{1,2})\s*\.\s*(januar|februar|märz|april|mai|juni|juli|august|september|oktober|november|dezember|january|february|march|april|may|june|july|august|september|october|november|december)', lower)
            if _month_day_m:
                _day_str = _month_day_m.group(1)
                _month_str = _month_day_m.group(2).lower()
                _MONTH_MAP = {"januar": 1, "februar": 2, "märz": 3, "maerz": 3, "april": 4, "mai": 5, "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11, "dezember": 12, "january": 1, "february": 2, "march": 3, "may": 5, "june": 6, "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12}
                _month_num = _MONTH_MAP.get(_month_str, _today.month)
                try:
                    state.reservation_date = _dt.date(_explicit_year, _month_num, int(_day_str)).isoformat()
                    logger.info(f'[Reservation_Date] Explicit year extraction: {_explicit_year} → {state.reservation_date}')
                except ValueError:
                    pass  # invalid date, skip
        elif "wochenende" in lower:
            # Next Saturday
            _days_to_sat = (5 - _today.weekday()) % 7 or 7
            state.reservation_date = (_today + _dt.timedelta(days=_days_to_sat)).isoformat()
        elif any(d in lower for d in _DAY_NAMES):
            # Unified weekday + optional week-offset handler.
            # Handles: "Samstag", "nächsten Samstag", "nächste Woche Samstag", "übernächste Woche Freitag"
            _DE_TO_DOW = {
                "montag": 0, "monday": 0,
                "dienstag": 1, "tuesday": 1,
                "mittwoch": 2, "wednesday": 2,
                "donnerstag": 3, "thursday": 3,
                "freitag": 4, "friday": 4,
                "samstag": 5, "saturday": 5,
                "sonntag": 6, "sunday": 6,
            }
            _has_uebernächste = bool(re.search(r"ü+bernächste|uebernächste|ü+bernächsten|uebernächsten|übernächste Woche|uebernächste Woche", lower))
            # "nächste Woche Samstag" requires explicit "Woche" to mean NEXT WEEK's Saturday.
            # "nächsten Samstag" without "Woche" means the upcoming Saturday (this week).
            _nächste_pattern = r'(?:nächste|naechste|kommende[n]?)\s+woche\s+(?:' + '|'.join(_DAY_NAMES) + r')'
            _has_next_week_qualifier = bool(re.search(_nächste_pattern, lower))
            _days_ahead = 0
            for d in _DAY_NAMES:
                if d in lower:
                    _target_dow = _DE_TO_DOW.get(d)
                    if _target_dow is not None:
                        if _has_uebernächste:
                            # "übernächste Woche Freitag": find the target weekday in the week AFTER next
                            # "Week after next" starts on Monday 14 days from this Monday.
                            _this_monday = _today - _dt.timedelta(days=_today.weekday())
                            _ü_week_monday = _this_monday + _dt.timedelta(days=14)
                            _days_ahead_raw = (_target_dow - _ü_week_monday.weekday()) % 7
                            state.reservation_date = (_ü_week_monday + _dt.timedelta(days=_days_ahead_raw)).isoformat()
                        elif _has_next_week_qualifier:
                            # "nächste Woche Samstag": find target weekday within the FOLLOWING calendar week
                            _this_monday = _today - _dt.timedelta(days=_today.weekday())
                            _next_monday = _this_monday + _dt.timedelta(days=7)
                            _days_ahead_raw = (_target_dow - _next_monday.weekday()) % 7
                            state.reservation_date = (_next_monday + _dt.timedelta(days=_days_ahead_raw)).isoformat()
                        else:
                            # Bare weekday: "nächsten Samstag" or just "Samstag"
                            _days_ahead = (_target_dow - _today.weekday()) % 7 or 7
                            state.reservation_date = (_today + _dt.timedelta(days=_days_ahead)).isoformat()
                        logger.info(f'[Reservation_Date] Weekday={d} uebernächste={_has_uebernächste} nächste={_has_next_week_qualifier} → {state.reservation_date}')
                    break
        elif "übernächsten" in lower or "uebernächsten" in lower or "übernächste" in lower or "uebernächste" in lower:
            # "übernächste Woche" with no weekday → +14 days
            state.reservation_date = (_today + _dt.timedelta(days=14)).isoformat()
        elif "nächste woche" in lower or "naechste woche" in lower or "kommende woche" in lower:
            # "nächste Woche" with no weekday → +7 days
            state.reservation_date = (_today + _dt.timedelta(days=7)).isoformat()
        elif "morgen" in lower:
            state.reservation_date = (_today + _dt.timedelta(days=1)).isoformat()
        elif "heute" in lower:
            state.reservation_date = _today.isoformat()
    if _old_reservation_date and state.reservation_date != _old_reservation_date:
        state.check_availability_called = False
        state.pre_commit_shown = False
        state.reset_commit_readback("create_reservation", "date_corrected")
        state.end_call_stage = "idle"
        _date_correction_applied = True
        logger.info(f"[update_state] Date correction: {_old_reservation_date} → {state.reservation_date}")
    # Ordinal month pattern: "ersten April", "zweiten Mai", "dritten Juni", etc.
    if not state.reservation_date or _date_correction_requested:
        import datetime as _dt2
        _today2 = _dt2.date.today()
        _ORDINAL_DE_CS = {
            "ersten": 1, "zweiten": 2, "dritten": 3, "vierten": 4, "fünften": 5,
            "sechsten": 6, "siebten": 7, "achten": 8, "neunten": 9,
            "zehnten": 10, "elften": 11, "zwölften": 12, "dreizehnten": 13,
            "vierzehnten": 14, "fünfzehnten": 15, "sechzehnten": 16,
            "siebzehnten": 17, "achtzehnten": 18, "neunzehnten": 19,
            "zwanzigsten": 20, "einundzwanzigsten": 21, "zweiundzwanzigsten": 22,
            "dreiundzwanzigsten": 23, "vierundzwanzigsten": 24,
            "fünfundzwanzigsten": 25, "sechsundzwanzigsten": 26,
            "siebenundzwanzigsten": 27, "achtundzwanzigsten": 28,
            "neunundzwanzigsten": 29, "dreißigsten": 30, "einunddreißigsten": 31,
        }
        _MONTH_MAP_CS = {
            "januar": 1, "februar": 2, "märz": 3, "april": 4, "mai": 5,
            "juni": 6, "juli": 7, "august": 8, "september": 9,
            "oktober": 10, "november": 11, "dezember": 12,
        }
        _ord_month_re = re.compile(
            r"\b(" + "|".join(_ORDINAL_DE_CS.keys()) + r")\s+"
            r"(januar|februar|märz|april|mai|juni|juli|august|september|oktober|november|dezember)\b",
            re.I,
        )
        _m_ord = _ord_month_re.search(lower)
        if _m_ord:
            _ord_day = _ORDINAL_DE_CS[_m_ord.group(1).lower()]
            _ord_month = _MONTH_MAP_CS[_m_ord.group(2).lower()]
            try:
                _ord_date = _dt2.date(_today2.year, _ord_month, _ord_day)
                if _ord_date <= _today2:
                    _ord_date = _dt2.date(_today2.year + 1, _ord_month, _ord_day)
                state.reservation_date = _ord_date.isoformat()
                logger.info(f"[Reservation_Date] Ordinal month extracted: {_m_ord.group(0)} → {state.reservation_date}")
            except ValueError:
                pass
        if not state.reservation_date:
            # Numeric day + month name: "am 1. April", "am 15. Mai" → ISO
            _num_month_re = re.compile(
                r"\b(\d{1,2})\.\s*(januar|februar|märz|april|mai|juni|juli|august|september|oktober|november|dezember)\b",
                re.I,
            )
            _m_num = _num_month_re.search(lower)
            if _m_num:
                _num_day = int(_m_num.group(1))
                _num_month = _MONTH_MAP_CS.get(_m_num.group(2).lower(), 0)
                if _num_month:
                    try:
                        _num_date = _dt2.date(_today2.year, _num_month, _num_day)
                        if _num_date <= _today2:
                            _num_date = _dt2.date(_today2.year + 1, _num_month, _num_day)
                        state.reservation_date = _num_date.isoformat()
                        logger.info(f"[Reservation_Date] Numeric+month extracted: {_m_num.group(0)} → {state.reservation_date}")
                    except ValueError:
                        pass
    dm = re.search(r"am\s+(\d{1,2})\.?\s*(\w+)?", lower)
    if dm:
        # Keep raw text match only if we don't already have an ISO date.
        if not state.reservation_date:
            state.reservation_date = dm.group(0).strip()
    if (
        _old_reservation_date
        and state.reservation_date != _old_reservation_date
        and not _date_correction_applied
    ):
        state.check_availability_called = False
        state.pre_commit_shown = False
        state.reset_commit_readback("create_reservation", "date_corrected")
        state.end_call_stage = "idle"
        logger.info(f"[update_state] Date correction: {_old_reservation_date} → {state.reservation_date}")

    # Reservation time: "um 19 uhr", "19:30", "halb acht", "um acht"
    # CRITICAL: Always extract time from current utterance to honor corrections.
    # User says "Nein, 19 Uhr" → must immediately override the old 14:00.
    tm = re.search(r"(?:um\s+)?(\d{1,2})[:.:]?(\d{2})?\s*(?:uhr)", lower)
    if tm:
        h = int(tm.group(1))
        m_min = int(tm.group(2)) if tm.group(2) else 0
        if 10 <= h <= 23:
            old_time = state.reservation_time
            state.reservation_time = f"{h:02d}:{m_min:02d}"
            if old_time and old_time != state.reservation_time:
                logger.info(f"[update_state] Time correction: {old_time} → {state.reservation_time}")
                # Clear pre_commit_shown so updated readback fires on next turn
                state.pre_commit_shown = False
                state.reset_commit_readback("create_reservation", "time_corrected")
                state.end_call_stage = "idle"
    tw = re.search(r"um\s+(\w+)", lower)
    if tw and not state.reservation_time:
        word = tw.group(1)
        h = _HOUR_WORDS.get(word)
        if h and 10 <= h <= 23:
            state.reservation_time = f"{h:02d}:00"
    # Also match spoken time without "um": "neunzehn Uhr", "acht Uhr"
    if not state.reservation_time:
        tw2 = re.search(r"\b(\w+)\s+uhr\b", lower)
        if tw2:
            h = _HOUR_WORDS.get(tw2.group(1))
            if h and 10 <= h <= 23:
                state.reservation_time = f"{h:02d}:00"
    if "halb acht" in lower:
        state.reservation_time = "19:30"
    elif "halb sieben" in lower:
        state.reservation_time = "18:30"
    elif "halb neun" in lower:
        state.reservation_time = "20:30"

    # F3: Extended time detection for informal time expressions
    if not state.reservation_time:
        if "abends" in lower or "am abend" in lower:
            state.reservation_time = "19:00"
        elif "mittags" in lower or "mittagessen" in lower or "am mittag" in lower:
            state.reservation_time = "12:00"
        elif "nachmittags" in lower or "am nachmittag" in lower:
            state.reservation_time = "15:00"
        elif "morgens" in lower or "zum frühstück" in lower:
            state.reservation_time = "10:00"
        else:
            # "gegen acht" / "gegen 20 Uhr" (approximate time)
            gm = re.search(r"gegen\s+(\d{1,2}|[a-zäöü]+)", lower)
            if gm:
                val = gm.group(1)
                try:
                    h = int(val)
                except ValueError:
                    h = _HOUR_WORDS.get(val, 0)
                if 10 <= h <= 23:
                    state.reservation_time = f"{h:02d}:00"

    # FIX: Stammkundenrabatt-Fragen brauchen SOFORT escalation zu Team (kein Loop)
    _RABATT_KEYWORDS = {
        "stammkunde", "rabatt", "discount", "ermäßigung", "ermaessigung",
        "treue", "treueprogramm", "regelmäßiger kunde",
    }
    _has_rabatt_frage = any(kw in lower for kw in _RABATT_KEYWORDS)
    if _has_rabatt_frage:
        # Bot kann Rabatte nicht direkt vergeben — SOFORT Team kontaktieren
        # Setze escalation_requested Flag damit v4_pipeline sofort transfer_to_human aufruft
        state.escalation_requested = True
        state.customer_confirmed = False
        logger.info(f'[update_state] Stammkundenrabatt-Frage detected → escalation_requested=True')
    
    # FIX G1.1_D2 + G2.3_D5: Extract multi-intent order slots early for FAQ/reservation/delivery queries
    _HOURS_CHECK_KWS = {
        "öffnungszeit", "geöffnet", "wann", "uhrzeit", "offen", "aufmachen",
        "zumachen", "haben sie geöffnet", "sind sie offen",
    }
    _DELIVERY_CHECK_KWS = {
        "liefern", "liefergebiet", "lieferzone", "beuel", "bonn-beuel",
        "lieferung", "delivery", "bring",
    }
    _has_hours_question = any(kw in lower for kw in _HOURS_CHECK_KWS)
    _has_delivery_question = any(kw in lower for kw in _DELIVERY_CHECK_KWS)
    _has_both_reservation_and_order = (
        any(kw in lower for kw in ["reservieren", "reservierung", "tisch", "buchen"])
        and any(kw in lower for kw in ["bestellen", "vorbestellen", "bibimbap", "mandu", "bulgogi"])
    )
    if (_has_hours_question or _has_delivery_question or _has_both_reservation_and_order) and not _has_rabatt_frage:
        # User asked about hours/delivery OR mentioned both reservation + order.
        # Extract any order slots mentioned so they persist across FAQ/delivery-check turns.
        _dishes = _extract_all_dishes(utterance)
        if _dishes:
            state.selected_dish = _dishes[0]
            state.order_intent = True
            for extra_dish in _dishes[1:]:
                state.add_extra_item(extra_dish)
        _qty = _extract_order_quantity(utterance)
        if _qty:
            state.order_quantity = _qty
        _name = _extract_name_from_utterance(utterance)
        if _name:
            state.customer_name = _name

    # Delivery intent flag — caller mentioned they want delivery (not necessarily gave address)
    if not state.delivery_intended:
        if any(kw in lower for kw in _DELIVERY_INTENT_KW):
            state.delivery_intended = True

    # Delivery address detection — set once when any delivery keyword detected, never cleared.
    if not state.delivery_address_mentioned:
        if any(kw in lower for kw in _ADDRESS_KW_STATE):
            state.delivery_address_mentioned = True

    # === Bug B: NAME EXTRACTION (strict, blocklist-based) ===
    # CRITICAL FIX: During cancellation, accept the name ONCE and never re-ask
    _cancel_in_progress = getattr(state, "_cancel_in_progress", False)
    current = state.customer_name or ""
    current_valid = _is_valid_name_candidate(current)
    _name_correction_context = _is_name_correction_context(utterance)
    new_name = _extract_name_correction(utterance) or _extract_name_from_utterance(utterance)
    if new_name:
        _changed_name = current_valid and new_name.lower() != current.lower()
        if not current_valid or (
            _changed_name
            and (_name_correction_context or len(new_name) > len(current))
        ):
            if current and current != new_name:
                logger.info(f"[NAME_EXTRACT] overriding {current!r} -> {new_name!r}")
            state.customer_name = new_name
            state.first_name = None if " " in new_name else state.first_name
            state.name_confirmed = True
            state.field_attempts["name"] = 0
            state._name_corrected_this_turn = bool(_changed_name and _name_correction_context)
            if state._name_corrected_this_turn:
                state._name_correction_ack_text = f"Verstanden, ich habe den Namen auf {new_name} geändert."
            # CRITICAL FIX H2.2_D3: Immediately remove from recent_responses so deterministic clarify doesn't re-ask
            state.recent_responses = [r for r in getattr(state, "recent_responses", []) if "welchen namen" not in r.lower()]
            logger.debug(f"[NAME_EXTRACT] name set to {new_name!r}, attempt reset to 0")
        elif current_valid and new_name.lower() == current.lower():
            # Name already set and matches extraction — confirm and reset attempts to prevent re-asking
            state.name_confirmed = True
            state.field_attempts["name"] = 0
            logger.debug(f"[NAME_EXTRACT] name already confirmed: {new_name!r}, attempt reset to 0")
            # During cancellation: lock the name so we don't re-ask on next turn
            if _cancel_in_progress:
                state._name_locked_for_cancel = True
            # If we just got the full name, first_name is no longer needed separately
            if state.first_name:
                state.first_name = None
        elif current_valid and new_name.lower() == current.lower():
            # Name already set and matches extraction — confirm and reset attempts to prevent re-asking
            state.name_confirmed = True
            state.field_attempts["name"] = 0
            logger.debug(f"[NAME_EXTRACT] name already confirmed: {new_name!r}")
    else:
        # Full name extraction failed — try single first-name extraction (partial capture).
        # Only populate first_name when we don't already have a full customer_name.
        if not state.has_valid_name():
            if not state.first_name:
                fn = _extract_first_name_from_utterance(utterance)
                if fn:
                    state.first_name = fn
                    state.field_attempts["name"] = 0  # reset so bot won't escalate
                    logger.info(f"[NAME_EXTRACT] partial first-name captured: {fn!r}")
                else:
                    # Context-aware bare-name detection: if the bot's last utterance was a
                    # direct name question and the user replied with a single capitalized word,
                    # treat it as the customer name even without an explicit "mein Name ist"
                    # marker (e.g. caller says just "Schäfer" in reply to "Auf welchen Namen?").
                    # CRITICAL: Skip if user is repeating the same utterance (avoid loop)
                    _last_bot_ctx = (state.recent_responses[-1] if state.recent_responses else "").lower()
                    _BOT_NAME_REQUEST_KW = (
                        "auf welchen namen", "wie ist ihr name", "wie heißen sie",
                        "wie heissen sie", "welchen namen", "ihren namen", "den namen",
                        "name bitte", "ihr name", "namen darf",
                    )
                    _ctx_asked_name = any(kw in _last_bot_ctx for kw in _BOT_NAME_REQUEST_KW)
                    _last_ut = getattr(state, "_last_user_text", None)
                    _is_repeat = (_last_ut and _last_ut.lower() == utterance.lower()) or (state.last_user_utterance and state.last_user_utterance.lower() == utterance.lower())
                    if _ctx_asked_name and not _is_repeat:
                        _bare = [t.strip(".,!?;:") for t in utterance.strip().split() if t.strip(".,!?;:")]
                        if len(_bare) == 1:
                            _bc = _bare[0]
                            _TEMPORAL_BLOCKLIST = {
                                "montag", "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag",
                                "januar", "februar", "märz", "maerz", "april", "mai", "juni", "juli",
                                "august", "september", "oktober", "november", "dezember",
                            }
                            if (
                                len(_bc) >= 3
                                and _bc[0].isupper()
                                and _bc.lower() not in _NAME_BLOCKLIST
                                and _bc.lower() not in _TEMPORAL_BLOCKLIST
                                and re.match(r"^[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]+$", _bc)
                            ):
                                state.customer_name = _bc
                                state.first_name = None
                                state.name_confirmed = True
                                state.field_attempts["name"] = 0
                                logger.info(f"[NAME_EXTRACT] context-aware bare name as FULL customer_name: {_bc!r}")
            else:
                # first_name already set — only assemble a surname from a short bare-word
                # reply if the PREVIOUS bot utterance explicitly asked for it (Nachname /
                # Türschild / Klingel / Familienname). Without that gate any filler word
                # like "Weiter", "Super", "Ja" would silently become a surname.
                _SURNAME_REQUEST_KW = (
                    "nachname", "familienname", "türschild", "tuerschild",
                    "klingel", "wie heißen", "wie heissen", "ihr name",
                )
                _last_bot = (state.recent_responses[-1] if state.recent_responses else "").lower()
                _bot_asked_for_surname = any(kw in _last_bot for kw in _SURNAME_REQUEST_KW)
                if not _bot_asked_for_surname:
                    logger.debug(
                        f"[NAME_EXTRACT] skipping silent surname assembly — "
                        f"last bot did not ask for Nachname: {_last_bot[:80]!r}"
                    )
                else:
                    # A short bare-word reply (1-2 tokens, no marker) is likely the surname.
                    # Combine first_name + surname → customer_name.
                    _tokens = [t.strip(".,!?;:") for t in utterance.strip().split() if t.strip(".,!?;:")]
                    _single = None
                    if len(_tokens) == 1:
                        _single = _tokens[0]
                    elif len(_tokens) == 2:
                        # could be "Mein Nachname" — ignore; otherwise take second token as surname
                        if _tokens[0].lower() in {"mein", "ist", "der", "die", "das"}:
                            _single = _tokens[1]
                        else:
                            _single = _tokens[1]  # safer: take last word
                    if _single:
                        _single = _single[0].upper() + _single[1:] if len(_single) > 1 else _single.upper()
                        if (
                            len(_single) >= 2
                            and _single.lower() not in _NAME_BLOCKLIST
                            and re.match(r"^[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]+$", _single)
                        ):
                            full = f"{state.first_name} {_single}"
                            if _is_valid_name_candidate(full):
                                state.customer_name = full
                                state.first_name = None
                                state.name_confirmed = True
                                state.field_attempts["name"] = 0
                                logger.info(f"[NAME_EXTRACT] assembled full name from first+last: {full!r}")

    # === Bug D: PHONE EXTRACTION (digit OR spoken, with cross-turn buffer) ===
    # CRITICAL: Phone is NOT required to block reservation commit. Only extract if explicitly given.
    if not state.phone_number:
        # Try single-utterance extraction first
        phone_digits = _extract_phone_digits(utterance)
        
        if phone_digits:
            # Accept any German phone number with 8-13 digits (landlines and mobiles)
            state.phone_number = phone_digits
            state.phone_is_landline = not phone_digits.startswith(("015", "016", "017", "014", "018", "019"))
            state.phone_confirmed = True
            state.phone_readback_confirmed = False
            state.field_attempts["phone"] = 0
            state.phone_digits_buffer = ""
            logger.info(f"[PHONE_EXTRACT] single-turn: {phone_digits} (landline={state.phone_is_landline})")
        else:
            # No complete number in this utterance. Try cross-turn buffer.
            # Expand German shorthand ("viermal die vier" → "4 4 4 4") first.
            expanded = _expand_spoken_shorthand(utterance)
            # Collect digits from this utterance — respecting address break words
            # so street numbers (e.g. "20" from "Friedrichstraße zwanzig") don't contaminate.
            _BUFFER_BREAK = {
                "straße", "strasse", "str", "str.", "gasse", "platz", "weg", "allee", "ring",
                "damm", "ufer", "chaussee", "boulevard",
                "bonn", "köln", "berlin", "hamburg", "frankfurt", "münchen", "muenchen",
            }
            this_turn_digits = ""
            _in_phone_region = False
            for token in expanded.split():
                t = token.strip(".,!?;:-/").lower()
                # Reset digit accumulation when we hit an address word, so only
                # digits AFTER the last address word are considered phone digits.
                if t in _BUFFER_BREAK:
                    this_turn_digits = ""
                    _in_phone_region = False
                    continue
                if t.isdigit():
                    this_turn_digits += t
                    _in_phone_region = True
                elif t in _SPOKEN_DIGITS:
                    this_turn_digits += _SPOKEN_DIGITS[t]
                    _in_phone_region = True

            # If this utterance starts a fresh full number (caller repeating),
            # RESET the buffer instead of appending. Heuristic: ≥6 digits in one utterance.
            if len(this_turn_digits) >= 6:
                if state.phone_digits_buffer and state.phone_digits_buffer != this_turn_digits:
                    logger.info(
                        f"[PHONE_EXTRACT] buffer reset — caller repeated number "
                        f"(was {len(state.phone_digits_buffer)} digits, now {len(this_turn_digits)})"
                    )
                state.phone_digits_buffer = this_turn_digits
            else:
                # Short fragment (continuation) — always append regardless of length
                state.phone_digits_buffer += this_turn_digits
            
            # Check if buffer now has enough digits
            logger.info(
                f"[PHONE_BUFFER] utterance={utterance!r} expanded={expanded!r} "
                f"this_turn_digits={this_turn_digits!r} "
                f"buffer_now={state.phone_digits_buffer!r} ({len(state.phone_digits_buffer)} digits)"
            )
            if 9 <= len(state.phone_digits_buffer) <= 13:
                buffered = state.phone_digits_buffer
                # Accept any German number regardless of mobile/landline prefix
                state.phone_number = buffered
                state.phone_is_landline = not buffered.startswith(("015", "016", "017", "014", "018", "019"))
                state.phone_confirmed = True
                state.phone_readback_confirmed = False
                state.field_attempts["phone"] = 0
                state.phone_digits_buffer = ""
                logger.info(f"[PHONE_EXTRACT] cross-turn buffer completed: {buffered} (landline={state.phone_is_landline})")
            elif len(state.phone_digits_buffer) > 13:
                # Buffer overflow — save the current fragment in case it's a fresh start
                logger.warning(
                    f"[PHONE_EXTRACT] buffer overflow {len(state.phone_digits_buffer)} digits, "
                    f"resetting to current fragment ({len(this_turn_digits)} digits)"
                )
                # Keep current turn's digits rather than losing them entirely
                state.phone_digits_buffer = this_turn_digits
            else:
                # Still accumulating
                logger.info(f"[PHONE_EXTRACT] buffering: {len(state.phone_digits_buffer)}/10 digits")

    # === ACTIVE COLLECTION: DELIVERY CHOICE (F-A Fix) ===
    # Allow re-evaluation even after confirmation so user corrections ("Ach warten,
    # ich komme doch lieber selbst abholen") in the same or a later turn take effect.
    # Position-based: the keyword that appears LATEST in the text wins (G1.3 fix).
    _delivery_kw = ["lieferung", "liefern", "liefere", "delivery", "zu mir", "nach hause"]
    _pickup_kw = ["abholen", "mitnehmen", "takeaway", "zum mitnehmen", "pickup", "selbst abholen"]
    _delivery_positions = [lower.find(kw) for kw in _delivery_kw if kw in lower]
    _pickup_positions = [lower.find(kw) for kw in _pickup_kw if kw in lower]
    if _delivery_positions or _pickup_positions:
        _last_delivery = max(_delivery_positions) if _delivery_positions else -1
        _last_pickup = max(_pickup_positions) if _pickup_positions else -1
        if _last_pickup > _last_delivery:
            # Pickup keyword appears after delivery keyword → user corrected to pickup
            state.delivery_intended = False
            state.delivery_address_mentioned = False
            state.delivery_confirmed = True
            logger.debug(f"[Collection] Pickup confirmed (pos={_last_pickup} > delivery pos={_last_delivery})")
        elif _last_delivery > _last_pickup:
            state.delivery_intended = True
            state.delivery_address_mentioned = True
            state.delivery_confirmed = True
            logger.debug(f"[Collection] Delivery confirmed (pos={_last_delivery})")

    # === Bug C: ADDRESS EXTRACTION (requires street+number+real city) ===
    # CRITICAL FIX I1.1_D3: Also trigger re-extraction on explicit address corrections
    # "Die Adresse stimmt nicht" or "falsch" + address mention should override previous
    _address_correction_markers = (
        "korrektur", "falsch", "nicht richtig", "nicht korrekt",
        "stimmt nicht", "das stimmt nicht", "die adresse stimmt nicht",
        "bitte ändern", "bitte aendern",
    )
    _is_address_correction = any(m in utterance.lower() for m in _address_correction_markers)
    
    if not state.delivery_address or not _address_looks_valid(state.delivery_address) or _is_address_correction:
        new_addr = _extract_address_from_utterance(utterance)
        if new_addr:
            if state.delivery_address and state.delivery_address != new_addr:
                logger.info(f"[ADDRESS_EXTRACT] overriding {state.delivery_address!r} -> {new_addr!r} (correction detected)")
            state.delivery_address = new_addr
            state.delivery_address_mentioned = True
            state.field_attempts["address"] = 0
            # CRITICAL: On explicit address correction, reset confirmation gates to prevent stale flow
            if _is_address_correction:
                state.check_availability_called = False
                state.pre_commit_shown = False
                state.reset_commit_readback("create_order", "address_corrected")
                state.reset_commit_readback("create_reservation", "address_corrected")
                logger.info(f"[ADDRESS_CORRECT] Reset availability/commit gates after address correction")

    # Implicit reservation intent: party_size >= 2 without food → reservation
    # Guard: skip when the caller is already in a delivery flow (P2_13)
    _order_type = getattr(state, 'order_type', None) or getattr(state, 'delivery_type', None)
    _is_delivery = (
        _order_type in ('delivery', 'lieferung', 'liefern')
        or bool(getattr(state, 'delivery_intended', False))
    )
    if (
        state.party_size is not None
        and state.party_size >= 2
        and not state.selected_dish
        and not state.order_intent
        and not _is_delivery
    ):
        state.reservation_intent = True

    # FIX F2.3_D3: Explicit callback + date mention = reservation intent
    # When caller says "Rufen Sie mich zurück, ich wollte für Freitag reservieren",
    # extraction above sets reservation_date but never sets reservation_intent flag.
    # This causes the entire context doc to skip reservation slot validation.
    _callback_kw = (
        "zurückrufen", "rueckrufen", "rufen sie mich zurück", "rufen sie mich zurueck",
        "callback", "rückruf", "rueckruf",
    )
    _has_callback_request = any(kw in lower for kw in _callback_kw)
    if _has_callback_request and state.reservation_date:
        state.reservation_intent = True
        logger.info(f'[update_state] Callback + date detected → setting reservation_intent=True')

    # Fix C: implicit reservation intent from party_size + date/time together
    # (even party_size 1 is enough when combined with a date/time)
    # Handles cases where accent/sleepy caller gives date+party without
    # explicit "reservieren" keyword.
    if (
        not state.reservation_intent
        and state.party_size is not None
        and (state.reservation_date is not None or state.reservation_time is not None)
        and not state.order_intent
        and not _is_delivery
    ):
        state.reservation_intent = True

    # SMS/menu-send request detection
    _SMS_REQUEST_KW = [
        "schicken", "senden", "zuschicken", "per sms",
        "speisekarte schicken", "menü schicken", "menu schicken",
    ]
    if not state.sms_requested:
        if any(kw in lower for kw in _SMS_REQUEST_KW):
            state.sms_requested = True

    # Complaint detection: set flag for downstream handlers
    _COMPLAINT_KW = [
        "falsch", "falsche", "falsches", "falsch geliefert", "falsch bestellt",
        "nicht das", "nicht die", "nicht das gericht", "nicht ordnung", "nicht richtig",
        "beschwerde", "problem", "fehler", "falsche bestellung", "falsche lieferung",
        "unzufrieden", "nicht zufrieden", "nicht stimmt", "stimmt nicht",
        "hatte bestellt", "bestellt und bekommen", "statt", "anstatt", "anstelle",
    ]
    if not getattr(state, "complaint_logged", False):
        if any(kw in lower for kw in _COMPLAINT_KW):
            state.complaint_logged = True
            logger.info(f"[v4_pipeline] Complaint detected in utterance: {utterance[:60]!r}")

    # Confirmation detection (sticky: once confirmed, stays confirmed until consumed)
    _CONFIRM_KW = [
        "ja", "bitte", "genau", "stimmt", "passt", "richtig",
        "machen sie", "buchen sie", "ok", "okay", "jawohl",
        "ja bitte", "ja genau", "ja gerne", "machen wir",
        "klingt gut", "perfekt", "einverstanden", "gerne",
    ]
    if any(kw in lower for kw in _CONFIRM_KW):
        state.customer_confirmed = True


def update_state_after_bot(state: ConversationState, bot_response: str) -> None:
    """
    Track readback completeness (items + prices) in bot responses.
    Does NOT block order commits — that gate lives in v4_pipeline.py pre-commit readback.
    """
    if not state.order_intent:
        return
    lower = bot_response.lower()
    _confirm_phrases = ("aufgenommen", "bestätigt", "notiert", "reserviert")
    _has_confirm = any(p in lower for p in _confirm_phrases)
    if _has_confirm:
        # Track whether readback contained items + prices (for logging/audit only — NOT a gate)
        items = state.all_order_items() or []
        _has_item_names = any(item.lower() in lower for item in items)
        _has_price = ("euro" in lower or "€" in lower)
        if not (_has_item_names and _has_price):
            logger.debug(
                f"[update_state_after_bot] Commit response lacks items/prices — OK if pre-commit readback already shown. "
                f"Items mentioned: {_has_item_names}, Prices mentioned: {_has_price}."
            )
            # DO NOT reset order_created here — the order may have already been committed
        else:
            state._order_readback_confirmed = True
            state._order_items_for_readback = items
    lower = bot_response.lower()
    # Hard exclude: bot is suggesting an alternative or rejecting the request
    exclude_patterns = [
        "empfehle", "empfehlen", "leider", "haben wir nicht", "nicht auf der karte",
        "nicht im angebot", "können wir nicht", "alternativ", "stattdessen",
        "alternativlich", "vorschlag",
    ]
    if any(p in lower for p in exclude_patterns):
        return
    # Require confirmation language before extracting dish from bot.
    # Removed "ich habe" and "sie haben" — too broad: these match the forced-commit
    # template ("Ich habe Ihre Bestellung für X aufgenommen") and general statements,
    # causing a self-triggering loop: LLM text → dish extraction → premature create_order.
    confirm_patterns = [
        "bestellt", "aufgenommen", "notiert", "nehme ich auf", "ihre bestellung",
        "ich bestätige", "bestellung für",
    ]
    if not any(p in lower for p in confirm_patterns):
        return
    dish = _extract_dish(bot_response)
    if dish and dish.lower() in (d.lower() for d in state.all_order_items()):
        state.selected_dish = dish


def sanitize_bot_text_pre_commit(bot_text: str, state: "ConversationState", escalating: bool) -> str:
    """Rewrite bot text BEFORE commit attempt if fields are invalid.
    
    Bug D follow-up: When the F-A gate refuses to commit (escalating=True),
    the LLM often drew its own false conclusion ("Ich habe alle Informationen",
    "Ihre Bestellung aufgenommen"). Rewrite these to match reality.
    
    Returns rewritten bot_text, or original if no rewrite needed.
    """
    if not escalating:
        return bot_text
    
    # If name is missing/invalid, strip claims about having the name
    if not state.has_valid_name():
        bot_text = re.sub(
            r"Herr\s+\w+|Frau\s+\w+|Ihr Name",
            "Sie",
            bot_text,
        )
        bot_text = re.sub(
            r"(?:Ich habe|Sie haben).*?Name.*?\.",
            "",
            bot_text,
            flags=re.IGNORECASE,
        )
    
    # If phone is missing/invalid, reframe
    if not state.has_valid_phone():
        bot_text = re.sub(
            r"Es fehlt nichts mehr|Ich habe alle Informationen|alles notiert",
            "Es fehlt noch Ihre Telefonnummer",
            bot_text,
            flags=re.IGNORECASE,
        )
    
    # If address is missing/invalid (despite delivery being chosen)
    if state.delivery_intended and not state.has_valid_address():
        bot_text = re.sub(
            r"Lieferadresse.*?vollständig|(?:alle Daten|alle Informationen).*?verarbeitet",
            "Lieferadresse bitte noch bestätigen",
            bot_text,
            flags=re.IGNORECASE,
        )
    
    logger.info(f"[PreCommitSanitize] rewrote due to escalation")
    return bot_text
