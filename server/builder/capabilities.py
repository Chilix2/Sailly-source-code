"""Industry capability packs for the Flow Builder.

Capabilities are the reusable business building blocks behind scenarios,
workflows, and tenant onboarding. They let the Builder express "what this agent
can do" independently from one hardcoded DOBOO graph.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional

import yaml
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
INDUSTRY_PACK_DIR = REPO_ROOT / "configs" / "industry_packs"


class CapabilityTool(BaseModel):
    name: str
    required: bool = False
    description: str = ""
    required_slots: list[str] = Field(default_factory=list)
    optional_slots: list[str] = Field(default_factory=list)


class CapabilityGuard(BaseModel):
    id: str
    description: str
    severity: Literal["info", "warning", "blocking"] = "blocking"
    applies_to: list[str] = Field(default_factory=list)
    forbidden_behaviors: list[Any] = Field(default_factory=list)


class ExpectedOutcome(BaseModel):
    tools: list[str] = Field(default_factory=list)
    final_state: Optional[str] = None
    transcript_assertions: list[str] = Field(default_factory=list)
    forbidden_behaviors: list[str] = Field(default_factory=list)
    guards: list[str] = Field(default_factory=list)


class CapabilityScenario(BaseModel):
    id: str
    name: str
    description: str = ""
    caller_goal: str
    required_data: dict[str, Any] = Field(default_factory=dict)
    expected: ExpectedOutcome = Field(default_factory=ExpectedOutcome)
    mandatory: bool = True


class CapabilityPack(BaseModel):
    id: str
    name: str
    description: str = ""
    category: str = "general"
    default_enabled: bool = True
    tools: list[CapabilityTool] = Field(default_factory=list)
    slots: list[str] = Field(default_factory=list)
    variables: list[str] = Field(default_factory=list)
    guards: list[CapabilityGuard] = Field(default_factory=list)
    prompt_fragments: list[str] = Field(default_factory=list)
    scenarios: list[CapabilityScenario] = Field(default_factory=list)


class IndustryPack(BaseModel):
    id: str
    name: str
    description: str = ""
    version: str = "1.0"
    language_defaults: list[str] = Field(default_factory=lambda: ["de"])
    capabilities: list[CapabilityPack] = Field(default_factory=list)
    compliance_checklist: list[str] = Field(default_factory=list)


def load_industry_pack(industry: str) -> IndustryPack:
    path = INDUSTRY_PACK_DIR / f"{industry}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Industry pack not found: {industry}")
    return IndustryPack(**(yaml.safe_load(path.read_text(encoding="utf-8")) or {}))


def _model_dump(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[attr-defined]
    return model.dict()


def list_industry_packs() -> list[dict[str, Any]]:
    packs: list[dict[str, Any]] = []
    if not INDUSTRY_PACK_DIR.exists():
        return packs
    for path in sorted(INDUSTRY_PACK_DIR.glob("*.yaml")):
        try:
            pack = load_industry_pack(path.stem)
            packs.append(
                {
                    "id": pack.id,
                    "name": pack.name,
                    "description": pack.description,
                    "version": pack.version,
                    "capability_count": len(pack.capabilities),
                }
            )
        except Exception:
            continue
    return packs


def capabilities_response(industry: Optional[str] = None) -> dict[str, Any]:
    if industry:
        pack = load_industry_pack(industry)
        return {"packs": [_model_dump(pack)]}
    return {"packs": list_industry_packs()}


def scenario_templates_response(
    industry: Optional[str] = None,
    capability: Optional[str] = None,
) -> dict[str, Any]:
    """Return scenario templates embedded in industry capability packs."""

    templates: list[dict[str, Any]] = []
    pack_ids = [industry] if industry else [pack["id"] for pack in list_industry_packs()]
    for pack_id in pack_ids:
        pack = load_industry_pack(pack_id)
        for cap in pack.capabilities:
            if capability and cap.id != capability:
                continue
            for scenario in cap.scenarios:
                templates.append(
                    {
                        "id": scenario.id,
                        "name": scenario.name,
                        "description": scenario.description,
                        "industry": pack.id,
                        "industry_name": pack.name,
                        "capability": cap.id,
                        "capability_name": cap.name,
                        "category": cap.category,
                        "caller_goal": scenario.caller_goal,
                        "required_data": scenario.required_data,
                        "expected": _model_dump(scenario.expected),
                        "mandatory": scenario.mandatory,
                    }
                )
    return {"templates": templates}
