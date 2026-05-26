"""
layer1/forced_commits/rules — Registered forced-commit rule files.

ALL_RULES is the consolidated list consumed by apply_rules().
Import order determines load-time priority (lower priority values always win anyway).
"""
from server.brain.layer1.forced_commits.rules.negation import NEGATION_RULES

ALL_RULES = [
    *NEGATION_RULES,
]

__all__ = ["ALL_RULES"]
