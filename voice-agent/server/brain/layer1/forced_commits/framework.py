"""
layer1/forced_commits/framework.py — Minimal framework for forced-commit rules.

A Rule inspects the current conversation state + last extraction and may
force one or more tool calls before the LLM responds.

Public API:
  Rule       — dataclass for a forced-commit rule
  ForcedTool — dataclass describing a tool call to force
  apply_rules(rules, state, extraction) → list[ForcedTool]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from server.brain.conversation_state import ConversationState


@dataclass
class ForcedTool:
    """
    A tool call that a Rule insists must be fired before LLM response.

    Attributes:
        name:    Tool name (must exist in executor.handlers)
        args:    Arguments to pass
        reason:  Human-readable explanation (for logging / tracing)
        replace_response: Optional German text to emit instead of LLM response
    """
    name: str
    args: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    replace_response: Optional[str] = None


@dataclass
class Rule:
    """
    A forced-commit rule.

    Attributes:
        rule_id:    Unique identifier (for logging and deduplication)
        description: Short human-readable description
        matches:    Callable(state, extraction) → bool  — True if the rule fires
        apply:      Callable(state, extraction) → list[ForcedTool]
        priority:   Lower = fires first. Default 50.
    """
    rule_id: str
    description: str
    matches: Callable[["ConversationState", dict], bool]
    apply: Callable[["ConversationState", dict], List[ForcedTool]]
    priority: int = 50


def apply_rules(
    rules: List[Rule],
    state: "ConversationState",
    extraction: dict,
) -> List[ForcedTool]:
    """
    Evaluate all rules in priority order and return the combined list of ForcedTools.

    Multiple rules can fire in the same turn. Results are de-duplicated by tool name
    (first match wins for each tool name).
    """
    forced: List[ForcedTool] = []
    seen_tools: set = set()

    for rule in sorted(rules, key=lambda r: r.priority):
        try:
            if rule.matches(state, extraction):
                for ft in rule.apply(state, extraction):
                    if ft.name not in seen_tools:
                        forced.append(ft)
                        seen_tools.add(ft.name)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "[forced_commits] rule %s raised: %s", rule.rule_id, exc
            )

    return forced
