"""
ConversationState schema migrations.

Each migrator upgrades a persisted state dict from one version to the next.
`migrate_to_current` applies the full chain and returns the dict ready for
`ConversationState.from_dict()`.

Migration chain:
  v0 → v2 (Phase 1/2 — handled inline in from_dict)
  v2 → v5 (Phase 5.5 — adds validation_entries)
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

CURRENT_VERSION = 5


def migrate_to_current(data: dict[str, Any]) -> dict[str, Any]:
    """
    Apply all pending migrations in sequence.

    Args:
        data: Raw dict loaded from Redis / JSON storage.

    Returns:
        Updated dict at CURRENT_VERSION ready for ConversationState.from_dict().
    """
    version = data.get("schema_version", 0)

    if version < 5:
        data = _migrate_v2_to_v5(data)

    return data


# ── Migrators ─────────────────────────────────────────────────────────────────

def _migrate_v2_to_v5(data: dict[str, Any]) -> dict[str, Any]:
    """
    v0/v1/v2 → v5: add validation_entries.

    All prior versions lacked the validation_entries key. Default to empty
    dict so the ValidationRegistry starts fresh on reconnect (per-call-cache
    decision — no cross-call leakage).
    """
    old_version = data.get("schema_version", 0)
    data = dict(data)  # shallow copy — never mutate caller's dict

    if "validation_entries" not in data:
        data["validation_entries"] = {}

    data["schema_version"] = 5
    logger.debug(
        "state_migration",
        extra={"from_version": old_version, "to_version": 5},
    )
    return data
