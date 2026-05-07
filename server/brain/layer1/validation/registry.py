"""
ValidationRegistry — owns per-call validator state.

Per Phase 5.5 decisions:
  - eager-keep: validators run when slot is FILLED, not when tool is dispatched
  - filled-and-confirmed: tool may fire only when slot status = CONFIRMED
                          and validator status = VERIFIED
  - log-only: validator failures log; bot does not surface "validation failed"
              verbatim to caller
  - retry-1x: one silent retry on transient (network) failure, then FAILED
  - stale-and-revalidate: caller correction downgrades CONFIRMED to STALE;
                          registry re-runs validator on next fill
  - gate-all: dispatcher consults registry before firing every state-mutating tool
  - per-call-cache: validator results live for this call only (key by slot+value)
  - per-validator-tile: each invocation emits start/result/error to layer1_decision
  - pattern-checklist: new validators follow documented contract

This is Layer 1 territory — pure code, deterministic, no LLM calls.
Validators may make external calls (Maps API, phone-format service) but
their internal logic is rule-based.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ValidationStatus(str, Enum):
    UNVALIDATED = "unvalidated"  # slot exists, validator hasn't run
    PENDING = "pending"           # validator is running
    VERIFIED = "verified"         # validator passed
    FAILED = "failed"             # validator returned negative result
    STALE = "stale"               # caller corrected the slot; needs re-run
    ERROR = "error"               # validator raised an exception (transient)


@dataclass
class ValidationResult:
    status: ValidationStatus
    detail: str = ""
    enriched_data: dict = field(default_factory=dict)  # canonical/normalized form
    validator_name: str = ""
    duration_ms: int = 0
    retry_count: int = 0


@dataclass
class ValidationEntry:
    """One slot's validation state across the call."""
    slot_path: str            # e.g. "intent[0].address"
    last_value: Optional[str]
    result: ValidationResult
    last_run_at: float = 0.0


# Type alias: validator(value, tenant_cfg, ctx) -> ValidationResult
Validator = Callable[[str, dict, "ValidationContext"], Awaitable[ValidationResult]]


@dataclass
class ValidationContext:
    """Read-only snapshot validators may use."""
    tenant_id: str
    call_sid: str
    turn_idx: int
    tenant_cfg: dict


class ValidationRegistry:
    """
    Per-call registry. One instance per ConversationState.

    Validators are registered by slot-name once at startup (idempotent).
    `validate_slot` is invoked by the extractor merge step on FILLED slots.
    `is_committable` is invoked by the dispatcher before state-mutating tools fire.
    """

    def __init__(self, ctx: ValidationContext):
        self._ctx = ctx
        self._validators: Dict[str, Validator] = {}
        self._entries: Dict[str, ValidationEntry] = {}
        self._cache: Dict[str, ValidationResult] = {}  # per-call-cache key: slot::value
        self._trace_writer: Optional[Callable[[dict], None]] = None

    def register(self, slot_name: str, validator: Validator) -> None:
        """Idempotent. Called once at startup by `register_default_validators`."""
        if slot_name in self._validators:
            return
        self._validators[slot_name] = validator

    def attach_trace_writer(self, writer: Callable[[dict], None]) -> None:
        """Layer 1 trace adapter; receives per-validator events for observability."""
        self._trace_writer = writer

    async def validate_slot(
        self, slot_path: str, slot_name: str, value: str
    ) -> ValidationResult:
        """
        Run validator for this slot. Cached by (slot_name, value) for the call.
        Per decisions: retry-1x on ERROR, log-only on FAILED, per-call-cache.
        """
        cache_key = f"{slot_name}::{value}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            self._emit_trace({
                "event": "validator_cache_hit",
                "slot": slot_name,
                "status": cached.status.value,
            })
            return cached

        validator = self._validators.get(slot_name)
        if validator is None:
            return ValidationResult(
                status=ValidationStatus.UNVALIDATED,
                detail=f"no validator registered for {slot_name}",
                validator_name="",
            )

        # Mark PENDING so concurrent reads see it
        self._entries[slot_path] = ValidationEntry(
            slot_path=slot_path,
            last_value=value,
            result=ValidationResult(
                status=ValidationStatus.PENDING,
                validator_name=slot_name,
            ),
            last_run_at=time.time(),
        )
        self._emit_trace({
            "event": "validator_start",
            "slot": slot_name,
            "value_hash": _hash_short(value),
        })

        # Run with one retry on ERROR (per retry-1x)
        for attempt in range(2):
            start = time.monotonic()
            try:
                result = await validator(value, self._ctx.tenant_cfg, self._ctx)
                result.duration_ms = int((time.monotonic() - start) * 1000)
                result.validator_name = slot_name
                result.retry_count = attempt

                self._cache[cache_key] = result
                self._entries[slot_path] = ValidationEntry(
                    slot_path=slot_path,
                    last_value=value,
                    result=result,
                    last_run_at=time.time(),
                )
                self._emit_trace({
                    "event": "validator_completed",
                    "slot": slot_name,
                    "status": result.status.value,
                    "duration_ms": result.duration_ms,
                    "retry": attempt,
                })
                if result.status == ValidationStatus.FAILED:
                    logger.info(
                        "validator_failed",
                        extra={
                            "slot": slot_name,
                            "detail": result.detail[:200],
                        },
                    )
                return result

            except Exception as e:
                logger.warning(
                    "validator_raised",
                    extra={
                        "slot": slot_name,
                        "attempt": attempt,
                        "error": str(e)[:200],
                    },
                )
                if attempt == 1:
                    duration_ms = int((time.monotonic() - start) * 1000)
                    result = ValidationResult(
                        status=ValidationStatus.ERROR,
                        detail=str(e)[:200],
                        validator_name=slot_name,
                        retry_count=2,
                        duration_ms=duration_ms,
                    )
                    self._cache[cache_key] = result
                    self._entries[slot_path] = ValidationEntry(
                        slot_path=slot_path,
                        last_value=value,
                        result=result,
                        last_run_at=time.time(),
                    )
                    self._emit_trace({
                        "event": "validator_error",
                        "slot": slot_name,
                        "error": result.detail,
                        "duration_ms": duration_ms,
                    })
                    return result
                # First failure → backoff and retry
                await asyncio.sleep(0.2)

    def mark_stale(self, slot_path: str) -> None:
        """
        Per stale-and-revalidate: caller correction downgrades validation.
        Called by the negation rule (Phase 4 Stream C) when a CONFIRMED slot
        is overwritten by a correction.
        """
        if slot_path not in self._entries:
            return
        entry = self._entries[slot_path]
        old_validator_name = entry.result.validator_name
        entry.result = ValidationResult(
            status=ValidationStatus.STALE,
            detail="superseded by correction",
            validator_name=old_validator_name,
        )
        # Drop cache so re-validation runs on next fill
        cache_key = f"{old_validator_name}::{entry.last_value}"
        self._cache.pop(cache_key, None)
        self._emit_trace({
            "event": "validator_marked_stale",
            "slot": old_validator_name,
        })

    def get_status(self, slot_path: str) -> ValidationStatus:
        entry = self._entries.get(slot_path)
        if entry is None:
            return ValidationStatus.UNVALIDATED
        return entry.result.status

    def get_enriched(self, slot_path: str) -> dict:
        """Returns validator's canonical/normalized data, or empty dict."""
        entry = self._entries.get(slot_path)
        if entry is None:
            return {}
        return entry.result.enriched_data

    def is_committable(self, slot_paths: List[str]) -> bool:
        """
        Per filled-and-confirmed + gate-all: all required slot paths must
        currently be VERIFIED. Tool dispatcher uses this before firing.
        """
        return all(
            self.get_status(p) == ValidationStatus.VERIFIED for p in slot_paths
        )

    def snapshot_for_prompt(self) -> Dict[str, dict]:
        """
        Render snapshot for PromptSlot.L4 (validation indicators in main LLM prompt).
        Per `l4-verified-and-pending`, FAILED is hidden — bot handles failure
        in the response itself.
        """
        return {
            entry.slot_path: {
                "status": entry.result.status.value,
                "detail": entry.result.detail[:80],
            }
            for entry in self._entries.values()
        }

    def _emit_trace(self, event: dict) -> None:
        event["call_sid"] = self._ctx.call_sid
        event["turn_idx"] = self._ctx.turn_idx
        if self._trace_writer:
            self._trace_writer(event)


def _hash_short(value: str) -> str:
    """8-char hash for trace events; never log raw PII values."""
    import hashlib
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
