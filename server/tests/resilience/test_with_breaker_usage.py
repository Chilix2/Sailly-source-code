"""
PR-1 regression guard — circuit breaker API consolidation.

Verifies:
  1. with_breaker passes through return value on success.
  2. with_breaker raises BreakerOpenError when the breaker is OPEN.
  3. verify_address.maps_lookup returns None when MAPS_BREAKER is open.
  4. No production file imports the dead `call_external` or `CircuitBreakerOpenError` names.

Run with:
  cd /home/charles2/sailly-browser-demo
  source venv/bin/activate
  python -m pytest server/tests/resilience/test_with_breaker_usage.py -v
"""
from __future__ import annotations

import subprocess
import sys

import pytest

from server.core.resilience import (
    BreakerOpenError,
    BreakerState,
    CircuitBreaker,
    MAPS_BREAKER,
    SMS_BREAKER,
    with_breaker,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset(breaker: CircuitBreaker) -> None:
    """Reset breaker to CLOSED state between tests."""
    breaker.state = BreakerState.CLOSED
    breaker._consecutive_failures = 0
    breaker._consecutive_successes = 0


# ---------------------------------------------------------------------------
# Test 1 — pass-through on success
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_with_breaker_passes_through_on_success():
    _reset(MAPS_BREAKER)

    async def successful_call():
        return {"ok": True}

    result = await with_breaker(MAPS_BREAKER, successful_call())
    assert result == {"ok": True}

    _reset(MAPS_BREAKER)


# ---------------------------------------------------------------------------
# Test 2 — raises BreakerOpenError when breaker is OPEN
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_with_breaker_raises_when_open():
    isolated = CircuitBreaker(name="test_isolated", failure_threshold=3, timeout_seconds=60)

    # Trip the breaker
    for _ in range(isolated.failure_threshold):
        isolated.on_failure()

    assert isolated.state == BreakerState.OPEN

    async def any_call():
        return "should not reach"

    with pytest.raises(BreakerOpenError):
        await with_breaker(isolated, any_call())


# ---------------------------------------------------------------------------
# Test 3 — maps_lookup returns None when MAPS_BREAKER is open
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_maps_lookup_returns_none_when_breaker_open():
    from server.tools.handlers.verify_address import maps_lookup

    # Use an isolated breaker to avoid affecting the shared MAPS_BREAKER singleton
    isolated = CircuitBreaker(name="maps_test_isolated", failure_threshold=3, timeout_seconds=60)
    for _ in range(isolated.failure_threshold):
        isolated.on_failure()
    assert isolated.state == BreakerState.OPEN

    # Patch MAPS_BREAKER in the handler's module
    import server.core.resilience.breakers as breakers_mod
    import server.tools.handlers.verify_address as va_mod

    original_maps = breakers_mod.MAPS_BREAKER
    breakers_mod.MAPS_BREAKER = isolated
    try:
        result = await maps_lookup("Friedrichstraße 20, Bonn")
        assert result is None, f"Expected None when breaker is open, got {result!r}"
    finally:
        breakers_mod.MAPS_BREAKER = original_maps


# ---------------------------------------------------------------------------
# Test 4 — regression guard: no dead imports remain in production code
# ---------------------------------------------------------------------------

def test_no_dead_imports_remain():
    """
    Ensure no production .py file imports call_external, CircuitBreakerOpenError,
    or references POS_BREAKER.

    Excludes:
      - venv/ (third-party packages)
      - This test file itself (contains the names in comments/strings)
    """
    result = subprocess.run(
        [
            sys.executable, "-c",
            (
                "import subprocess, sys\n"
                "r = subprocess.run(\n"
                "    ['grep', '-rn',\n"
                "     'call_external|CircuitBreakerOpenError|POS_BREAKER',\n"
                "     '--include=*.py',\n"
                "     '--exclude-dir=venv',\n"
                "     '--exclude-dir=__pycache__',\n"
                "     '.'],\n"
                "    capture_output=True, text=True,\n"
                "    cwd='/home/charles2/sailly-browser-demo'\n"
                ")\n"
                "print(r.stdout)\n"
            ),
        ],
        capture_output=True,
        text=True,
    )

    # grep -rn with | in pattern doesn't work — use Python to filter
    import os

    dead_patterns = ["call_external", "CircuitBreakerOpenError", "POS_BREAKER"]
    project_root = "/home/charles2/sailly-browser-demo"
    this_file = os.path.abspath(__file__)

    flagged: list[str] = []
    for dirpath, dirnames, filenames in os.walk(project_root):
        # Skip venv and pycache
        dirnames[:] = [d for d in dirnames if d not in {"venv", "__pycache__", ".git"}]
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            filepath = os.path.join(dirpath, fname)
            if os.path.abspath(filepath) == this_file:
                continue  # skip this guard file itself
            try:
                with open(filepath, encoding="utf-8", errors="ignore") as f:
                    for lineno, line in enumerate(f, 1):
                        # Skip comment-only lines
                        stripped = line.lstrip()
                        if stripped.startswith("#"):
                            continue
                        for pat in dead_patterns:
                            if pat in line:
                                flagged.append(f"{filepath}:{lineno}: {line.rstrip()}")
            except OSError:
                pass

    assert flagged == [], (
        "Dead circuit-breaker imports still present in production code:\n"
        + "\n".join(flagged)
    )
