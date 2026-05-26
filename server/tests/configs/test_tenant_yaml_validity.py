"""
FINDING-020 tests — Tenant YAML validity.

Guards that:
  1. No tenant YAML has duplicate keys at any level (would silently drop the
     first value in PyYAML's safe_load).
  2. doboo.yaml language key is exactly "de" (ISO-639-1) after the dedup fix.
  3. TenantConfig accepts the cleaned-up doboo.yaml without validation errors.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_ROOT = Path(__file__).parents[3]  # sailly-browser-demo/
_TENANTS_DIR = _ROOT / "configs" / "tenants"


# ---------------------------------------------------------------------------
# Custom YAML loader that raises on duplicate keys
# ---------------------------------------------------------------------------

class _UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that raises ConstructorError on duplicate keys at the same level."""


def _construct_mapping_unique(loader, node, deep=False):
    mapping: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None,
                None,
                f"Duplicate YAML key: {key!r}",
                key_node.start_mark,
            )
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping_unique,
)


# ---------------------------------------------------------------------------
# 1. No duplicates in any tenant YAML
# ---------------------------------------------------------------------------

def _all_tenant_yamls():
    if not _TENANTS_DIR.exists():
        return []
    return list(_TENANTS_DIR.glob("*.yaml")) + list(_TENANTS_DIR.glob("*.yml"))


@pytest.mark.parametrize("yaml_path", _all_tenant_yamls(), ids=lambda p: p.name)
def test_no_duplicate_keys_in_tenant_yaml(yaml_path):
    """
    Regression for FINDING-020: every tenant YAML must have unique keys at
    every nesting level.  PyYAML's safe_load silently ignores the first value
    when a key appears twice; this loader makes the ambiguity an error.
    """
    with open(yaml_path, encoding="utf-8") as f:
        try:
            yaml.load(f, Loader=_UniqueKeyLoader)
        except yaml.constructor.ConstructorError as exc:
            raise AssertionError(
                f"{yaml_path.name} has duplicate YAML keys:\n{exc}"
            ) from exc


# ---------------------------------------------------------------------------
# 2. doboo-specific assertions post-fix
# ---------------------------------------------------------------------------

def test_doboo_has_exactly_one_top_level_language_key():
    """After the dedup fix doboo.yaml must have exactly one 'language:' at top level."""
    text = (_TENANTS_DIR / "doboo.yaml").read_text(encoding="utf-8")
    top_level = [
        line for line in text.splitlines()
        if line.startswith("language:")
    ]
    assert len(top_level) == 1, (
        f"Expected 1 top-level 'language:' key, found {len(top_level)}: {top_level}"
    )


def test_doboo_language_is_iso639_code():
    """doboo.yaml must use ISO-639-1 'de', not the English word 'German'."""
    cfg = yaml.safe_load((_TENANTS_DIR / "doboo.yaml").read_text(encoding="utf-8"))
    assert cfg["language"] == "de", (
        f"Expected language='de', got {cfg['language']!r}. "
        "Use ISO-639-1 codes, not English language names."
    )


def test_doboo_locale_is_bcp47():
    """doboo.yaml locale must stay as BCP-47 'de-DE' (for TTS/STT)."""
    cfg = yaml.safe_load((_TENANTS_DIR / "doboo.yaml").read_text(encoding="utf-8"))
    assert cfg["locale"] == "de-DE"


# ---------------------------------------------------------------------------
# 3. TenantConfig loads cleaned YAML without Pydantic errors
# ---------------------------------------------------------------------------

def test_doboo_tenant_config_loads():
    """TenantConfig must accept the cleaned-up doboo.yaml."""
    from server.core.tenant_config import load_tenant_config
    cfg = load_tenant_config("doboo")
    assert cfg.tenant_id == "doboo"


def test_doboo_tenant_config_language_is_de():
    """After the fix, TenantConfig.language must be 'de'."""
    from server.core.tenant_config import load_tenant_config
    cfg = load_tenant_config("doboo")
    assert cfg.language == "de", (
        f"TenantConfig.language={cfg.language!r}, expected 'de'"
    )


def test_tenant_config_language_default_is_de():
    """TenantConfig.language default must now be 'de' (not 'German')."""
    from server.core.tenant_config import TenantConfig
    field_default = TenantConfig.model_fields["language"].default
    assert field_default == "de", (
        f"TenantConfig.language default is {field_default!r}, expected 'de'. "
        "Update the Field(default=...) if the YAML dedup fix changed the convention."
    )
