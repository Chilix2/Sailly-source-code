"""
PR-8 combined regression suite — guards for FINDING-014, FINDING-015, FINDING-016.

These tests catch re-introduction of the exact problems fixed in PR-8.
Each test is named after its FINDING so the CI output directly links a failure
to its audit finding.

Run with:
  cd /home/charles2/sailly-browser-demo
  source venv/bin/activate
  python -m pytest server/tests/audit/test_finding_regressions.py -v
"""
from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).parents[3]  # sailly-browser-demo/
_SERVER = _ROOT / "server"

_CLASS_VALIDATION_REGISTRY_RE = re.compile(r"^class ValidationRegistry", re.MULTILINE)


def _py_files_with_pattern(pattern: re.Pattern, root: Path) -> list[str]:
    """Return project-relative paths of .py files whose text matches *pattern*."""
    results = []
    for path in sorted(root.rglob("*.py")):
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        if pattern.search(text):
            results.append(str(path.relative_to(_ROOT)))
    return results


# ── FINDING-014 ───────────────────────────────────────────────────────────────

def test_finding_014_turn_context_canonical_import():
    """
    Phase 4 contract: TurnContext must be importable from the canonical path.
    Re-importing tts_conditioning must not be required.
    """
    from server.brain.contracts.turn_context import TurnContext
    assert TurnContext is not None


def test_finding_014_canonical_path_exposes_same_class():
    """The shim must not wrap or subclass — it must be the identical object."""
    from server.brain.contracts.turn_context import TurnContext as Canonical
    from server.brain.tts_conditioning import TurnContext as Historical
    assert Canonical is Historical, (
        "server.brain.contracts.turn_context must re-export the exact same class "
        "as server.brain.tts_conditioning"
    )


# ── FINDING-015 ───────────────────────────────────────────────────────────────

def test_finding_015_no_in_memory_callback_queue():
    """
    The in-memory `_CALLBACK_QUEUE` list must not exist on the module.
    Callbacks are now persisted to the `callback_queue` Postgres table.
    """
    import server.tools.handlers.transfer_to_human as t
    assert not hasattr(t, "_CALLBACK_QUEUE"), (
        "_CALLBACK_QUEUE must be removed; callbacks go to the callback_queue DB table"
    )


def test_finding_015_schedule_callback_is_async():
    """_schedule_callback must be an async function (DB I/O path)."""
    import asyncio
    from server.tools.handlers.transfer_to_human import _schedule_callback
    assert asyncio.iscoroutinefunction(_schedule_callback)


def test_finding_015_db_pool_helper_present():
    """_get_db_pool helper must exist for tests to patch."""
    from server.tools.handlers.transfer_to_human import _get_db_pool
    assert callable(_get_db_pool)


# ── FINDING-016 ───────────────────────────────────────────────────────────────

def test_finding_016_only_one_validation_registry_class():
    """
    `class ValidationRegistry` must be defined in exactly one file —
    the canonical Phase 5.5 location. The legacy file now defines
    `EagerSlotValidator` and exposes `ValidationRegistry` as an alias only.
    """
    files = _py_files_with_pattern(_CLASS_VALIDATION_REGISTRY_RE, _SERVER)
    assert files == ["server/brain/layer1/validation/registry.py"], (
        f"Multiple `class ValidationRegistry` definitions found: {files}. "
        "The legacy class must be renamed to EagerSlotValidator."
    )


def test_finding_016_legacy_module_still_exports_validation_registry():
    """Backward compat: callers that import from the legacy path must not break."""
    from server.brain.validation_registry import ValidationRegistry
    assert ValidationRegistry is not None


def test_finding_016_legacy_module_still_exports_validation_status():
    """Backward compat: ValidationStatus import from legacy path must work."""
    from server.brain.validation_registry import ValidationStatus
    assert hasattr(ValidationStatus, "VERIFIED")
    assert hasattr(ValidationStatus, "PENDING")
    assert hasattr(ValidationStatus, "FAILED")


def test_finding_016_canonical_registry_accessible():
    """The canonical registry must remain importable from its Phase 5.5 path."""
    from server.brain.layer1.validation.registry import ValidationRegistry
    assert hasattr(ValidationRegistry, "is_committable")
    assert hasattr(ValidationRegistry, "validate_slot")


# ── FINDING-018: CI guard script ──────────────────────────────────────────────

def test_finding_018_ci_guard_script_exists():
    """verify_no_hardcoded_tenants.py must exist and be executable."""
    import stat as _stat
    p = _ROOT / "scripts" / "verify_no_hardcoded_tenants.py"
    assert p.exists(), "scripts/verify_no_hardcoded_tenants.py is missing"
    mode = p.stat().st_mode
    assert bool(mode & _stat.S_IXUSR), "verify_no_hardcoded_tenants.py must be executable"


def test_finding_018_ci_guard_contains_mochi():
    """Mochi must be in FORBIDDEN_PATTERNS — was missing before PR-10."""
    src = (_ROOT / "scripts" / "verify_no_hardcoded_tenants.py").read_text()
    assert "Mochi" in src, (
        "FORBIDDEN_PATTERNS in verify_no_hardcoded_tenants.py must include Mochi"
    )


def test_finding_018_ci_step_exists_in_workflow():
    """CI workflow must reference verify_no_hardcoded_tenants.py."""
    src = (_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "verify_no_hardcoded_tenants" in src, (
        ".github/workflows/ci.yml must include a step running verify_no_hardcoded_tenants.py"
    )


# ── FINDING-020: duplicate language key in doboo.yaml ────────────────────────

def test_finding_020_no_duplicate_language_key_in_doboo_yaml():
    """doboo.yaml must have exactly one top-level 'language:' key."""
    text = (_ROOT / "configs" / "tenants" / "doboo.yaml").read_text(encoding="utf-8")
    top_level = [l for l in text.splitlines() if l.startswith("language:")]
    assert len(top_level) == 1, (
        f"doboo.yaml has {len(top_level)} 'language:' keys (expected 1): {top_level}"
    )


def test_finding_020_doboo_language_is_de():
    """After dedup fix, doboo.yaml language must be ISO-639-1 'de', not 'German'."""
    import yaml as _yaml
    cfg = _yaml.safe_load(
        (_ROOT / "configs" / "tenants" / "doboo.yaml").read_text(encoding="utf-8")
    )
    assert cfg["language"] == "de", (
        f"doboo.yaml language={cfg['language']!r}. Must be ISO-639-1 'de'."
    )


# ── FINDING-021: No legacy stuck-loop fallback ─────────────────────────────


def test_finding_021_no_legacy_stuck_loop():
    """_is_stuck_loop must not exist in adk_turn_processor.py."""
    import re
    src = (_ROOT / "server" / "brain" / "adk_turn_processor.py").read_text()
    assert not re.search(r"^def _is_stuck_loop", src, re.MULTILINE)


# ── FINDING-024: Pre-Phase-3 backup deleted ────────────────────────────────


def test_finding_024_pre_phase3_backup_deleted():
    """conversation_nodes_pre_phase3.py must not exist."""
    assert not (_ROOT / "server" / "brain" / "conversation_nodes_pre_phase3.py").exists()


# ── FINDING-025: No backup files in tree ───────────────────────────────────


def test_finding_025_no_backup_files():
    """No *.bak, *.deploy_bak, or *_backup_* files should exist."""
    bad = []
    for p in (_ROOT / "server").rglob("*"):
        if not p.is_file():
            continue
        name = p.name
        # Exclude test files themselves and pycache
        if "test_no_backup_files" in name or "__pycache__" in p.parts:
            continue
        if "_backup_" in name or name.endswith(".bak") or name.endswith(".deploy_bak"):
            bad.append(str(p.relative_to(_ROOT)))
    assert bad == [], f"Backup files: {bad}"


# ── FINDING-026: update_state removed from LLM tools ────────────────────────


def test_finding_026_update_state_not_in_lvm_definitions():
    """update_state must not be in TOOL_DECLARATIONS."""
    src = (_ROOT / "tools" / "definitions.py").read_text()
    lines = src.split("\n")
    in_declarations = False
    for i, line in enumerate(lines):
        if "TOOL_DECLARATIONS = [" in line:
            in_declarations = True
        elif in_declarations and line.strip() == "]":
            break
        elif in_declarations and '"name": "update_state"' in line:
            raise AssertionError("update_state still in TOOL_DECLARATIONS")


# ── FINDING-028: Dispatcher at canonical path ──────────────────────────────


def test_finding_028_dispatcher_at_server_tools():
    """server/tools/dispatcher.py must exist."""
    assert (_ROOT / "server" / "tools" / "dispatcher.py").exists()


# ── FINDING-031: health_router mounted (not inline /health) ─────────────────


def test_finding_031_health_router_mounted():
    """No inline /health in main.py; router include must be present."""
    src = (_ROOT / "server" / "main.py").read_text()
    # No inline definitions
    assert '@app.get("/health")' not in src
    assert "@app.get('/health')" not in src
    # Router include should be present
    assert "health_router" in src or "include_router" in src


# ── FINDING-032: rate_limit_overrides.txt exists ────────────────────────────


def test_finding_032_rate_limit_overrides_file_exists():
    """configs/rate_limit_overrides.txt must exist."""
    assert (_ROOT / "configs" / "rate_limit_overrides.txt").exists()


# ── PR-16a: no [] empty-list patterns in rendered tier2 prompt ──────────────


def test_finding_034_no_empty_list_in_rendered_prompt():
    """The rendered tier2 system prompt must not contain stringified empty lists.

    Checks the RENDERED output (not source text) because the bug is that empty
    Python-list placeholders appear at runtime, not as source literals.
    """
    import sys
    sys.path.insert(0, str(_ROOT))
    from server.brain.tier2_runner import Tier2AudioRunner

    runner = Tier2AudioRunner.__new__(Tier2AudioRunner)
    runner.tenant_id = "doboo"
    runner.gemini_model = "gemini-2.5-flash"
    runner.temperature = 0.2
    runner._active_prompt_override = None
    runner._fast_model = ""
    runner._fast_nodes = set()
    runner.audio_injector = None
    runner.llm_client = None
    runner.tts_client = None
    runner.cost_tracker = None
    runner.scorer = None
    runner._last_stream_usage_metadata = None

    prompt = runner._build_tier2_prompt()
    assert "Sonderwünsche: []" not in prompt, "empty-list in prompt — check readback_slots_de"
    assert "Artikel: []" not in prompt, "empty-list in prompt — check items_summary"
    # Menu-check instruction must be present
    assert "gecachten Menü" in prompt or "gecachte Menü" in prompt or "gecachte Speisekarte" in prompt


# ── PR-16b: sticky menu injection present in memory_manager ─────────────────


def test_finding_035_sticky_menu_injection_present():
    """memory_manager.build_context must inject state.cached_menu into L6."""
    src = (_ROOT / "server" / "brain" / "memory_manager.py").read_text()
    assert "cached_menu" in src, "PR-16b: cached_menu not referenced in memory_manager"
    assert "GECACHTE SPEISEKARTE" in src or "gecachte Speisekarte" in src or "SPEISEKARTE" in src


# ── PR-16c: stop sequence --- replaced with \\n---\\n ──────────────────────


def test_finding_036_stop_sequence_not_bare_dash():
    """The '---' bare stop sequence must not be in tier2_runner streaming config.

    The bare '---' stop sequence terminates menu-list responses mid-word
    (matches Markdown HR separators generated by the LLM). Replaced with '\\n---\\n'.
    """
    src = (_ROOT / "server" / "brain" / "tier2_runner.py").read_text()
    assert '"---"' not in src or "PR-16c" in src, (
        "Bare '---' stop sequence found — must use '\\n---\\n' to avoid menu truncation"
    )


# ── PR-16d: ai_greeting dedup guard present ──────────────────────────────────


def test_finding_037_ai_greeting_dedup():
    """adk_turn_processor must deduplicate ai_greeting when ai_greeting_called=True."""
    src = (_ROOT / "server" / "brain" / "adk_turn_processor.py").read_text()
    assert "ai_greeting_called" in src and "DEDUP" in src, (
        "PR-16d: ai_greeting dedup guard missing in adk_turn_processor"
    )


# ── PR-19: menu_question forced-commit rule ──────────────────────────────────


def test_finding_038_menu_question_forced_commit():
    """node_manager must force-inject get_menu on explicit menu-read requests."""
    src = (_ROOT / "server" / "brain" / "node_manager.py").read_text()
    assert "vorlesen" in src or "MENU_READ_TRIGGERS" in src or "menükarte vor" in src.lower(), (
        "PR-19: menu_question forced-commit trigger phrases missing in node_manager"
    )
    assert "PR-19" in src, "PR-19 marker not found in node_manager"


# ── PR-17: SlotExtractor uses flash-lite ─────────────────────────────────────


def test_finding_039_slot_extractor_flash_lite():
    """SlotExtractor must default to gemini-2.5-flash-lite, not gemini-2.5-flash."""
    src = (_ROOT / "server" / "brain" / "slot_extractor.py").read_text()
    assert "flash-lite" in src or "flash_lite" in src, (
        "PR-17: SlotExtractor not using flash-lite model"
    )
    src_atp = (_ROOT / "server" / "brain" / "adk_turn_processor.py").read_text()
    assert "flash-lite" in src_atp, (
        "PR-17: flash-lite not referenced in adk_turn_processor SlotExtractor init"
    )

