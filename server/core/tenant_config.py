"""
Tenant configuration model for multi-tenant support.
Each tenant (client) has its own prompt, tools, tool data, and Twilio numbers.
"""

from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
import yaml
import os
import re
from pathlib import Path

class ToolDeclaration(BaseModel):
    """Tool definition for a tenant."""
    name: str
    description: str
    parameters: Optional[Dict[str, Any]] = None
    response_examples: Optional[List[str]] = None

class PracticeInfo(BaseModel):
    """Business/practice information specific to the tenant."""
    name: str
    location: str
    phone: Optional[str] = None
    email: Optional[str] = None
    hours: Optional[str] = None
    staff_count: Optional[int] = None
    specializations: Optional[List[str]] = None

class ToolData(BaseModel):
    """Dynamic business data for tool execution (menu, services, etc.)."""
    # For restaurants: menu items, pricing
    menu: Optional[Dict[str, Any]] = None
    # For medical: clinic info, doctors, services
    clinic_info: Optional[Dict[str, Any]] = None
    # For hotels: rooms, amenities, rates
    rooms: Optional[Dict[str, Any]] = None
    # For salons: services, pricing, staff
    services: Optional[Dict[str, Any]] = None
    # Generic custom data per industry
    custom: Optional[Dict[str, Any]] = None

class TenantConfig(BaseModel):
    """Complete tenant configuration."""
    tenant_id: str = Field(..., description="Unique tenant slug (e.g. 'doboo', 'praxis-ebert')")
    industry: str = Field(..., description="Industry type: restaurant, medical, hotel, beauty")
    
    # Twilio integration
    twilio_numbers: List[str] = Field(default_factory=list, description="Incoming Twilio numbers routed to this tenant")
    
    # LLM configuration
    system_prompt: str = Field(..., description="System instruction for Gemini Live")
    voice: Optional[str] = Field(default="Kore", description="Gemini Live voice")
    model: Optional[str] = Field(default="google/gemini-live-2.5-flash-native-audio", description="Model name")
    
    # Tools
    tools: List[ToolDeclaration] = Field(default_factory=list, description="Enabled tools for this tenant")
    
    # Business data
    practice: PracticeInfo = Field(..., description="Tenant's business information")
    tool_data: ToolData = Field(default_factory=ToolData, description="Dynamic data for tools")
    
    # Localization
    locale: str = Field(default="de-DE", description="Locale/language (de-DE, en-US, fr-FR, etc.)")
    # ISO-639-1 language code (e.g. "de", "en"). Drives STT language hints, LLM language
    # instructions, and response_variations pool selection. Use locale for BCP-47 TTS codes.
    language: str = Field(default="de", description="ISO-639-1 language code (e.g. 'de', 'en')")
    
    # TTS configuration (FINDING-019: moved from hardcoded tts/*.py to tenant YAML)
    tts: Dict[str, Any] = Field(
        default_factory=dict,
        description="TTS config: voice, language_code, speed_multiplier, pronunciations, etc."
    )
    
    # Legal/compliance
    # NOTE: We persist transcripts only, NOT raw audio. §201 StGB governs audio
    # recording and does NOT apply here. GDPR Art. 13 duty is satisfied by
    # privacy-policy-by-reference — no spoken "aufgezeichnet" claim.
    ai_disclosure_text: str = Field(
        default="Sie sprechen mit einer KI-gestützten Sprachassistentin. Hinweise zum Datenschutz finden Sie auf unserer Webseite.",
        description="AI disclosure text for TwiML <Say> before the stream connects"
    )

    # Centralized greeting line used for the first audible bot utterance.
    # Should contain "KI" (EU AI Act Art. 50) — tenant must supply.
    greeting_line: str = Field(
        default="",
        description="First audible line spoken to the caller; tenant must populate"
    )

    # Farewell text — tenant must populate
    farewell_text: str = Field(
        default="",
        description="Closing line spoken before end_call"
    )

    # Operational / retention
    transcript_retention_days: int = Field(
        default=90,
        description="How long transcripts (Redis + Postgres) are kept before the purge cron deletes them"
    )

    # POS integration (optional outgoing webhook after create_order)
    pos_webhook_url: Optional[str] = Field(
        default=None,
        description="If set, create_order will POST the order payload to this URL with retries"
    )

    # SMS ETA defaults (passed into format_order_message)
    estimated_delivery_minutes: int = Field(
        default=35,
        description="Default ETA (minutes) for delivery orders in SMS confirmations"
    )
    estimated_takeaway_minutes: int = Field(
        default=20,
        description="Default ETA (minutes) for takeaway orders in SMS confirmations"
    )

    # Audio pipeline configuration (raw dict from YAML ``audio:`` block)
    audio: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Audio pipeline config: stt_model, stt_endpoint, stt_endpointing_ms, smart_format, eot_threshold"
    )

    # Tenant-scoped pipeline behavior knobs (optional).
    # Defaults keep current global behavior.
    pipeline: Dict[str, Any] = Field(
        default_factory=dict,
        description="Pipeline overrides: enabled_profiles, intent_overrides, profile_overrides"
    )

    # Delivery zone configuration (Phase 6 extraction: no more hardcoded Bonn/Munich logic)
    delivery_config: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="delivery",
        description="Delivery rules: rejected_cities (list), rejected_postcode_prefixes (list), zone_polygon (list)"
    )

    # C2: Restaurant identity fields — now sourced from YAML; avoid hardcoding in Python
    restaurant_name: str = Field(
        default="",
        description="Restaurant trading name (e.g. 'DOBOO Korean Soulfood')"
    )
    cuisine_type: str = Field(
        default="",
        description="Cuisine description for prompts"
    )
    location: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Location dict: address, city, lat, lng, parking, postcode_prefix (e.g. '53' for Bonn)"
    )
    opening_hours: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Opening hours dict: monday..sunday, formatted"
    )
    menu: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Menu dict: categories[].items[].name/price/description"
    )

    # STT language — Nova-3 supports 'multi' for code-switching in the same endpoint
    stt_language: str = Field(
        default="de",
        description="Deepgram Nova-3 language code. Use 'multi' for code-switching"
    )

    # Reservation capacity (Sprint 2): how many seats exist per 30-minute slot.
    # Used by check_availability to determine if a reservation can be booked.
    reservation_capacity_per_slot: int = Field(
        default=10,
        description="Max concurrent reservations per 30-minute slot (restaurant capacity)"
    )

    # Order quantity ceiling (Phase 3): guards against catering orders
    max_order_quantity: int = Field(
        default=30,
        description="Hard ceiling on order quantity; above this requires human approval (catering)"
    )

    # Coordinates (for restaurant info, nearby parking, etc.)
    coordinates: Optional[Dict[str, float]] = Field(
        default=None,
        description="{'lat': 50.7323, 'lng': 7.0954} for restaurant location"
    )

    # City (for defaults in address normalization)
    city: str = Field(default="Bonn", description="Default city for address normalization")

    # NLU / training fields — used by NodeManager, adk_turn_processor, main.py
    agent_name: str = Field(default="Sailly", description="Bot name for greetings")
    greeting_prefix: str = Field(
        default="Hallo, hier ist Sailly, die KI-Assistentin. ",
        description="Opening phrase prefix used by NodeManager for dynamic greetings"
    )
    hours_formatted: str = Field(
        default="",
        description="Human-readable opening hours injected into prompts"
    )
    formality: str = Field(default="Sie", description="Grammatical formality: Sie or du")
    state_extraction: str = Field(default="keyword", description="Slot extraction strategy")

    @property
    def formality_rule(self) -> str:
        """Returns a prompt rule string for the configured formality level."""
        if self.formality.lower() == "du":
            return "Sprich den Kunden mit 'du' an (informelle Anrede).\n"
        return "Sprich den Kunden mit 'Sie' an (formelle Anrede).\n"

    # Menu item names — used for STT keyword biasing and slot extraction
    items: List[str] = Field(
        default_factory=list,
        description="Known menu item names for ASR keyword biasing and NLU slot extraction"
    )

    # ── Priority 1 Hardcodes Extraction ────────────────────────────────────────
    # These fields replace hardcoded values in v4_pipeline_legacy.py and conversation_state.py
    
    # B6: Multi-intent fallback dish for menu_price injection (reservation + FAQ price intent)
    multi_intent_fallback_dish: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Fallback dish for multi-intent (reservation + menu_price): {name, price, note}"
    )

    # #5: Friday split hours (if restaurant is closed midday Friday)
    friday_hours_lunch: Optional[str] = Field(
        default=None,
        description="Friday lunch hours (e.g. '11:30–14:00'); None if not split"
    )
    friday_hours_dinner: Optional[str] = Field(
        default=None,
        description="Friday dinner hours (e.g. '18:00–21:30'); None if not split"
    )

    # B7: Menu items that definitely don't exist (prevent price_falsch)
    menu_items_nonexistent: List[str] = Field(
        default_factory=list,
        description="List of canonical menu item names known to NOT exist on this menu (e.g. ['kimchi jjigae'])"
    )

    # B8: Variant fallbacks for dish extraction (handle common menu variants)
    dish_variants_fallback: List[str] = Field(
        default_factory=list,
        description="Known dish variant names for fallback when exact match not found (e.g. ['Korean Pancake Kimchi', 'Bibimbap Rind'])"
    )

    # #6: Farewell options for post-confirmation and general completion
    farewell_options_list: List[str] = Field(
        default_factory=list,
        description="Rotating farewell phrases after confirmation (e.g. ['Vielen Dank und auf Wiederhören!', ...])"
    )

    # Post-commitment farewell options (after order/reservation committed, user speaks again)
    post_commit_farewell_options: List[str] = Field(
        default_factory=list,
        description="Short farewell options after commitment (e.g. ['Bis bald bei uns — auf Wiederhören!', ...])"
    )

    # Idempotency guard farewell (order already created)
    order_already_created_farewell: str = Field(
        default="Ihre Bestellung ist bereits aufgenommen. Vielen Dank und auf Wiederhören!",
        description="Farewell when order was already created (idempotency guard)"
    )

    # Extra ASR keyword lists for order, menu, reservation and FAQ domains
    extra_order_keywords: List[str] = Field(default_factory=list)
    extra_menu_keywords: List[str] = Field(default_factory=list)
    extra_reservation_keywords: List[str] = Field(default_factory=list)
    extra_faq_keywords: List[str] = Field(default_factory=list)

    def asr_keywords(self) -> List[str]:
        """Return combined ASR keyword biasing list for Deepgram."""
        seen: set = set()
        result: List[str] = []
        all_kw = (
            self.items
            + self.extra_order_keywords
            + self.extra_menu_keywords
            + self.extra_reservation_keywords
            + self.extra_faq_keywords
        )
        for kw in all_kw:
            kw_lower = kw.lower()
            if kw_lower not in seen:
                seen.add(kw_lower)
                result.append(kw)
        return result

    @classmethod
    def load_from_file(cls, path: str) -> "TenantConfig":
        """Load tenant config from YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    @classmethod
    def load_all_from_directory(cls, directory: str) -> Dict[str, "TenantConfig"]:
        """Load all tenant configs from a directory (one YAML per tenant)."""
        tenants = {}
        for filename in os.listdir(directory):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                tenant_id = filename.replace(".yaml", "").replace(".yml", "")
                path = os.path.join(directory, filename)
                try:
                    tenants[tenant_id] = cls.load_from_file(path)
                except Exception as e:
                    print(f"Failed to load tenant {tenant_id} from {path}: {e}")
        return tenants


# ── Tenant registry singleton ──────────────────────────────────────────────────

_TENANT_CONFIG_DIR = os.path.join(
    os.path.dirname(__file__),  # server/core/
    "..", "..", "configs", "tenants"
)

_TENANT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")


def normalize_tenant_id(raw: str) -> str:
    tid = (raw or "").strip().lower()
    if not tid or not _TENANT_ID_RE.match(tid):
        raise ValueError(f"invalid tenant_id: {raw!r}")
    return tid


def tenant_config_dir() -> Path:
    return Path(os.path.normpath(_TENANT_CONFIG_DIR))


def tenant_yaml_path(tenant_id: str) -> Optional[Path]:
    tid = normalize_tenant_id(tenant_id)
    root = tenant_config_dir()
    for ext in (".yaml", ".yml"):
        candidate = root / f"{tid}{ext}"
        if candidate.exists():
            return candidate
    return None


def list_known_tenant_ids() -> List[str]:
    root = tenant_config_dir()
    if not root.exists():
        return []
    out: List[str] = []
    for p in root.iterdir():
        if p.is_file() and p.suffix in (".yaml", ".yml"):
            out.append(p.stem)
    return sorted(set(out))


class TenantRegistry:
    """Loads and caches TenantConfig objects from the configs/tenants/ directory."""

    _cache: Dict[str, TenantConfig] = {}
    _mtime: Dict[str, float] = {}

    def load_tenant(self, tenant_id: str) -> TenantConfig:
        tid = normalize_tenant_id(tenant_id)
        config_dir = os.path.normpath(_TENANT_CONFIG_DIR)
        for ext in (".yaml", ".yml"):
            path = os.path.join(config_dir, f"{tid}{ext}")
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                if tid in self._cache and self._mtime.get(tid) == mtime:
                    return self._cache[tid]
                tc = TenantConfig.load_from_file(path)
                if normalize_tenant_id(tc.tenant_id) != tid:
                    raise ValueError(
                        f"tenant_id mismatch: file {tid}{ext} has tenant_id={tc.tenant_id!r}"
                    )
                self._cache[tid] = tc
                self._mtime[tid] = mtime
                return tc
        raise FileNotFoundError(
            f"No tenant config found for '{tid}' in {config_dir}"
        )

    def load_all(self) -> Dict[str, TenantConfig]:
        config_dir = os.path.normpath(_TENANT_CONFIG_DIR)
        return TenantConfig.load_all_from_directory(config_dir)

    def exists(self, tenant_id: str) -> bool:
        try:
            return tenant_yaml_path(tenant_id) is not None
        except ValueError:
            return False

    def invalidate_tenant(self, tenant_id: str) -> None:
        tid = normalize_tenant_id(tenant_id)
        self._cache.pop(tid, None)
        self._mtime.pop(tid, None)

    def invalidate_all(self) -> None:
        self._cache.clear()
        self._mtime.clear()


_registry_singleton: Optional[TenantRegistry] = None


def get_tenant_registry() -> TenantRegistry:
    global _registry_singleton
    if _registry_singleton is None:
        _registry_singleton = TenantRegistry()
    return _registry_singleton


def load_tenant_config(tenant_id: str) -> TenantConfig:
    """Load a tenant config by ID from the canonical configs/tenants/ directory."""
    return get_tenant_registry().load_tenant(tenant_id)


def require_tenant_config(tenant_id: str) -> TenantConfig:
    """Strict tenant lookup with normalization + typed config load."""
    return get_tenant_registry().load_tenant(tenant_id)
