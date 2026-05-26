from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml

from server.configs.tenant_schema import load_and_validate
from server.core.tenant_config import (
    get_tenant_registry,
    normalize_tenant_id,
    tenant_config_dir,
    tenant_yaml_path,
)
from server.tenants.schemas import TenantProvisionRequest, TenantProvisionResponse


def _minimal_tools() -> list[dict[str, Any]]:
    return [
        {"name": "check_availability", "description": "Check reservation availability"},
        {"name": "create_reservation", "description": "Create a reservation"},
        {"name": "create_order", "description": "Create an order"},
        {"name": "get_menu", "description": "Get menu items"},
        {"name": "end_call", "description": "End call politely"},
        {"name": "transfer_to_human", "description": "Transfer to human agent"},
    ]


def _to_plain_dict(model_obj) -> Dict[str, Any]:
    if hasattr(model_obj, "model_dump"):
        return model_obj.model_dump(exclude_none=True)  # pydantic v2
    if hasattr(model_obj, "dict"):
        return model_obj.dict(exclude_none=True)  # pydantic v1
    return {}


def scaffold_tenant_dict(req: TenantProvisionRequest) -> Dict[str, Any]:
    tid = normalize_tenant_id(req.tenant_id)
    location = req.location or {}
    opening_hours = req.opening_hours or {}
    data: Dict[str, Any] = {
        "tenant_id": tid,
        "industry": req.industry,
        "restaurant_name": req.restaurant_name,
        "language": req.language,
        "locale": req.locale,
        "city": req.city,
        "system_prompt": req.system_prompt or f"Du bist Sailly fuer {req.restaurant_name}.",
        "greeting_line": req.greeting_line
        or f"Hallo, hier ist Sailly, die KI-Assistentin von {req.restaurant_name}. Wie kann ich helfen?",
        "farewell_text": req.farewell_text or "Vielen Dank fuer Ihren Anruf. Auf Wiederhoeren.",
        "voice": "Kore",
        "model": "gemini-2.5-flash",
        "stt_language": req.language,
        "twilio_numbers": [],
        "practice": {
            "name": req.restaurant_name,
            "location": location.get("address", ""),
            "hours": opening_hours.get("formatted", ""),
        },
        "tool_data": {"menu": {"categories": []}},
        "location": {
            "address": location.get("address", ""),
            "city": location.get("city", req.city),
            "lat": location.get("lat"),
            "lng": location.get("lng"),
            "parking": location.get("parking", ""),
        },
        "opening_hours": {
            "monday": opening_hours.get("monday", ""),
            "tuesday": opening_hours.get("tuesday", ""),
            "wednesday": opening_hours.get("wednesday", ""),
            "thursday": opening_hours.get("thursday", ""),
            "friday": opening_hours.get("friday", ""),
            "saturday": opening_hours.get("saturday", ""),
            "sunday": opening_hours.get("sunday", ""),
            "formatted": opening_hours.get("formatted", ""),
        },
        "menu": {"categories": []},
        "items": [],
        "tools": _minimal_tools() if req.tools_minimal else [],
    }
    if req.pipeline and req.pipeline.audio:
        data["audio"] = _to_plain_dict(req.pipeline.audio)
    if req.pipeline and req.pipeline.tts:
        data["tts"] = _to_plain_dict(req.pipeline.tts)
    return data


def _validate_yaml_dict(data: Dict[str, Any], tenant_id: str) -> None:
    if normalize_tenant_id(str(data.get("tenant_id", ""))) != normalize_tenant_id(tenant_id):
        raise ValueError("tenant_id in payload/YAML must match request tenant_id")
    # Schema validation
    _ = load_and_validate_dict(data)


def load_and_validate_dict(data: Dict[str, Any]):
    # reuse schema path by temp file to avoid duplicating schema logic
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        yaml.safe_dump(data, tmp, sort_keys=False, allow_unicode=True)
        tmp_path = tmp.name
    try:
        return load_and_validate(tmp_path)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def _write_atomically(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, target)


def create_tenant(req: TenantProvisionRequest) -> TenantProvisionResponse:
    tid = normalize_tenant_id(req.tenant_id)
    existing = tenant_yaml_path(tid)
    if existing is not None:
        raise FileExistsError(f"tenant_exists:{existing}")

    if req.yaml:
        data = yaml.safe_load(req.yaml) or {}
        if not isinstance(data, dict):
            raise ValueError("yaml payload must decode to an object")
    else:
        data = scaffold_tenant_dict(req)

    _validate_yaml_dict(data, tid)

    target = tenant_config_dir() / f"{tid}.yaml"
    if not req.dry_run:
        rendered = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
        _write_atomically(target, rendered)
        registry = get_tenant_registry()
        registry.invalidate_tenant(tid)
        registry.load_tenant(tid)

    return TenantProvisionResponse(
        tenant_id=tid,
        path=str(target),
        created=not req.dry_run,
        validated=True,
        dry_run=req.dry_run,
    )
