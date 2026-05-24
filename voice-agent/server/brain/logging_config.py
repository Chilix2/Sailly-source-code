"""
Structured logging configuration per decision structlog (9.X2).

Provides a single `configure_logging()` call that:
  - Removes the default loguru handler.
  - Adds a JSON-serialised handler for Cloud Logging ingestion (production) or
    a pretty-print handler for local development.
  - Attaches the PII redaction filter from Phase 8.
  - Establishes the standard field names that must appear on every hot-path log.

Standard log keys (use these consistently everywhere):
    call_sid    -- str   Active call SID (empty string if no active call)
    tenant_id   -- str   Tenant slug (e.g. "doboo")
    turn_idx    -- int   Turn counter within the call
    node_id     -- str   Current conversation node name
    tool_name   -- str   For tool-scoped logs
    duration_ms -- int   Latency of the logged operation
    error_code  -- str   ERR_* taxonomy code (see server.tools.common.error_codes)

Usage:
    from server.brain.logging_config import configure_logging
    configure_logging()   # called once at server startup in server/main.py

Migration guide:
    # Before (free-form f-string)
    logger.info(f"Turn completed in {duration}ms for {call_sid}")

    # After (structured bind)
    logger.bind(call_sid=call_sid, duration_ms=duration).info("turn_completed")
"""
from __future__ import annotations

import os
import sys
import logging

_CONFIGURED = False


def configure_logging(env: str | None = None) -> None:
    """
    Configure loguru for structured output.

    Args:
        env: Override environment string. Defaults to SAILLY_ENV env var,
             falling back to "dev".
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    try:
        from loguru import logger
    except ImportError:
        logging.basicConfig(level=logging.INFO)
        return

    env = env or os.getenv("SAILLY_ENV", "dev")
    is_prod = env in ("prod", "staging")

    # Remove default loguru handler
    logger.remove()

    def _pii_filter(record: dict) -> bool:
        try:
            from server.brain.observability.pii_redactor import redact
            record["message"] = redact(record["message"])
            extra = record.get("extra", {})
            record["extra"] = {
                k: redact(v) if isinstance(v, str) else v
                for k, v in extra.items()
            }
        except Exception:
            pass
        return True

    if is_prod:
        logger.add(
            sys.stdout,
            serialize=True,
            filter=_pii_filter,
            level="INFO",
            backtrace=False,
            diagnose=False,
        )
    else:
        dev_format = (
            "<green>{time:HH:mm:ss.SSS}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<white>{extra}</white> | "
            "{message}"
        )
        logger.add(
            sys.stdout,
            format=dev_format,
            filter=_pii_filter,
            level="DEBUG",
            colorize=True,
        )

    class _InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = str(record.levelno)

            frame, depth = logging.currentframe(), 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back  # type: ignore[assignment]
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    logger.info("logging_configured", extra={"env": env, "serialize": is_prod})
