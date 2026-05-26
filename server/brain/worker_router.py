"""
server/brain/worker_router.py — Worker Router.

Maps (worker_profile, turn_type) → ExecutionPlan.

All 12 profiles are live (MIGRATED_PROFILES = set of all keys).
The v4 pipeline is the single request path; there is no legacy fallback.
"""
from __future__ import annotations

import logging
from typing import Optional
from dataclasses import replace

from server.brain.intent_session import TurnType
from server.brain.workers import ExecutionPlan, Worker
from server.brain.workers.abuse_detector import abuse_detector
from server.brain.workers.confirmation_parser import confirmation_parser
from server.brain.workers.goodbye_detector import goodbye_detector
from server.brain.workers.name_extractor import name_extractor
from server.brain.workers.reservation_workers import (
    date_parser,
    party_size_parser,
    schema_validator,
    time_parser,
)
from server.brain.workers.correction_workers import (
    correction_detector,
    previous_turn_reference_resolver,
    state_delta_builder,
)

logger = logging.getLogger(__name__)

# ── Profile definitions ─────────────────────────────────────────────────────────

_PROFILES: dict[str, ExecutionPlan] = {

    "greeting": ExecutionPlan(
        profile_name="greeting",
        required=[goodbye_detector, abuse_detector],
        optional=[name_extractor],
        background=[],
        scheduled_tools=["ai_greeting", "get_date_info"],
        deadline_required_ms=280,
        deadline_optional_ms=350,
    ),

    "smalltalk": ExecutionPlan(
        profile_name="smalltalk",
        required=[goodbye_detector, abuse_detector],
        optional=[],
        background=[],
        # No unconditional weather — get_weather is fired only when the user
        # actually mentions weather (universal secondary tool detector).
        scheduled_tools=[],
        deadline_required_ms=280,
        deadline_optional_ms=350,
    ),

    "business_info": ExecutionPlan(
        profile_name="business_info",
        required=[goodbye_detector],
        optional=[],
        background=[],
        # get_date_info for hours/date FAQ; get_menu for dish/price FAQ.
        scheduled_tools=["get_date_info", "get_menu"],
        deadline_required_ms=280,
        deadline_optional_ms=500,
    ),

    "directions_lookup": ExecutionPlan(
        profile_name="directions_lookup",
        required=[goodbye_detector],
        optional=[],
        background=[],
        scheduled_tools=["get_directions"],
        deadline_required_ms=280,
        deadline_optional_ms=500,  # get_directions can be slow
    ),

    "parking_lookup": ExecutionPlan(
        profile_name="parking_lookup",
        required=[goodbye_detector],
        optional=[],
        background=[],
        scheduled_tools=["get_nearby_parking"],
        deadline_required_ms=280,
        deadline_optional_ms=500,
    ),

    "goodbye": ExecutionPlan(
        profile_name="goodbye",
        required=[goodbye_detector],
        optional=[],
        background=[],
        # end_call removed from scheduled_tools — was a 6s latency spike.
        # The brain_service / pipeline handles end-of-call signalling via
        # should_end=True from goodbye_detector + the readback state machine.
        scheduled_tools=[],
        deadline_required_ms=280,
        deadline_optional_ms=350,
    ),

    # Phase 6 profiles — reservation slot extractors + schema validator
    "reservation_start": ExecutionPlan(
        profile_name="reservation_start",
        required=[
            date_parser,
            time_parser,
            party_size_parser,
            schema_validator,
            goodbye_detector,
        ],
        optional=[name_extractor],
        background=[],
        scheduled_tools=["get_date_info"],
        deadline_required_ms=280,
        deadline_optional_ms=350,
    ),

    "reservation_availability": ExecutionPlan(
        profile_name="reservation_availability",
        required=[
            date_parser,
            time_parser,
            party_size_parser,
            schema_validator,
            goodbye_detector,
        ],
        optional=[],
        background=[],
        scheduled_tools=["check_availability"],
        deadline_required_ms=280,
        deadline_optional_ms=500,
    ),

    "correction": ExecutionPlan(
        profile_name="correction",
        required=[
            correction_detector,
            previous_turn_reference_resolver,
            state_delta_builder,
            goodbye_detector,
        ],
        optional=[],
        background=[],
        scheduled_tools=[],
        deadline_required_ms=280,
        deadline_optional_ms=350,
    ),

    # Phase 9 order profiles — workers populated from existing extractors.
    # Order-specific item resolvers are still future work; today we rely on
    # update_state_from_utterance to populate selected_items, plus name+goodbye.
    "order_start": ExecutionPlan(
        profile_name="order_start",
        required=[goodbye_detector, abuse_detector],
        optional=[name_extractor],
        background=[],
        scheduled_tools=["get_menu"],
        deadline_required_ms=280,
        deadline_optional_ms=500,
    ),

    "order_modify": ExecutionPlan(
        profile_name="order_modify",
        required=[
            previous_turn_reference_resolver,
            state_delta_builder,
            goodbye_detector,
        ],
        optional=[],
        background=[],
        scheduled_tools=[],
        deadline_required_ms=280,
        deadline_optional_ms=350,
    ),

    "escalation": ExecutionPlan(
        profile_name="escalation",
        required=[abuse_detector, goodbye_detector],
        optional=[name_extractor],
        background=[],
        scheduled_tools=[],
        deadline_required_ms=280,
        deadline_optional_ms=350,
    ),
}

# All profiles are live — v4 is the single pipeline, no legacy fallback.
MIGRATED_PROFILES: set[str] = set(_PROFILES.keys())
ALL_PROFILE_NAMES: tuple[str, ...] = tuple(_PROFILES.keys())
DEFAULT_FALLBACK_PROFILE = "greeting"


def _apply_profile_override(plan: ExecutionPlan, override: dict) -> ExecutionPlan:
    """Apply shallow, safe ExecutionPlan overrides from tenant pipeline config."""
    if not isinstance(override, dict):
        return plan
    kwargs = {}
    if isinstance(override.get("scheduled_tools"), list):
        kwargs["scheduled_tools"] = [str(x) for x in override["scheduled_tools"]]
    if isinstance(override.get("deadline_required_ms"), int):
        kwargs["deadline_required_ms"] = int(override["deadline_required_ms"])
    if isinstance(override.get("deadline_optional_ms"), int):
        kwargs["deadline_optional_ms"] = int(override["deadline_optional_ms"])
    return replace(plan, **kwargs) if kwargs else plan


def route(
    profile_name: str,
    turn_type: Optional[TurnType] = None,
    pipeline: Optional[dict] = None,
) -> ExecutionPlan:
    """Return the ExecutionPlan for a given worker profile.

    Falls back to 'greeting' profile if profile_name is unknown.
    The returned plan is a shared object — do not mutate it.
    """
    enabled_profiles = None
    profile_overrides = {}
    if isinstance(pipeline, dict):
        enabled_profiles = pipeline.get("enabled_profiles")
        profile_overrides = pipeline.get("profile_overrides") or {}

    if isinstance(enabled_profiles, list) and profile_name not in enabled_profiles:
        profile_name = DEFAULT_FALLBACK_PROFILE

    plan = _PROFILES.get(profile_name)
    if plan is None:
        logger.warning(f"[WorkerRouter] unknown profile '{profile_name}', using greeting")
        profile_name = DEFAULT_FALLBACK_PROFILE
        plan = _PROFILES[DEFAULT_FALLBACK_PROFILE]

    # Turn-type overrides
    if turn_type in (TurnType.CONFIRM, TurnType.DENY):
        # Confirmation turns only need confirmation_parser + goodbye_detector
        confirm_plan = ExecutionPlan(
            profile_name=f"{profile_name}_confirm",
            required=[goodbye_detector, confirmation_parser],
            optional=[],
            background=plan.background,
            scheduled_tools=[],
            deadline_required_ms=plan.deadline_required_ms,
            deadline_optional_ms=plan.deadline_optional_ms,
        )
        return _apply_profile_override(confirm_plan, profile_overrides.get(profile_name, {}))

    return _apply_profile_override(plan, profile_overrides.get(profile_name, {}))


def is_migrated(profile_name: str, pipeline: Optional[dict] = None) -> bool:
    """True if this profile runs live (not shadow-only)."""
    if isinstance(pipeline, dict):
        enabled = pipeline.get("enabled_profiles")
        if isinstance(enabled, list):
            return profile_name in enabled
    return profile_name in MIGRATED_PROFILES
