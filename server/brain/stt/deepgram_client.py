"""
server/brain/stt/deepgram_client.py
------------------------------------
Builds Deepgram STT settings from tenant config, keeping all audio-pipeline
configuration in one place rather than scattered through main.py.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


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
