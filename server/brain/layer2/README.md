# Layer 2 — ExecutionLayer.LLM

Language generation only. Input: `TurnPackage`. Output: `text` (no tool emission, no state decisions).

**May:** read TurnPackage, generate text via Gemini 2.5 Flash.

**May not:** read ConversationState directly, emit [TOOL:...] tags, make tool dispatch decisions, know call_sid, fire side effects.

## Input/Output

**Input:** `TurnPackage` from Layer 1.

**Output:** `text` (streamed response, typically 100–512 tokens).

## See also

- [`data-flow.md`](../../architecture-review/02-data-flow.md) — canonical per-turn sequence
- [`layer1/`](../layer1/) — the orchestrator layer
- [`layer3/`](../layer3/) — the policy layer
