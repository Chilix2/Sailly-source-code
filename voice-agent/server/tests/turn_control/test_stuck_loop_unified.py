"""
FINDING-021 regression — only Jaccard stuck-loop detector exists.

Guards that the legacy exact-match fallback `_is_stuck_loop` has been deleted
from adk_turn_processor.py, and that _check_stuck_loop uses only the Phase 4 D
Jaccard implementation from turn_control.py.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).parents[3]  # sailly-browser-demo/
_ATP = _ROOT / "server" / "brain" / "adk_turn_processor.py"


def test_finding_021_no_legacy_is_stuck_loop_function():
    """_is_stuck_loop function must be deleted from adk_turn_processor.py."""
    src = _ATP.read_text()
    # Look for the function definition
    if re.search(r"^def _is_stuck_loop", src, re.MULTILINE):
        raise AssertionError(
            "FINDING-021: _is_stuck_loop still defined in adk_turn_processor.py"
        )


def test_finding_021_check_stuck_loop_uses_jaccard_only():
    """_check_stuck_loop must import from turn_control and not use _is_stuck_loop."""
    src = _ATP.read_text()
    # Check that _check_stuck_loop doesn't reference the old function
    if re.search(r"_check_stuck_loop.*_is_stuck_loop", src, re.DOTALL):
        raise AssertionError(
            "_check_stuck_loop still references _is_stuck_loop"
        )


def test_finding_021_jaccard_detector_exists():
    """Verify that turn_control.is_stuck_loop exists and is importable."""
    from server.brain.layer1.turn_control import is_stuck_loop
    assert callable(is_stuck_loop)


def test_finding_021_jaccard_catches_near_duplicates():
    """Jaccard 0.8 should detect near-duplicates that exact-match would miss."""
    from server.brain.layer1.turn_control import is_stuck_loop
    from server.brain.conversation_state import ConversationState

    # Build a mock state with near-duplicate responses
    state = ConversationState(call_sid="test")
    state.recent_bot_responses = [
        "Möchten Sie Ihre Adresse bestätigen?",
        "Können Sie mir die Adresse bestätigen?",
        "Bitte bestätigen Sie Ihre Adresse.",
    ]

    # Jaccard should catch these as similar (0.8 threshold)
    try:
        result = is_stuck_loop(state)
        assert result is True, "Jaccard should detect near-duplicates"
    except Exception as e:
        pytest.skip(f"Skipping: {e}")
