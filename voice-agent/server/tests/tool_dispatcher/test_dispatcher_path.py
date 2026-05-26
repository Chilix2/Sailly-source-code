"""
FINDING-028 regression — dispatcher at canonical path server/tools/dispatcher.py.

Guards that the dispatcher module is importable from the canonical path,
and that the deprecation shim at the old path works correctly.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import pytest

_ROOT = Path(__file__).parents[3]  # sailly-browser-demo/


def test_finding_028_dispatcher_at_canonical_path():
    """server/tools/dispatcher.py must exist and be importable."""
    from server.tools.dispatcher import (
        GATED_TOOLS_BASE,
        dispatch_with_validation,
        required_slots_for_tool,
    )
    assert callable(dispatch_with_validation)
    assert isinstance(GATED_TOOLS_BASE, dict)
    assert callable(required_slots_for_tool)


def test_finding_028_deprecation_shim_exists():
    """Deprecation shim at old path tools/dispatcher.py should exist."""
    shim = _ROOT / "tools" / "dispatcher.py"
    assert shim.exists(), f"Deprecation shim missing at {shim}"


def test_finding_028_shim_emits_deprecation_warning():
    """Importing from old path should emit DeprecationWarning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        from tools.dispatcher import dispatch_with_validation  # noqa: F401
        assert len(w) >= 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message).lower()


def test_finding_028_no_old_path_imports_in_codebase():
    """Production code should not import from tools.dispatcher (use server.tools)."""
    import re
    from pathlib import Path
    
    bad_files = []
    pattern = re.compile(r"from tools\.dispatcher|import tools\.dispatcher")
    
    for pyfile in (_ROOT / "server").rglob("*.py"):
        if "test_dispatcher_path" in pyfile.name or "__pycache__" in pyfile.parts:
            continue
        try:
            src = pyfile.read_text()
        except Exception:
            continue
        if pattern.search(src):
            bad_files.append(str(pyfile.relative_to(_ROOT)))
    
    assert bad_files == [], (
        f"FINDING-028: Old tools.dispatcher imports still in: {bad_files}"
    )
