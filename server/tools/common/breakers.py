"""
Per-tool circuit breakers — Phase 6 + Phase 9 (9.X4 breakers-everywhere).

Phase 9 B3: re-exports singletons from server.core.resilience.breakers,
which is now the canonical implementation.  This shim keeps Phase 6 callers
working without changes.
"""
from __future__ import annotations

# Re-export the canonical singletons and helpers
from server.core.resilience.breakers import (
    CircuitBreaker,
    BreakerOpenError,
    BreakerState,
    with_breaker,
    MAPS_BREAKER,
    TWILIO_BREAKER,
    WHATSAPP_BREAKER,
    SMS_BREAKER,
    GEMINI_BREAKER,
)

__all__ = [
    "CircuitBreaker",
    "BreakerOpenError",
    "BreakerState",
    "with_breaker",
    "MAPS_BREAKER",
    "TWILIO_BREAKER",
    "WHATSAPP_BREAKER",
    "SMS_BREAKER",
    "GEMINI_BREAKER",
]
