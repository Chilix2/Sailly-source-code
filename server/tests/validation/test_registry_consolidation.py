"""
PR-8 Part C tests — ValidationRegistry consolidation (FINDING-016).

Verifies:
  1. Only ONE file defines `class ValidationRegistry` (the canonical one).
  2. The legacy module still exports `ValidationRegistry` and `ValidationStatus`
     as backward-compat aliases so existing callers don't break.
  3. The renamed legacy class is `EagerSlotValidator`.
  4. The canonical registry is accessible from the canonical path.

Run with:
  cd /home/charles2/sailly-browser-demo
  source venv/bin/activate
  python -m pytest server/tests/validation/test_registry_consolidation.py -v
"""
from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).parents[3]  # /home/.../sailly-browser-demo
_SERVER = _ROOT / "server"

_CLASS_RE = re.compile(r"^class ValidationRegistry", re.MULTILINE)
_EAGER_RE = re.compile(r"^class EagerSlotValidator", re.MULTILINE)


def _py_files_with_class(pattern: re.Pattern, root: Path) -> list[str]:
    """Return relative paths of .py files whose text matches *pattern*."""
    matches = []
    for path in sorted(root.rglob("*.py")):
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        if pattern.search(text):
            matches.append(str(path.relative_to(_ROOT)))
    return matches


class TestSingleClassDefinition:

    def test_only_canonical_file_has_class_validationregistry(self):
        """
        Regression: `class ValidationRegistry` definition must exist in
        exactly one file — the canonical Phase 5.5 location.

        The legacy `server/brain/validation_registry.py` was renamed to
        EagerSlotValidator (FINDING-016). This test will catch any future
        reintroduction of a duplicate class definition.
        """
        files = _py_files_with_class(_CLASS_RE, _SERVER)
        assert files == ["server/brain/layer1/validation/registry.py"], (
            f"Expected only canonical registry; got: {files}"
        )

    def test_legacy_class_renamed_to_eager_slot_validator(self):
        """The legacy class must be EagerSlotValidator, not ValidationRegistry."""
        from server.brain.validation_registry import EagerSlotValidator
        assert EagerSlotValidator is not None
        assert EagerSlotValidator.__name__ == "EagerSlotValidator"

    def test_legacy_file_class_definition_is_not_validation_registry(self):
        """Direct check: the class keyword in legacy file uses EagerSlotValidator."""
        legacy_text = (_ROOT / "server/brain/validation_registry.py").read_text()
        assert _EAGER_RE.search(legacy_text), (
            "EagerSlotValidator class definition not found in legacy file"
        )
        assert not _CLASS_RE.search(legacy_text), (
            "class ValidationRegistry still present in legacy file — rename it"
        )


class TestBackwardCompatAliases:

    def test_legacy_module_exports_validation_registry_alias(self):
        """Existing callers using `from server.brain.validation_registry import ValidationRegistry`."""
        from server.brain.validation_registry import ValidationRegistry
        assert ValidationRegistry is not None

    def test_legacy_module_exports_validation_status(self):
        """Existing callers using `from server.brain.validation_registry import ValidationStatus`."""
        from server.brain.validation_registry import ValidationStatus
        assert ValidationStatus is not None
        # Verify it's the same enum as defined in the legacy module
        assert hasattr(ValidationStatus, "VERIFIED")
        assert hasattr(ValidationStatus, "PENDING")
        assert hasattr(ValidationStatus, "FAILED")

    def test_validation_registry_alias_points_to_eager_slot_validator(self):
        """The alias and the renamed class must be the same object."""
        from server.brain.validation_registry import (
            EagerSlotValidator,
            ValidationRegistry,
        )
        assert ValidationRegistry is EagerSlotValidator

    def test_validation_registry_is_not_canonical_registry(self):
        """
        The legacy alias must NOT point to the canonical registry — they have
        different APIs and different constructors.
        """
        from server.brain.validation_registry import ValidationRegistry as Legacy
        from server.brain.layer1.validation.registry import ValidationRegistry as Canonical
        assert Legacy is not Canonical


class TestCanonicalRegistryUnchanged:

    def test_canonical_registry_importable(self):
        from server.brain.layer1.validation.registry import ValidationRegistry
        assert ValidationRegistry is not None

    def test_canonical_registry_has_is_committable(self):
        """The gate-all API must still be present."""
        from server.brain.layer1.validation.registry import ValidationRegistry
        assert hasattr(ValidationRegistry, "is_committable")

    def test_canonical_registry_has_validate_slot(self):
        from server.brain.layer1.validation.registry import ValidationRegistry
        assert hasattr(ValidationRegistry, "validate_slot")

    def test_canonical_validation_status_imported_from_canonical(self):
        from server.brain.layer1.validation.registry import ValidationStatus
        assert hasattr(ValidationStatus, "VERIFIED")
        assert hasattr(ValidationStatus, "UNVALIDATED")  # canonical-only status
