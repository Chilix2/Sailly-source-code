"""
Tests for FINDING-014 fix — TurnContext canonical import path.

Run with:
  cd /home/charles2/sailly-browser-demo
  source venv/bin/activate
  python -m pytest server/tests/contracts/test_turn_context_shim.py -v
"""


def test_turn_context_importable_from_canonical_path():
    """Phase 4 contract: TurnContext must be importable from the canonical path."""
    from server.brain.contracts.turn_context import TurnContext
    assert TurnContext is not None


def test_turn_context_is_same_class_from_either_path():
    """Shim must expose the exact same class, not a copy or subclass."""
    from server.brain.contracts.turn_context import TurnContext as Canonical
    from server.brain.tts_conditioning import TurnContext as Legacy
    assert Canonical is Legacy  # identity, not just equality


def test_turn_context_canonical_path_in_all_list():
    """__all__ must list TurnContext so star-imports work correctly."""
    import server.brain.contracts.turn_context as module
    assert "TurnContext" in module.__all__
