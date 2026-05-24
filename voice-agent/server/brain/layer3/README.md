# Layer 3 — ExecutionLayer.POLICY

Pure filter function: `(text, tools, TurnPackage) -> PolicyResult(text, tools, warnings)`.

**May:** read text + tools + TurnPackage, rewrite text, modify tool calls, emit warnings, log.

**May not:** write state, fire tools directly, call external APIs, be non-deterministic.

## Input/Output

**Input:** Layer 2's generated `text`, Layer 1's computed `tools` list, and the `TurnPackage` context.

**Output:** `PolicyResult(text, tools, warnings)` — the filtered text and tools, plus any policy violations detected.

## See also

- [`data-flow.md`](../../architecture-review/02-data-flow.md) — canonical per-turn sequence
- [`layer1/`](../layer1/) — the orchestrator layer
- [`layer2/`](../layer2/) — the LLM layer
- [`policy.py`](./policy.py) — the filter-function implementation
