"""Layer 3 — ExecutionLayer.POLICY

Pure filter function: (text, tools, TurnPackage) -> PolicyResult(text, tools, warnings).

Layer 3 is deterministic and side-effect free (except logging). It can:
- Reject or rewrite text (e.g., strip hallucinations, block "technisches Problem")
- Reject or modify tool calls (e.g., enforce quantity ceilings)
- Emit warnings for observability

Phase 1: no-op pass-through. Phase 8 will fill in the actual guard rules.
"""
