"""
Regression guard for the LayerTrace persistence path.

Root cause this guards against: the live processor is ADKTurnProcessor, but the
``_current_layer_trace`` attribute + population logic originally lived only in the
unused V4TurnProcessor. brain_service reads ``_tp._current_layer_trace`` during
metrics accumulation, so when ADKTurnProcessor never set it, the
``layer1_decision`` / ``layer2_raw_output`` / ``layer3_changes`` columns in
google_turn_metrics stayed NULL across every row.

These tests lock in:
  1. The LayerTrace -> DB row contract (keys the INSERT relies on).
  2. ADKTurnProcessor exposing/initialising ``_current_layer_trace`` (the live seam).
"""
from __future__ import annotations


def test_layer_trace_to_db_row_contract():
    """to_db_row must emit exactly the 3 columns the INSERT statements unpack."""
    from server.brain.contracts.trace import LayerTrace

    trace = LayerTrace(turn_idx=2, call_sid="test-sid")
    trace.layer1_node = "order_start"
    trace.layer1_forced_tools = ["create_order"]
    trace.layer1_state_hash = "abc123"
    trace.layer2_raw_output = "[TOOL:create_order] Alles klar"
    trace.layer3_warnings = []

    row = trace.to_db_row()
    assert set(row.keys()) == {"layer1_decision", "layer2_raw_output", "layer3_changes"}

    l1 = row["layer1_decision"]
    assert l1["node"] == "order_start"
    assert l1["forced_tools"] == ["create_order"]
    assert l1["state_hash"] == "abc123"
    assert "validators_run" in l1

    assert row["layer2_raw_output"] == "[TOOL:create_order] Alles klar"
    assert set(row["layer3_changes"].keys()) == {
        "warnings",
        "text_changed",
        "tools_changed",
    }


def test_adk_turn_processor_wires_layer_trace():
    """The LIVE processor must initialise AND populate _current_layer_trace, so
    brain_service's getattr(_tp, '_current_layer_trace', None) can pick up a real
    trace instead of silently always reading None.

    Source inspection (not instantiation) keeps this guard independent of the
    heavy NodeManager/conversation_nodes import chain.
    """
    import inspect
    from server.training import adk_turn_processor as mod

    init_src = inspect.getsource(mod.ADKTurnProcessor.__init__)
    assert "self._current_layer_trace = None" in init_src, (
        "ADKTurnProcessor.__init__ must initialise _current_layer_trace"
    )

    turn_src = inspect.getsource(mod.ADKTurnProcessor._process_turn_inner)
    # Must build a LayerTrace and assign it to the live seam.
    assert "LayerTrace" in turn_src, "live turn must build a LayerTrace"
    assert "self._current_layer_trace = trace" in turn_src, (
        "live turn must assign the populated trace to _current_layer_trace"
    )


def test_brain_service_persists_layer_columns_in_live_writer():
    """The unified persist_turn_metric() with path_type='live' must also persist
    the layer columns (not just the finalize batch), so live telephony rows are
    not blind on layer1/2/3."""
    import inspect
    from server import brain_service as bs

    src = inspect.getsource(bs.BrowserBrainService.persist_turn_metric)
    for col in ("layer1_decision", "layer2_raw_output", "layer3_changes"):
        assert col in src, f"persist_turn_metric must handle {col} in live path"
