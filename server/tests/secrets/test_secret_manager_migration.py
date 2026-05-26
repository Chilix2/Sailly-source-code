"""
FINDING-017 regression tests — Secret Manager Migration.

Guards that:
  1. The migrated files no longer read known API-key env vars directly.
  2. get_secret() is wired into the correct call sites.
  3. Dev-mode fallback works (env var → value, no GSM call).
  4. In-process caching works (second call returns cached value).
  5. The provision script exists and is executable.
"""
from __future__ import annotations

import importlib
import os
import pathlib
import re
import stat

import pytest

_ROOT = pathlib.Path(__file__).parents[3]  # sailly-browser-demo/


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _src(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def _direct_environ_pattern(key: str) -> re.Pattern:
    """Matches os.environ['KEY'], os.environ.get('KEY'), os.getenv('KEY')."""
    return re.compile(
        rf"""os\.(environ\[["']{key}["']\]|environ\.get\(["']{key}["']|getenv\(["']{key}["'])"""
    )


MIGRATED_KEYS = {
    "DEEPGRAM_API_KEY": [
        "server/main.py",
        "server/brain/adk_turn_processor.py",
        "server/brain/health.py",
    ],
    "GEMINI_API_KEY": [
        "server/brain/health.py",
        "server/brain/layer1/text_mode_runner.py",
    ],
    "GOOGLE_MAPS_API_KEY": [
        "server/tools/handlers/verify_address.py",
    ],
    "SLACK_ALERTS_WEBHOOK": [
        "server/brain/observability/alerts.py",
    ],
}

EXEMPT_FILE = "server/configs/secrets.py"


# ---------------------------------------------------------------------------
# 1.  No direct os.environ reads for migrated keys in the target files
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key,files", MIGRATED_KEYS.items())
def test_no_direct_environ_read_in_migrated_files(key, files):
    """Each migrated file must not directly read the env var it migrated away from."""
    pattern = _direct_environ_pattern(key)
    for rel in files:
        src = _src(rel)
        assert not pattern.search(src), (
            f"Direct os.environ read for {key!r} still present in {rel}. "
            f"Migrate to get_secret()."
        )


def test_no_direct_environ_read_across_server_for_migrated_keys():
    """
    Exhaustive scan: no *.py file under server/ (except secrets.py) should
    directly read the env-var name for any migrated key.
    """
    server_dir = _ROOT / "server"
    failures = []
    for key in MIGRATED_KEYS:
        pattern = _direct_environ_pattern(key)
        for pyfile in server_dir.rglob("*.py"):
            if EXEMPT_FILE in pyfile.as_posix():
                continue
            if any("_backup" in part for part in pyfile.parts):
                continue
            src = pyfile.read_text(encoding="utf-8")
            if pattern.search(src):
                failures.append(f"{key!r} in {pyfile.relative_to(_ROOT)}")

    assert not failures, (
        "Direct environ reads for migrated secrets found:\n  " + "\n  ".join(failures)
    )


# ---------------------------------------------------------------------------
# 2.  get_secret() call sites are wired
# ---------------------------------------------------------------------------

def test_main_py_imports_get_secret():
    src = _src("server/main.py")
    assert "from server.configs.secrets import get_secret" in src, (
        "server/main.py must import get_secret"
    )


def test_main_py_calls_get_secret_for_deepgram():
    src = _src("server/main.py")
    assert 'get_secret("deepgram-api-key"' in src, (
        "server/main.py must call get_secret('deepgram-api-key')"
    )


def test_health_py_calls_get_secret_for_gemini_and_deepgram():
    src = _src("server/brain/health.py")
    assert 'get_secret("gemini-api-key"' in src, (
        "health.py must call get_secret('gemini-api-key')"
    )
    assert 'get_secret("deepgram-api-key"' in src, (
        "health.py must call get_secret('deepgram-api-key')"
    )


def test_alerts_py_uses_lazy_slack_webhook():
    src = _src("server/brain/observability/alerts.py")
    assert 'get_secret("slack-alerts-webhook"' in src, (
        "alerts.py must call get_secret('slack-alerts-webhook')"
    )
    assert "SLACK_WEBHOOK_URL" not in src or "os.getenv" not in src, (
        "alerts.py must not read SLACK_ALERTS_WEBHOOK via os.getenv at module level"
    )


def test_verify_address_uses_maps_secret():
    src = _src("server/tools/handlers/verify_address.py")
    assert 'get_secret("maps-api-key"' in src, (
        "verify_address.py must call get_secret('maps-api-key')"
    )


def test_text_mode_runner_uses_gemini_secret():
    src = _src("server/brain/layer1/text_mode_runner.py")
    assert 'get_secret("gemini-api-key"' in src, (
        "text_mode_runner.py must call get_secret('gemini-api-key')"
    )


def test_adk_turn_processor_uses_deepgram_secret():
    src = _src("server/brain/adk_turn_processor.py")
    assert 'get_secret("deepgram-api-key"' in src, (
        "adk_turn_processor.py must call get_secret('deepgram-api-key')"
    )


# ---------------------------------------------------------------------------
# 3.  Dev-mode fallback: get_secret reads env var, no GSM call
# ---------------------------------------------------------------------------

def test_get_secret_dev_fallback_reads_env_var(monkeypatch):
    """In SAILLY_ENV=dev, get_secret reads env var (no GSM call)."""
    monkeypatch.setenv("SAILLY_ENV", "dev")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-dg-value")

    # Clear cache so we get a fresh read
    from server.configs import secrets as _secrets_mod
    _secrets_mod.clear_cache()

    from server.configs.secrets import get_secret
    assert get_secret("deepgram-api-key") == "test-dg-value"

    _secrets_mod.clear_cache()


def test_get_secret_dev_fallback_with_explicit_default(monkeypatch):
    """Missing env var in dev returns the supplied default, not KeyError."""
    monkeypatch.setenv("SAILLY_ENV", "dev")
    monkeypatch.delenv("SOME_NONEXISTENT_SECRET", raising=False)

    from server.configs import secrets as _secrets_mod
    _secrets_mod.clear_cache()

    from server.configs.secrets import get_secret
    val = get_secret("some-nonexistent-secret", default="fallback")
    assert val == "fallback"

    _secrets_mod.clear_cache()


# ---------------------------------------------------------------------------
# 4.  In-process caching
# ---------------------------------------------------------------------------

def test_get_secret_caches_within_process(monkeypatch):
    """Second call returns cached value even if env var changes in between."""
    monkeypatch.setenv("SAILLY_ENV", "dev")
    monkeypatch.setenv("CACHE_TEST_KEY", "first-value")

    from server.configs import secrets as _secrets_mod
    _secrets_mod.clear_cache()

    from server.configs.secrets import get_secret

    first = get_secret("cache-test-key")
    monkeypatch.setenv("CACHE_TEST_KEY", "second-value")
    second = get_secret("cache-test-key")

    assert first == second == "first-value", (
        "get_secret must return the cached first value on subsequent calls"
    )

    _secrets_mod.clear_cache()


# ---------------------------------------------------------------------------
# 5.  Provision script exists and is executable
# ---------------------------------------------------------------------------

def test_provision_script_exists():
    script = _ROOT / "scripts" / "provision_secrets.sh"
    assert script.exists(), "scripts/provision_secrets.sh must exist"


def test_provision_script_is_executable():
    script = _ROOT / "scripts" / "provision_secrets.sh"
    mode = script.stat().st_mode
    assert bool(mode & stat.S_IXUSR), "scripts/provision_secrets.sh must be executable"


def test_provision_script_contains_all_secret_names():
    src = (_ROOT / "scripts" / "provision_secrets.sh").read_text(encoding="utf-8")
    expected = [
        "deepgram-api-key",
        "gemini-api-key",
        "maps-api-key",
        "twilio-account-sid",
        "twilio-auth-token",
        "whatsapp-token",
        "slack-alerts-webhook",
        "postgres-password",
        "redis-password",
    ]
    missing = [name for name in expected if name not in src]
    assert not missing, f"provision_secrets.sh is missing secrets: {missing}"
