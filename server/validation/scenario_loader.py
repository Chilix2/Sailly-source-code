"""Load YAML validation scenarios from test-infra/caller-bot-v4."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ValidationScenario:
    id: str
    phase: int
    description: str
    caller_goal: str
    caller_identity: dict[str, Any]
    caller_patience_turns: int
    tenant_id: str = "doboo"
    confirmation_phrases: list[str] = field(default_factory=list)
    expectations: dict[str, Any] = field(default_factory=dict)
    required_data: dict[str, Any] = field(default_factory=dict)  # slot answers pre-loaded for caller bot

    @property
    def bucket_name(self) -> Optional[str]:
        """Derive bucket name from expectations or phase."""
        exp = self.expectations or {}
        return exp.get("bucket") or None

    @property
    def expected_tools(self) -> list[str]:
        """Extract expected tools from expectations."""
        exp = self.expectations or {}
        return exp.get("tools", [])


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def scenarios_base_dir() -> Path:
    return repo_root() / "test-infra" / "caller-bot-v4" / "scenarios"


def load_scenario_file(path: Path) -> Optional[ValidationScenario]:
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.error("Failed to load %s: %s", path, e)
        return None
    if not data:
        return None
    caller_cfg = data.get("caller") or {}
    conf = caller_cfg.get("confirmation_phrases")
    if conf is None:
        conf = ["ja", "ja genau", "ja bitte", "passt so", "genau"]
    return ValidationScenario(
        id=data.get("id", path.stem),
        phase=int(data.get("phase", 0)),
        description=data.get("description", ""),
        caller_goal=caller_cfg.get("goal", ""),
        caller_identity=dict(caller_cfg.get("identity") or {}),
        caller_patience_turns=int(caller_cfg.get("patience_turns", 10)),
        tenant_id=data.get("tenant", "doboo"),
        confirmation_phrases=list(conf),
        expectations=dict(data.get("expectations") or {}),
    )


def load_scenarios_for_phase_folder(folder_name: str) -> list[ValidationScenario]:
    base = scenarios_base_dir() / folder_name
    if not base.is_dir():
        logger.warning("Scenario folder missing: %s", base)
        return []
    out: list[ValidationScenario] = []
    for yaml_file in sorted(base.rglob("*.yaml")):
        s = load_scenario_file(yaml_file)
        if s:
            out.append(s)
    return out
