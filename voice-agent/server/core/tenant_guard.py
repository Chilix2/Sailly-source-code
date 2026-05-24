"""Runtime tenant validation guards for HTTP/WebSocket entrypoints."""

from __future__ import annotations

from fastapi import HTTPException

from server.core.tenant_config import (
    list_known_tenant_ids,
    normalize_tenant_id,
    require_tenant_config,
)


def resolve_tenant_id(raw: str, *, default: str | None = None) -> str:
    """Normalize + validate a tenant_id against on-disk tenant configs."""
    try:
        tid = normalize_tenant_id(raw)
    except ValueError:
        if default is None:
            raise HTTPException(status_code=400, detail="invalid tenant_id")
        tid = normalize_tenant_id(default)

    if tid not in set(list_known_tenant_ids()):
        raise HTTPException(status_code=404, detail=f"unknown tenant: {tid}")

    # Warm and validate schema at runtime boundary.
    require_tenant_config(tid)
    return tid


async def assert_call_belongs_to_tenant(call_sid: str, tenant_id: str) -> None:
    """Fail closed when a call_sid is requested under the wrong tenant."""
    from server.database import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT tenant_id FROM google_calls WHERE call_sid = $1 LIMIT 1",
            call_sid,
        )
    if not row:
        raise HTTPException(status_code=404, detail="call not found")
    if (row["tenant_id"] or "") != tenant_id:
        raise HTTPException(status_code=403, detail="tenant mismatch")
