"""Pytest configuration and dual-tenant fixtures for all tests."""

import pytest
from pathlib import Path
import sys

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from server.core.tenant_config import TenantConfig, get_tenant_registry


@pytest.fixture(params=["doboo", "pizzeria_napoli"])
def tenant_id(request):
    """Parametrised fixture providing both tenant IDs for all tests."""
    return request.param


@pytest.fixture
def ctx(tenant_id):
    """Load TenantConfig for the parametrised tenant."""
    registry = get_tenant_registry()
    try:
        return registry.load_tenant(tenant_id)
    except Exception as e:
        pytest.fail(f"Failed to load tenant config for {tenant_id}: {e}")


@pytest.fixture
def doboo_ctx():
    """Load DOBOO tenant config (non-parametrised)."""
    registry = get_tenant_registry()
    return registry.load_tenant("doboo")


@pytest.fixture
def pizzeria_ctx():
    """Load Pizzeria Napoli tenant config (non-parametrised)."""
    registry = get_tenant_registry()
    return registry.load_tenant("pizzeria_napoli")


def pytest_configure(config):
    """Configure pytest to register custom markers."""
    config.addinivalue_line("markers", "doboo: mark test to run only with DOBOO tenant")
    config.addinivalue_line("markers", "pizzeria: mark test to run only with Pizzeria tenant")
    config.addinivalue_line("markers", "dual_tenant: mark test to run with both tenants (default)")
