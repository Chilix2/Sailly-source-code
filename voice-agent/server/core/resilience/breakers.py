"""
Canonical circuit breaker implementation per decision breakers-everywhere (9.X4).

Every external API call (Maps, Twilio, WhatsApp, SMS, Gemini) is wrapped by
a singleton breaker.  When a breaker is OPEN, callers receive `BreakerOpenError`
immediately instead of waiting for a network timeout.

State machine:
    CLOSED  → normal operation
    OPEN    → all calls fail fast (after failure_threshold consecutive failures)
    HALF_OPEN → one trial call allowed; success → CLOSED, failure → OPEN

Usage:
    from server.core.resilience.breakers import MAPS_BREAKER, with_breaker, BreakerOpenError

    try:
        result = await with_breaker(MAPS_BREAKER, _call_maps_api(query))
    except BreakerOpenError:
        # Degrade gracefully
        return ToolResult(ok=False, error="maps unavailable", error_code=ErrorCode.MAPS_BREAKER_OPEN)

The Phase 6 stubs in server/tools/common/breakers.py import from here and
re-export the singletons for backward compatibility.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable

logger = logging.getLogger(__name__)


class BreakerState(str, Enum):
    CLOSED    = "closed"    # normal
    OPEN      = "open"      # fail fast
    HALF_OPEN = "half_open" # trial


class BreakerOpenError(Exception):
    """Raised when a call is attempted while the breaker is OPEN."""


@dataclass
class CircuitBreaker:
    """
    Thread-safe* circuit breaker for async Python.

    * Async Python is single-threaded per event loop; no lock needed for
      the state transitions because they happen synchronously between awaits.
    """
    name: str
    failure_threshold: int = 5        # consecutive failures to trip open
    success_threshold: int = 2        # consecutive successes to close from half-open
    timeout_seconds: int   = 30       # seconds to stay open before half-open probe

    # Mutable runtime state
    state: BreakerState = field(default=BreakerState.CLOSED, init=False)
    _consecutive_failures: int = field(default=0, init=False)
    _consecutive_successes: int = field(default=0, init=False)
    _opened_at: float = field(default=0.0, init=False)
    _total_trips: int = field(default=0, init=False)

    def can_attempt(self) -> bool:
        """Return True if a call should be attempted."""
        if self.state == BreakerState.CLOSED:
            return True
        if self.state == BreakerState.OPEN:
            if time.monotonic() - self._opened_at >= self.timeout_seconds:
                self.state = BreakerState.HALF_OPEN
                logger.info(
                    "circuit_breaker_half_open",
                    extra={"breaker": self.name, "trips": self._total_trips},
                )
                return True
            return False
        # HALF_OPEN — allow one probe
        return True

    def on_success(self) -> None:
        self._consecutive_failures = 0
        if self.state == BreakerState.HALF_OPEN:
            self._consecutive_successes += 1
            if self._consecutive_successes >= self.success_threshold:
                self.state = BreakerState.CLOSED
                self._consecutive_successes = 0
                logger.info(
                    "circuit_breaker_closed",
                    extra={"breaker": self.name},
                )

    def on_failure(self) -> None:
        self._consecutive_successes = 0
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            if self.state != BreakerState.OPEN:
                self.state = BreakerState.OPEN
                self._opened_at = time.monotonic()
                self._total_trips += 1
                logger.warning(
                    "circuit_breaker_opened",
                    extra={
                        "breaker": self.name,
                        "failures": self._consecutive_failures,
                        "trips": self._total_trips,
                    },
                )
                # Phase 9 A4 — fire Slack alert (non-blocking)
                try:
                    import asyncio as _asyncio
                    from server.brain.observability.alerts import alert_circuit_breaker_opened
                    _loop = _asyncio.get_event_loop()
                    if _loop and _loop.is_running():
                        _asyncio.ensure_future(
                            alert_circuit_breaker_opened(self.name, self._consecutive_failures)
                        )
                except Exception:
                    pass

    @property
    def is_open(self) -> bool:
        return self.state == BreakerState.OPEN

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(name={self.name!r}, state={self.state.value}, "
            f"failures={self._consecutive_failures}, trips={self._total_trips})"
        )


async def with_breaker(breaker: CircuitBreaker, coro: Awaitable[Any]) -> Any:
    """
    Execute `coro` guarded by `breaker`.

    Raises:
        BreakerOpenError: if the breaker is OPEN (fast-fail without executing coro).
        Any exception raised by coro: after recording a failure.
    """
    if not breaker.can_attempt():
        # Close the coroutine immediately to avoid "coroutine was never awaited" warnings.
        if hasattr(coro, "close"):
            coro.close()  # type: ignore[union-attr]
        raise BreakerOpenError(
            f"Circuit breaker '{breaker.name}' is OPEN — dependency unavailable"
        )
    try:
        result = await coro
        breaker.on_success()
        return result
    except BreakerOpenError:
        raise  # don't double-count
    except Exception:
        breaker.on_failure()
        raise


# ── Singletons (one per external dependency) ─────────────────────────────────

MAPS_BREAKER     = CircuitBreaker(name="maps",     failure_threshold=5, timeout_seconds=30)
TWILIO_BREAKER   = CircuitBreaker(name="twilio",   failure_threshold=5, timeout_seconds=30)
WHATSAPP_BREAKER = CircuitBreaker(name="whatsapp", failure_threshold=5, timeout_seconds=30)
SMS_BREAKER      = CircuitBreaker(name="sms",      failure_threshold=5, timeout_seconds=30)
GEMINI_BREAKER   = CircuitBreaker(name="gemini",   failure_threshold=3, timeout_seconds=60)
