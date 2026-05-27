"""server/brain/v4_pipeline.py — Import shim maintaining backward compatibility.

This shim re-exports the required symbols from v4_pipeline_clean and v4_pipeline_legacy
so that existing imports continue to work without changes.

Re-exports:
  - process_turn_v4 (from v4_pipeline_clean, the new entry point)
  - _state_snapshot_for_gate (from v4_pipeline_legacy, for gate compatibility)
  - format_address_for_speech (from v4_pipeline_legacy, used in speech generation)
  - _default_menu_price_label (from v4_pipeline_legacy, for menu price formatting)
"""

# New FSM-based pipeline entry point
from server.brain.v4_pipeline_clean import process_turn_v4

# Legacy functions needed by existing gate and formatting code
from server.brain.v4_pipeline_legacy import (
    _state_snapshot_for_gate,
    format_address_for_speech,
    _default_menu_price_label,
)

__all__ = [
    'process_turn_v4',
    '_state_snapshot_for_gate',
    'format_address_for_speech',
    '_default_menu_price_label',
]
