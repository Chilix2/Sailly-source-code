"""Layer 1 — ExecutionLayer.ORCHESTRATOR

Deterministic code that owns:
- Node selection and routing
- Intent FSM (finite state machine)
- State mutation from extracted slots
- Forced commit decisions
- Tool dispatch (which tools fire, in what order)
- End-of-call state machine

Layer 1 MUST NOT generate natural-language text. All text comes from Layer 2 or
from deterministic templates. If you need to add a text phrase here, move it to
Layer 2 (the LLM) or Layer 3 (policy filtering).

This layer will absorb NodeManager, forced_commits.py, intent_fsm.py, and
dispatcher.py in Phase 3.
"""
