"""
server/brain/intent_session.py — Intent Session schemas for Phase 3 architecture.

The IntentSession is created on the first turn of a call and persists across the
entire conversation. Once the classifier is confident (≥0.85) on turns 1-2, the
session is locked and the active worker profile is stable for the rest of the call.

Reroute signals (REROUTE_REGEXES) are checked every turn even when locked, and
unlock the session for fresh classification when a genuine intent shift occurs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ── Intent kinds (mirrors server/brain/captured_intents.py IntentKind) ─────────

class IntentKind(str, Enum):
    TAKEAWAY           = "takeaway"
    DELIVERY           = "delivery"
    BULK_ORDER         = "bulk_order"
    RESERVATION        = "reservation"
    PRE_ORDER          = "pre_order"
    MODIFY_ORDER       = "modify_order"
    CANCEL_ORDER       = "cancel_order"
    ORDER_STATUS       = "order_status"
    MODIFY_RESERVATION = "modify_reservation"
    CANCEL_RESERVATION = "cancel_reservation"
    COMPLAINT          = "complaint"
    PAYMENT_ISSUE      = "payment_issue"
    LOST_AND_FOUND     = "lost_and_found"
    DIETARY_INQUIRY    = "dietary_inquiry"
    GROUP_CATERING     = "group_catering"
    FAQ                = "faq"
    SMALLTALK          = "smalltalk"
    GREETING           = "greeting"
    GOODBYE            = "goodbye"
    UNKNOWN            = "unknown"


# ── Turn types ──────────────────────────────────────────────────────────────────

class TurnType(str, Enum):
    START_INTENT        = "start_intent"
    ADD_INFORMATION     = "add_information"
    MODIFY_INFORMATION  = "modify_information"
    CORRECT_PREVIOUS    = "correct_previous"
    CONFIRM             = "confirm"
    DENY                = "deny"
    ASK_QUESTION        = "ask_question"
    FINALIZE            = "finalize"
    INTERRUPT           = "interrupt"
    UNCLEAR             = "unclear"


# ── Reroute signals — checked every turn, even when intent is locked ───────────

REROUTE_REGEXES: list[re.Pattern] = [
    re.compile(r"\bich wollte (eigentlich|nur)\b", re.I),
    re.compile(r"\beigentlich wollte ich\b", re.I),
    re.compile(r"\b(stop|halt|moment)\s*[,.]?\s*doch\b", re.I),
    re.compile(r"\bdoch (lieber|nicht|gar)\b", re.I),
    re.compile(r"\bnoch (eine|kurz eine)?\s*frage\b", re.I),
    re.compile(r"\b(ne|nein|nö)\s*[,.]?\s*ich (will|möchte)\b", re.I),
    re.compile(r"\bwarte\s*,?\s*doch\b", re.I),
    re.compile(r"\bich meine eigentlich\b", re.I),
]


def check_reroute_signals(text: str) -> bool:
    """Return True if any reroute signal is detected in user text."""
    for pattern in REROUTE_REGEXES:
        if pattern.search(text):
            return True
    return False


# ── Reroute event ───────────────────────────────────────────────────────────────

@dataclass
class RerouteEvent:
    turn_idx: int
    old_intent: IntentKind
    new_intent: IntentKind
    trigger_pattern: str


# ── Intent classification result ────────────────────────────────────────────────

@dataclass
class IntentResult:
    """Output of the two-axis classifier (Stage 1)."""
    intent: IntentKind
    turn_type: TurnType
    confidence: float                    # 0.0–1.0
    secondary_intent: Optional[IntentKind] = None
    secondary_confidence: float = 0.0
    worker_profile: str = "greeting"     # resolved profile key
    classifier_path: str = "regex"       # "regex" | "haiku"


# ── Intent Session ──────────────────────────────────────────────────────────────

@dataclass
class IntentSession:
    """Persists across the full call. Created on turn 1."""

    # Primary classification
    primary_intent: IntentKind = IntentKind.UNKNOWN
    secondary_intents: list[IntentKind] = field(default_factory=list)
    worker_profile: str = "greeting"

    # Locking
    locked: bool = False
    lock_confidence: float = 0.0
    locked_at_turn: int = -1

    # Reroute tracking
    reroute_history: list[RerouteEvent] = field(default_factory=list)

    # Current turn classification
    current_turn_type: TurnType = TurnType.START_INTENT
    current_intent_result: Optional[IntentResult] = None
    
    # Fix 7: Multi-intent queuing for transaction-level switches
    queued_intents: list[IntentKind] = field(default_factory=list)  # Secondary intents pending confirmation
    allow_secondary_faq: bool = True  # Allow FAQ interruptions during transactions

    def update(self, result: IntentResult, turn_idx: int) -> None:
        """Apply a new IntentResult to the session."""
        self.current_intent_result = result
        self.current_turn_type = result.turn_type

        if self.locked:
            # Only update turn_type when locked — intent stays fixed
            return

        old_intent = self.primary_intent
        self.primary_intent = result.intent
        self.worker_profile = result.worker_profile

        # Lock after turn 1–2 if confidence meets threshold, BUT only for transaction intents
        # (RESERVATION, TAKEAWAY, etc.) or non-transactional confirmed intents.
        # Do NOT lock on GREETING or FAQ — allow natural flow to transaction intents.
        info_only_intents = {IntentKind.GREETING, IntentKind.FAQ, IntentKind.SMALLTALK,
                             IntentKind.UNKNOWN, IntentKind.DIETARY_INQUIRY}
        should_lock = (
            not self.locked 
            and result.confidence >= 0.85 
            and turn_idx >= 1
            and result.intent not in info_only_intents
        )
        if should_lock:
            self.locked = True
            self.lock_confidence = result.confidence
            self.locked_at_turn = turn_idx

    def apply_reroute(self, result: IntentResult, turn_idx: int) -> None:
        """Unlock and re-classify after a reroute signal."""
        event = RerouteEvent(
            turn_idx=turn_idx,
            old_intent=self.primary_intent,
            new_intent=result.intent,
            trigger_pattern="reroute_signal",
        )
        self.reroute_history.append(event)
        self.locked = False
        self.update(result, turn_idx)
    
    def queue_secondary_intent(self, intent: IntentKind) -> None:
        """Fix 7: Queue a transaction-level intent switch (e.g., switch from RESERVATION to TAKEAWAY).
        
        The queued intent will be offered after the current transaction completes.
        """
        if intent not in self.queued_intents:
            self.queued_intents.append(intent)
    
    def pop_queued_intent(self) -> Optional[IntentKind]:
        """Fix 7: Retrieve and remove the oldest queued intent."""
        if self.queued_intents:
            return self.queued_intents.pop(0)
        return None
    
    def clear_queued_intents(self) -> None:
        """Fix 7: Clear all queued intents (e.g., at call end)."""
        self.queued_intents.clear()

    @property
    def spans_multiple_profiles(self) -> bool:
        """True if primary + secondary intents map to different worker profiles."""
        if not self.current_intent_result:
            return False
        sec = self.current_intent_result.secondary_intent
        if sec is None:
            return False
        # Simple heuristic: reservation vs order are different profiles
        order_intents = {IntentKind.TAKEAWAY, IntentKind.DELIVERY, IntentKind.BULK_ORDER,
                         IntentKind.PRE_ORDER, IntentKind.MODIFY_ORDER, IntentKind.CANCEL_ORDER}
        reservation_intents = {IntentKind.RESERVATION, IntentKind.MODIFY_RESERVATION,
                                IntentKind.CANCEL_RESERVATION}
        primary_is_order = self.primary_intent in order_intents
        secondary_is_reservation = sec in reservation_intents
        return (primary_is_order and secondary_is_reservation) or \
               (self.primary_intent in reservation_intents and sec in order_intents)

    def to_dict(self) -> dict:
        """Serialise for google_context_documents shadow logging."""
        return {
            "intent": self.primary_intent.value,
            "turn_type": self.current_turn_type.value,
            "intent_locked": self.locked,
            "lock_confidence": self.lock_confidence,
            "reroute_fired": len(self.reroute_history) > 0,
            "worker_profile": self.worker_profile,
            "queued_intents": [i.value for i in self.queued_intents],
            "allow_secondary_faq": self.allow_secondary_faq,
        }
