"""Runtime registry for tenant websocket workers and deploy checks."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from server.core.tenant_config import get_tenant_registry

REPO_ROOT = Path(__file__).resolve().parents[2]
TENANT_CONFIG_DIR = REPO_ROOT / "configs" / "tenants"
DEFAULT_WEBSOCKET_ROUTE = "/ws/headless"


def _tenant_yaml_path(tenant_id: str) -> Path:
    return TENANT_CONFIG_DIR / f"{tenant_id}.yaml"


def _get_config_value(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def tenant_runtime_record(tenant_id: str) -> dict[str, Any]:
    tenant = get_tenant_registry().load_tenant(tenant_id)
    runtime = getattr(tenant, "runtime", None)
    websocket_route = _get_config_value(runtime, "websocket_route") or DEFAULT_WEBSOCKET_ROUTE
    audio = getattr(tenant, "audio", None)
    tts = getattr(tenant, "tts", None)
    return {
        "tenant_id": tenant_id,
        "config_path": str(_tenant_yaml_path(tenant_id)),
        "config_exists": _tenant_yaml_path(tenant_id).exists(),
        "websocket_route": websocket_route,
        "websocket_url": f"wss://sailly.tech{websocket_route}?tenant={tenant_id}",
        "worker": {
            "service": "sailly-browser-demo",
            "status": systemd_status("sailly-browser-demo"),
            "restart_supported": True,
        },
        "providers": {
            "stt_provider": _get_config_value(audio, "stt_provider", "deepgram"),
            "stt_model": _get_config_value(audio, "stt_model"),
            "tts_provider": _get_config_value(tts, "tts_provider", "google"),
            "tts_model": _get_config_value(tts, "model"),
            "llm_model": getattr(tenant, "model", None),
        },
        "checks": deploy_checks(tenant_id),
    }


def list_runtime_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(TENANT_CONFIG_DIR.glob("*.yaml")):
        try:
            records.append(tenant_runtime_record(path.stem))
        except Exception as e:
            records.append({"tenant_id": path.stem, "error": str(e), "config_path": str(path)})
    return records


def deploy_checks(tenant_id: str) -> list[dict[str, Any]]:
    path = _tenant_yaml_path(tenant_id)
    checks = [
        {"id": "tenant_config", "label": "Tenant YAML exists", "ok": path.exists()},
        {"id": "deepgram_key", "label": "Deepgram key configured", "ok": bool(os.getenv("DEEPGRAM_API_KEY"))},
        {"id": "google_project", "label": "Google project configured", "ok": bool(os.getenv("GOOGLE_PROJECT_ID"))},
        {"id": "google_credentials", "label": "Google credentials configured", "ok": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))},
        {"id": "anthropic_key", "label": "Anthropic key configured", "ok": bool(os.getenv("ANTHROPIC_API_KEY"))},
    ]
    return checks


def systemd_status(service_name: str) -> str:
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            check=False,
            text=True,
            capture_output=True,
            timeout=3,
        )
        return (result.stdout or result.stderr or "unknown").strip()
    except Exception:
        return "unknown"


def service_logs(service_name: str = "sailly-browser-demo", lines: int = 120) -> dict[str, Any]:
    safe_lines = max(20, min(int(lines), 500))
    try:
        result = subprocess.run(
            ["journalctl", "-u", service_name, "-n", str(safe_lines), "--no-pager"],
            check=False,
            text=True,
            capture_output=True,
            timeout=5,
        )
        return {"service": service_name, "lines": safe_lines, "output": result.stdout or result.stderr}
    except Exception as e:
        return {"service": service_name, "lines": safe_lines, "output": "", "error": str(e)}


def restart_service(service_name: str = "sailly-browser-demo") -> dict[str, Any]:
    return {
        "service": service_name,
        "status": systemd_status(service_name),
        "restart_supported": True,
        "message": "Restart is exposed as a guarded builder action; wire sudo/systemd policy before enabling mutation from the dashboard.",
    }
