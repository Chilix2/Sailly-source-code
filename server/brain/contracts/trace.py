"""
Per-layer trace — populate the observability columns.

Phase 1: scaffolding only, no writes happen yet.
Phase 3 will wire this into the turn processor to capture layer-by-layer
decisions and filter changes for debugging and monitoring.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class LayerTrace:
    """Observability data from each ExecutionLayer for a single turn."""

    turn_idx: int
    call_sid: str

    # Populated by Layer 1 (Orchestrator)
    layer1_node: str = ""
    layer1_forced_tools: List[str] = field(default_factory=list)
    layer1_state_hash: str = ""

    # Populated by Layer 2 (LLM)
    layer2_raw_output: str = ""
    layer2_latency_ms: int = 0
    layer2_input_tokens: int = 0
    layer2_output_tokens: int = 0

    # Populated by Layer 3 (Policy)
    layer3_warnings: List[Dict[str, Any]] = field(default_factory=list)
    layer3_text_changed: bool = False
    layer3_tools_changed: bool = False

    # Phase 5.5 — per-validator timing tile (per per-validator-tile decision)
    # Each entry: {"slot": "phone", "status": "verified", "duration_ms": 120, "retry": 0}
    validators_run: List[Dict[str, Any]] = field(default_factory=list)

    def to_db_row(self) -> Dict[str, Any]:
        """Serialise for INSERT into google_turn_metrics per-layer columns.
        
        Returns a dict suitable for **unpacking into the INSERT statement:
            INSERT INTO google_turn_metrics (..., layer1_decision, layer2_raw_output, layer3_changes)
            VALUES (..., %(layer1_decision)s, %(layer2_raw_output)s, %(layer3_changes)s)
        """
        return {
            "layer1_decision": {
                "node": self.layer1_node,
                "forced_tools": self.layer1_forced_tools,
                "state_hash": self.layer1_state_hash,
                "validators_run": self.validators_run,
            },
            "layer2_raw_output": self.layer2_raw_output,
            "layer3_changes": {
                "warnings": self.layer3_warnings,
                "text_changed": self.layer3_text_changed,
                "tools_changed": self.layer3_tools_changed,
            },
        }
