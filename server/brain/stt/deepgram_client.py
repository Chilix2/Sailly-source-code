"""
server/brain/stt/deepgram_client.py
------------------------------------
Builds Deepgram STT settings from tenant config, keeping all audio-pipeline
configuration in one place rather than scattered through main.py.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from pipecat.transcriptions.language import Language
from pipecat.services.deepgram.flux.stt import DeepgramFluxSTTSettings


_DEFAULTS: Dict[str, Any] = {
    "model": "nova-3",
    "endpointing": 1200,
    "interim_results": True,
    "punctuate": True,
    "smart_format": False,
}


def build_stt_settings(tenant_cfg) -> Dict[str, Any]:
    """Return a kwargs dict suitable for ``DeepgramSTTService.Settings(**kwargs)``.

    Reads ``audio.stt_model``, ``audio.stt_endpoint``, and ``audio.smart_format``
    from the tenant config when present; falls back to sane defaults.

    Args:
        tenant_cfg: A ``TenantConfig`` instance (or any object with the same
                    attributes).  Also accepts a plain ``dict``.

    Returns:
        Dict ready to be unpacked into ``DeepgramSTTService.Settings``.
    """
    settings = dict(_DEFAULTS)

    # Pull the audio sub-config — TenantConfig stores it as a raw dict under
    # ``audio`` (loaded verbatim from YAML) when the model does not have a
    # typed field for it.
    audio_cfg: Dict[str, Any] = {}
    if isinstance(tenant_cfg, dict):
        audio_cfg = tenant_cfg.get("audio", {}) or {}
    else:
        audio_cfg = getattr(tenant_cfg, "audio", None) or {}
        # Pydantic models may expose it as a typed dict attribute
        if not isinstance(audio_cfg, dict):
            audio_cfg = {}

    stt_model: str = audio_cfg.get("stt_model") or "nova-3"
    smart_format: bool = bool(audio_cfg.get("smart_format", False))
    endpointing: int = int(audio_cfg.get("stt_endpointing_ms") or _DEFAULTS["endpointing"])

    # stt_language lives as a top-level field on TenantConfig
    stt_language: str = "de"
    if isinstance(tenant_cfg, dict):
        stt_language = tenant_cfg.get("stt_language", "de") or "de"
    else:
        stt_language = getattr(tenant_cfg, "stt_language", "de") or "de"

    settings["model"] = stt_model
    settings["language"] = stt_language
    settings["smart_format"] = smart_format
    settings["endpointing"] = endpointing

    return settings


def get_stt_endpoint(tenant_cfg) -> Optional[str]:
    """Return the Deepgram WebSocket endpoint URL override, or None for default.

    ``configs/tenants/doboo.yaml`` can set ``audio.stt_endpoint`` to a region-
    specific URL such as ``wss://api.eu.deepgram.com/v2/listen``.
    """
    audio_cfg: Dict[str, Any] = {}
    if isinstance(tenant_cfg, dict):
        audio_cfg = tenant_cfg.get("audio", {}) or {}
    else:
        audio_cfg = getattr(tenant_cfg, "audio", None) or {}
        if not isinstance(audio_cfg, dict):
            audio_cfg = {}
    return audio_cfg.get("stt_endpoint") or None


_FLUX_EU_ENDPOINT = "wss://api.eu.deepgram.com/v2/listen"


def build_flux_stt_settings(tenant_cfg) -> Dict[str, Any]:
    """Return a kwargs dict suitable for ``DeepgramFluxSTTService``.

    Builds Deepgram Flux STT settings with:
    - EU endpoint for GDPR compliance
    - mip_opt_out=True to disable Model Improvement Program
    - flux-general-multi model for multilingual German support

    P2.1/P2.2 tuning:
    - eot_threshold 0.7 → 0.6: more aggressive semantic EOT (-50–100ms latency).
      A/B 3 days: revert to 0.65 if utterance-fragmentation rate rises above 5%.
    - eot_timeout_ms 1200 → 3000: the old 1.2s hard cut was the real latency bug.
      The semantic model now decides; timeout is a last resort for genuinely silent
      callers only.

    Args:
        tenant_cfg: A ``TenantConfig`` instance (or dict).

    Returns:
        Dict ready to be unpacked into ``DeepgramFluxSTTService(**kwargs)``.
    """
    base_kwargs: Dict[str, Any] = {
        "model": "flux-general-multi",
        "language": Language.DE,
        "eot_threshold": 0.6,        # P2.1: was 0.7 — more aggressive semantic EOT
        "eot_timeout_ms": 3000,      # P2.2: was 1200 — last-resort fallback only
    }
    # P8.4: enable EagerEndOfTurn events when the SDK supports the field.
    # Speculative workers fire on EagerEndOfTurn (~200-400ms head-start).
    try:
        settings = DeepgramFluxSTTSettings(**base_kwargs, eager_eot_threshold=0.5)
    except TypeError:
        # SDK without eager_eot support — speculative path stays dormant.
        settings = DeepgramFluxSTTSettings(**base_kwargs)
    return {
        "url": _FLUX_EU_ENDPOINT,
        "mip_opt_out": True,
        "settings": settings,
    }
