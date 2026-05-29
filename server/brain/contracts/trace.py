"""
Per-layer trace — populate the observability columns.

Phase 1: scaffolding only, no writes happen yet.
Phase 3 will wire this into the turn processor to capture layer-by-layer
decisions and filter changes for debugging and monitoring.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


# Span operation vocabulary — mirrors OpenTelemetry GenAI semantic conventions so
# the trace is portable to a real tracer later (chat / execute_tool / invoke_agent).
SPAN_OP_CLASSIFY = "classify"      # Layer 1: node selection / routing
SPAN_OP_PREREQ = "prereq"          # Layer 1: forced/prerequisite tools before LLM
SPAN_OP_CHAT = "chat"              # Layer 2: LLM generation (gen_ai.chat)
SPAN_OP_COMMIT_GATE = "commit_gate"  # Layer 1: code-driven forced commits
SPAN_OP_POLICY = "policy"          # Layer 3: validation/policy gating
SPAN_OP_EXECUTE_TOOL = "execute_tool"  # Layer 1: tool execution (gen_ai.execute_tool)


@dataclass
class ExecutionSpan:
    """One operation within a turn, OTel gen_ai-shaped.

    Times are milliseconds relative to the start of the turn (t0), so they are
    comparable across calls without absolute clock alignment. ``latency_ms`` is
    the wall time of the operation itself.
    """

    layer: int
    operation: str
    name: str
    t_start_ms: float
    t_end_ms: float
    status: str = "ok"  # ok | error | blocked
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    parent_span_id: Optional[str] = None
    model: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    finish_reason: Optional[str] = None
    io: Dict[str, Any] = field(default_factory=dict)

    @property
    def latency_ms(self) -> float:
        return round(self.t_end_ms - self.t_start_ms, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "layer": self.layer,
            "operation": self.operation,
            "name": self.name,
            "t_start_ms": round(self.t_start_ms, 2),
            "t_end_ms": round(self.t_end_ms, 2),
            "latency_ms": self.latency_ms,
            "status": self.status,
            "model": self.model,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "finish_reason": self.finish_reason,
            "io": self.io,
        }


class TurnSpanCollector:
    """Accumulates ExecutionSpans for a single turn.

    All methods are defensive (never raise into the hot path). Use ``mark()`` to
    grab a monotonic-derived relative timestamp, then ``add()`` to record a span.
    """

    def __init__(self, t0_monotonic: float):
        import time

        self._time = time.monotonic
        self._t0 = t0_monotonic
        self.spans: List[Dict[str, Any]] = []

    def now_ms(self) -> float:
        try:
            return (self._time() - self._t0) * 1000.0
        except Exception:
            return 0.0

    def add(
        self,
        layer: int,
        operation: str,
        name: str,
        t_start_ms: float,
        status: str = "ok",
        **kwargs: Any,
    ) -> None:
        try:
            span = ExecutionSpan(
                layer=layer,
                operation=operation,
                name=name,
                t_start_ms=t_start_ms,
                t_end_ms=self.now_ms(),
                status=status,
                **kwargs,
            )
            self.spans.append(span.to_dict())
        except Exception:
            # Observability must never break a live turn.
            pass


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
