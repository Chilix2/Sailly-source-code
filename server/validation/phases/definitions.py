"""
Maps CLI phase letters to scenario directories under ``test-infra/caller-bot-v4/scenarios``.

Each phase folder holds YAML scenarios executed via ``simple_audio_bridge``.
"""

PHASE_SCENARIO_DIRS: dict[str, str] = {
    "a": "phase0",
    "b": "phase1",
    "c": "phase2",
    "d": "phase3",
    "e": "phase4",
    "f": "phase5",
    "g": "phase6",
    "h": "phase7",
    "i": "phase8",
}
