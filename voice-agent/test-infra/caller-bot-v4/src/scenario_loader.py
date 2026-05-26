"""
src/scenario_loader.py — Load and parse YAML scenarios
"""
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Scenario:
    id: str
    phase: int
    description: str
    caller_goal: str
    caller_identity: dict
    caller_patience_turns: int
    caller_hesitation: str = "normal"
    confirmation_phrases: list[str] = None
    denial_phrases: list[str] = None
    expectations: dict = None
    release_thresholds: dict = None
    # Scripted mode: fixed utterances instead of LLM persona
    utterance_sequence: list[str] = None
    # Multi-call test support
    multi_call_test: bool = False
    repeat_calls: int = 1

    def __post_init__(self):
        if self.confirmation_phrases is None:
            self.confirmation_phrases = ["ja", "ja genau", "ja bitte", "passt so", "genau"]
        if self.denial_phrases is None:
            self.denial_phrases = ["nein", "nein so nicht", "nein das stimmt nicht", "warte"]
        if self.expectations is None:
            self.expectations = {}
        if self.release_thresholds is None:
            self.release_thresholds = {}
        if self.utterance_sequence is None:
            self.utterance_sequence = []


def load_scenario_file(path: Path) -> Optional[Scenario]:
    """Parse a single YAML scenario file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load {path}: {e}")
        return None

    if not data:
        return None

    # Extract caller block
    caller_cfg = data.get("caller", {})

    try:
        phase_val = int(data.get("phase", 0))
    except (ValueError, TypeError):
        phase_val = 99  # non-numeric phase (e.g. "bugfix") → put in high bucket
    return Scenario(
        id=data.get("id", path.stem),
        phase=phase_val,
        description=data.get("description", ""),
        caller_goal=caller_cfg.get("goal", ""),
        caller_identity=caller_cfg.get("identity", {}),
        caller_patience_turns=caller_cfg.get("patience_turns", 10),
        caller_hesitation=caller_cfg.get("hesitation", "normal"),
        confirmation_phrases=caller_cfg.get("confirmation_phrases", None),
        denial_phrases=caller_cfg.get("denial_phrases", None),
        expectations=data.get("expectations", {}),
        release_thresholds=data.get("release_thresholds", {}),
        utterance_sequence=[str(u) for u in caller_cfg.get("utterance_sequence", []) or []],
        multi_call_test=bool(caller_cfg.get("multi_call_test", False)),
        repeat_calls=int(caller_cfg.get("repeat_calls", 1)),
    )


def load_all_scenarios(scenarios_dir: Path) -> list[Scenario]:
    """Load all YAML scenario files from directory tree."""
    scenarios = []
    for yaml_file in sorted(scenarios_dir.rglob("*.yaml")):
        scenario = load_scenario_file(yaml_file)
        if scenario:
            scenarios.append(scenario)
    return scenarios


def get_scenarios_by_suite(scenarios: list[Scenario], suite: str) -> list[Scenario]:
    """Filter scenarios by suite preset."""
    if suite == "smoke":
        # Phase 0 + 1.1 + 2.1 + 7.1
        ids = [
            "phase0_test_0_1_greeting",
            "phase1_test_1_1_clean_reservation",
            "phase2_test_2_1_order_start",
            "phase7_test_7_1_clean_reservation",
        ]
        return [s for s in scenarios if s.id in ids]
    elif suite == "core":
        # All of Phase 0-7 (no safety, no observability, no messy)
        return [s for s in scenarios if s.phase <= 7]
    elif suite == "all":
        return scenarios
    else:
        return scenarios


def get_scenarios_by_phase(scenarios: list[Scenario], phase: int) -> list[Scenario]:
    """Filter scenarios by phase."""
    return [s for s in scenarios if s.phase == phase]
