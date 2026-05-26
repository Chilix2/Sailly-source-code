# Layer 1 — ExecutionLayer.ORCHESTRATOR

Deterministic code that owns:
- Node selection and routing
- Intent FSM (finite state machine)
- State mutation from extracted slots
- Forced commit decisions
- Tool dispatch (which tools fire, in what order)
- End-of-call state machine

**May:** read/write ConversationState, fire tools, update Redis, pick nodes, maintain the intent FSM, emit forced tool commits.

**May not:** generate natural-language text. All text comes from Layer 2 or from deterministic templates.

## Input/Output

**Input:** `ConversationState`, last utterance, extracted slots.

**Output:** `TurnPackage` (handed to Layer 2), tool dispatch decisions.

## See also

- [`data-flow.md`](../../architecture-review/02-data-flow.md) — canonical per-turn sequence showing all three layers
- [`layer2/`](../layer2/) — the LLM layer
- [`layer3/`](../layer3/) — the policy layer
