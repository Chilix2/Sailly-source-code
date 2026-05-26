from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TenantPipelineAudio(BaseModel):
    stt_model: Optional[str] = None
    stt_endpointing_ms: Optional[int] = Field(default=None, ge=100, le=3000)
    eot_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    eager_eot_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    smart_format: Optional[bool] = None


class TenantPipelineTTS(BaseModel):
    voice: Optional[str] = None
    language_code: Optional[str] = None
    speed_multiplier: Optional[float] = Field(default=None, ge=0.5, le=2.0)


class TenantPipelineSection(BaseModel):
    audio: Optional[TenantPipelineAudio] = None
    tts: Optional[TenantPipelineTTS] = None


class TenantProvisionRequest(BaseModel):
    tenant_id: str
    restaurant_name: str
    industry: str = "restaurant"
    language: str = "de"
    locale: str = "de-DE"
    city: str = "Bonn"
    system_prompt: str = ""
    greeting_line: str = ""
    farewell_text: str = ""
    location: Dict[str, Any] = Field(default_factory=dict)
    opening_hours: Dict[str, Any] = Field(default_factory=dict)
    pipeline: Optional[TenantPipelineSection] = None
    tools_minimal: bool = True
    dry_run: bool = False
    yaml: Optional[str] = None


class TenantProvisionResponse(BaseModel):
    tenant_id: str
    path: str
    created: bool
    validated: bool
    dry_run: bool = False
