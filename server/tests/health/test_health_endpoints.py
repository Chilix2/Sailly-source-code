"""Tests for health endpoints (FINDING-031: router mounting)."""
import asyncio
import pytest
from fastapi.testclient import TestClient
from pathlib import Path


def test_health_handler_is_canonical():
    """Regression for FINDING-031: no inline /health in main.py."""
    src = Path("server/main.py").read_text()
    # Inline definitions should be gone
    assert '@app.get("/health")' not in src
    assert "@app.get('/health')" not in src
    # Router include should be present
    assert "health_router" in src or "include_router" in src


def test_liveness_function_is_used():
    """liveness() in health.py is the actual handler — not dead code."""
    from server.brain.health import liveness
    # The function exists and is awaitable
    result = asyncio.run(liveness())
    assert result["status"] == "alive"
    assert "service" in result


@pytest.mark.asyncio
async def test_readiness_has_checks():
    """readiness() checks all dependencies."""
    from fastapi import Response
    from server.brain.health import readiness
    
    response = Response()
    result = await readiness(response)
    assert "ready" in result
    assert "checks" in result
    assert isinstance(result["checks"], dict)
    assert "redis" in result["checks"]
    assert "postgres" in result["checks"]
    assert "gemini" in result["checks"]
    assert "deepgram" in result["checks"]


def test_router_defined_in_health():
    """health.py exports a router with both /health and /ready."""
    from server.brain.health import router
    # Router should be defined
    assert router is not None
    # Check that routes are registered
    assert any(route.path == "/health" for route in router.routes)
    assert any(route.path == "/ready" for route in router.routes)
