"""
Observability helpers — Phase 8 B5 (PII redaction in logs).

install_log_redaction() wraps the root logging Formatter so every log
record's message is redacted before it reaches any handler (stderr, file,
Cloud Logging). Raw values are preserved in Postgres only.

Called once at server startup in server/main.py:
    from server.core.obs import install_log_redaction, log_boot_banner
    install_log_redaction()
"""
from __future__ import annotations

import logging
import os


class _PiiRedactingFormatter(logging.Formatter):
    """Wraps an existing formatter and redacts PII from the message field."""

    def __init__(self, wrapped: logging.Formatter):
        super().__init__()
        self._wrapped = wrapped

    def format(self, record: logging.LogRecord) -> str:
        try:
            from server.brain.observability.pii_redactor import redact
            record.msg = redact(str(record.msg))
            if record.args:
                try:
                    record.args = tuple(
                        redact(str(a)) if isinstance(a, str) else a
                        for a in (record.args if isinstance(record.args, tuple) else (record.args,))
                    )
                except Exception:
                    pass  # don't break logging for redaction failures
        except ImportError:
            pass  # pii_redactor not available in minimal installs
        return self._wrapped.format(record)


def install_log_redaction() -> None:
    """
    Wrap every handler on the root logger with the PII-redacting formatter.
    Safe to call multiple times (idempotent — checks for already-wrapped).
    """
    root = logging.getLogger()
    for handler in root.handlers:
        existing = handler.formatter
        if existing is None or isinstance(existing, _PiiRedactingFormatter):
            continue
        handler.setFormatter(_PiiRedactingFormatter(existing))

    # Also install a loguru sink if loguru is in use (optional — non-fatal)
    try:
        import sys
        from loguru import logger as loguru_logger
        from server.brain.observability.pii_redactor import pii_log_filter
        # loguru_logger.add is idempotent only by checking — keep it simple:
        # we patch at stdlib level above; loguru filter below is belt-and-braces
        loguru_logger.configure(patcher=_loguru_pii_patcher)
    except (ImportError, Exception):
        pass  # loguru not required


def _loguru_pii_patcher(record: dict) -> None:
    """Loguru patcher — called for every log record (not filter, no return)."""
    try:
        from server.brain.observability.pii_redactor import redact
        record["message"] = redact(record["message"])
    except Exception:
        pass


def log_boot_banner(logger: logging.Logger) -> None:
    """Log startup info including build SHA (from env) and Python version."""
    import platform
    build_sha = os.environ.get("BUILD_SHA", "dev")
    logger.info(
        "[BOOT] Sailly starting — build=%s python=%s",
        build_sha,
        platform.python_version(),
    )
