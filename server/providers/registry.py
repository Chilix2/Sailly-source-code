"""Provider catalog and runtime factory helpers.

The Builder uses this registry to display all supported STT, LLM, and TTS
options. The runtime uses the factory helpers for the providers that are wired
today; unsupported providers are surfaced as configured-but-not-runtime-ready
instead of being silently accepted.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

import yaml

ProviderKind = Literal["stt", "llm", "tts"]

REPO_ROOT = Path(__file__).resolve().parents[2]
PROVIDER_CONFIG_DIR = REPO_ROOT / "configs" / "providers"


@dataclass
class ModelDescriptor:
    id: str
    label: str
    latency_class: str = "unknown"
    streaming: bool = False
    voice_agent_ready: bool = False
    recommended: bool = False
    notes: str = ""


@dataclass
class ProviderDescriptor:
    id: str
    label: str
    kind: ProviderKind
    configured_by: list[str] = field(default_factory=list)
    models: list[ModelDescriptor] = field(default_factory=list)

    @property
    def configured(self) -> bool:
        return all(bool(os.getenv(secret)) for secret in self.configured_by)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "kind": self.kind,
            "configured_by": self.configured_by,
            "configured": self.configured,
            "models": [model.__dict__ for model in self.models],
        }


def _load_catalog(kind: ProviderKind) -> list[ProviderDescriptor]:
    path = PROVIDER_CONFIG_DIR / f"{kind}.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    providers: list[ProviderDescriptor] = []
    for raw in data.get("providers", []):
        providers.append(
            ProviderDescriptor(
                id=raw["id"],
                label=raw.get("label", raw["id"]),
                kind=kind,
                configured_by=list(raw.get("configured_by") or []),
                models=[ModelDescriptor(**model) for model in raw.get("models", [])],
            )
        )
    return providers


def list_providers(kind: Optional[ProviderKind] = None) -> dict[str, list[dict[str, Any]]]:
    kinds: list[ProviderKind] = [kind] if kind else ["stt", "llm", "tts"]
    return {k: [provider.to_dict() for provider in _load_catalog(k)] for k in kinds}


def get_provider(kind: ProviderKind, provider_id: str) -> Optional[ProviderDescriptor]:
    for provider in _load_catalog(kind):
        if provider.id == provider_id:
            return provider
    return None


def _tenant_dict(tenant_cfg: Any, attr: str) -> dict[str, Any]:
    if isinstance(tenant_cfg, dict):
        value = tenant_cfg.get(attr) or {}
    else:
        value = getattr(tenant_cfg, attr, None) or {}
    return value if isinstance(value, dict) else {}


def instantiate_stt(
    tenant_cfg: Any,
    deepgram_api_key: str,
    *,
    keyterms: Optional[list[str]] = None,
):
    """Instantiate the currently supported STT providers.

    Supported runtime providers:
    - Deepgram Flux via DeepgramFluxSTTService when model starts with flux-
    - Deepgram Nova via DeepgramSTTService otherwise
    """
    from pipecat.services.deepgram.stt import DeepgramSTTService
    from server.brain.stt.deepgram_client import (
        build_flux_stt_settings,
        build_stt_settings,
        get_stt_endpoint,
        is_flux_model,
    )

    audio_cfg = _tenant_dict(tenant_cfg, "audio")
    provider_id = audio_cfg.get("stt_provider", "deepgram")
    if provider_id != "deepgram":
        raise ValueError(f"Runtime STT provider '{provider_id}' is not wired yet")

    settings_kwargs = build_stt_settings(tenant_cfg)
    if keyterms:
        settings_kwargs["keyterm"] = keyterms
    model_name = settings_kwargs.get("model", "nova-3")
    if is_flux_model(model_name):
        from pipecat.services.deepgram.stt import DeepgramFluxSTTService

        return DeepgramFluxSTTService(
            api_key=deepgram_api_key,
            **build_flux_stt_settings(tenant_cfg),
        )

    endpoint = get_stt_endpoint(tenant_cfg)
    kwargs: dict[str, Any] = {
        "api_key": deepgram_api_key,
        "settings": DeepgramSTTService.Settings(**settings_kwargs),
    }
    if endpoint:
        kwargs["base_url"] = endpoint
    return DeepgramSTTService(**kwargs)


DEFAULT_TTS_STYLE_PROMPT = (
    "Warm, natürlich und kompetent — wie eine freundliche Restaurantmitarbeiterin am Telefon."
)
DEFAULT_GEMINI_TTS_SPEAKING_RATE = 1.3


def instantiate_tts(
    tenant_cfg: Any,
    *,
    credentials_path: str,
    project_id: str,
):
    """Instantiate the currently supported TTS provider.

    Supported runtime provider today:
    - Google/Gemini via SaillyGeminiTTSService
    """
    from pipecat.services.google.tts import GeminiTTSService
    from server.sailly_gemini_tts import SaillyGeminiTTSService

    tts_cfg = _tenant_dict(tenant_cfg, "tts")
    provider_id = tts_cfg.get("tts_provider") or tts_cfg.get("provider") or "google"
    if provider_id not in {"google", "gemini-tts", "gemini-live"}:
        raise ValueError(f"Runtime TTS provider '{provider_id}' is not wired yet")

    voice = tts_cfg.get("voice") or getattr(tenant_cfg, "voice", "Kore")
    language = tts_cfg.get("language_code") or getattr(tenant_cfg, "locale", "de-DE")
    model = tts_cfg.get("model") or "gemini-2.5-flash-tts"
    speaking_rate = float(tts_cfg.get("speaking_rate") or DEFAULT_GEMINI_TTS_SPEAKING_RATE)
    style_prompt = tts_cfg.get("style_prompt") or DEFAULT_TTS_STYLE_PROMPT

    return SaillyGeminiTTSService(
        credentials_path=credentials_path,
        project_id=project_id,
        cascade_speaking_rate=speaking_rate,
        settings=GeminiTTSService.Settings(
            model=model,
            language=language,
            voice=voice,
            prompt=style_prompt,
        ),
    )


def runtime_provider_status() -> dict[str, Any]:
    return {
        "stt": {"wired": ["deepgram"], "notes": "Deepgram Flux/Nova runtime is active."},
        "llm": {"wired": ["tenant model config", "existing brain pipeline"], "notes": "Provider catalog is exposed; full LLM factory is a follow-up runtime migration."},
        "tts": {"wired": ["google", "gemini-tts", "gemini-live"], "notes": "Gemini/Sailly TTS runtime is active; other providers are catalog-only."},
    }
