"""
FINDING-018 tests — CI vertical boundary guard script.

Verifies that verify_no_hardcoded_tenants.py:
  1. Imports and exposes a callable scan().
  2. Flags known forbidden tokens (DOBOO, dish names).
  3. Skips allowed paths (configs/tenants/, server/tests/, _backup_).
  4. Exits 1 on violations, 0 when clean.
  5. Is executable.
"""
from __future__ import annotations

import importlib
import stat
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).parents[3]  # sailly-browser-demo/
_SCRIPTS = _ROOT / "scripts"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _load_module():
    """Import verify_no_hardcoded_tenants fresh (avoids cached state)."""
    mod_path = str(_SCRIPTS)
    if mod_path not in sys.path:
        sys.path.insert(0, mod_path)
    if "verify_no_hardcoded_tenants" in sys.modules:
        del sys.modules["verify_no_hardcoded_tenants"]
    return importlib.import_module("verify_no_hardcoded_tenants")


# ---------------------------------------------------------------------------
# 1. Basic import and interface
# ---------------------------------------------------------------------------

def test_script_imports_cleanly():
    v = _load_module()
    assert callable(v.scan)
    assert callable(v.main)


def test_script_exposes_forbidden_patterns():
    v = _load_module()
    assert hasattr(v, "FORBIDDEN_PATTERNS")
    names = [name for name, _ in v.FORBIDDEN_PATTERNS]
    assert "DOBOO" in names
    assert "Bibimbap" in names
    assert "Mochi" in names


def test_script_is_executable():
    script = _SCRIPTS / "verify_no_hardcoded_tenants.py"
    assert script.exists(), "scripts/verify_no_hardcoded_tenants.py must exist"
    mode = script.stat().st_mode
    assert bool(mode & stat.S_IXUSR), "script must be user-executable"


# ---------------------------------------------------------------------------
# 2. Violation detection
# ---------------------------------------------------------------------------

def test_flags_doboo_token(tmp_path, monkeypatch):
    """Plant a DOBOO reference in a fake brain file — scan() must catch it."""
    v = _load_module()

    fake_brain = tmp_path / "brain"
    fake_brain.mkdir()
    # Use whitespace boundary so \bDOBOO\b matches (underscore is a word char)
    (fake_brain / "bad_module.py").write_text('TENANT = "DOBOO"\n')

    monkeypatch.setattr(v, "SCAN_DIRS", [str(fake_brain) + "/"])
    violations = v.scan(root=tmp_path)
    assert any("DOBOO" in viol for viol in violations), violations


def test_flags_bibimbap_token(tmp_path, monkeypatch):
    v = _load_module()

    fake_brain = tmp_path / "brain"
    fake_brain.mkdir()
    (fake_brain / "menu_helper.py").write_text('ITEM = "Bibimbap"\n')

    monkeypatch.setattr(v, "SCAN_DIRS", [str(fake_brain) + "/"])
    violations = v.scan(root=tmp_path)
    assert any("Bibimbap" in viol for viol in violations), violations


def test_flags_mochi_token(tmp_path, monkeypatch):
    """Mochi must be in FORBIDDEN_PATTERNS after PR-10 (was missing before)."""
    v = _load_module()

    fake_brain = tmp_path / "brain"
    fake_brain.mkdir()
    (fake_brain / "dessert.py").write_text('ITEM = "Mochi-Eis"\n')

    monkeypatch.setattr(v, "SCAN_DIRS", [str(fake_brain) + "/"])
    violations = v.scan(root=tmp_path)
    assert any("Mochi" in viol for viol in violations), violations


# ---------------------------------------------------------------------------
# 3. Allowed-path exclusion
# ---------------------------------------------------------------------------

def test_skips_configs_tenants(tmp_path, monkeypatch):
    """configs/tenants/ must be exempt — that IS where tenant content belongs."""
    v = _load_module()

    cfg = tmp_path / "configs" / "tenants"
    cfg.mkdir(parents=True)
    (cfg / "doboo.yaml").write_text("name: DOBOO\n")

    # scan only looks at Python files — yaml is skipped by suffix, but verify
    # the path exclusion works for .py too
    (cfg / "fixture.py").write_text('TENANT = "DOBOO"\n')

    fake_brain = tmp_path / "brain"
    fake_brain.mkdir()

    monkeypatch.setattr(v, "SCAN_DIRS", [str(fake_brain) + "/"])
    violations = v.scan(root=tmp_path)
    assert violations == [], violations


def test_skips_backup_dirs(tmp_path, monkeypatch):
    """Files under _backup_* dirs must not cause violations."""
    v = _load_module()

    fake_brain = tmp_path / "brain"
    fake_brain.mkdir()
    backup = fake_brain / "_backup_broken"
    backup.mkdir()
    (backup / "old.py").write_text('PLACE = "DOBOO"\n')

    monkeypatch.setattr(v, "SCAN_DIRS", [str(fake_brain) + "/"])
    violations = v.scan(root=tmp_path)
    assert violations == [], violations


def test_skips_comment_only_lines(tmp_path, monkeypatch):
    """Pure comment lines with forbidden tokens must be skipped."""
    v = _load_module()

    fake_brain = tmp_path / "brain"
    fake_brain.mkdir()
    (fake_brain / "ok.py").write_text("# This restaurant is DOBOO — comment only\n")

    monkeypatch.setattr(v, "SCAN_DIRS", [str(fake_brain) + "/"])
    violations = v.scan(root=tmp_path)
    assert violations == [], violations


def test_respects_suppress_annotation(tmp_path, monkeypatch):
    """Lines annotated with # tenant-specific fallback must be skipped."""
    v = _load_module()

    fake_brain = tmp_path / "brain"
    fake_brain.mkdir()
    (fake_brain / "ok2.py").write_text(
        'TENANT_ID = "DOBOO"  # tenant-specific fallback\n'
    )

    monkeypatch.setattr(v, "SCAN_DIRS", [str(fake_brain) + "/"])
    violations = v.scan(root=tmp_path)
    assert violations == [], violations


# ---------------------------------------------------------------------------
# 4. Exit-code integration
# ---------------------------------------------------------------------------

def test_main_returns_0_on_clean(tmp_path, monkeypatch):
    v = _load_module()
    fake_brain = tmp_path / "brain"
    fake_brain.mkdir()
    (fake_brain / "clean.py").write_text("x = 1\n")

    monkeypatch.setattr(v, "SCAN_DIRS", [str(fake_brain) + "/"])
    code = v.main(root=tmp_path)
    assert code == 0


def test_main_returns_1_on_violation(tmp_path, monkeypatch):
    v = _load_module()
    fake_brain = tmp_path / "brain"
    fake_brain.mkdir()
    (fake_brain / "bad.py").write_text('ITEM = "Bulgogi"\n')

    monkeypatch.setattr(v, "SCAN_DIRS", [str(fake_brain) + "/"])
    code = v.main(root=tmp_path)
    assert code == 1
