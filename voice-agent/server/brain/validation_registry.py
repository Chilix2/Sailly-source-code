"""
EagerSlotValidator — eager background validation for extracted slots.

FINDING-016 fix: this module is the historical home of a "push" validation
registry that fires background asyncio Tasks the moment a slot is extracted.
It has been renamed from `ValidationRegistry` to `EagerSlotValidator` so
the canonical `ValidationRegistry` class lives in exactly one location:
  server/brain/layer1/validation/registry.py  (Phase 5.5)

The backward-compat alias `ValidationRegistry = EagerSlotValidator` is
kept so all existing callers (`adk_turn_processor`, `conversation_state`)
continue to work without modification.

Architecture note:
  EagerSlotValidator (this file) — background-task push model:
    • Fires the moment a slot is extracted (zero-confidence threshold)
    • Non-blocking; answers "is this value already known-good?"
    • Used by the turn processor for UX optimisation (don't wait for Maps)

  ValidationRegistry (layer1/validation/registry.py) — registered-validator pull model:
    • Validators registered once at startup; called on FILLED slots
    • gate-all: dispatcher calls is_committable() before state-mutating tools
    • Used by dispatch_with_validation (PR-6) for safety gating

Both instances are created per-call and stored on ConversationState:
  state.validation_registry_ref  ← EagerSlotValidator (legacy turn-processor path)
  state._validation_registry     ← ValidationRegistry (canonical gating path)

A future PR should decide whether to merge these into a single unified
registry or keep them separate with clearly documented responsibilities.

Design decisions (EagerSlotValidator):
- Zero confidence threshold: validation fires on any extraction. Worst
  case is a few extra Maps calls/day; best case is every validation is
  done before the bot's confirmation turn.
- Deduplication by value: same value = no new task, regardless of how
  many times the extractor emits it.
- Cancellation on correction: new value cancels the old pending task
  and re-fires immediately.
- Non-blocking: validation is a background optimization. If Maps goes
  down, addresses commit as FAILED and the caller's verbal confirmation
  is the source of truth. Nothing blocks the turn loop.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)


class ValidationStatus(str, Enum):
    NOT_NEEDED = "not_needed"
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    STALE = "stale"  # value changed, needs re-validation


@dataclass
class ValidationEntry:
    slot_name: str
    status: ValidationStatus
    value_validated: Optional[str] = None
    result: Any = None
    error: Optional[str] = None
    started_at: float = field(default_factory=time.perf_counter)
    completed_at: Optional[float] = None
    task: Optional[asyncio.Task] = None

    @property
    def elapsed_ms(self) -> Optional[int]:
        if self.completed_at is None:
            return None
        return int((self.completed_at - self.started_at) * 1000)

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            ValidationStatus.VERIFIED,
            ValidationStatus.FAILED,
        )


# German display labels for prompt injection
_SLOT_LABEL_DE: dict[str, str] = {
    "address": "Lieferadresse",
    "phone": "Telefonnummer",
    "items": "Bestellung",
    "delivery_eta": "Lieferzeit",
}


class EagerSlotValidator:
    """
    Eager-fire validation task tracker. Zero confidence threshold.

    One instance per call (owned by ADKTurnProcessor). Thread-safe for
    asyncio — all operations happen in the same event loop.

    Renamed from ValidationRegistry (FINDING-016): the canonical
    ValidationRegistry now lives at server.brain.layer1.validation.registry.
    Use the backward-compat alias below to avoid breaking existing callers.
    """

    # Maps slot_name → tool_name for executor.py
    VALIDATOR_MAP: dict[str, str] = {
        "address": "verify_address",
        "phone": "validate_phone_format",
        "items": "check_item_availability",
        "delivery_eta": "estimate_delivery_time",
    }

    # Slots that do not need background validation (handled by sub-slot address)
    VALIDATION_SKIP: frozenset = frozenset({
        "name",
        "delivery_type",
        "party_size",
        "reservation_date",
        "reservation_time",
        "address_street",
        "address_number",
        "address_city",
    })

    def __init__(
        self,
        execute_tool: Callable[..., Awaitable[Any]],
        call_sid: str,
        tenant_id: str,
        state: Any,
    ) -> None:
        self._entries: dict[str, ValidationEntry] = {}
        self._execute_tool = execute_tool
        self._call_sid = call_sid
        self._tenant_id = tenant_id
        self._state = state

    # ── Queries ──────────────────────────────────────────────────────────

    def get(self, slot_name: str) -> Optional[ValidationEntry]:
        return self._entries.get(slot_name)

    def is_verified(self, slot_name: str) -> bool:
        e = self._entries.get(slot_name)
        return e is not None and e.status == ValidationStatus.VERIFIED

    def is_pending(self, slot_name: str) -> bool:
        e = self._entries.get(slot_name)
        return e is not None and e.status == ValidationStatus.PENDING

    def is_failed(self, slot_name: str) -> bool:
        e = self._entries.get(slot_name)
        return e is not None and e.status == ValidationStatus.FAILED

    def all_terminal(self, slot_names: list[str]) -> bool:
        """True if every named slot has reached a terminal state."""
        return all(
            (e := self._entries.get(name)) is not None and e.is_terminal
            for name in slot_names
        )

    def pending_slot_names(self) -> list[str]:
        return [
            _SLOT_LABEL_DE.get(name, name)
            for name, e in self._entries.items()
            if e.status == ValidationStatus.PENDING
        ]

    def failed_slot_names(self) -> list[str]:
        return [
            _SLOT_LABEL_DE.get(name, name)
            for name, e in self._entries.items()
            if e.status == ValidationStatus.FAILED
        ]

    def has_any_failed(self) -> bool:
        return any(e.status == ValidationStatus.FAILED for e in self._entries.values())

    def has_any_pending(self) -> bool:
        return any(e.status == ValidationStatus.PENDING for e in self._entries.values())

    # ── Commands ─────────────────────────────────────────────────────────

    async def ensure_validated(
        self,
        slot_name: str,
        value: str,
        tool_args: dict,
    ) -> None:
        """
        Fire a background validation for this slot/value pair.

        No-op if we're already validating (or have validated) this exact
        value. If the value changed, cancel the previous task and restart.

        Args:
            slot_name: Logical slot name ("address", "phone", "items")
            value:     Canonical string representation to deduplicate on
            tool_args: Dict passed directly to the executor tool
        """
        if not value or not value.strip():
            return
        if slot_name in self.VALIDATION_SKIP:
            return
        if slot_name not in self.VALIDATOR_MAP:
            return

        existing = self._entries.get(slot_name)
        if existing and existing.value_validated == value:
            # Same value already handled — no-op (deduplication)
            return

        # Cancel stale task if value changed
        if existing:
            if existing.task and not existing.task.done():
                existing.task.cancel()
                logger.info(
                    f"[Validation] cancelled stale {slot_name} task "
                    f"(was: {existing.value_validated!r}, now: {value!r})"
                )

        tool_name = self.VALIDATOR_MAP[slot_name]
        entry = ValidationEntry(
            slot_name=slot_name,
            status=ValidationStatus.PENDING,
            value_validated=value,
            started_at=time.perf_counter(),
        )
        self._entries[slot_name] = entry

        async def _run() -> None:
            try:
                result = await self._execute_tool(
                    tool_name,
                    tool_args,
                    self._call_sid,
                    self._tenant_id,
                    conversation_state=self._state,
                )
                entry.completed_at = time.perf_counter()
                if isinstance(result, dict) and (
                    result.get("error") or result.get("status") == "failed"
                ):
                    entry.status = ValidationStatus.FAILED
                    entry.error = str(
                        result.get("error") or result.get("message") or "validation failed"
                    )
                else:
                    entry.status = ValidationStatus.VERIFIED
                    entry.result = result
                logger.info(
                    f"[Validation] {slot_name} → {entry.status.value} "
                    f"({entry.elapsed_ms}ms)"
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                entry.completed_at = time.perf_counter()
                entry.status = ValidationStatus.FAILED
                entry.error = str(exc)
                logger.warning(
                    f"[Validation] {slot_name} task crashed: {exc}"
                )

        entry.task = asyncio.create_task(_run())
        logger.info(
            f"[Validation] scheduled {slot_name}={value!r} (tool={tool_name})"
        )

    def mark_stale(self, slot_name: str) -> None:
        """Caller corrected a slot — force re-validation on next extraction."""
        e = self._entries.get(slot_name)
        if e:
            if e.task and not e.task.done():
                e.task.cancel()
            e.status = ValidationStatus.STALE
            logger.info(f"[Validation] {slot_name} marked STALE (caller correction)")

    async def wait_for(
        self, slot_name: str, timeout_s: float = 0.5
    ) -> Optional[ValidationEntry]:
        """
        If a validation is pending, wait up to timeout_s for it to finish.
        Used for the rare case where the bot reaches the confirmation turn
        before address validation completes.
        Never raises — returns whatever state we're in after timeout.
        """
        e = self._entries.get(slot_name)
        if e is None or e.task is None or e.task.done():
            return e
        try:
            await asyncio.wait_for(asyncio.shield(e.task), timeout=timeout_s)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
        return self._entries.get(slot_name)

    # ── Prompt formatting ─────────────────────────────────────────────────

    def summary_for_prompt_de(self) -> str:
        """German-language summary for LLM prompt injection."""
        if not self._entries:
            return "(keine Validierungen aktiv)"
        lines = []
        for name, e in self._entries.items():
            label = _SLOT_LABEL_DE.get(name, name)
            if e.status == ValidationStatus.VERIFIED:
                lines.append(f"- {label}: ✓ automatisch bestätigt")
            elif e.status == ValidationStatus.PENDING:
                lines.append(f"- {label}: ⏳ wird im Hintergrund geprüft")
            elif e.status == ValidationStatus.FAILED:
                lines.append(f"- {label}: ✗ Problem — {e.error or 'unbekannter Fehler'}")
            elif e.status == ValidationStatus.STALE:
                lines.append(f"- {label}: wird nach Korrektur neu geprüft")
        return "\n".join(lines) if lines else "(keine Validierungen aktiv)"

    def metrics_dict(self) -> dict:
        """Returns serializable metrics for google_turn_metrics JSONB field."""
        result = {}
        for name, e in self._entries.items():
            val_hash = (
                hashlib.md5((e.value_validated or "").encode()).hexdigest()[:8]
                if e.value_validated
                else None
            )
            result[name] = {
                "status": e.status.value,
                "elapsed_ms": e.elapsed_ms,
                "value_hash": val_hash,
            }
        return result

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def shutdown(self) -> None:
        """Cancel all pending background tasks. Call on call end."""
        cancelled = 0
        for e in self._entries.values():
            if e.task and not e.task.done():
                e.task.cancel()
                cancelled += 1
        if cancelled:
            logger.info(f"[Validation] shutdown: cancelled {cancelled} pending tasks")


# ── Backward-compat aliases ────────────────────────────────────────────────────
# Callers that do `from server.brain.validation_registry import ValidationRegistry`
# or `import ValidationStatus` continue to work unchanged (FINDING-016 fix:
# only the class *definition* is renamed; the public name stays the same).
ValidationRegistry = EagerSlotValidator
