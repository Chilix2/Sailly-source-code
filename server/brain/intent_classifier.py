"""
server/brain/intent_classifier.py — Two-axis intent + turn-type classifier.

Architecture:
    1. Regex fast-path covers ~80% of cases (greeting, goodbye, confirmation,
       correction, FAQ keywords) with near-zero latency.
    2. Haiku fallback for ambiguous cases — returns IntentResult with confidence.

This is the single source of intent classification — drives worker_router for
all profiles (no shadow mode; v4 pipeline is the only live path).
"""
from __future__ import annotations

import re
import logging
from typing import Optional

from server.brain.intent_session import (
    IntentKind,
    IntentResult,
    TurnType,
)

logger = logging.getLogger(__name__)

# ── Intent → worker profile mapping ────────────────────────────────────────────

INTENT_TO_PROFILE: dict[IntentKind, str] = {
    IntentKind.GREETING:           "greeting",
    IntentKind.SMALLTALK:          "smalltalk",
    IntentKind.FAQ:                "business_info",
    IntentKind.DIETARY_INQUIRY:    "business_info",
    IntentKind.GOODBYE:            "goodbye",
    IntentKind.RESERVATION:        "reservation_start",
    IntentKind.MODIFY_RESERVATION: "reservation_start",
    IntentKind.CANCEL_RESERVATION: "reservation_start",
    IntentKind.TAKEAWAY:           "order_start",
    IntentKind.DELIVERY:           "order_start",
    IntentKind.BULK_ORDER:         "order_start",
    IntentKind.PRE_ORDER:          "order_start",
    IntentKind.MODIFY_ORDER:       "order_modify",
    IntentKind.CANCEL_ORDER:       "order_modify",
    IntentKind.ORDER_STATUS:       "order_modify",
    IntentKind.COMPLAINT:          "escalation",
    IntentKind.PAYMENT_ISSUE:      "escalation",
    IntentKind.LOST_AND_FOUND:     "escalation",
    IntentKind.GROUP_CATERING:     "escalation",
    IntentKind.UNKNOWN:            "greeting",
}

# ── Regex fast-path rules ──────────────────────────────────────────────────────

_GREETING_RE = re.compile(
    r"^(hallo|hi|guten (tag|morgen|abend|nachmittag)|hey|servus|moin|"
    r"guten\s*tag|herzlich|willkommen|grias|salut)\b",
    re.I,
)
_GOODBYE_RE = re.compile(
    r"\b(tschüss?|auf wiedersehen|auf wiederhören|bye|ciao|tschau|"
    r"das war.?s|das wär.?s|schönen (tag|abend|morgen|nachmittag)|"
    r"noch einen schönen)\b",
    re.I,
)
_CONFIRM_RE = re.compile(
    r"^(ja\b|genau\b|richtig\b|stimmt\b|korrekt\b|okay\b|ok\b|"
    r"alles klar\b|super\b|prima\b|das stimmt\b|ja,?\s*bitte\b)",
    re.I,
)
_DENY_RE = re.compile(
    r"^(nein\b|ne\b|nö\b|nicht\b|falsch\b|das stimmt nicht\b|"
    r"das ist falsch\b|nein,?\s*danke\b)",
    re.I,
)
_CORRECTION_RE = re.compile(
    r"\b(ich wollte (eigentlich|lieber|stattdessen)|"
    r"eigentlich (wollte|meinte|habe ich|ist es)|"
    r"ich meinte|korrektur|nicht .{1,20}sondern|"
    r"entschuldigung,? ich)\b",
    re.I,
)
_RESERVATION_RE = re.compile(
    r"\b(reservier|reservierung|tisch\s*(für|reserv)|"
    r"platz\s*(für|reserv)|tafel|abend(essen)?\s*(für|reserv)|"
    r"buche?n?)\b",
    re.I,
)
_ORDER_RE = re.compile(
    r"\b(bestell|bestellung|ich (hätte|möchte|will|nehme)\s+(gerne|bitte)?|"
    r"liefern|lieferung|abhole?n?|zum mitnehmen|take.?away)\b",
    re.I,
)
_FAQ_RE = re.compile(
    r"\b(öffnungszeit|geöffnet|geschlossen|adresse|wo (ist|seid|sind|liegt)|"
    r"parken|parkplatz|telefon|nummer|preis|kostet|wetter|"
    r"anfahrt|wie komm|weg|"
    r"gerichte?|speise(karte)?|menü|menu|empfehl|was (gibt|haben|habt|bieten)|"
    r"was\s+habt|essen\s*(hier|bei|von)|das gericht|was kostet|"
    r"habt\s+ihr\b|haben\s+sie\b|gibt\s+es\b)\b",
    re.I,
)
_ESCALATION_RE = re.compile(
    r"\b(beschwerde|unzufrieden|ärger|falsch (geliefert|bestellt)|"
    r"reklamation|chef|manager|leiter|supervisor|"
    r"zahlung|bezahl|rechnung|verloren|verlegt|"
    r"group|gruppe|event|catering|veranstaltung)\b",
    re.I,
)

# Price inquiry — checked BEFORE _ORDER_RE to prevent "was kostet das Bulgogi?"
# from being misclassified as an order intent.
_PRICE_RE = re.compile(
    r"\b(was kostet|wie teuer|kostet das|preis (von|für)|was ist der preis)\b",
    re.I,
)

# Slot-filling turns: user provides name or phone in response to a bot question.
# These should be ADD_INFORMATION for the current locked intent, not UNKNOWN.
_NAME_SLOT_RE = re.compile(
    r"\b(auf den namen|auf name|mein name\b|name ist|heisse|heiße|ich heisse|ich heiße"
    r"|name:?\s+\w|auf\s+\w+\s+\w+\s*$)\b",
    re.I,
)
_PHONE_SLOT_RE = re.compile(
    r"\b(nummer|telefon|handy|mobil|rückruf|meine nummer|die nummer)\b.*\d{4,}|\d{6,}",
    re.I,
)

# Turn-type fast paths
_FINALIZE_RE = re.compile(
    r"\b(fertig|das ist alles|schicken|aufgeben|bestätigen|"
    r"abschließen|buchen|reservieren)\b",
    re.I,
)


def classify(text: str, turn_idx: int = 0) -> IntentResult:
    """Classify intent and turn-type from user utterance.

    Uses regex fast-path first. Falls back to Haiku only when regex is
    ambiguous (returns UNKNOWN). Haiku fallback not implemented here —
    the caller (IntentSessionManager) handles the async Haiku call when
    this returns confidence < 0.6.
    """
    if not text:
        return IntentResult(
            intent=IntentKind.UNKNOWN,
            turn_type=TurnType.UNCLEAR,
            confidence=0.5,
            worker_profile="greeting",
            classifier_path="regex",
        )

    lower = text.lower().strip()

    # ── Turn 0: Check for multi-intent or reservation before defaulting to greeting ──
    if turn_idx == 0:
        # If turn 0 has explicit reservation/order keywords, classify accordingly
        # This allows multi-intent on first turn (e.g., "weather + reservation")
        has_reservation = _RESERVATION_RE.search(lower)
        has_order = _ORDER_RE.search(lower)
        has_faq = _FAQ_RE.search(lower)
        
        # If both a transaction intent AND an info intent are present, prefer transaction
        # but signal multi-intent via ADD_INFORMATION turn_type for worker_router
        if has_reservation and has_faq:
            return IntentResult(
                intent=IntentKind.RESERVATION,
                turn_type=TurnType.ADD_INFORMATION,  # signals: also gather info this turn
                confidence=0.85,
                worker_profile="reservation_start",
                classifier_path="regex",
            )
        if has_order and has_faq:
            return IntentResult(
                intent=IntentKind.TAKEAWAY,
                turn_type=TurnType.ADD_INFORMATION,
                confidence=0.85,
                worker_profile="order_start",
                classifier_path="regex",
            )
        if has_reservation:
            return IntentResult(
                intent=IntentKind.RESERVATION,
                turn_type=TurnType.ADD_INFORMATION,
                confidence=0.85,
                worker_profile="reservation_start",
                classifier_path="regex",
            )
        if has_order:
            return IntentResult(
                intent=IntentKind.TAKEAWAY,
                turn_type=TurnType.ADD_INFORMATION,
                confidence=0.85,
                worker_profile="order_start",
                classifier_path="regex",
            )
        # Default: greeting
        return IntentResult(
            intent=IntentKind.GREETING,
            turn_type=TurnType.START_INTENT,
            confidence=1.0,
            worker_profile="greeting",
            classifier_path="regex",
        )

    # ── Goodbye ─────────────────────────────────────────────────────────────────
    if _GOODBYE_RE.search(lower):
        return IntentResult(
            intent=IntentKind.GOODBYE,
            turn_type=TurnType.FINALIZE,
            confidence=0.95,
            worker_profile="goodbye",
            classifier_path="regex",
        )

    # ── Confirmation / Denial ───────────────────────────────────────────────────
    if len(lower) < 40:
        if _CONFIRM_RE.match(lower):
            return IntentResult(
                intent=IntentKind.UNKNOWN,   # intent unchanged (session-locked)
                turn_type=TurnType.CONFIRM,
                confidence=0.95,
                worker_profile="greeting",
                classifier_path="regex",
            )
        if _DENY_RE.match(lower):
            return IntentResult(
                intent=IntentKind.UNKNOWN,
                turn_type=TurnType.DENY,
                confidence=0.95,
                worker_profile="greeting",
                classifier_path="regex",
            )

    # ── Correction ──────────────────────────────────────────────────────────────
    if _CORRECTION_RE.search(lower):
        return IntentResult(
            intent=IntentKind.UNKNOWN,   # intent unchanged; correction modifies slots
            turn_type=TurnType.CORRECT_PREVIOUS,
            confidence=0.90,
            worker_profile="correction",
            classifier_path="regex",
        )

    # ── Slot-filling turns (name / phone provided in response to bot question) ──
    # These must be recognized as ADD_INFORMATION before the UNKNOWN fallthrough.
    if _NAME_SLOT_RE.search(lower) or _PHONE_SLOT_RE.search(lower):
        return IntentResult(
            intent=IntentKind.UNKNOWN,    # intent unchanged; slot-filling mid-conversation
            turn_type=TurnType.ADD_INFORMATION,
            confidence=0.80,
            worker_profile="reservation_start",  # name/phone workers live here
            classifier_path="regex",
        )

    # ── Domain intents ──────────────────────────────────────────────────────────
    intent = IntentKind.UNKNOWN
    confidence = 0.0
    turn_type = TurnType.START_INTENT

    if _RESERVATION_RE.search(lower):
        intent = IntentKind.RESERVATION
        confidence = 0.85
    elif _PRICE_RE.search(lower):
        # Price inquiry takes priority over ORDER to avoid mis-routing
        # "Was kostet das Bulgogi?" into order-slot-filling
        intent = IntentKind.FAQ
        confidence = 0.85
    elif _FAQ_RE.search(lower):
        # FAQ takes priority over ORDER: "Was habt ihr zum bestellen?" is a menu
        # inquiry, not an actual order. Pure ordering ("Ich möchte Bibimbap bestellen")
        # won't match _FAQ_RE so the ORDER branch below handles those correctly.
        intent = IntentKind.FAQ
        confidence = 0.80
    elif _ORDER_RE.search(lower):
        intent = IntentKind.TAKEAWAY
        confidence = 0.85
    elif _ESCALATION_RE.search(lower):
        # Differentiate by sub-pattern
        if re.search(r"\b(group|gruppe|event|catering|veranstaltung)\b", lower, re.I):
            intent = IntentKind.GROUP_CATERING
        elif re.search(r"\b(zahlung|bezahl|rechnung)\b", lower, re.I):
            intent = IntentKind.PAYMENT_ISSUE
        elif re.search(r"\b(verloren|verlegt)\b", lower, re.I):
            intent = IntentKind.LOST_AND_FOUND
        else:
            intent = IntentKind.COMPLAINT
        confidence = 0.82
    elif _GREETING_RE.match(lower) and turn_idx <= 1:
        intent = IntentKind.GREETING
        confidence = 0.90
    else:
        # Ambiguous — needs Haiku
        intent = IntentKind.UNKNOWN
        confidence = 0.4
        turn_type = TurnType.UNCLEAR

    # Refine turn_type
    if intent != IntentKind.UNKNOWN:
        if _FINALIZE_RE.search(lower):
            turn_type = TurnType.FINALIZE
        elif re.search(r"\b(und auch|außerdem|noch)\b", lower, re.I):
            turn_type = TurnType.ADD_INFORMATION
        else:
            turn_type = TurnType.START_INTENT

    profile = INTENT_TO_PROFILE.get(intent, "greeting")
    return IntentResult(
        intent=intent,
        turn_type=turn_type,
        confidence=confidence,
        worker_profile=profile,
        classifier_path="regex",
    )


async def classify_with_haiku(
    user_text: str,
    turn_idx: int = 0,
    llm_client=None,
) -> IntentResult:
    """LLM fallback for utterances that the regex fast-path cannot classify.

    Called when classify() returns UNKNOWN (confidence 0.4).  Creates a
    one-shot Anthropic async client if none is provided — uses the same
    ANTHROPIC_API_KEY env var that tier2_runner uses.

    Returns IntentResult with classifier_path="haiku" and confidence 0.75.
    Falls back to an UNKNOWN result on any error so the caller is never blocked.
    """
    import os

    valid_intents = ", ".join(k.value for k in IntentKind)
    prompt = (
        f"Classify the following user message into exactly one intent.\n"
        f"Valid intents: {valid_intents}\n"
        f"Message: \"{user_text}\"\n"
        f"Reply with ONLY the intent name, nothing else."
    )

    try:
        if llm_client is None:
            from anthropic import AsyncAnthropic
            llm_client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

        model = os.environ.get("INTENT_HAIKU_MODEL", "claude-haiku-4-5")
        response = await llm_client.messages.create(
            model=model,
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip().lower()
        intent = next((k for k in IntentKind if k.value == raw), IntentKind.UNKNOWN)
        profile = INTENT_TO_PROFILE.get(intent, "greeting")
        logger.info(
            f"[IntentClassifier] Haiku classified '{user_text[:40]}' → {intent.value}"
        )
        return IntentResult(
            intent=intent,
            turn_type=TurnType.START_INTENT,
            confidence=0.75,
            worker_profile=profile,
            classifier_path="haiku",
        )
    except Exception as _haiku_err:
        logger.warning(f"[IntentClassifier] Haiku fallback failed: {_haiku_err}")
        return IntentResult(
            intent=IntentKind.UNKNOWN,
            turn_type=TurnType.UNCLEAR,
            confidence=0.4,
            worker_profile=INTENT_TO_PROFILE.get(IntentKind.UNKNOWN, "greeting"),
            classifier_path="regex",
        )
