"""Tracks order/reservation intent across training conversation turns."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List

logger = logging.getLogger(__name__)


# FIX 3: End-of-call state machine for proper multi-intent conclusion
class EndOfCallState(Enum):
    """States for multi-intent call completion sequence."""
    NOT_READY = "not_ready"                    # More intents to confirm or not in multi-intent mode
    READY_FOR_SMS = "ready_for_sms"            # All intents confirmed, ready to send final SMS
    READY_FOR_FAREWELL = "ready_for_farewell"  # SMS sent, ready to speak goodbye
    FAREWELL_SPOKEN = "farewell_spoken"        # Goodbye TTS complete, safe to end_call


# C2: KNOWN_DISHES is now an empty default — actual values come from tenant config
# via set_known_items() called in ADKTurnProcessor.__init__().
# Keeping a short legacy list as ultimate fallback only (loaded when tenant config is unavailable).
KNOWN_DISHES: List[str] = []  # populated from configs/tenants/<id>.yaml at startup

# Global known items (for backward compatibility when not using tenant config)
_KNOWN_ITEMS: List[str] = list(KNOWN_DISHES)


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
    # articles / determiners that can start false-positive 2-word phrases like "Ein Getränk"
    "ein", "eine", "einen", "einem", "einer", "eines",
    "kein", "keine", "keinen", "keinem", "keiner", "keines",
    "dieser", "diese", "diesen", "diesem", "jeder", "jede", "jeden",
    # food/drink/order words that are not names
    "getränk", "getränke", "gericht", "gerichte", "speise", "speisen",
    "wasser", "bier", "wein", "saft", "tee", "kaffee",
    "pizza", "nudeln", "suppe", "salat", "dessert",
}


def _is_valid_name_candidate(candidate: str) -> bool:
    """Two-plus words, each ≥ 3 chars, none in blocklist, proper capitalization."""
    if not candidate:
        return False
    parts = candidate.strip().split()
    if len(parts) < 2:
        return False
    for part in parts:
        if len(part) < 3:
            return False
        if part.lower() in _NAME_BLOCKLIST:
            return False
        # Must start with capital German letter and rest lowercase-ish
        if not re.match(r"^[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]+$", part):
            return False
    return True


def _extract_name_from_utterance(utterance: str) -> Optional[str]:
    """Extract a valid full name (first + last).

    Strategy 1: marker-based (mein name ist …, ich heiße …, ich bin …)
    Strategy 2: bare short utterance (user answering a direct name question)

    Returns the full name string only (or None). For single first names use
    _extract_first_name_from_utterance instead.
    """
    if not utterance:
        return None

    markers = [
        r"mein\s+name\s+ist",
        r"ich\s+heiße",
        r"ich\s+heisse",
        r"ich\s+bin",
        r"hier\s+(?:ist|spricht)",
        r"(?:hallo[,.]?\s+)?hier",  # "Hallo, hier Philipp Schneider" (no ist/spricht)
        r"auf\s+den\s+namen",
        r"name\s+ist",
    ]
    for marker in markers:
        pattern = (
            rf"{marker}\s+"
            r"(?:der\s+|die\s+|herr\s+|frau\s+)?"
            r"([A-ZÄÖÜ][a-zäöüß\-]{2,})\s+([A-ZÄÖÜ][a-zäöüß\-]{2,})"
        )
        m = re.search(pattern, utterance, re.IGNORECASE)
        if m:
            first = m.group(1).capitalize()
            last = m.group(2).capitalize()
            candidate = f"{first} {last}"
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
        r"(?:straße|strasse|str\.?|allee|ring|gasse|damm|weg|platz|ufer|chaussee)",
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
        r"(?:straße|strasse|str\.?|allee|ring|gasse|damm|weg|platz|ufer|chaussee|feld|berg|heim)"
    )
    # Primary: street + number + city
    pattern_full = (
        rf"([A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]*{street_suffix})"
        r"\s+(\d{1,4}[a-z]?)"
        r"[,.\s]+"
        r"([A-ZÄÖÜ][a-zäöüß\-]{2,})"
    )
    m = re.search(pattern_full, normalized, re.IGNORECASE)
    if m:
        street = m.group(1).strip()
        number = m.group(2).strip()
        city = m.group(3).strip()
        if city.lower() not in _GARBAGE_CITIES and len(city) >= 3:
            street = "".join(c.upper() if i == 0 else c for i, c in enumerate(street))
            city = city[0].upper() + city[1:].lower()
            return f"{street} {number}, {city}"

    # Fallback: street + number only → default city Bonn
    pattern_partial = (
        rf"([A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]*{street_suffix})"
        r"\s+(\d{1,4}[a-z]?)"
    )
    m2 = re.search(pattern_partial, normalized, re.IGNORECASE)
    if m2:
        street = m2.group(1).strip()
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

    Returns the full digit string (no formatting) if ≥ 10 digits found,
    else None.
    """
    if not utterance:
        return None
    # Pre-expand spoken shorthand so the rest of the pipeline sees plain digits
    expanded = _expand_spoken_shorthand(utterance)
    # First attempt: look for ≥10 contiguous digits (with optional separators)
    m = re.search(r"(\+?\d[\d\s\-/\.]{8,}\d)", expanded)
    if m:
        digits = re.sub(r"\D", "", m.group(1))
        if 10 <= len(digits) <= 13:
            return digits
    # Spoken-digit assembly: scan tokens, pick both numeric and spoken
    # Sprint B: extended connector/separator set to keep scanning through grouping words
    # BUG FIX: add address-related words as BREAK words so "Friedrichstraße 20" does not
    # contribute digits to a phone number scan — these cause buffer contamination.
    _PHONE_CONNECTORS = {
        "und", "komma", "pause", "dann", "strich", "bindestrich",
        "schrägstrich", "schraegstrich", "vorwahl", "durchwahl", "also", "so",
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
    if 10 <= len(s) <= 13:
        return s
    return None


def _count_digit_tokens(utterance: str) -> int:
    """Count how many digit tokens (spoken or numeric) are present in an utterance
    after shorthand expansion. Used to decide whether to RESET the cross-turn
    buffer (caller repeated the full number) or APPEND to it (caller is adding)."""
    if not utterance:
        return 0
    expanded = _expand_spoken_shorthand(utterance)
    count = 0
    for token in expanded.split():
        t = token.strip(".,!?;:-/")
        if not t:
            continue
        if t.isdigit():
            count += len(t)
        elif t in _SPOKEN_DIGITS:
            count += 1
    return count


# === Bug F: Strip tool-call / code leakage from TTS-bound text ===
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

    # Hard rule: if the utterance is clearly a phone/time/party expression,
    # don't try to read a dish count out of it.
    if any(ctx in lower for ctx in _QTY_NEGATIVE_CONTEXT) and \
            not re.search(r"\b(?:mal|portion(?:en)?)\b", lower):
        return None

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
class ConversationState:
    # Phase 2: schema_version = 2 (CapturedIntent as primary storage; shared_slots added)
    # Phase 1 set this to 1; from_dict() handles the 0→1→2 migration chain.
    # Phase 5.5: schema_version = 5 (validation_entries added).
    schema_version: int = 5

    order_intent: bool = False
    selected_dish: Optional[str] = None
    # Extra items beyond primary selected_dish (upsells, sides, drinks).
    # Stored as list of canonical short names; prices resolved via get_cached_dish_price.
    order_items_extras: List[str] = field(default_factory=list)
    phone_number: Optional[str] = None
    order_created: bool = False
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

    def ready_for_order_commit(self) -> bool:
        """
        Single authoritative check for whether create_order can fire.

        With ValidationRegistry active: requires all required slots filled,
        all three confirmation gates passed (address/phone/summary), and
        phone format-verified. Address can be FAILED (Maps error) as long
        as the caller verbally confirmed it.

        Legacy fallback (no slots): intent + dish present.
        """
        if self.order_created:
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
        """Address with street + number + street suffix (non-garbage)."""
        if not self.delivery_address:
            return False
        a = self.delivery_address.strip()
        if len(a) < 8:
            return False
        has_digit = bool(re.search(r"\d", a))
        has_street_suffix = bool(re.search(
            r"(?:straße|str\.?|allee|ring|gasse|damm|weg|platz|ufer|chaussee)",
            a.lower(),
        ))
        return has_digit and has_street_suffix

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
            "phone_number": self.phone_number,
            "order_created": self.order_created,
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
        }

    @classmethod
    def from_dict(cls, data: dict) -> ConversationState:
        """Reconstruct ConversationState from dict (e.g., from Redis).

        Migration chain:
          v0 (no schema_version) → load as-is
          v1 (Phase 1) → add call_sid, shared_slots defaults
          v2 (Phase 2) → current_intent_idx is Optional[int]; shared_slots present
          v5 (Phase 5.5) → validation_entries dict added
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

        return cls(
            schema_version=5,  # always normalize to current version on load
            call_sid=data.get("call_sid", ""),
            order_intent=data.get("order_intent", False),
            selected_dish=data.get("selected_dish"),
            phone_number=data.get("phone_number"),
            order_created=data.get("order_created", False),
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
        )

def get_cached_dish_price(state: "ConversationState", dish_name: str) -> Optional[float]:
    """Case-insensitive price lookup against the cached menu (get_menu tool result).

    Uses a cascade inside the live menu only — no hardcoded fallback prices.
    Menu items are the authoritative tenant-specific source and can change per season.
    If the menu isn't cached yet, returns None and the caller must fetch it via get_menu.

    Match strategy (best → worst, within cached_menu):
      1. Exact (case-insensitive) match on stored name.
      2. Substring match either direction (handles "Mandu" vs "Mandu (Teigtaschen)").
      3. Fuzzy SequenceMatcher ≥ 0.70.
    """
    from difflib import SequenceMatcher

    if not dish_name or not state.cached_menu:
        return None

    target = dish_name.lower().strip()
    best_price: Optional[float] = None
    best_ratio = 0.0

    for category, items in state.cached_menu.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            item_name = (item.get("name") or "").lower().strip()
            if not item_name:
                continue
            price = item.get("price") or item.get("preis")
            # Exact match wins immediately
            if target == item_name and price:
                return float(price)
            # Substring match either way wins immediately
            if (target in item_name or item_name in target) and price:
                return float(price)
            # Track best fuzzy candidate
            ratio = SequenceMatcher(None, target, item_name).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_price = price

    if best_ratio >= 0.70 and best_price is not None:
        return float(best_price)
    return None


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
    lower = text.lower()
    found: List[tuple[int, str]] = []

    # --- Pass 1: full substring match ---
    for dish in items:
        idx = lower.find(dish.lower())
        if idx >= 0:
            found.append((idx, dish))

    # --- Pass 2: first-word token fallback ---
    # Build first-word → dish map (first-in-list wins for ambiguous first words).
    _first_word_map: dict[str, str] = {}
    for dish in items:
        fw = dish.lower().split()[0]
        if fw not in _first_word_map:
            _first_word_map[fw] = dish

    _already_found_dishes = {d for _, d in found}
    for token in lower.split():
        clean = re.sub(r"[^a-zäöüß]", "", token)
        if len(clean) < 4:
            continue
        if clean in _first_word_map:
            candidate = _first_word_map[clean]
            if candidate not in _already_found_dishes:
                # Use the token's position in the text as the sort key
                idx = lower.find(clean)
                found.append((idx if idx >= 0 else len(lower), candidate))
                _already_found_dishes.add(candidate)

    # Sort by position in text, deduplicate, return names only
    found.sort(key=lambda t: t[0])
    result: List[str] = []
    for _, dish in found:
        if dish not in result:
            result.append(dish)
    return result


def _extract_dish(text: str, items: Optional[List[str]] = None) -> Optional[str]:
    # F9: Removed 5-char prefix match — it was causing hallucinations by
    # matching non-menu dish names. Exact substring match only.
    # Uses provided items list or falls back to global _KNOWN_ITEMS
    if items is None:
        items = _KNOWN_ITEMS
    
    lower = text.lower()
    for dish in items:
        if dish.lower() in lower:
            return dish
    # Safe first-word token match: "kimchi" → "Kimchi Jjigae", "tofu" → "Tofu Jjigae"
    # First-in-list wins — keeps "Tofu Jjigae" preferred over "Tofu Bibimbap".
    # Punctuation is stripped from tokens so "kimchi..." still matches "kimchi".
    # Only tokens >= 4 chars matched to prevent noise ("eis", etc.)
    first_words: dict[str, str] = {}
    for dish in items:
        fw = dish.lower().split()[0]
        if fw not in first_words:
            first_words[fw] = dish
    import re as _re
    for token in lower.split():
        clean = _re.sub(r"[^a-zäöüß]", "", token)
        if clean in first_words and len(clean) >= 4:
            return first_words[clean]
    return None


def _digits_only(s: str) -> str:
    return re.sub(r"\D", "", s)


def normalize_dish_name(dish_input: str, cached_menu: dict | None) -> str | None:
    """Normalize dish name against cached menu, then KNOWN_DISHES.
    
    Returns the canonical dish name if found, None if not on any menu.
    Prefers cached_menu (real DOBOO data) over KNOWN_DISHES (stale hardcoded list).
    
    F-B Fix: Validates dish exists on actual menu before order commit.
    """
    from difflib import SequenceMatcher
    
    if not dish_input:
        return None
    
    target = dish_input.lower().strip()
    best_match = None
    best_ratio = 0.0
    
    # === Search cached_menu first (authoritative source) ===
    if cached_menu:
        for category, items in cached_menu.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                item_name = item.get("name", "")
                if not item_name:
                    continue
                ratio = SequenceMatcher(None, target, item_name.lower().strip()).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = item_name
    
    # If found with >= 0.75 confidence in cached_menu, return it
    if best_ratio >= 0.75 and best_match:
        return best_match
    
    # === Fallback to KNOWN_DISHES (stale but at least vetted) ===
    best_ratio = 0.0
    best_match = None
    
    for known_dish in KNOWN_DISHES:
        ratio = SequenceMatcher(None, target, known_dish.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = known_dish
    
    if best_ratio >= 0.75 and best_match:
        return best_match
    
    # === Not found anywhere ===
    return None


# Shared hour-word lookup used both in update_state_from_utterance and externally
_HOUR_WORDS = {
    "zwölf": 12, "zwoelf": 12, "dreizehn": 13, "vierzehn": 14,
    "fünfzehn": 15, "fuenfzehn": 15, "sechzehn": 16, "siebzehn": 17,
    "achtzehn": 18, "neunzehn": 19, "zwanzig": 20, "einundzwanzig": 21,
    "eins": 13, "zwei": 14, "drei": 15, "vier": 16, "fünf": 17,
    "fuenf": 17, "sechs": 18, "sieben": 19, "acht": 20, "neun": 21,
    "zehn": 22, "elf": 23,
}


def update_state_from_utterance(state: ConversationState, utterance: str) -> None:
    lower = utterance.lower()

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

    if any(kw in lower for kw in RESERVATION_KEYWORDS):
        state.reservation_intent = True

    # Fix 2: Extract dish BEFORE checking order_intent
    # This allows dishes in customer utterances to be captured even on the first turn
    # before order_intent is explicitly set
    # Multi-item support: extract ALL dishes mentioned, first becomes/stays primary,
    # subsequent ones are added to extras cart (unless user is negating them).
    # Skip extraction if utterance is a negation ("Nein, kein Mandu", "ohne Kimchi").
    _neg_words = ("nein", "kein ", "keine ", "keinen ", "ohne ", "nicht ")
    _is_negation = any(nw in lower for nw in _neg_words)
    all_dishes = _extract_all_dishes(utterance) if not _is_negation else []
    dish = all_dishes[0] if all_dishes else None
    if dish:
        if state.selected_dish is None:
            state.selected_dish = dish
            # Any additional dishes in the same utterance become extras
            for extra in all_dishes[1:]:
                state.add_extra_item(extra)
        else:
            # Primary already set — add ALL mentioned (new) dishes as extras.
            # This handles "und dann noch Mandu und Mochi-Eis" after a dish is already selected.
            for d in all_dishes:
                state.add_extra_item(d)
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
            state.party_size = n

    # Also catch "21 Personen" / "25 Leute" without a für/zu prefix
    if state.party_size is None:
        pm2 = re.search(
            r"\b(\d{1,2})\s+(?:person(?:en)?|pers\.?|leute|gäste|gaeste)\b",
            lower,
        )
        if pm2:
            try:
                n2 = int(pm2.group(1))
                if 1 <= n2 <= 50:
                    state.party_size = n2
            except ValueError:
                pass

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
    if not state.reservation_date:
        import datetime as _dt
        _today = _dt.date.today()
        if "übermorgen" in lower or "uebermorgen" in lower:
            state.reservation_date = (_today + _dt.timedelta(days=2)).isoformat()
        elif "wochenende" in lower:
            # Next Saturday
            _days_to_sat = (5 - _today.weekday()) % 7 or 7
            state.reservation_date = (_today + _dt.timedelta(days=_days_to_sat)).isoformat()
        elif "nächste woche" in lower or "naechste woche" in lower:
            state.reservation_date = (_today + _dt.timedelta(days=7)).isoformat()
        elif "übernächsten" in lower or "uebernächsten" in lower:
            state.reservation_date = (_today + _dt.timedelta(days=14)).isoformat()
        elif any(d in lower for d in _DAY_NAMES):
            _DE_TO_DOW = {
                "montag": 0, "monday": 0,
                "dienstag": 1, "tuesday": 1,
                "mittwoch": 2, "wednesday": 2,
                "donnerstag": 3, "thursday": 3,
                "freitag": 4, "friday": 4,
                "samstag": 5, "saturday": 5,
                "sonntag": 6, "sunday": 6,
            }
            for d in _DAY_NAMES:
                if d in lower:
                    _target_dow = _DE_TO_DOW.get(d)
                    if _target_dow is not None:
                        _days_ahead = (_target_dow - _today.weekday()) % 7 or 7
                        state.reservation_date = (_today + _dt.timedelta(days=_days_ahead)).isoformat()
                    break
        elif "morgen" in lower:
            state.reservation_date = (_today + _dt.timedelta(days=1)).isoformat()
        elif "heute" in lower:
            state.reservation_date = _today.isoformat()
    dm = re.search(r"am\s+(\d{1,2})\.?\s*(\w+)?", lower)
    if dm:
        # Keep raw text match only if we don't already have an ISO date.
        # The date_parser worker will convert it to ISO on the next turn.
        if not state.reservation_date:
            state.reservation_date = dm.group(0).strip()

    # Reservation time: "um 19 uhr", "19:30", "halb acht", "um acht"
    tm = re.search(r"(?:um\s+)?(\d{1,2})[:.:]?(\d{2})?\s*(?:uhr)", lower)
    if tm:
        h = int(tm.group(1))
        m_min = int(tm.group(2)) if tm.group(2) else 0
        if 10 <= h <= 23:
            state.reservation_time = f"{h:02d}:{m_min:02d}"
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

    # Delivery intent flag — caller mentioned they want delivery (not necessarily gave address)
    if not state.delivery_intended:
        if any(kw in lower for kw in _DELIVERY_INTENT_KW):
            state.delivery_intended = True

    # Delivery address detection — set once when any delivery keyword detected, never cleared.
    if not state.delivery_address_mentioned:
        if any(kw in lower for kw in _ADDRESS_KW_STATE):
            state.delivery_address_mentioned = True

    # === Bug B: NAME EXTRACTION (strict, blocklist-based) ===
    new_name = _extract_name_from_utterance(utterance)
    if new_name:
        current = state.customer_name or ""
        current_valid = _is_valid_name_candidate(current)
        if not current_valid or (new_name != current and len(new_name) > len(current)):
            if current and current != new_name:
                logger.info(f"[NAME_EXTRACT] overriding {current!r} -> {new_name!r}")
            state.customer_name = new_name
            state.name_confirmed = True
            state.field_attempts["name"] = 0
            # If we just got the full name, first_name is no longer needed separately
            if state.first_name:
                state.first_name = None
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
    if not state.phone_number:
        # Try single-utterance extraction first
        phone_digits = _extract_phone_digits(utterance)
        
        if phone_digits:
            # Accept any German phone number with 8-13 digits (landlines and mobiles)
            state.phone_number = phone_digits
            state.phone_is_landline = not phone_digits.startswith(("015", "016", "017", "014", "018", "019"))
            state.phone_confirmed = True
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
                "straße", "strasse", "str", "gasse", "platz", "weg", "allee", "ring",
                "damm", "ufer", "chaussee", "boulevard",
                "bonn", "köln", "berlin", "hamburg", "frankfurt", "münchen", "muenchen",
            }
            this_turn_digits = ""
            _in_phone_region = False
            for token in expanded.split():
                t = token.strip(".,!?;:-/")
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
            if 10 <= len(state.phone_digits_buffer) <= 13:
                buffered = state.phone_digits_buffer
                # Accept any German number regardless of mobile/landline prefix
                state.phone_number = buffered
                state.phone_is_landline = not buffered.startswith(("015", "016", "017", "014", "018", "019"))
                state.phone_confirmed = True
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
    if not state.delivery_confirmed:
        delivery_kw = ["lieferung", "liefern", "liefere", "delivery", "zu mir", "nach hause"]
        pickup_kw = ["abholen", "mitnehmen", "takeaway", "zum mitnehmen", "pickup"]
        
        if any(kw in lower for kw in delivery_kw):
            state.delivery_intended = True
            state.delivery_address_mentioned = True
            state.delivery_confirmed = True
            logger.debug(f"[Collection] Delivery confirmed")
        elif any(kw in lower for kw in pickup_kw):
            state.delivery_intended = False
            state.delivery_address_mentioned = False
            state.delivery_confirmed = True
            logger.debug(f"[Collection] Pickup confirmed")

    # === Bug C: ADDRESS EXTRACTION (requires street+number+real city) ===
    if not state.delivery_address or not _address_looks_valid(state.delivery_address):
        new_addr = _extract_address_from_utterance(utterance)
        if new_addr:
            if state.delivery_address and state.delivery_address != new_addr:
                logger.info(f"[ADDRESS_EXTRACT] overriding {state.delivery_address!r} -> {new_addr!r}")
            state.delivery_address = new_addr
            state.delivery_address_mentioned = True
            state.field_attempts["address"] = 0

    # Implicit reservation intent: party_size >= 2 without food → reservation
    if (
        state.party_size is not None
        and state.party_size >= 2
        and not state.selected_dish
        and not state.order_intent
    ):
        state.reservation_intent = True

    # Fix C: implicit reservation intent from party_size + date/time together
    # (even party_size 1 is enough when combined with a date/time)
    # Handles cases where accent/sleepy caller gives date+party without
    # explicit "reservieren" keyword.
    if (
        not state.reservation_intent
        and state.party_size is not None
        and (state.reservation_date is not None or state.reservation_time is not None)
        and not state.order_intent
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
    Only set dish from bot response if the bot is EXPLICITLY CONFIRMING an order —
    never from suggestions or menu recommendations.

    Hallucination root cause: bot says "Ich empfehle Bibimbap" as a suggestion for
    a non-menu request → old code extracted Bibimbap → create_order fired for a
    dish the customer never chose.

    Fix: require confirmation language before extracting. Suggestions (empfehle,
    haben wir nicht, leider) are explicitly excluded.
    """
    if not state.order_intent or state.selected_dish:
        return
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
    if dish:
        state.selected_dish = dish


def sanitize_bot_text_against_tool_results(bot_text: str, tool_results: dict) -> str:
    """Rewrite bot text if tools failed, to avoid false confirmations.
    Also strips verbatim tool 'message' field content that the LLM echoed.

    F-C Fix: Ensures bot doesn't claim false confirmation when tools error.
    Sprint B: Extended to strip echoed prose from ALL tool message fields,
    not just create_order/create_reservation.
    """
    if not tool_results:
        return bot_text

    # ── Strip verbatim tool message fields the LLM may have echoed ──────
    # When a tool returns {"message": "Adresse bestätigt: Friedrichstr. 20"},
    # the LLM sometimes pastes this string verbatim. Strip any substring that
    # is an exact substring of a tool's "message" field.
    _TOOLS_WITH_MESSAGES = (
        "verify_address", "get_weather", "get_restaurant_info",
        "get_nearby_parking", "get_directions", "faq", "check_availability",
        "get_date_info", "get_caller_history",
    )
    for tool_name in _TOOLS_WITH_MESSAGES:
        result = tool_results.get(tool_name)
        if not isinstance(result, dict):
            continue
        msg = result.get("message") or result.get("result") or ""
        if not msg or not isinstance(msg, str) or len(msg) < 10:
            continue
        if msg[:40] in bot_text:
            bot_text = bot_text.replace(msg, "").strip()
            logger.debug(f"[Sanitize] Stripped {tool_name} message echo from bot text")

    # ── Handle tool failures (original logic) ────────────────────────────
    create_order_failed = (
        "create_order" in tool_results
        and tool_results["create_order"].get("error")
    )
    create_reservation_failed = (
        "create_reservation" in tool_results
        and tool_results["create_reservation"].get("error")
    )

    if create_order_failed or create_reservation_failed:
        # Replace "aufgenommen" / "bestätigt" with apology
        bot_text = re.sub(
            r"(Ich habe Ihre Bestellung.*?aufgenommen|Bestellung.*?bestätigt|wurde verarbeitet)",
            "Entschuldigung, Ihre Bestellung konnte leider nicht verarbeitet werden. Bitte versuchen Sie es später erneut oder kontaktieren Sie uns.",
            bot_text,
            flags=re.IGNORECASE,
        )
        logger.warning(f"[Sanitize] Rewrote bot text due to tool failure")

    return bot_text


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
