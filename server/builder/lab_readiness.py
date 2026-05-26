"""Builder Lab readiness and channel isolation helpers.

These helpers are deliberately read-only. They describe whether the current
process environment looks like a safe Builder Lab and which URLs/keys a draft
test call should use before any publish path is enabled.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse, urlunparse
from typing import Any, Mapping

from server.providers.registry import list_providers, runtime_provider_status
from server.runtime.registry import deploy_checks

LAB_DEFAULT_BACKEND_PORT = "18080"
LAB_DEFAULT_DASHBOARD_PORT = "13001"
LAB_DEFAULT_REDIS_DB = "14"
LAB_DB_NAME = "sailly_builder_lab"
LAB_KEY_PREFIX = "builder_lab:"


def builder_lab_readiness(tenant_id: str = "builder_lab_doboo") -> dict[str, Any]:
    """Return read-only readiness checks for Builder Lab execution."""

    checks = [
        _check("sailly_env", "SAILLY_ENV is builder_lab", os.getenv("SAILLY_ENV") == "builder_lab"),
        _check("backend_port", "Backend lab port is 18080", os.getenv("DEMO_PORT") == LAB_DEFAULT_BACKEND_PORT),
        _check("redis_db", "Redis URL uses lab DB 14", _redis_db(os.getenv("REDIS_URL")) == LAB_DEFAULT_REDIS_DB),
        _check("postgres_db", "Database URL uses sailly_builder_lab", LAB_DB_NAME in (os.getenv("DATABASE_URL") or "")),
        _check("twilio_disabled", "Twilio is disabled", _env_false("ENABLE_TWILIO")),
        _check("sms_dry_run", "SMS dry-run is enabled", _env_true("SMS_DRY_RUN")),
    ]
    checks.extend(deploy_checks(tenant_id))

    return {
        "tenant_id": tenant_id,
        "ok": all(check["ok"] for check in checks),
        "checks": checks,
        "providers": provider_readiness(),
        "channels": lab_channel_plan(tenant_id),
    }


def provider_readiness() -> dict[str, Any]:
    """Describe configured provider catalogs without exposing secret values."""

    catalogs = list_providers()
    return {
        "catalogs": catalogs,
        "runtime": runtime_provider_status(),
        "missing_env": {
            kind: {
                provider["id"]: [
                    env_name
                    for env_name in provider.get("configured_by", [])
                    if not os.getenv(env_name)
                ]
                for provider in providers
            }
            for kind, providers in catalogs.items()
        },
    }


def lab_channel_plan(
    tenant_id: str = "builder_lab_doboo",
    draft_id: str | None = None,
) -> dict[str, Any]:
    """Return isolated channel names for test-call-from-canvas flows."""

    backend_port = os.getenv("DEMO_PORT") or LAB_DEFAULT_BACKEND_PORT
    dashboard_port = os.getenv("BUILDER_LAB_DASHBOARD_PORT") or LAB_DEFAULT_DASHBOARD_PORT
    draft_suffix = f":draft:{draft_id}" if draft_id else ""

    return {
        "tenant_id": tenant_id,
        "draft_id": draft_id,
        "backend_http_url": f"http://127.0.0.1:{backend_port}",
        "dashboard_http_url": f"http://127.0.0.1:{dashboard_port}",
        "websocket_url": f"ws://127.0.0.1:{backend_port}/ws/headless?tenant={tenant_id}",
        "redis_url": _redact_url_password(os.getenv("REDIS_URL") or f"redis://localhost:6379/{LAB_DEFAULT_REDIS_DB}"),
        "redis_key_prefix": f"{LAB_KEY_PREFIX}{tenant_id}{draft_suffix}",
        "database_url": _redact_url_password(os.getenv("DATABASE_URL") or ""),
        "side_effects": {
            "twilio_enabled": _env_true("ENABLE_TWILIO"),
            "sms_dry_run": _env_true("SMS_DRY_RUN"),
        },
    }


def _check(check_id: str, label: str, ok: bool, details: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {"id": check_id, "label": label, "ok": bool(ok), "details": dict(details or {})}


def _redis_db(redis_url: str | None) -> str:
    if not redis_url:
        return ""
    path = urlparse(redis_url).path.strip("/")
    return path or "0"


def _env_true(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _env_false(name: str) -> bool:
    value = (os.getenv(name) or "").strip().lower()
    return value in {"", "0", "false", "no", "off"}


def _redact_url_password(raw_url: str) -> str:
    if not raw_url:
        return ""
    parsed = urlparse(raw_url)
    if not parsed.password:
        return raw_url
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    username = parsed.username or ""
    netloc = f"{username}:***@{host}" if username else host
    return urlunparse(parsed._replace(netloc=netloc))
