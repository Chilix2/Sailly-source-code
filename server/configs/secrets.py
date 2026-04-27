"""
Secret loader per decision cloud-secret-manager (9.D3).

Reads secrets from Google Secret Manager in production, falls back to
environment variables in development.

Selection:
    SAILLY_ENV=dev      → read from os.environ (key = SECRET_NAME.upper().replace("-", "_"))
    SAILLY_ENV=staging  → read from GSM
    SAILLY_ENV=prod     → read from GSM

Required IAM:  the service account running the server must have
    roles/secretmanager.secretAccessor
on the project that holds the secrets.

Usage:
    from server.configs.secrets import get_secret
    DEEPGRAM_API_KEY = get_secret("deepgram-api-key")

Secrets managed in GSM (create with):
    gcloud secrets create deepgram-api-key --replication-policy=automatic
    echo -n "<value>" | gcloud secrets versions add deepgram-api-key --data-file=-

Managed secrets list:
    deepgram-api-key
    gemini-api-key
    twilio-account-sid
    twilio-auth-token
    whatsapp-token
    maps-api-key
    postgres-password
    redis-password
    slack-alerts-webhook
"""
from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)

_client = None
_cache: dict[str, str] = {}


def _get_client():
    global _client
    if _client is None:
        from google.cloud import secretmanager  # type: ignore
        _client = secretmanager.SecretManagerServiceClient()
    return _client


def get_secret(name: str, default: str | None = None) -> str:
    """
    Retrieve a secret value by name.

    Args:
        name:    Secret name in GSM (e.g. "deepgram-api-key").
        default: Fallback value if the secret is missing in dev mode.
                 In prod/staging, a missing secret raises KeyError.

    Returns:
        The secret value as a UTF-8 string.

    Raises:
        KeyError: If the secret is not found and no default is given (prod/staging).
    """
    if name in _cache:
        return _cache[name]

    env = os.getenv("SAILLY_ENV", "dev")

    if env == "dev":
        # Dev: read from environment variable.
        # Convention: "deepgram-api-key" → "DEEPGRAM_API_KEY"
        env_key = name.upper().replace("-", "_")
        value = os.environ.get(env_key) or os.environ.get(name)
        if value is None:
            if default is not None:
                logger.debug("secrets[dev]: %s not set — using default", name)
                return default
            raise KeyError(
                f"Secret '{name}' not found. "
                f"Set the '{env_key}' environment variable in dev."
            )
        logger.debug("secrets[dev]: loaded %s from env", name)
    else:
        # Staging/prod: read from Google Secret Manager
        project_id = os.environ.get("GCP_PROJECT_ID")
        if not project_id:
            raise EnvironmentError(
                "GCP_PROJECT_ID must be set in staging/prod to load secrets from GSM"
            )

        secret_path = f"projects/{project_id}/secrets/{name}/versions/latest"
        try:
            response = _get_client().access_secret_version(request={"name": secret_path})
            value = response.payload.data.decode("UTF-8")
            logger.debug("secrets[%s]: loaded %s from GSM", env, name)
        except Exception as exc:
            if default is not None:
                logger.warning("secrets[%s]: GSM error for %s — using default: %s", env, name, exc)
                return default
            raise

    _cache[name] = value
    return value




def clear_cache() -> None:
    """Clear the in-memory secret cache.  Use in tests."""
    _cache.clear()
