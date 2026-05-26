"""
server/configs/tenant_schema.py
---------------------------------
Pydantic v2 schema for the ``configs/tenants/<id>.yaml`` files.

Validates required fields at startup and provides typed access to all
restaurant-specific fields that were previously hardcoded in brain files.

Usage::

    from server.configs.tenant_schema import TenantSchema, load_and_validate
    schema = load_and_validate("configs/tenants/doboo.yaml")

Raises ``pydantic.ValidationError`` on startup if required fields are missing,
preventing the server from running with a misconfigured tenant.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import yaml

try:
    from pydantic import BaseModel, Field, field_validator, model_validator
    _PYDANTIC_V2 = True
except ImportError:
    from pydantic import BaseModel, Field, validator as field_validator  # type: ignore
    _PYDANTIC_V2 = False


class MenuItem(BaseModel):
    """A single menu item."""
    name: str
    price: float = 0.0
    description: str = ""
    vegetarian: bool = False
    vegan: bool = False
    allergens: List[str] = Field(default_factory=list)


class MenuCategory(BaseModel):
    """A category of menu items."""
    name: str
    items: List[MenuItem] = Field(default_factory=list)


class MenuSchema(BaseModel):
    """Full menu structure."""
    categories: List[MenuCategory] = Field(default_factory=list)

    def all_item_names(self) -> List[str]:
        """Return flat list of all item names."""
        return [item.name for cat in self.categories for item in cat.items]


class LocationSchema(BaseModel):
    """Restaurant location and coordinates."""
    address: str = ""
    address_secondary: str = ""
    city: str = "Bonn"
    lat: Optional[float] = None
    lng: Optional[float] = None
    parking: str = ""


class OpeningHoursSchema(BaseModel):
    """Structured opening hours."""
    monday: str = ""
    tuesday: str = ""
    wednesday: str = ""
    thursday: str = ""
    friday: str = ""
    saturday: str = ""
    sunday: str = ""
    formatted: str = ""  # human-readable one-liner for prompts


class AudioSchema(BaseModel):
    """Audio pipeline configuration."""
    stt_model: str = "nova-3"
    stt_endpoint: Optional[str] = None
    stt_endpointing_ms: int = 700
    smart_format: bool = True
    eot_threshold: float = 0.7
    eager_eot_threshold: float = 0.5


class PreOrderSchema(BaseModel):
    """Pre-order / kitchen prep configuration."""
    kitchen_prep_minutes: int = 30


class ProfileOverrideSchema(BaseModel):
    """Shallow runtime overrides for a worker profile."""
    scheduled_tools: Optional[List[str]] = None
    deadline_required_ms: Optional[int] = Field(default=None, ge=100, le=2000)
    deadline_optional_ms: Optional[int] = Field(default=None, ge=100, le=3000)


class PipelineSchema(BaseModel):
    """Tenant-scoped pipeline overrides with safe defaults."""
    enabled_profiles: Optional[List[str]] = None
    intent_overrides: Dict[str, str] = Field(default_factory=dict)
    profile_overrides: Dict[str, ProfileOverrideSchema] = Field(default_factory=dict)

    @field_validator("enabled_profiles")
    @classmethod
    def _non_empty_if_set(cls, v):
        if v is not None and len(v) == 0:
            raise ValueError("enabled_profiles cannot be empty")
        return v

    if _PYDANTIC_V2:
        @model_validator(mode="after")
        def _validate_names(self):
            from server.brain.intent_session import IntentKind
            from server.brain.worker_router import ALL_PROFILE_NAMES

            known = set(ALL_PROFILE_NAMES)
            enabled = set(self.enabled_profiles) if self.enabled_profiles else known

            for p in (self.enabled_profiles or []):
                if p not in known:
                    raise ValueError(f"unknown profile '{p}'")

            if "greeting" not in enabled:
                raise ValueError("greeting must remain enabled (fallback profile)")

            valid_intents = {k.value for k in IntentKind}
            for intent, prof in self.intent_overrides.items():
                if intent not in valid_intents:
                    raise ValueError(f"unknown intent '{intent}'")
                if prof not in known:
                    raise ValueError(f"intent_overrides.{intent}: unknown profile '{prof}'")
                if prof not in enabled:
                    raise ValueError(f"intent_overrides.{intent}: '{prof}' not in enabled_profiles")

            for prof in self.profile_overrides:
                if prof not in known:
                    raise ValueError(f"unknown profile_overrides key '{prof}'")
                if prof not in enabled:
                    raise ValueError(f"profile_overrides.{prof}: profile not enabled")
            return self


class TenantSchema(BaseModel):
    """
    Full tenant configuration schema.

    Required at startup:
      - tenant_id
      - restaurant_name
      - industry

    All other fields have sensible defaults.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    tenant_id: str
    industry: str
    restaurant_name: str = ""

    # ── Vertical content ──────────────────────────────────────────────────────
    cuisine_type: str = ""
    location: LocationSchema = Field(default_factory=LocationSchema)
    opening_hours: OpeningHoursSchema = Field(default_factory=OpeningHoursSchema)
    menu: MenuSchema = Field(default_factory=MenuSchema)
    pre_order: PreOrderSchema = Field(default_factory=PreOrderSchema)

    # ── Audio ─────────────────────────────────────────────────────────────────
    audio: AudioSchema = Field(default_factory=AudioSchema)
    pipeline: PipelineSchema = Field(default_factory=PipelineSchema)

    # ── LLM / Voice ───────────────────────────────────────────────────────────
    system_prompt: str = ""
    greeting_line: str = ""
    farewell_text: str = ""
    voice: str = "Kore"
    model: str = "gemini-2.5-flash"
    stt_language: str = "de"

    # ── Operations ────────────────────────────────────────────────────────────
    twilio_numbers: List[str] = Field(default_factory=list)
    pos_webhook_url: Optional[str] = None
    transcript_retention_days: int = 90
    estimated_delivery_minutes: int = 35
    estimated_takeaway_minutes: int = 20

    # ── NLU ───────────────────────────────────────────────────────────────────
    agent_name: str = "Sailly"
    formality: str = "Sie"
    items: List[str] = Field(default_factory=list)  # legacy ASR keyword list
    extra_order_keywords: List[str] = Field(default_factory=list)
    extra_menu_keywords: List[str] = Field(default_factory=list)
    extra_reservation_keywords: List[str] = Field(default_factory=list)
    extra_faq_keywords: List[str] = Field(default_factory=list)

    # Allow extra fields from legacy YAML (e.g. TenantConfig-only fields)
    model_config = {"extra": "allow"} if _PYDANTIC_V2 else None  # type: ignore

    def all_menu_item_names(self) -> List[str]:
        """Return all menu item names — primary source for ASR biasing."""
        return self.menu.all_item_names()

    def opening_hours_string(self) -> str:
        """Return formatted opening hours string for prompts."""
        return self.opening_hours.formatted or (
            f"Mo–Do {self.opening_hours.monday} | "
            f"Fr {self.opening_hours.friday} | "
            f"Sa {self.opening_hours.saturday} | "
            f"So {self.opening_hours.sunday}"
        )


def load_and_validate(path: str) -> TenantSchema:
    """Load a tenant YAML file and validate it against TenantSchema.

    Raises:
        pydantic.ValidationError: if required fields are missing or invalid.
        FileNotFoundError: if the YAML file does not exist.
    """
    with open(path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = yaml.safe_load(f) or {}
    return TenantSchema.model_validate(data) if _PYDANTIC_V2 else TenantSchema(**data)


def validate_all_tenants(configs_dir: str = "configs/tenants") -> Dict[str, TenantSchema]:
    """Validate all tenant YAML files in *configs_dir*.

    Returns dict of {tenant_id: TenantSchema}.
    Prints validation errors but does NOT raise — allows partial startup.
    """
    import os
    results: Dict[str, TenantSchema] = {}
    for fname in sorted(os.listdir(configs_dir)):
        if not (fname.endswith(".yaml") or fname.endswith(".yml")):
            continue
        path = os.path.join(configs_dir, fname)
        try:
            schema = load_and_validate(path)
            results[schema.tenant_id] = schema
        except Exception as exc:
            print(f"[TenantSchema] VALIDATION FAILED for {path}: {exc}")
    return results
