"""Layer 2 — ExecutionLayer.LLM

Language generation only. Input: TurnPackage. Output: text (no tool emission, no state decisions).

Layer 2 MUST NOT:
- Read ConversationState directly — only read via TurnPackage
- Emit [TOOL:...] tags or make tool dispatch decisions
- Know the call_sid or any identifying info (Phase 8: redaction)
- Fire side effects or external API calls

This layer will absorb main_llm.py and memory_manager.py in Phase 3.
"""
