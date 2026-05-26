"""
Unit tests for EU AI Act Art. 50 compliance on the first bot utterance.

The first audible line the caller hears MUST contain the token "KI" so that
the caller is unambiguously informed that they are speaking to an AI system.
This test guards:

  1. The default `TenantConfig.greeting_line` value.
  2. The fallback greeting baked into `brain_service._send_greeting` so the
     disclosure survives even when tenant config fails to load.
"""
from __future__ import annotations

import re

try:  # pragma: no cover — optional dep in dev env
    import pytest
except ImportError:  # fall back to a no-op shim so the module still imports
    class _PytestShim:
        @staticmethod
        def parametrize(*_args, **_kwargs):
            def decorator(func):
                return func
            return decorator
    pytest = _PytestShim()  # type: ignore[assignment]

from server.core.tenant_config import TenantConfig, PracticeInfo


def _has_ki_token(text: str) -> bool:
    """True if the raw word 'KI' appears as its own token (word-boundary match).

    Catches "KI-Assistentin", " KI ", "KI." etc. but rejects accidental
    substrings like "Kino" or "Kickstart".
    """
    return re.search(r"\bKI\b", text) is not None


def _minimal_tenant(**overrides) -> TenantConfig:
    defaults = dict(
        tenant_id="doboo",
        industry="restaurant",
        system_prompt="dummy",
        practice=PracticeInfo(name="DOBOO", location="Bonn"),
    )
    defaults.update(overrides)
    return TenantConfig(**defaults)


def test_default_greeting_line_contains_ki_token():
    tenant = _minimal_tenant()
    assert _has_ki_token(tenant.greeting_line), (
        f"Default greeting_line must contain the standalone token 'KI' "
        f"(EU AI Act Art. 50). Got: {tenant.greeting_line!r}"
    )


def test_default_ai_disclosure_does_not_claim_audio_recording():
    """We persist transcripts only — never raw audio. The TwiML <Say> line
    must not falsely claim that the audio is being recorded.
    """
    tenant = _minimal_tenant()
    assert "aufgezeichnet" not in tenant.ai_disclosure_text.lower(), (
        "ai_disclosure_text must not contain 'aufgezeichnet' — audio is never "
        "persisted, only transcripts."
    )


def test_brain_service_fallback_greeting_contains_ki():
    """Re-read the brain_service source and assert the hard fallback also
    contains the KI token, so compliance survives a tenant-config failure.
    """
    from pathlib import Path

    src = Path(__file__).resolve().parent.parent / "server" / "brain_service.py"
    text = src.read_text(encoding="utf-8")
    match = re.search(
        r"_fallback_greeting\s*=\s*\(([^)]+)\)",
        text,
        flags=re.DOTALL,
    )
    assert match, "Could not locate _fallback_greeting literal in brain_service.py"
    literal = match.group(1)
    assert _has_ki_token(literal), (
        "Hard fallback greeting in brain_service._send_greeting must contain "
        "the standalone token 'KI'."
    )


def test_detector_rejects_non_compliant_greetings():
    for bad_line in [
        "Hallo, hier ist Sailly — Willkommen!",  # no KI
        "Hallo vom digitalen Assistenten.",  # no KI
        "Willkommen im Kino.",  # substring, not standalone token
    ]:
        assert not _has_ki_token(bad_line), bad_line


if __name__ == "__main__":
    test_default_greeting_line_contains_ki_token()
    test_default_ai_disclosure_does_not_claim_audio_recording()
    test_brain_service_fallback_greeting_contains_ki()
    test_detector_rejects_non_compliant_greetings()
    print("ALL PASS")
