"""
Layer 1 persistence helpers — serialize LayerTrace and TurnTimings for DB.

Phase 5.5: `serialize_layer_trace` includes the `validators_run` tile so
per-validator timing data appears in `google_turn_metrics.layer1_decision`.

Phase 9 A1: `build_turn_metrics_extra` reads a TurnTimings accumulator
from the state and merges per-stage latency + token + cost columns into a
dict suitable for merging into the `to_db_row()` payload written by
adk_turn_processor.
"""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from server.brain.contracts.trace import LayerTrace
    from server.brain.conversation_state import ConversationState


def serialize_layer_trace(trace: "LayerTrace") -> dict[str, Any]:
    """
    Serialize a LayerTrace to a JSON-safe dict for the layer1_decision column.

    Matches the shape expected by the to_db_row() contract but allows callers
    to customise or extend the dict before insertion.
    """
    return {
        "node": trace.layer1_node,
        "forced_tools": trace.layer1_forced_tools,
        "state_hash": trace.layer1_state_hash,
        "validators_run": trace.validators_run,
    }


def build_turn_metrics_extra(state: "ConversationState") -> dict[str, Any]:
    """
    Build per-stage latency, token-count, and cost columns from the TurnTimings
    accumulator stored on `state._turn_timings`.

    Returns an empty dict if no timings accumulator exists (back-compat: rows
    written before Phase 9 will have NULLs for these columns).

    Usage (in adk_turn_processor after generating the turn row):

        row = state.to_db_row()
        row.update(build_turn_metrics_extra(state))
        await db.insert("google_turn_metrics", row)
    """
    timings = getattr(state, "_turn_timings", None)
    if timings is None:
        return {}

    metrics = timings.to_metrics_dict()

    # Compute cost if token counts are available
    if metrics.get("prompt_tokens_in") or metrics.get("extract_tokens_in"):
        from server.brain.observability.cost import calc_turn_cost_eur
        metrics["cost_eur"] = calc_turn_cost_eur(
            prompt_in=metrics.get("prompt_tokens_in") or 0,
            prompt_out=metrics.get("prompt_tokens_out") or 0,
            extract_in=metrics.get("extract_tokens_in") or 0,
            extract_out=metrics.get("extract_tokens_out") or 0,
        )

    return {k: v for k, v in metrics.items() if v is not None}
