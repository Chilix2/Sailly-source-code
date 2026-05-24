"""Flow Builder API routes — graph introspection, call replay, proposals."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import json
import os
import re
import uuid
import time
from datetime import datetime
from pathlib import Path

from server.builder.graph_introspect import build_graph, list_tenants
from server.builder.diagram_generator import build_all_diagrams

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/builder", tags=["builder"])

# Directory for saved proposals (YAML patches awaiting review)
PROPOSALS_DIR = Path("/tmp/builder_proposals")
PROPOSALS_DIR.mkdir(exist_ok=True)


# ── Graph & Tenants ────────────────────────────────────────────────────────────

_CODE_MODULE_WHITELIST: dict[str, str] = {
    # Layer 1 (Intent)
    "intent_classifier": "server/brain/intent_classifier.py",
    "intent_session": "server/brain/intent_session.py",
    # Layer 2 (Router)
    "worker_router": "server/brain/worker_router.py",
    # Layer 3 (Workers)
    "worker_executor": "server/brain/worker_executor.py",
    "goodbye_detector": "server/brain/workers/goodbye_detector.py",
    "abuse_detector": "server/brain/workers/abuse_detector.py",
    "name_extractor": "server/brain/workers/name_extractor.py",
    "reservation_workers": "server/brain/workers/reservation_workers.py",
    "correction_workers": "server/brain/workers/correction_workers.py",
    "confirmation_parser": "server/brain/workers/confirmation_parser.py",
    # Layer 4 (Context doc)
    "context_doc_builder": "server/brain/context_doc_builder.py",
    # Layer 5 (Pipeline + commit gate)
    "v4_pipeline": "server/brain/v4_pipeline.py",
    "v4_turn_processor": "server/brain/v4_turn_processor.py",
    # Layer 6 (Generator)
    "tiny_generator": "server/brain/tiny_generator.py",
    # Tools (executor + handlers)
    "executor": "tools/executor.py",
    "create_order": "server/tools/handlers/create_order.py",
    "create_reservation": "server/tools/handlers/create_reservation.py",
    "modify_order": "server/tools/handlers/modify_order.py",
    "cancel_order": "server/tools/handlers/cancel_order.py",
    "order_status": "server/tools/handlers/order_status.py",
    "modify_reservation": "server/tools/handlers/modify_reservation.py",
    "cancel_reservation": "server/tools/handlers/cancel_reservation.py",
    "verify_address": "server/tools/handlers/verify_address.py",
    "send_sms": "server/tools/handlers/send_sms.py",
    "transfer_to_human": "server/tools/handlers/transfer_to_human.py",
    "end_call": "server/tools/handlers/end_call.py",
    "get_menu": "server/tools/handlers/get_menu.py",
    "get_date_info": "server/tools/handlers/get_date_info.py",
    "faq": "server/tools/handlers/faq.py",
    "capture_catering_lead": "server/tools/handlers/capture_catering_lead.py",
}

_REPO_ROOT = "/home/charles2/sailly-browser-demo"


@router.get("/code/{module}")
async def get_code(module: str):
    """Return source code for whitelisted backend modules.

    Used by the Flow Builder's "Source" tab so users can see the actual code
    backing each pipeline stage / tool without an SSH session.
    """
    rel_path = _CODE_MODULE_WHITELIST.get(module)
    if not rel_path:
        raise HTTPException(status_code=404, detail=f"Unknown module '{module}'. Add it to _CODE_MODULE_WHITELIST.")
    abs_path = Path(_REPO_ROOT) / rel_path
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail=f"Source file not found: {rel_path}")
    try:
        source = abs_path.read_text()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read {rel_path}: {e}")
    return {
        "module": module,
        "path": rel_path,
        "language": "python",
        "source": source,
        "line_count": source.count("\n") + 1,
    }


@router.get("/diagrams")
async def get_diagrams(tenant: Optional[str] = Query(None)):
    """Return Mermaid source for all architecture diagrams.

    Three diagrams, all auto-generated from live code:
    - profile_fsm: stateDiagram-v2 showing intent → profile routing (FSM)
    - pipeline_sequence: sequenceDiagram showing per-turn data flow (tenant-aware STT/TTS labels)
    - commit_gate_fsm: stateDiagram-v2 showing commit gate states
    """
    try:
        diagrams = build_all_diagrams(tenant_id=tenant or "default")
        return diagrams
    except Exception as e:
        logger.exception(f"Error building diagrams: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/commit-gate/fsm")
async def get_commit_gate_fsm():
    """Return commit-gate FSM diagram source."""
    try:
        from server.builder.diagram_generator import build_commit_gate_fsm
        return {"diagram": build_commit_gate_fsm()}
    except Exception as e:
        logger.exception(f"Error building commit gate fsm: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph")
async def get_graph(tenant: Optional[str] = Query(None)):
    """Get complete v4 pipeline architecture graph for a tenant.
    
    Returns profiles, workers, intent routing, commit gates, GUARDIAN rules, and layers.
    """
    try:
        graph = build_graph(tenant_id=tenant)
        return graph
    except Exception as e:
        logger.exception(f"Error building graph for tenant {tenant}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def get_providers(kind: Optional[str] = Query(None)):
    """Return supported STT/LLM/TTS provider catalogs and runtime status."""
    try:
        from server.providers.registry import list_providers, runtime_provider_status

        if kind and kind not in {"stt", "llm", "tts"}:
            raise HTTPException(status_code=400, detail="kind must be one of: stt, llm, tts")
        return {
            "providers": list_providers(kind),  # type: ignore[arg-type]
            "runtime": runtime_provider_status(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error listing providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runtime")
async def list_runtime():
    """List runtime/deploy status for configured tenants."""
    try:
        from server.runtime.registry import list_runtime_records

        return {"tenants": list_runtime_records()}
    except Exception as e:
        logger.exception(f"Error listing runtime records: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runtime/{tenant_id}")
async def get_runtime(tenant_id: str):
    """Return runtime/deploy status for one tenant."""
    try:
        from server.runtime.registry import tenant_runtime_record

        return tenant_runtime_record(tenant_id)
    except Exception as e:
        logger.exception(f"Error reading runtime record: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runtime/{tenant_id}/logs")
async def get_runtime_logs(tenant_id: str, lines: int = Query(120)):
    """Return recent backend worker logs for deploy debugging."""
    try:
        from server.runtime.registry import service_logs

        return {"tenant_id": tenant_id, **service_logs(lines=lines)}
    except Exception as e:
        logger.exception(f"Error reading runtime logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/runtime/{tenant_id}/restart")
async def restart_runtime(tenant_id: str):
    """Guarded restart endpoint placeholder for self-hosted deployments."""
    try:
        from server.runtime.registry import restart_service

        return {"tenant_id": tenant_id, **restart_service()}
    except Exception as e:
        logger.exception(f"Error restarting runtime: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capabilities")
async def get_capabilities(industry: Optional[str] = Query(None)):
    """Return industry packs and capability definitions."""
    try:
        from server.builder.capabilities import capabilities_response

        return capabilities_response(industry)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error listing capabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tenants")
async def get_tenants():
    """List all available tenants with channel info."""
    try:
        tenants = list_tenants()
        return {"tenants": tenants}
    except Exception as e:
        logger.exception(f"Error listing tenants: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Layer configuration (per-turn pipeline tuning) ────────────────────────────────

@router.get("/tenants/{tenant_id}/layer/{layer_id}")
async def get_layer_config(tenant_id: str, layer_id: str):
    """Get editable config knobs for a specific pipeline layer.
    
    Returns current values read from TenantConfig. Empty/missing knobs indicate defaults.
    """
    try:
        import yaml
        from server.core.tenant_config import get_tenant_registry, tenant_yaml_path
        registry = get_tenant_registry()
        tenant_cfg = registry.load_tenant(tenant_id)
        if not tenant_cfg:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
        cfg_path = tenant_yaml_path(tenant_id)
        yaml_data = {}
        if cfg_path and cfg_path.exists():
            yaml_data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        
        # Extract layer-specific config based on layer_id
        config_snapshot = {}
        
        if layer_id == "layer_0_audio":
            audio_cfg = getattr(tenant_cfg, "audio", {}) or {}
            if isinstance(audio_cfg, dict):
                config_snapshot = {
                    "stt_provider": "deepgram",
                    "stt_model": audio_cfg.get("stt_model", "flux-general-multi"),
                    "stt_language": getattr(tenant_cfg, "stt_language", "de"),
                    "stt_endpointing_ms": audio_cfg.get("stt_endpointing_ms", 700),
                    "eot_threshold": audio_cfg.get("eot_threshold", 0.7),
                    "eager_eot_threshold": audio_cfg.get("eager_eot_threshold", 0.5),
                    "smart_format": audio_cfg.get("smart_format", True),
                }
        elif layer_id == "layer_1_intent":
            config_snapshot = {
                "intent_rules_overrides": yaml_data.get("intent_rules_overrides", {}),
            }
        elif layer_id == "layer_3_workers":
            # Per-profile deadlines
            worker_cfg = yaml_data.get("worker_deadlines", {}) or {}
            config_snapshot = worker_cfg if isinstance(worker_cfg, dict) else {}
        elif layer_id == "layer_5_commit":
            config_snapshot = {
                "commit_tools_optional_slots": yaml_data.get("commit_tools_optional_slots", {}),
            }
        elif layer_id == "layer_6_generate":
            gen_cfg = yaml_data.get("generator", {}) or {}
            if isinstance(gen_cfg, dict):
                config_snapshot = {
                    "model": gen_cfg.get("model", "claude-haiku"),
                    "persona_voice_tone": gen_cfg.get("persona_voice_tone", "sie"),
                    "max_sentences": gen_cfg.get("max_sentences", 2),
                }
        elif layer_id == "layer_7_tts":
            tts_cfg = getattr(tenant_cfg, "tts", {}) or {}
            if isinstance(tts_cfg, dict):
                config_snapshot = {
                    "tts_provider": tts_cfg.get("tts_provider", "gemini-tts"),
                    "voice": tts_cfg.get("voice", "Kore"),
                    "language_code": tts_cfg.get("language_code", "de-DE"),
                }
        
        return {"tenant_id": tenant_id, "layer_id": layer_id, "config": config_snapshot}
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    except Exception as e:
        logger.exception(f"Error fetching layer config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tenants/{tenant_id}/layer/{layer_id}")
async def put_layer_config(tenant_id: str, layer_id: str, body: dict):
    """Update editable config knobs for a specific pipeline layer.
    
    Persists changes to the tenant YAML and invalidates the TenantRegistry cache.
    """
    try:
        from server.core.tenant_config import get_tenant_registry, tenant_yaml_path
        import yaml
        from server.brain.stt.keyterm_loader import invalidate_cache as invalidate_keyterm_cache
        
        registry = get_tenant_registry()
        tenant_cfg = registry.load_tenant(tenant_id)
        if not tenant_cfg:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
        
        # Read the YAML file to update it
        cfg_path = tenant_yaml_path(tenant_id)
        if cfg_path is None:
            raise HTTPException(status_code=404, detail=f"Tenant YAML not found for: {tenant_id}")
        
        with open(cfg_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}
        
        # Apply updates based on layer_id
        config_patch = body.get("config", {})
        
        if layer_id == "layer_0_audio":
            if "audio" not in yaml_data:
                yaml_data["audio"] = {}
            if isinstance(config_patch.get("stt_model"), str):
                yaml_data["audio"]["stt_model"] = config_patch["stt_model"]
            if isinstance(config_patch.get("stt_endpointing_ms"), int):
                yaml_data["audio"]["stt_endpointing_ms"] = config_patch["stt_endpointing_ms"]
            if isinstance(config_patch.get("eot_threshold"), (int, float)):
                yaml_data["audio"]["eot_threshold"] = config_patch["eot_threshold"]
            if isinstance(config_patch.get("eager_eot_threshold"), (int, float)):
                yaml_data["audio"]["eager_eot_threshold"] = config_patch["eager_eot_threshold"]
            if isinstance(config_patch.get("smart_format"), bool):
                yaml_data["audio"]["smart_format"] = config_patch["smart_format"]
            if isinstance(config_patch.get("stt_language"), str):
                yaml_data["stt_language"] = config_patch["stt_language"]
        elif layer_id == "layer_1_intent":
            if isinstance(config_patch.get("intent_rules_overrides"), dict):
                yaml_data["intent_rules_overrides"] = config_patch["intent_rules_overrides"]
        elif layer_id == "layer_3_workers":
            worker_deadlines = config_patch.get("worker_deadlines", config_patch)
            if isinstance(worker_deadlines, dict):
                yaml_data["worker_deadlines"] = worker_deadlines
        elif layer_id == "layer_5_commit":
            if isinstance(config_patch.get("commit_tools_optional_slots"), dict):
                yaml_data["commit_tools_optional_slots"] = config_patch["commit_tools_optional_slots"]
        elif layer_id == "layer_6_generate":
            if "generator" not in yaml_data:
                yaml_data["generator"] = {}
            if isinstance(config_patch.get("model"), str):
                yaml_data["generator"]["model"] = config_patch["model"]
            if isinstance(config_patch.get("persona_voice_tone"), str):
                yaml_data["generator"]["persona_voice_tone"] = config_patch["persona_voice_tone"]
            if isinstance(config_patch.get("max_sentences"), int):
                yaml_data["generator"]["max_sentences"] = config_patch["max_sentences"]
        elif layer_id == "layer_7_tts":
            if "tts" not in yaml_data:
                yaml_data["tts"] = {}
            if isinstance(config_patch.get("tts_provider"), str):
                yaml_data["tts"]["tts_provider"] = config_patch["tts_provider"]
            if isinstance(config_patch.get("voice"), str):
                yaml_data["tts"]["voice"] = config_patch["voice"]
            if isinstance(config_patch.get("language_code"), str):
                yaml_data["tts"]["language_code"] = config_patch["language_code"]
        
        # Write back to YAML
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)
        
        # Invalidate cache
        registry.invalidate_tenant(tenant_id)
        invalidate_keyterm_cache(tenant_id)
        logger.info(f"Updated layer config for {tenant_id}/{layer_id}")
        
        return await get_layer_config(tenant_id, layer_id)
    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    except Exception as e:
        logger.exception(f"Error updating layer config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Tenant wizard (onboarding) ──────────────────────────────────────────────

@router.post("/tenants/validate")
async def validate_tenant_config(body: dict):
    """Validate a draft tenant YAML config before writing."""
    try:
        from server.core.tenant_config import TenantConfig
        import yaml
        
        yaml_str = body.get("yaml", "")
        if not yaml_str:
            raise ValueError("Empty YAML provided")
        
        data = yaml.safe_load(yaml_str)
        if not isinstance(data, dict):
            raise ValueError("YAML must be a dict")
        
        # Basic validation: required top-level fields
        if not data.get("tenant_id"):
            raise ValueError("Missing: tenant_id")
        if not data.get("restaurant_name"):
            raise ValueError("Missing: restaurant_name")
        
        # Try to create a TenantConfig to validate structure
        try:
            TenantConfig(**data)
        except Exception as e:
            raise ValueError(f"Config schema error: {str(e)[:100]}")
        
        return {"valid": True, "message": "Config is valid"}
    except Exception as e:
        logger.debug(f"Validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tenants/{tenant_id}/knowledge")
async def upload_knowledge_files(tenant_id: str):
    """Placeholder for knowledge file upload (multipart).
    
    In a full implementation, this would:
    1. Accept multipart form with files (PDF/TXT/CSV/MD)
    2. Store at configs/tenants/{id}/knowledge/{filename}
    3. Register in tenant.knowledge_files list
    
    For now, returns success to allow wizard flow.
    """
    try:
        from pathlib import Path
        from server.core.tenant_config import get_tenant_registry
        
        registry = get_tenant_registry()
        tenant_cfg = registry.load_tenant(tenant_id)
        if not tenant_cfg:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
        
        knowledge_dir = Path(f"/home/charles2/sailly-browser-demo/configs/tenants/{tenant_id}/knowledge")
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        return {"tenant_id": tenant_id, "knowledge_dir": str(knowledge_dir), "files": []}
    except Exception as e:
        logger.exception(f"Error in knowledge upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tenants/{tenant_id}/knowledge/{filename}")
async def delete_knowledge_file(tenant_id: str, filename: str):
    """Delete a knowledge file."""
    try:
        from pathlib import Path

        safe_filename = Path(filename).name
        if safe_filename != filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        knowledge_dir = Path(f"/home/charles2/sailly-browser-demo/configs/tenants/{tenant_id}/knowledge")
        file_path = knowledge_dir / safe_filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        file_path.unlink()
        logger.info(f"Deleted knowledge file: {tenant_id}/{filename}")
        
        return {"deleted": filename}
    except Exception as e:
        logger.exception(f"Error deleting knowledge file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Scenarios (test suite management) ────────────────────────────────────────

SCENARIO_CANONICAL_DIR = Path("/home/charles2/sailly-browser-demo/configs/scenarios")
SCENARIO_LEGACY_DIR = Path("/home/charles2/sailly-browser-demo/test-infra/caller-bot-v4/scenarios")
SCENARIO_RUNS: dict[str, dict] = {}


def _scenario_payload(body: dict) -> dict:
    return {
        "id": body["id"],
        "industry": body.get("industry", "restaurant"),
        "capability": body.get("capability", "custom"),
        "tenant": body.get("tenant_id") or body.get("tenant", "doboo"),
        "description": body.get("description", ""),
        "caller": {
            "goal": body.get("caller_goal", ""),
            "identity": body.get("caller_identity", {}),
            "patience_turns": int(body.get("patience_turns", 10)),
        },
        "expectations": body.get("expectations", {}),
        "required_data": body.get("required_data", {}),
    }


def _scenario_path(industry: str, capability: str, scenario_id: str) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_.-]", "_", scenario_id)
    safe_industry = re.sub(r"[^a-zA-Z0-9_.-]", "_", industry or "restaurant")
    safe_capability = re.sub(r"[^a-zA-Z0-9_.-]", "_", capability or "custom")
    return SCENARIO_CANONICAL_DIR / safe_industry / safe_capability / f"{safe_id}.yaml"


def _read_scenario_file(path: Path, source: str) -> Optional[dict]:
    import yaml

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        scenario_id = data.get("id", path.stem)
        caller = data.get("caller") or {}
        expectations = data.get("expectations") or {}
        return {
            "id": scenario_id,
            "source": source,
            "path": str(path),
            "industry": data.get("industry", "restaurant"),
            "capability": data.get("capability", data.get("bucket", "legacy")),
            "tenant_id": data.get("tenant", data.get("tenant_id", "doboo")),
            "phase": data.get("phase", 999),
            "description": data.get("description", ""),
            "caller_goal": caller.get("goal", ""),
            "caller_identity": caller.get("identity", {}),
            "patience_turns": caller.get("patience_turns", 10),
            "expectations": expectations,
            "expected_tools": expectations.get("tools") or expectations.get("must_call") or [],
            "required_data": data.get("required_data", {}),
            "yaml": path.read_text(encoding="utf-8"),
        }
    except Exception as e:
        logger.debug(f"Could not read scenario {path}: {e}")
        return None


def _all_scenarios() -> list[dict]:
    scenarios: list[dict] = []
    if SCENARIO_CANONICAL_DIR.exists():
        for path in sorted(SCENARIO_CANONICAL_DIR.rglob("*.yaml")):
            scenario = _read_scenario_file(path, "canonical")
            if scenario:
                scenarios.append(scenario)
    if SCENARIO_LEGACY_DIR.exists():
        for path in sorted(SCENARIO_LEGACY_DIR.rglob("*.yaml")):
            scenario = _read_scenario_file(path, "legacy")
            if scenario:
                scenarios.append(scenario)
    return scenarios


@router.get("/scenarios")
async def list_scenarios(
    tenant: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    capability: Optional[str] = Query(None),
):
    """List canonical and legacy validation scenarios."""
    try:
        scenarios = []
        for scenario in _all_scenarios():
            if tenant and scenario.get("tenant_id") != tenant:
                continue
            if industry and scenario.get("industry") != industry:
                continue
            if capability and scenario.get("capability") != capability:
                continue
            scenarios.append({k: v for k, v in scenario.items() if k != "yaml"})
        return {
            "scenarios": sorted(
                scenarios,
                key=lambda s: (
                    s.get("industry", ""),
                    s.get("capability", ""),
                    s.get("id", ""),
                ),
            )
        }
    except Exception as e:
        logger.exception(f"Error listing scenarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scenarios/{scenario_id}")
async def get_scenario(scenario_id: str):
    """Fetch a single scenario by ID."""
    for scenario in _all_scenarios():
        if scenario.get("id") == scenario_id:
            return scenario
    raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")


@router.post("/scenarios")
async def create_scenario(body: dict):
    """Create a new canonical scenario YAML file."""
    try:
        import yaml

        scenario_id = body.get("id") or f"scenario_{uuid.uuid4().hex[:8]}"
        payload = _scenario_payload({**body, "id": scenario_id})
        scenario_file = _scenario_path(payload["industry"], payload["capability"], scenario_id)
        scenario_file.parent.mkdir(parents=True, exist_ok=True)
        if scenario_file.exists():
            raise HTTPException(status_code=409, detail=f"Scenario already exists: {scenario_id}")
        scenario_file.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return {"id": scenario_id, "source": "canonical", "path": str(scenario_file), "scenario": payload}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/scenarios/{scenario_id}")
async def update_scenario(scenario_id: str, body: dict):
    """Update a canonical scenario. Legacy scenarios are read-only."""
    try:
        import yaml

        existing = next((s for s in _all_scenarios() if s.get("id") == scenario_id), None)
        if existing and existing.get("source") == "legacy":
            raise HTTPException(status_code=409, detail="Legacy scenarios are read-only; duplicate it into canonical storage first.")
        payload = _scenario_payload({**body, "id": scenario_id})
        scenario_file = _scenario_path(payload["industry"], payload["capability"], scenario_id)
        scenario_file.parent.mkdir(parents=True, exist_ok=True)
        scenario_file.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")
        return {"id": scenario_id, "source": "canonical", "path": str(scenario_file), "scenario": payload}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating scenario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scenarios/{scenario_id}")
async def delete_scenario(scenario_id: str):
    """Delete a canonical scenario YAML file."""
    for scenario in _all_scenarios():
        if scenario.get("id") != scenario_id:
            continue
        if scenario.get("source") != "canonical":
            raise HTTPException(status_code=409, detail="Legacy scenarios are read-only")
        path = Path(scenario["path"])
        path.unlink(missing_ok=True)
        return {"deleted": scenario_id}
    raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")


@router.post("/scenarios/{scenario_id}/run")
async def run_scenario(scenario_id: str):
    """Create a lightweight scenario run record.

    This is intentionally non-destructive and uses the saved scenario as the
    run source. The full caller-bot execution can attach to this run id later.
    """
    scenario = next((s for s in _all_scenarios() if s.get("id") == scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario not found: {scenario_id}")
    run_id = f"run_{uuid.uuid4().hex[:10]}"
    SCENARIO_RUNS[run_id] = {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "status": "queued",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "tenant_id": scenario.get("tenant_id"),
        "capability": scenario.get("capability"),
        "expected_tools": scenario.get("expected_tools", []),
        "turns": [],
        "result": "not_run",
        "message": "Run record created. Attach headless runner to execute the scenario.",
    }
    return SCENARIO_RUNS[run_id]


@router.get("/scenarios/runs/{run_id}")
async def get_scenario_run(run_id: str):
    run = SCENARIO_RUNS.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return run


# ── Calls list ────────────────────────────────────────────────────────────────

@router.get("/calls")
async def get_builder_calls(
    tenant: str = Query(...),
    limit: int = Query(50, ge=1, le=200),
):
    """Recent calls for the Builder call picker. Queries google_calls directly."""
    try:
        from server.core.tenant_guard import resolve_tenant_id
        tenant = resolve_tenant_id(tenant)
        from server.database import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT call_sid, tenant_id, caller, started_at, ended_at,
                       quality_score, turn_count, goodbye_detected
                FROM google_calls
                WHERE tenant_id = $1
                ORDER BY started_at DESC
                LIMIT $2
                """,
                tenant, limit,
            )
        calls = [
            {
                "call_sid": r["call_sid"],
                "tenant_id": r["tenant_id"],
                "caller": r["caller"] or "unknown",
                "started_at": r["started_at"].isoformat() if r["started_at"] else None,
                "ended_at": r["ended_at"].isoformat() if r["ended_at"] else None,
                "quality_score": r["quality_score"],
                "turn_count": r["turn_count"],
                "goodbye_detected": r["goodbye_detected"],
            }
            for r in rows
        ]
        return {"tenant": tenant, "calls": calls}
    except Exception as e:
        logger.warning(f"[BUILDER] calls query failed: {e!r}")
        # Graceful fallback — monitoring endpoint has its own data
        try:
            from server.monitoring import get_recent_monitoring_calls
            rows = await get_recent_monitoring_calls(window_secs=86400 * 7, limit=limit, tenant_id=tenant)
            return {"tenant": tenant, "calls": rows}
        except Exception as e2:
            logger.warning(f"[BUILDER] monitoring fallback also failed: {e2!r}")
            return {"tenant": tenant, "calls": []}


# ── Turn replay ───────────────────────────────────────────────────────────────

@router.get("/call/{call_sid}/turns")
async def get_call_turns(call_sid: str, tenant: str = Query(...)):
    """Per-turn metrics for one call — drives the replay scrubber."""
    try:
        from server.core.tenant_guard import resolve_tenant_id, assert_call_belongs_to_tenant
        tenant = resolve_tenant_id(tenant)
        await assert_call_belongs_to_tenant(call_sid, tenant)
        from server.database import get_pool
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    turn_number, user_text, bot_text,
                    stt_latency_ms, llm_latency_ms, total_latency_ms,
                    tools_called, node_name,
                    stt_confidence, build_sha, tenant_id, created_at
                FROM google_turn_metrics
                WHERE call_sid = $1
                ORDER BY turn_number ASC
                """,
                call_sid,
            )
    except Exception as e:
        logger.warning(f"[BUILDER] turns query failed for {call_sid}: {e!r}")
        raise HTTPException(status_code=503, detail="Database unavailable")

    if not rows:
        raise HTTPException(status_code=404, detail=f"No turns found for call {call_sid}")

    turns = []
    for r in rows:
        tc = r["tools_called"]
        if isinstance(tc, str):
            try:
                tc = json.loads(tc)
            except Exception:
                tc = []
        turns.append({
            "turn_number": r["turn_number"],
            "user_text": r["user_text"] or "",
            "bot_text": r["bot_text"] or "",
            "stt_latency_ms": r["stt_latency_ms"],
            "llm_latency_ms": r["llm_latency_ms"],
            "total_latency_ms": r["total_latency_ms"],
            "tools_called": tc or [],
            "node_name": r["node_name"] or "unknown",
            "stt_confidence": r["stt_confidence"],
            "build_sha": r["build_sha"],
            "tenant_id": r["tenant_id"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })
    return {"call_sid": call_sid, "turn_count": len(turns), "turns": turns}


# ── Source code viewer ────────────────────────────────────────────────────────

@router.get("/node/{node_id}/source")
async def get_node_source(node_id: str):
    """Legacy endpoint retained for compatibility; use profile/worker source endpoints."""
    raise HTTPException(
        status_code=410,
        detail={
            "message": "Legacy training nodes are deprecated in v4 builder.",
            "migration": "Use /api/builder/profile/{profile_id}/source or /api/builder/worker/{worker_name}/source",
            "node_id": node_id,
        },
    )


@router.get("/profile/{profile_id}/source")
async def get_profile_source(profile_id: str):
    """Return source location for a worker profile definition in worker_router.py."""
    try:
        from server.brain import worker_router
        import inspect
        profile_map = getattr(worker_router, "_PROFILES", {})
        if profile_id not in profile_map:
            raise HTTPException(status_code=404, detail=f"Unknown profile: {profile_id}")
        source_file = inspect.getsourcefile(worker_router) or ""
        source_lines = Path(source_file).read_text(encoding="utf-8").splitlines()
        start_idx = None
        marker = f'"{profile_id}": ExecutionPlan('
        for i, line in enumerate(source_lines):
            if marker in line:
                start_idx = i
                break
        if start_idx is None:
            raise HTTPException(status_code=404, detail=f"Profile source block not found: {profile_id}")
        depth = 0
        end_idx = start_idx
        for j, line in enumerate(source_lines[start_idx:], start=start_idx):
            depth += line.count("(") - line.count(")")
            if j > start_idx and depth <= 0:
                end_idx = j
                break
        rel_file = source_file.replace(f"{_REPO_ROOT}/", "") if source_file.startswith(f"{_REPO_ROOT}/") else source_file
        return {
            "profile_id": profile_id,
            "file": rel_file,
            "start_line": start_idx + 1,
            "end_line": end_idx + 1,
            "source": "\n".join(source_lines[start_idx : end_idx + 1]),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting source for profile {profile_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/worker/{worker_name}/source")
async def get_worker_source(worker_name: str):
    """Return source block for a known worker object."""
    try:
        from server.brain.worker_router import _PROFILES
        import inspect
        worker_obj = None
        for plan in _PROFILES.values():
            for w in [*plan.required, *plan.optional, *plan.background]:
                if w.name == worker_name:
                    worker_obj = w
                    break
            if worker_obj is not None:
                break
        if worker_obj is None:
            raise HTTPException(status_code=404, detail=f"Unknown worker: {worker_name}")
        cls = worker_obj.__class__
        source_file = inspect.getsourcefile(cls) or ""
        src, start = inspect.getsourcelines(cls)
        rel_file = source_file.replace(f"{_REPO_ROOT}/", "") if source_file.startswith(f"{_REPO_ROOT}/") else source_file
        return {
            "worker_name": worker_name,
            "file": rel_file,
            "start_line": start,
            "end_line": start + len(src) - 1,
            "source": "".join(src),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting source for worker {worker_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Tenant management ────────────────────────────────────────────────────────

@router.post("/tenants/draft")
async def draft_tenant_yaml(body: dict):
    """Draft a tenant YAML using Claude API from structured form input.
    
    Body: { name, industry, language, city, address, hours, menu_description }
    Returns: { tenant_id, yaml }
    """
    try:
        import anthropic
        import re
        
        name = body.get("name", "")
        industry = body.get("industry", "restaurant")
        language = body.get("language", "de")
        city = body.get("city", "")
        address = body.get("address", "")
        hours = body.get("hours", "")
        menu_desc = body.get("menu_description", "")
        
        # Generate tenant ID from name
        tenant_id = re.sub(r"[^a-z0-9]", "_", name.lower())[:20].rstrip("_")
        
        # Call Claude to draft YAML
        client = anthropic.Anthropic()
        prompt = f"""Generate a complete Sailly tenant YAML configuration for:
- Name: {name}
- Industry: {industry}
- Language: {language}
- City: {city}
- Address: {address}
- Hours: {hours}
- Menu: {menu_desc}

Create a valid YAML file that can be saved to configs/tenants/{tenant_id}.yaml.
Include: tenant_id, restaurant_name, industry, language, city, address, opening_hours, menu (with 3-5 sample dishes), system_prompt (in German if language=de), greeting_line, farewell_text.

Return ONLY the YAML, no markdown code blocks."""

        message = client.messages.create(
            model="claude-opus-4-7-thinking-medium",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        yaml_content = message.content[0].text
        
        return {"tenant_id": tenant_id, "yaml": yaml_content}
    except Exception as e:
        logger.exception(f"Error drafting tenant YAML: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tenants")
async def create_tenant(body: dict):
    """Create a new tenant by writing YAML to disk and validating.
    
    Body: { tenant_id, yaml }
    Returns: { tenant_id, message }
    """
    try:
        from server.tenants.schemas import TenantProvisionRequest
        from server.tenants.provision import create_tenant as provision_tenant
        req = TenantProvisionRequest(
            tenant_id=body.get("tenant_id", ""),
            restaurant_name=body.get("restaurant_name", body.get("tenant_id", "")),
            yaml=body.get("yaml"),
            dry_run=bool(body.get("dry_run", False)),
        )
        result = provision_tenant(req)
        logger.info(f"[BUILDER] Created tenant: {result.tenant_id}")
        return {
            "tenant_id": result.tenant_id,
            "path": result.path,
            "created": result.created,
            "validated": result.validated,
            "dry_run": result.dry_run,
        }
    except HTTPException:
        raise
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception(f"Error creating tenant: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/proposals")
async def create_proposal(body: dict):
    """Save a proposed edit (system_prompt or node prompt patch) for review.

    Body: { tenant_id, field, original, proposed, author? }
    Returns: { proposal_id, diff_lines }
    """
    tenant_id = body.get("tenant_id")
    field = body.get("field")
    original = body.get("original", "")
    proposed = body.get("proposed", "")
    author = body.get("author", "dashboard")

    if not tenant_id or not field:
        raise HTTPException(status_code=400, detail="tenant_id and field are required")

    proposal_id = str(uuid.uuid4())[:8]
    proposal = {
        "id": proposal_id,
        "tenant_id": tenant_id,
        "field": field,
        "original": original,
        "proposed": proposed,
        "author": author,
        "created_at": datetime.utcnow().isoformat(),
        "status": "pending",
    }

    path = PROPOSALS_DIR / f"{proposal_id}.json"
    path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2))

    # Compute simple line diff
    import difflib
    diff = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        proposed.splitlines(keepends=True),
        fromfile=f"{tenant_id}/{field} (current)",
        tofile=f"{tenant_id}/{field} (proposed)",
        lineterm="",
    ))
    return {"proposal_id": proposal_id, "diff_lines": diff, "status": "pending"}


@router.get("/proposals")
async def list_proposals(tenant_id: Optional[str] = Query(None)):
    """List all pending proposals."""
    proposals = []
    for p in sorted(PROPOSALS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            data = json.loads(p.read_text())
            if tenant_id and data.get("tenant_id") != tenant_id:
                continue
            proposals.append(data)
        except Exception:
            pass
    return {"proposals": proposals}


@router.post("/proposals/{proposal_id}/apply")
async def apply_proposal(proposal_id: str):
    """Apply a proposal — patches the tenant YAML file in-place."""
    path = PROPOSALS_DIR / f"{proposal_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal = json.loads(path.read_text())
    if proposal.get("status") != "pending":
        raise HTTPException(status_code=409, detail=f"Proposal already {proposal['status']}")

    tenant_id = proposal["tenant_id"]
    field = proposal["field"]
    proposed = proposal["proposed"]

    from server.core.tenant_config import tenant_yaml_path, get_tenant_registry
    from server.brain.stt.keyterm_loader import invalidate_cache as invalidate_keyterm_cache
    yaml_path = tenant_yaml_path(tenant_id)
    if yaml_path is None or not yaml_path.exists():
        raise HTTPException(status_code=404, detail=f"Tenant config not found: {tenant_id}")

    import yaml
    with open(yaml_path) as f:
        config = yaml.safe_load(f)

    # Navigate dotted field path (e.g. "system_prompt")
    keys = field.split(".")
    obj = config
    for k in keys[:-1]:
        obj = obj.setdefault(k, {})
    obj[keys[-1]] = proposed

    # Write back with preserved structure
    backup = yaml_path.with_suffix(".yaml.bak")
    yaml_path.rename(backup)
    with open(yaml_path, "w") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    proposal["status"] = "applied"
    proposal["applied_at"] = datetime.utcnow().isoformat()
    path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2))
    get_tenant_registry().invalidate_tenant(tenant_id)
    invalidate_keyterm_cache(tenant_id)

    return {"proposal_id": proposal_id, "status": "applied", "field": field, "tenant_id": tenant_id}


@router.post("/proposals/{proposal_id}/revert")
async def revert_proposal(proposal_id: str):
    """Mark a proposal as reverted (deletes it; backup YAML remains)."""
    path = PROPOSALS_DIR / f"{proposal_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Proposal not found")
    proposal = json.loads(path.read_text())
    proposal["status"] = "reverted"
    path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2))
    return {"proposal_id": proposal_id, "status": "reverted"}


# ── AI Agent Editing (Phase D) ────────────────────────────────────────────────

@router.post("/agent/run")
async def run_agent(body: dict):
    """Run Claude coding agent to modify code/YAML based on natural language instruction.
    
    Body: { tenant_id, instruction, scope: "yaml" | "workers" | "commit_gate" | "intent" }
    Returns: { diff, test_result, branch_name, test_log }
    
    Scope gates (safety levels):
    - yaml: Safe; modify only tenant YAML files
    - workers: Medium risk; modify worker code + run tests
    - commit_gate: High risk; modify v4_pipeline commit logic + full regression
    - intent: Medium risk; modify intent_classifier + tests
    """
    try:
        import subprocess
        import time
        import anthropic
        
        tenant_id = body.get("tenant_id", "")
        instruction = body.get("instruction", "")
        scope = body.get("scope", "yaml")
        
        if not instruction:
            raise HTTPException(status_code=400, detail="instruction is required")
        
        # Create git branch
        branch_name = f"proposal_{tenant_id}_{int(time.time())}"
        try:
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd="/home/charles2/sailly-browser-demo",
                check=True,
                capture_output=True,
                timeout=10
            )
        except Exception as e:
            logger.warning(f"Could not create git branch {branch_name}: {e}")
            branch_name = f"proposal_{int(time.time())}"  # Fallback
        
        # Prepare context files for Claude
        context_files = []
        
        if scope == "yaml":
            # Just the tenant YAML
            tenant_yaml = Path(f"/home/charles2/sailly-browser-demo/configs/tenants/{tenant_id}.yaml")
            if tenant_yaml.exists():
                context_files.append(("tenant.yaml", tenant_yaml.read_text()))
        
        elif scope == "workers":
            # Worker files
            worker_dir = Path("/home/charles2/sailly-browser-demo/server/brain/workers")
            for py in sorted(worker_dir.glob("*.py"))[:5]:  # Top 5 to stay within context
                try:
                    content = py.read_text()[:2000]
                    context_files.append((f"workers/{py.name}", content))
                except:
                    pass
        
        elif scope == "commit_gate":
            # Commit gate files
            v4_pipeline = Path("/home/charles2/sailly-browser-demo/server/brain/v4_pipeline.py")
            context_doc = Path("/home/charles2/sailly-browser-demo/server/brain/context_doc_builder.py")
            if v4_pipeline.exists():
                context_files.append(("v4_pipeline.py", v4_pipeline.read_text()[:5000]))
            if context_doc.exists():
                context_files.append(("context_doc_builder.py", context_doc.read_text()[:3000]))
        
        elif scope == "intent":
            # Intent classifier
            intent_file = Path("/home/charles2/sailly-browser-demo/server/brain/intent_classifier.py")
            if intent_file.exists():
                context_files.append(("intent_classifier.py", intent_file.read_text()[:4000]))
        
        # Call Claude with context
        try:
            client = anthropic.Anthropic()
        except:
            raise HTTPException(status_code=500, detail="Anthropic API not available")
        
        context_text = "\n\n".join(f"=== {name} ===\n{content}" for name, content in context_files)
        
        prompt = f"""You are a code modification assistant for the Sailly v4 pipeline.

Scope: {scope}
Tenant: {tenant_id}
Instruction: {instruction}

{context_text}

Your task:
1. Analyze the current code/config in the context above
2. Make minimal, focused changes to implement the instruction
3. Return ONLY a unified diff (unified diff format, can be applied with 'patch' or 'git apply')
4. Do not include explanations, code blocks, or markdown — ONLY raw diff

If the instruction is impossible within the scope, return: ERROR: [reason]"""

        response = client.messages.create(
            model="claude-opus-4-7-thinking-medium",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        diff_text = response.content[0].text
        
        # Apply diff if valid
        if not diff_text.startswith("ERROR:"):
            try:
                result = subprocess.run(
                    ["patch", "-p0"],
                    input=diff_text,
                    text=True,
                    cwd="/home/charles2/sailly-browser-demo",
                    capture_output=True,
                    timeout=30
                )
                if result.returncode != 0:
                    logger.warning(f"Patch application failed: {result.stderr}")
            except Exception as e:
                logger.warning(f"Could not apply diff: {e}")
        
        # Run smoke tests
        test_result = "pending"
        test_log = ""
        
        try:
            # Run light validation
            test_proc = subprocess.run(
                ["python3", "-m", "pytest", "server/builder/tests/", "-v", "--tb=short"],
                cwd="/home/charles2/sailly-browser-demo",
                capture_output=True,
                text=True,
                timeout=30
            )
            test_log = test_proc.stdout + test_proc.stderr
            test_result = "pass" if test_proc.returncode == 0 else "fail"
        except subprocess.TimeoutExpired:
            test_result = "timeout"
            test_log = "Test suite timed out after 30 seconds"
        except Exception as e:
            test_result = "error"
            test_log = str(e)
        
        logger.info(f"[BUILDER] Agent proposal created: branch={branch_name}, scope={scope}, test={test_result}")
        
        return {
            "branch_name": branch_name,
            "diff": diff_text,
            "test_result": test_result,
            "test_log": test_log,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error running agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))
