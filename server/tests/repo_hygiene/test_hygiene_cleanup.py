"""
Repository hygiene tests for FINDING-024 and FINDING-025.

Guards that backup files don't accumulate in the source tree.
"""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).parents[3]  # sailly-browser-demo/


def test_finding_024_pre_phase3_backup_deleted():
    """conversation_nodes_pre_phase3.py must be deleted (FINDING-024)."""
    stale_file = _ROOT / "server" / "brain" / "conversation_nodes_pre_phase3.py"
    assert not stale_file.exists(), (
        f"FINDING-024: {stale_file} should be deleted"
    )


def test_finding_025_no_backup_files_in_server():
    """No *.bak, *.deploy_bak, or *_backup_* files should exist in server/."""
    bad = []
    for p in (_ROOT / "server").rglob("*"):
        if not p.is_file():
            continue
        name = p.name
        # Skip test files and cache
        if "test" in p.parts or "__pycache__" in p.parts:
            continue
        if "_backup_" in name or name.endswith(".bak") or name.endswith(".deploy_bak"):
            bad.append(str(p.relative_to(_ROOT)))
    assert bad == [], f"Backup files: {bad}"


def test_finding_025_gitignore_updated():
    """`.gitignore` must exclude backup patterns."""
    gitignore = (_ROOT / ".gitignore").read_text()
    patterns = ["*.bak", "*.deploy_bak", "*_backup_*"]
    for pattern in patterns:
        assert pattern in gitignore, (
            f".gitignore must include '{pattern}' pattern"
        )
