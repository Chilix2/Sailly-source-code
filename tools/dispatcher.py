"""
DEPRECATED — moved to server.tools.dispatcher per architectural alignment.

This shim will be deleted once all callers migrate (target: 14 days).
Use: from server.tools.dispatcher import ...
"""
import warnings

warnings.warn(
    "tools.dispatcher is deprecated; import from server.tools.dispatcher instead",
    DeprecationWarning,
    stacklevel=2,
)

from server.tools.dispatcher import *  # noqa: F401, F403
from server.tools.dispatcher import (  # explicit for IDE
    GATED_TOOLS_BASE,
    dispatch_with_validation,
    required_slots_for_tool,
)

__all__ = [
    "GATED_TOOLS_BASE",
    "dispatch_with_validation",
    "required_slots_for_tool",
]
