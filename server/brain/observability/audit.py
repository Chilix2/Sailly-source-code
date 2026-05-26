"""
Append-only audit trail per decision postgres-audit-table (8.S8).

Writes a row to bot_tool_audit_log after every state-mutating tool execution.
Used for dispute resolution: "did the bot actually place this order?"

Note: The existing Postgres database has an 'audit_log' table used by the CRM/dashboard
system (different schema). This module uses 'bot_tool_audit_log' to avoid collision.
The table was created by the direct SQL migration run on 2026-04-25 (see
migrations/0001_audit_log_table.sql for the intended schema, applied manually as
bot_tool_audit_log).

The table is append-only: UPDATE and DELETE are revoked at the DB level for the
sailly application user. Application code never deletes.

Usage (from tools/executor.py):
    from server.brain.observability.audit import write_audit_entry
    await write_audit_entry(
        call_sid=ctx.call_sid,
        tenant_id=ctx.tenant_id,
        tool_name="create_order",
        args=args,
        result=result_dict,
        success=True,
    )
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Tools whose executions are written to audit_log.
AUDITED_TOOLS: frozenset[str] = frozenset({
    "create_order",
    "create_reservation",
    "modify_order",
    "cancel_order",
    "transfer_to_human",  # included for accountability on warm handoffs
})


async def write_audit_entry(
    call_sid: str,
    tenant_id: str,
    tool_name: str,
    args: dict,
    result: Any,
    success: bool,
) -> None:
    """
    Append one row to audit_log.

    Silently no-ops for non-audited tools so callers don't need to filter.
    Catches and logs all DB errors — audit failures must NOT crash the call.
    """
    if tool_name not in AUDITED_TOOLS:
        return

    result_dict = result if isinstance(result, dict) else {"value": str(result)}
    args_json = json.dumps(args, ensure_ascii=False, default=str)
    result_json = json.dumps(result_dict, ensure_ascii=False, default=str)

    try:
        pool = await _get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO bot_tool_audit_log
                    (call_sid, tenant_id, tool_name, args, result, success)
                VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6)
                """,
                call_sid,
                tenant_id,
                tool_name,
                args_json,
                result_json,
                success,
            )
        logger.debug(
            "[AUDIT] wrote %s success=%s call_sid=%s", tool_name, success, call_sid
        )
    except Exception as exc:
        # Audit failure MUST NOT crash the call — log and continue.
        logger.error("[AUDIT] write failed: %s (tool=%s call_sid=%s)", exc, tool_name, call_sid)


async def _get_pool():
    """Lazy import of DB pool to avoid circular imports at module load."""
    try:
        from server.configs.db import get_pool  # type: ignore
        return await get_pool()
    except ImportError:
        # DB not configured (dev/test) — raise so callers see clean error
        raise RuntimeError("DB pool not available; set POSTGRES_DSN in environment")
