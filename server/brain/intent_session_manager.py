"""
server/brain/intent_session_manager.py — Stage 1.5: Intent Session Manager (Phase 3.3).

Manages the IntentSession lifecycle across a call:
    - Turn 0–1: classify intent, create session, do not lock yet
    - Turn 2+: if same intent and confidence ≥ 0.85 → lock
    - Every turn: check REROUTE_REGEXES regardless of locked state
    - On reroute: unlock + re-classify fresh

In shadow mode (Phase 3–4) this runs alongside the legacy pipeline.
Its output is persisted to google_context_documents but does not change
live behaviour. Phase 5+ switches migrated profiles live.
"""
from __future__ import annotations

import logging
from typing import Optional

from server.brain.intent_classifier import classify
from server.brain.intent_session import (
    IntentKind,
    IntentResult,
    IntentSession,
    TurnType,
    check_reroute_signals,
)

logger = logging.getLogger(__name__)

# Confidence threshold to lock the session
LOCK_CONFIDENCE_THRESHOLD = 0.85


class IntentSessionManager:
    """One instance per call. Created at call start."""

    def __init__(self) -> None:
        self.session = IntentSession()
        self._last_regex_result: Optional[IntentResult] = None

    def process_turn(self, user_text: str, turn_idx: int) -> IntentSession:
        """Update the session based on the current user utterance.

        Returns the updated IntentSession. In shadow mode, the caller
        persists session.to_dict() to google_context_documents.
        """
        if not user_text:
            return self.session

        # Always check reroute signals first, even when locked
        reroute_detected = False
        if self.session.locked and check_reroute_signals(user_text):
            reroute_detected = True
            logger.info(
                f"[IntentSession] T{turn_idx}: reroute signal detected, unlocking"
            )

        # Run regex classifier
        result = classify(user_text, turn_idx=turn_idx)
        self._last_regex_result = result

        # Handle CONFIRM/DENY: inherit current intent from session
        if result.turn_type in (TurnType.CONFIRM, TurnType.DENY, TurnType.CORRECT_PREVIOUS):
            result = IntentResult(
                intent=self.session.primary_intent
                       if self.session.primary_intent != IntentKind.UNKNOWN
                       else result.intent,
                turn_type=result.turn_type,
                confidence=result.confidence,
                worker_profile=self.session.worker_profile,
                classifier_path=result.classifier_path,
            )

        if reroute_detected:
            self.session.apply_reroute(result, turn_idx)
            logger.info(
                f"[IntentSession] T{turn_idx}: rerouted to {result.intent.value} "
                f"(profile={result.worker_profile})"
            )
        else:
            # Also reroute when top-2 intents span different profiles
            if (
                self.session.locked
                and result.secondary_confidence >= 0.4
                and result.secondary_intent is not None
                and self.session.spans_multiple_profiles
            ):
                logger.info(
                    f"[IntentSession] T{turn_idx}: profile-spanning top-2 → reroute"
                )
                self.session.apply_reroute(result, turn_idx)
            else:
                self.session.update(result, turn_idx)

        if self.session.locked and turn_idx == self.session.locked_at_turn:
            logger.info(
                f"[IntentSession] T{turn_idx}: session LOCKED "
                f"intent={self.session.primary_intent.value} "
                f"profile={self.session.worker_profile} "
                f"confidence={self.session.lock_confidence:.2f}"
            )

        return self.session

    def get_worker_profile(self) -> str:
        """Current worker profile key for the WorkerRouter."""
        return self.session.worker_profile

    def get_turn_type(self) -> TurnType:
        """Current turn type for the WorkerRouter."""
        return self.session.current_turn_type

    def to_shadow_dict(self, turn_idx: int) -> dict:
        """Serialise for google_context_documents shadow logging."""
        d = self.session.to_dict()
        d["classifier_path"] = (
            self._last_regex_result.classifier_path
            if self._last_regex_result else "unknown"
        )
        return d
