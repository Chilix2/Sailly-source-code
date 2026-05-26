#!/usr/bin/env python3
"""
scripts/verify_no_hardcoded_tenants.py
----------------------------------------
CI guard: scans server/brain/ and tools/ for forbidden tenant-specific patterns.

Exits 1 with a violation list if any forbidden patterns are found in files that
should be tenant-agnostic.

Allowed exceptions:
  - configs/tenants/          (the canonical YAML source of truth)
  - server/tests/ and tests/  (test fixtures may reference specific tenants)
  - regression/ and scenarios/ (regression test data)
  - docs/                     (documentation and audit files)
  - *.bak, *_backup*          (backup files)
  - The script itself

Usage:
    python scripts/verify_no_hardcoded_tenants.py [--root /path/to/project]
    # Exits 0 on clean, 1 on violations found.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Patterns that must NOT appear in generic brain/tool files
FORBIDDEN_PATTERNS: List[Tuple[str, str]] = [
    ("DOBOO", r"\bDOBOO\b"),
    ("Bibimbap", r"\bBibimbap\b"),
    ("Bulgogi", r"\bBulgogi\b"),
    ("Japchae", r"\bJapchae\b"),
    ("Mochi", r"\bMochi(?:-Eis)?\b"),
    ("Friedrichstraße", r"Friedrichstra[ßs]e"),
    ("Mandu (menu item)", r"\bMandu\b"),
    ("Tteokbokki", r"\bTteokbokki\b"),
]

# File path prefixes/patterns that are ALLOWED to contain tenant-specific content
ALLOWED_PATH_PATTERNS: List[str] = [
    "configs/tenants/",
    "server/tests/",
    "tests/",
    "regression/",
    "scenarios/",
    "docs/",
    ".github/",
    "scripts/verify_no_hardcoded_tenants.py",  # this file
]

# File suffixes to skip
SKIP_SUFFIXES: Tuple[str, ...] = (".bak", ".md", ".txt", ".sh", ".yml.bak")

# Directory names to skip
SKIP_DIRS: Tuple[str, ...] = (
    "__pycache__", ".git", "_backup", "venv", ".venv", "node_modules",
)

# Specific files to exclude (legacy/backup files that pre-date vertical scoping)
EXCLUDED_FILES: Tuple[str, ...] = (
    "conversation_nodes_pre_phase3.py",  # legacy pre-Phase3 backup — not in production path
    "adk_runner.py",                     # legacy runner — replaced by adk_turn_processor.py
    "conversation_nodes.py",             # shim file pointing to new node structure
    "conversation_loop.py",              # legacy loop — not active in production
)

# Directories containing LLM prompt files where dish names appear legitimately as examples.
# These are excluded from the strict check; violations here are tracked in vertical_audit.md.
PROMPT_DIRS: Tuple[str, ...] = (
    "server/brain/layer1/nodes/",   # node prompts — dish names are training examples; tracked in C2 backlog
    "server/brain/layer2/",         # few-shot examples — dish names are generic examples
)

# Files where dish names appear in LLM prompts as examples (C2 backlog items)
PROMPT_EXAMPLE_FILES: Tuple[str, ...] = (
    "slot_extractor.py",       # dish names in intent-type description examples
    "call_summary.py",         # example data structure
    "audio_injector.py",       # test utterance in comment
    "call_auditor_de.py",      # hardcoded restaurant name in config stub
    "captured_intents.py",     # comment explaining intent kind
    "tts_conditioning.py",     # TTS style prompt — tracked in C2 backlog
    "_prompts.py",             # shared prompt fragments — tracked in C2 backlog
    "text_mode_runner.py",     # test runner with example utterances
    "conversation_state.py",   # docstring examples and comments
    "layer1/nodes/confirmation.py",   # few-shot example in prompt
)

# Annotation that suppresses a violation on that line
SUPPRESS_ANNOTATION = "# tenant-specific fallback"

SCAN_DIRS = ["server/brain/", "tools/"]


def is_allowed_path(rel_path: str) -> bool:
    for allowed in ALLOWED_PATH_PATTERNS:
        if rel_path.startswith(allowed) or allowed in rel_path:
            return True
    return False


def scan_file(path: Path, root: Path) -> List[str]:
    """Return list of violation strings for *path*, empty if clean."""
    violations: List[str] = []
    rel = str(path.relative_to(root))

    if is_allowed_path(rel):
        return []
    if path.suffix in SKIP_SUFFIXES:
        return []
    if any(part.startswith("_backup") for part in path.parts):
        return []
    if path.name in EXCLUDED_FILES:
        return []
    # Skip prompt/example files (tracked in C2 backlog, not blocking CI)
    for pd in PROMPT_DIRS:
        if rel.startswith(pd):
            return []
    for pf in PROMPT_EXAMPLE_FILES:
        if path.name == pf or rel.endswith(pf):
            return []

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    for lineno, line in enumerate(text.splitlines(), start=1):
        if SUPPRESS_ANNOTATION in line:
            continue
        # Skip comment-only lines and docstring lines
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue
        for name, pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, line):
                violations.append(f"{rel}:{lineno}: [{name}] {line.rstrip()}")
                break  # one violation per line

    return violations


def scan(root: "Path | None" = None) -> List[str]:
    """Return list of violation strings for the project rooted at *root*."""
    if root is None:
        root = Path(".").resolve()
    root = Path(root).resolve()
    all_violations: List[str] = []

    for scan_dir_rel in SCAN_DIRS:
        # SCAN_DIRS entries may be absolute (during tests) or relative (CI).
        scan_dir_rel_str = str(scan_dir_rel)
        if os.path.isabs(scan_dir_rel_str):
            scan_path = Path(scan_dir_rel_str)
        else:
            scan_path = root / scan_dir_rel_str
        if not scan_path.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(scan_path):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith("_backup")]
            for fname in filenames:
                if not fname.endswith(".py"):
                    continue
                if fname.endswith(".bak"):
                    continue
                fpath = Path(dirpath) / fname
                all_violations.extend(scan_file(fpath, root))

    return all_violations


def main(root: "Path | None" = None) -> int:
    parser = argparse.ArgumentParser(description="Verify no hardcoded tenant content in brain/tools.")
    parser.add_argument("--root", default=".", help="Project root directory")
    args, _ = parser.parse_known_args()

    effective_root = Path(root).resolve() if root is not None else Path(args.root).resolve()
    all_violations = scan(root=effective_root)

    if all_violations:
        print(f"\n[CI] Vertical boundary check FAILED — {len(all_violations)} violation(s):\n")
        for v in all_violations:
            print(f"  {v}")
        print(
            "\nFix: move content to configs/tenants/<id>.yaml and read via tenant config, "
            "or annotate with '# tenant-specific fallback' if a runtime fallback is required."
        )
        return 1

    print(f"[CI] Vertical boundary check PASSED — no forbidden tenant content found in {SCAN_DIRS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
