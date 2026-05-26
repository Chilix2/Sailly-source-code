from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException

from server.tenants.provision import create_tenant
from server.tenants.schemas import TenantProvisionRequest

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


def _check_admin_write(token: str | None) -> bool:
    if not token:
        return False
    role, _, secret = token.strip().partition(":")
    if not secret:
        role, secret = "admin", token.strip()
    expected = os.getenv("ADMIN_API_TOKEN", "").strip()
    if not expected or secret != expected:
        return False
    levels = {"read": 0, "write": 1, "admin": 2}
    return levels.get(role, -1) >= levels["write"]


@router.post("")
async def provision_tenant(
    body: TenantProvisionRequest,
    x_admin_token: str | None = Header(default=None),
):
    if not _check_admin_write(x_admin_token):
        raise HTTPException(status_code=401, detail="unauthorized_admin")
    try:
        result = create_tenant(body)
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return result.dict()
    except FileExistsError as e:
        detail = str(e)
        existing_path = detail.split("tenant_exists:", 1)[1] if "tenant_exists:" in detail else ""
        raise HTTPException(
            status_code=409,
            detail={"error": "tenant_exists", "tenant_id": body.tenant_id, "existing_path": existing_path},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": "validation_error", "message": str(e)})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "write_failed", "message": str(e)})
