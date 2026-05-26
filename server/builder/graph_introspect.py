"""Graph introspection engine for Flow Builder — v4 pipeline architecture.

Analyzes v4 brain sources to extract:
- Worker profiles (12 routing targets)
- Intent classifier rules (fast-path regex + Haiku fallback)
- Worker executor (parallel workers per profile, deadlines)
- Context doc builder (required slots, commit gates)
- Tiny generator (response assembly)
- GUARDIAN preconditions (executor-level gates)
- Tenant system (available tenants + config)

This replaces the legacy conversation_nodes / check_forced_commits introspection.
"""

import inspect
import os
import re
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SourceLocation:
    """Source file and line range for a code element."""
    file: str
    start_line: int
    end_line: int

    def to_dict(self) -> dict:
        return {"file": self.file, "start_line": self.start_line, "end_line": self.end_line}


_REPO_ROOT = str(Path(__file__).resolve().parents[2])


def _get_source_lines(obj: Any, repo_root: str = _REPO_ROOT) -> Optional[SourceLocation]:
    """Get source file and line range for a Python object."""
    try:
        source_file = inspect.getsourcefile(obj)
        if not source_file:
            return None
        
        if source_file.startswith(repo_root):
            rel_path = source_file[len(repo_root):].lstrip("/")
        else:
            rel_path = source_file
        
        lines, start_line = inspect.getsourcelines(obj)
        end_line = start_line + len(lines) - 1
        
        return SourceLocation(file=rel_path, start_line=start_line, end_line=end_line)
    except Exception as e:
        logger.debug(f"Could not get source lines: {e}")
        return None


def build_graph(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """Build the v4 pipeline architecture graph.
    
    Returns a graph structure representing:
    - 12 worker profiles (routing destinations)
    - Intent classification rules
    - Worker definitions (required, optional, scheduled tools)
    - Commit gate requirements
    - GUARDIAN preconditions
    """
    from server.brain.worker_router import _PROFILES, ALL_PROFILE_NAMES
    from server.brain import intent_classifier as ic_module
    from server.brain.intent_classifier import INTENT_TO_PROFILE, classify
    from server.brain.context_doc_builder import (
        COMMIT_TOOLS_REQUIRED_SLOTS,
        COMMIT_TOOLS_OPTIONAL_SLOTS,
    )
    from server.brain.intent_session import IntentKind
    from tools.executor import _GUARDIAN_PRECONDITIONS
    
    # Load tenant config if provided
    tenant_config = None
    if not tenant_id:
        tenant_id = "doboo"
    try:
        from server.core.tenant_config import get_tenant_registry
        registry = get_tenant_registry()
        tenant_config = registry.load_tenant(tenant_id)
    except Exception as e:
        logger.warning(f"Failed to load tenant config {tenant_id}: {e}")
    
    # ── Extract profiles ────────────────────────────────────────────────────────────
    
    _enabled_profiles = set(ALL_PROFILE_NAMES)
    if tenant_config is not None:
        pipeline_cfg = getattr(tenant_config, "pipeline", {}) or {}
        if isinstance(pipeline_cfg, dict) and isinstance(pipeline_cfg.get("enabled_profiles"), list):
            _enabled_profiles = set(str(x) for x in pipeline_cfg["enabled_profiles"])

    profiles = []
    for profile_name, execution_plan in sorted(_PROFILES.items()):
        if profile_name not in _enabled_profiles:
            continue
        profile_dict = {
            "id": profile_name,
            "label": profile_name.replace("_", " ").title(),
            "required_workers": [w.name for w in execution_plan.required],
            "optional_workers": [w.name for w in execution_plan.optional],
            "background_workers": [w.name for w in execution_plan.background],
            "scheduled_tools": execution_plan.scheduled_tools,
            "deadline_required_ms": execution_plan.deadline_required_ms,
            "deadline_optional_ms": execution_plan.deadline_optional_ms,
        }
        profiles.append(profile_dict)
    
    # ── Mark orphan profiles (in _PROFILES but no intent edges) ─────────────────────
    referenced_profiles = set(INTENT_TO_PROFILE.values())
    for p in profiles:
        p["orphan"] = p["id"] not in referenced_profiles

    # ── Extract intent → profile edges ──────────────────────────────────────────────

    intent_edges = []
    intent_profiles = []
    for intent, profile in INTENT_TO_PROFILE.items():
        if profile not in _enabled_profiles:
            profile = "greeting"
        edge_dict = {
            "from": f"intent_{intent.value}",
            "to": f"profile_{profile}",
            "label": intent.value,
            "kind": "intent_classification",
        }
        intent_edges.append(edge_dict)
        intent_profiles.append({
            "intent": intent.value,
            "turn_type": None,
            "profile": profile,
            "kind": "intent_classification",
        })

    # ── Extract intent classifier regex rules (Layer 1 fast-path) ───────────────────
    # Surface every _<NAME>_RE in intent_classifier so the builder can show the
    # actual patterns that drive routing, instead of pretending the system is opaque.
    intent_rules: List[Dict[str, Any]] = []
    for attr in dir(ic_module):
        if not (attr.startswith("_") and attr.endswith("_RE")):
            continue
        pattern_obj = getattr(ic_module, attr, None)
        if pattern_obj is None or not hasattr(pattern_obj, "pattern"):
            continue
        intent_rules.append({
            "id": attr.strip("_").lower(),  # e.g. _GREETING_RE -> "greeting_re"
            "name": attr.strip("_").replace("_RE", "").title(),  # "Greeting"
            "pattern": pattern_obj.pattern,
            "flags": "IGNORECASE" if (pattern_obj.flags & re.I) else "",
            "priority": _intent_rule_priority(attr),
        })
    intent_rules.sort(key=lambda r: r["priority"])

    # Turn-type routing summary (the order_check sequence in classify())
    intent_routing = {
        "turn_0": [
            "If reservation+faq keywords -> RESERVATION + ADD_INFORMATION",
            "If order+faq keywords -> TAKEAWAY + ADD_INFORMATION",
            "If reservation keywords -> RESERVATION",
            "If order keywords -> TAKEAWAY",
            "Else -> GREETING + START_INTENT",
        ],
        "later_turns": [
            "GOODBYE_RE -> GOODBYE + FINALIZE",
            "CONFIRM_RE (len<40) -> UNKNOWN + CONFIRM (intent locked)",
            "DENY_RE (len<40) -> UNKNOWN + DENY",
            "CORRECTION_RE -> UNKNOWN + CORRECT_PREVIOUS (-> correction profile)",
            "NAME/PHONE_SLOT_RE -> UNKNOWN + ADD_INFORMATION (slot-filling)",
            "PRICE_RE -> FAQ (BEFORE order check)",
            "Domain intents (RESERVATION/ORDER/FAQ/ESCALATION)",
            "Else -> Haiku async fallback (confidence < 0.6)",
        ],
    }

    profile_reroutes = [
        {
            "id": "unknown_to_reservation_on_keywords",
            "from_profiles": ["greeting", "business_info"],
            "to_profile": "reservation_start",
            "condition": "intent in (UNKNOWN, FAQ) and reservation_keywords",
            "source": "v4_pipeline keyword override",
        },
        {
            "id": "unknown_to_order_on_keywords",
            "from_profiles": ["greeting", "business_info"],
            "to_profile": "order_start",
            "condition": "intent in (UNKNOWN, FAQ) and order_keywords",
            "source": "v4_pipeline keyword override",
        },
        {
            "id": "slot_fill_to_reservation",
            "from_profiles": ["greeting", "business_info"],
            "to_profile": "reservation_start",
            "condition": "slot-fill continuation with reservation slots present",
            "source": "v4_pipeline slot hydration reroute",
        },
        {
            "id": "slot_fill_to_order",
            "from_profiles": ["greeting", "business_info"],
            "to_profile": "order_start",
            "condition": "slot-fill continuation with order slots present",
            "source": "v4_pipeline slot hydration reroute",
        },
    ]

    commit_gate_fsm = {
        "entry": "idle",
        "terminal": ["confirmed"],
        "states": [
            {"id": "idle", "label": "idle", "description": "Normal deterministic turn processing"},
            {"id": "pre_commit_readback", "label": "pre_commit_readback", "description": "Reservation readback before commit"},
            {"id": "order_pre_commit_readback", "label": "order_pre_commit_readback", "description": "Order readback before commit"},
            {"id": "readback_pending", "label": "readback_pending", "description": "Post-commit readback pending confirmation"},
            {"id": "correction_pending", "label": "correction_pending", "description": "Waiting for correction after denial"},
            {"id": "confirmed", "label": "confirmed", "description": "Commit accepted and closing"},
        ],
        "transitions": [
            {"from": "idle", "to": "pre_commit_readback", "on": "reservation slots full"},
            {"from": "idle", "to": "order_pre_commit_readback", "on": "order slots full"},
            {"from": "pre_commit_readback", "to": "idle", "on": "user confirms"},
            {"from": "pre_commit_readback", "to": "correction_pending", "on": "user denies"},
            {"from": "order_pre_commit_readback", "to": "idle", "on": "user confirms"},
            {"from": "order_pre_commit_readback", "to": "correction_pending", "on": "user denies"},
            {"from": "idle", "to": "readback_pending", "on": "commit succeeded"},
            {"from": "readback_pending", "to": "confirmed", "on": "user confirms"},
            {"from": "readback_pending", "to": "correction_pending", "on": "user denies"},
            {"from": "correction_pending", "to": "idle", "on": "corrections applied"},
        ],
    }

    # ── Extract commit gate requirements ────────────────────────────────────────────

    commit_gates = []
    for tool_name, required_slots in COMMIT_TOOLS_REQUIRED_SLOTS.items():
        gate_dict = {
            "tool": tool_name,
            "required_slots": required_slots,
            "optional_slots": COMMIT_TOOLS_OPTIONAL_SLOTS.get(tool_name, []),
        }
        commit_gates.append(gate_dict)
    
    # ── Extract GUARDIAN preconditions ──────────────────────────────────────────────
    
    guardian_rules = []
    for tool_name, preconditions in _GUARDIAN_PRECONDITIONS.items():
        rule_dict = {
            "tool": tool_name,
            "required_from_args": preconditions.get("required_from_args", []),
            "min_prior_assistant_turns": preconditions.get("min_prior_assistant_turns", 0),
        }
        guardian_rules.append(rule_dict)
    
    # ── Extract workers ─────────────────────────────────────────────────────────────
    
    from server.brain.workers.goodbye_detector import goodbye_detector
    from server.brain.workers.abuse_detector import abuse_detector
    from server.brain.workers.name_extractor import name_extractor
    from server.brain.workers.reservation_workers import date_parser, time_parser, party_size_parser, schema_validator
    from server.brain.workers.correction_workers import correction_detector, previous_turn_reference_resolver, state_delta_builder
    from server.brain.workers.confirmation_parser import confirmation_parser
    
    all_workers = {
        "goodbye_detector": goodbye_detector,
        "abuse_detector": abuse_detector,
        "name_extractor": name_extractor,
        "date_parser": date_parser,
        "time_parser": time_parser,
        "party_size_parser": party_size_parser,
        "schema_validator": schema_validator,
        "correction_detector": correction_detector,
        "previous_turn_reference_resolver": previous_turn_reference_resolver,
        "state_delta_builder": state_delta_builder,
        "confirmation_parser": confirmation_parser,
    }
    
    workers = []
    for worker_name, worker_obj in all_workers.items():
        source_loc = _get_source_lines(worker_obj.__class__)
        worker_dict = {
            "name": worker_name,
            "description": worker_obj.description if hasattr(worker_obj, "description") else "Worker",
            "source": source_loc.to_dict() if source_loc else None,
        }
        workers.append(worker_dict)

    # ── Build tool catalog (every handler registered in ALL_HANDLERS) ───────────────
    tool_catalog: List[Dict[str, Any]] = []
    try:
        from server.tools.handlers import ALL_HANDLERS  # type: ignore
        for tool_name, handler_fn in sorted(ALL_HANDLERS.items()):
            handler_source = _get_source_lines(handler_fn)
            tool_catalog.append({
                "name": tool_name,
                "is_commit_tool": tool_name in COMMIT_TOOLS_REQUIRED_SLOTS,
                "required_slots": COMMIT_TOOLS_REQUIRED_SLOTS.get(tool_name, []),
                "optional_slots": COMMIT_TOOLS_OPTIONAL_SLOTS.get(tool_name, []),
                "guardian": _GUARDIAN_PRECONDITIONS.get(tool_name, {}),
                "source": handler_source.to_dict() if handler_source else None,
                "description": (handler_fn.__doc__ or "").strip().split("\n")[0][:160],
            })
    except Exception as e:
        logger.warning(f"Could not build tool catalog: {e}")
    
    # ── Extract architecture layers ─────────────────────────────────────────────────
    
    # Dynamically determine STT model and TTS from tenant config
    stt_model_display = "Deepgram Nova-3 (default)"
    stt_service_class = "DeepgramSTTService"
    tts_model_display = "Gemini TTS"
    
    if tenant_config:
        try:
            # Get STT model from tenant audio config
            audio_cfg = getattr(tenant_config, "audio", {}) or {}
            if isinstance(audio_cfg, dict):
                configured_stt = audio_cfg.get("stt_model", "")
                if configured_stt:
                    stt_model_display = f"Deepgram {configured_stt}"
                    # Determine which service class is used
                    if configured_stt.lower().startswith("flux-"):
                        stt_service_class = "DeepgramFluxSTTService (EU endpoint, Flux semantics)"
                    else:
                        stt_service_class = "DeepgramSTTService"
                elif hasattr(tenant_config, "stt_language") and tenant_config.stt_language == "de":
                    stt_model_display = "Deepgram flux-general-multi (German)"
                    stt_service_class = "DeepgramFluxSTTService (EU endpoint, Flux semantics)"
                else:
                    stt_model_display = "Deepgram flux-general-multi"
                    stt_service_class = "DeepgramFluxSTTService (EU endpoint, Flux semantics)"
            
            # Get TTS from llm config if available
            llm_cfg = getattr(tenant_config, "llm", {}) or {}
            if isinstance(llm_cfg, dict):
                model = llm_cfg.get("model", "")
                if "gemini-live" in model.lower():
                    tts_model_display = "Gemini Live Audio (native)"
                elif "elevenlabs" in model.lower():
                    tts_model_display = "ElevenLabs"
                elif "gemini" in model.lower():
                    tts_model_display = "Gemini TTS"
        except Exception as e:
            logger.debug(f"Could not extract STT/TTS from tenant config: {e}")
    
    layers = [
        {
            "id": "layer_0_audio",
            "name": "Layer 0 - Audio",
            "description": f"{stt_service_class} · {stt_model_display}, VAD, Barge-in",
            "components": [stt_service_class, stt_model_display, "VAD", "Barge-in"],
        },
        {
            "id": "layer_1_intent",
            "name": "Layer 1 - Intent Classification",
            "description": "Regex fast-path + Haiku fallback",
            "components": ["Regex Rules", "Haiku LLM Fallback"],
        },
        {
            "id": "layer_2_route",
            "name": "Layer 2 - Worker Router",
            "description": "Intent + TurnType → ExecutionPlan (profile)",
            "components": ["worker_router.py"],
        },
        {
            "id": "layer_3_workers",
            "name": "Layer 3 - Worker Executor",
            "description": "Parallel workers (280ms/350ms deadlines)",
            "components": [w["name"] for w in workers],
        },
        {
            "id": "layer_4_context",
            "name": "Layer 4 - Context Document",
            "description": "ContextDocument + next_action (say/clarify/commit/end_call)",
            "components": ["context_doc_builder.py"],
        },
        {
            "id": "layer_5_commit",
            "name": "Layer 5 - Commit Gate",
            "description": "FSM (pre_commit → readback → create_order/reservation) + GUARDIAN",
            "components": ["v4_pipeline.py", "executor.py GUARDIAN"],
        },
        {
            "id": "layer_6_generate",
            "name": "Layer 6 - Generator",
            "description": "Haiku inner monologue + spoken German",
            "components": ["tiny_generator.py"],
        },
        {
            "id": "layer_7_tts",
            "name": "Layer 7 - TTS",
            "description": f"{tts_model_display}",
            "components": [tts_model_display],
        },
    ]
    
    # ── Extract tenant metadata ─────────────────────────────────────────────────────
    
    tenant_meta = {}
    if tenant_config:
        try:
            sp = getattr(tenant_config, "system_prompt", None)
            if sp:
                tenant_meta["system_prompt"] = sp
            # Channel info
            twilio = getattr(tenant_config, "twilio_numbers", None)
            tenant_meta["channels"] = {
                "voice": getattr(tenant_config, "audio", {}).get("voice", "Kore") if isinstance(getattr(tenant_config, "audio", None), dict) else "Kore",
                "stt_language": getattr(tenant_config, "stt_language", "de"),
                "twilio_numbers": list(twilio) if twilio else [],
                "restaurant_name": getattr(tenant_config, "restaurant_name", ""),
            }
        except Exception as e:
            logger.debug(f"Could not extract tenant meta: {e}")
    
    return {
        "schema_version": "v4.1",
        "tenant": tenant_id or "default",
        "profiles": profiles,
        "worker_plans": profiles,
        "workers": workers,
        "intent_profiles": intent_profiles,
        "intent_edges": intent_edges,
        "profile_reroutes": profile_reroutes,
        "intent_rules": intent_rules,
        "intent_routing": intent_routing,
        "commit_slot_gates": commit_gates,
        "commit_gates": commit_gates,
        "commit_gate_fsm": commit_gate_fsm,
        "guardian_rules": guardian_rules,
        "tool_catalog": tool_catalog,
        "layers": layers,
        "meta": tenant_meta,
    }


# Priority mirrors the actual order classify() checks patterns in.
_INTENT_RULE_PRIORITY = {
    "_GREETING_RE": 10,
    "_GOODBYE_RE": 20,
    "_CONFIRM_RE": 30,
    "_DENY_RE": 31,
    "_CORRECTION_RE": 40,
    "_NAME_SLOT_RE": 45,
    "_PHONE_SLOT_RE": 46,
    "_PRICE_RE": 50,
    "_RESERVATION_RE": 60,
    "_ORDER_RE": 61,
    "_FAQ_RE": 70,
    "_ESCALATION_RE": 80,
    "_FINALIZE_RE": 90,
}


def _intent_rule_priority(attr_name: str) -> int:
    return _INTENT_RULE_PRIORITY.get(attr_name, 999)


def list_tenants() -> List[Dict[str, str]]:
    """List all available tenant IDs and basic info from configs/tenants/*.yaml."""
    import yaml
    from server.core.tenant_config import tenant_config_dir

    tenants = []
    tenant_dir = tenant_config_dir()
    
    if not tenant_dir.exists():
        logger.warning(f"Tenant config directory not found: {tenant_dir}")
        return tenants
    
    for yaml_file in sorted(tenant_dir.glob("*.yaml")):
        try:
            with open(yaml_file) as f:
                config = yaml.safe_load(f)
            tenant_id = config.get("tenant_id", yaml_file.stem)
            industry = config.get("industry", "unknown")
            restaurant_name = config.get("restaurant_name", tenant_id)
            tenants.append({
                "id": tenant_id,
                "name": restaurant_name,
                "industry": industry,
                "stt_language": config.get("stt_language", "de-DE"),
                "twilio_numbers": config.get("twilio_numbers", []),
            })
        except Exception as e:
            logger.warning(f"Failed to parse tenant config {yaml_file}: {e}")
    
    return tenants


# Legacy compatibility: allow imports
__all__ = ["build_graph", "list_tenants", "SourceLocation"]
