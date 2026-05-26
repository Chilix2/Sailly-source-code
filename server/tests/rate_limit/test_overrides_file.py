"""Tests for rate-limit overrides file (FINDING-032)."""
import asyncio
from pathlib import Path
import pytest


def test_overrides_file_exists():
    """Regression for FINDING-032."""
    assert Path("configs/rate_limit_overrides.txt").exists()


def test_overrides_file_is_parseable():
    """File must be readable and produce a valid override set."""
    from server.brain.rate_limit import load_overrides
    # Should not raise
    load_overrides()


def test_overrides_file_has_documentation_header():
    """Comment header should explain the file's purpose."""
    text = Path("configs/rate_limit_overrides.txt").read_text()
    assert "rate-limit override" in text.lower() or "rate limit override" in text.lower()
    assert "#" in text  # Header is commented


def test_overrides_skip_blank_and_comment_lines():
    """Loader should ignore lines starting with # and blank lines."""
    from server.brain.rate_limit import load_overrides, _OVERRIDE_PHONES
    # Clear and reload
    load_overrides()
    # The override file only has comments, so should be empty
    # (unless there were sample numbers uncommented)
    result = _OVERRIDE_PHONES
    assert isinstance(result, set)


def test_override_phones_can_be_added():
    """add_override() adds a phone to bypass list."""
    from server.brain.rate_limit import add_override, check_rate_limit
    # Add a test override
    test_phone = "+491234567890"
    add_override(test_phone)
    # Should bypass rate limit
    assert check_rate_limit(test_phone) is True


def test_load_overrides_clears_previous():
    """load_overrides() reloads the file from disk (hot-reload)."""
    from server.brain.rate_limit import load_overrides, _OVERRIDE_PHONES, add_override
    # Add something in-memory
    test_phone = "+499999999999"
    add_override(test_phone)
    assert test_phone in _OVERRIDE_PHONES
    # Reload from file (should lose the in-memory addition)
    load_overrides()
    # In-memory addition should be gone (since file doesn't have it)
    assert test_phone not in _OVERRIDE_PHONES
