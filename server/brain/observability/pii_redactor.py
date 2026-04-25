"""
PII redaction for log output per decision redact-logs (8.S6).

Phone numbers and street addresses are replaced in log messages.
Raw values are preserved in Postgres (google_turn_metrics) with
row-level access control — only the log sink is redacted.

Usage:
    from server.brain.observability.pii_redactor import redact

    # In loguru sink or logging formatter:
    redacted_message = redact(original_message)

Wire into loguru via a filter function or a custom sink:
    logger.add(sys.stdout, filter=pii_log_filter)
"""
from __future__ import annotations

import re

# German phone numbers: +49..., 0049..., 0... with optional spaces/dashes
_PHONE_RE = re.compile(
    r"(?:\+49|0049)[\s\-]?\d[\d\s\-]{7,12}\d"  # +49 / 0049 form
    r"|(?<!\d)0\d{2,4}[\s\-\/]?\d{5,9}(?!\d)",  # 0XXX YYYYYYY form
    re.IGNORECASE,
)

# German-style street addresses: "Musterstraße 12", "Musterstr. 4a", etc.
_ADDRESS_RE = re.compile(
    r"\b[A-ZÄÖÜ][A-Za-zäöüÄÖÜß\-]+"
    r"(?:straße|strasse|str\.|gasse|platz|weg|allee|ring|damm|ufer)\s*\d+\w*",
    re.IGNORECASE,
)

_PHONE_PLACEHOLDER = "[PHONE_REDACTED]"
_ADDRESS_PLACEHOLDER = "[ADDRESS_REDACTED]"


def redact(text: str) -> str:
    """Replace phone numbers and street addresses with placeholders."""
    text = _PHONE_RE.sub(_PHONE_PLACEHOLDER, text)
    text = _ADDRESS_RE.sub(_ADDRESS_PLACEHOLDER, text)
    return text


def pii_log_filter(record: dict) -> bool:
    """
    Loguru filter function — redacts PII from the log record message in-place.

    Install with:
        logger.add(sys.stdout, filter=pii_log_filter, ...)
    """
    record["message"] = redact(record["message"])
    # Also redact any "extra" dict values that are strings
    for key, val in record.get("extra", {}).items():
        if isinstance(val, str):
            record["extra"][key] = redact(val)
    return True
