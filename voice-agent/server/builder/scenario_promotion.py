"""Scenario requirement and promotion-gate scaffolding for Builder Lab.

This module is intentionally side-effect free. It does not execute the
regression harness; it only makes the requirements and lifecycle state explicit
so Builder run records can be populated consistently.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Mapping

from server.builder.capabilities import load_industry_pack


DRAFT = "draft"
VALIDATE = "validate"
PUBLISH = "publish"

GATE_BLOCKED = "blocked"
GATE_NOT_STARTED = "not_started"
GATE_READY = "ready"
GATE_PASSED = "passed"


@dataclass(frozen=True)
class GateEvaluation:
    """One promotion gate in the Builder Lab scenario lifecycle."""

    stage: str
    status: str
    required: list[str] = field(default_factory=list)
    satisfied: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityRequirements:
    """Requirements a scenario must satisfy for a capability."""

    industry: str
    capability: str
    capability_name: str = ""
    required_tools: list[str] = field(default_factory=list)
    optional_tools: list[str] = field(default_factory=list)
    required_slots: list[str] = field(default_factory=list)
    capability_scenarios: list[str] = field(default_factory=list)
    expected_tools: list[str] = field(default_factory=list)
    required_data_keys: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value if v]
    return []


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out


def expected_tools_from_scenario(scenario: Mapping[str, Any]) -> list[str]:
    """Normalize expected tool declarations from Builder or legacy scenarios."""

    expectations = scenario.get("expectations") or {}
    expected = _as_list(scenario.get("expected_tools"))
    if isinstance(expectations, Mapping):
        expected.extend(_as_list(expectations.get("tools")))
        expected.extend(_as_list(expectations.get("must_call")))
    return _dedupe(expected)


def capability_requirements(
    industry: str,
    capability_id: str,
    scenario: Mapping[str, Any] | None = None,
) -> CapabilityRequirements:
    """Load capability-level requirements and overlay scenario expectations."""

    scenario = scenario or {}
    pack = load_industry_pack(industry)
    capability = next((c for c in pack.capabilities if c.id == capability_id), None)

    if capability is None:
        return CapabilityRequirements(
            industry=industry,
            capability=capability_id,
            expected_tools=expected_tools_from_scenario(scenario),
            required_data_keys=sorted((scenario.get("required_data") or {}).keys()),
        )

    required_tools: list[str] = []
    optional_tools: list[str] = []
    required_slots: list[str] = []
    for tool in capability.tools:
        if tool.required:
            required_tools.append(tool.name)
        else:
            optional_tools.append(tool.name)
        required_slots.extend(tool.required_slots)

    expected_tools = expected_tools_from_scenario(scenario)
    if not expected_tools:
        expected_tools = list(required_tools)

    required_data = scenario.get("required_data") or {}
    return CapabilityRequirements(
        industry=industry,
        capability=capability_id,
        capability_name=capability.name,
        required_tools=_dedupe(required_tools),
        optional_tools=_dedupe(optional_tools),
        required_slots=_dedupe([*capability.slots, *required_slots]),
        capability_scenarios=[s.id for s in capability.scenarios],
        expected_tools=_dedupe(expected_tools),
        required_data_keys=sorted(required_data.keys()),
    )


def scenario_requirements(scenario: Mapping[str, Any]) -> CapabilityRequirements:
    """Build requirements for a Builder scenario dictionary."""

    industry = str(scenario.get("industry") or "restaurant")
    capability = str(scenario.get("capability") or "custom")
    return capability_requirements(industry, capability, scenario)


def evaluate_draft_gate(
    scenario: Mapping[str, Any],
    requirements: CapabilityRequirements,
) -> GateEvaluation:
    required = ["id", "description", "caller_goal", "expected_tools_or_outcome"]
    satisfied: list[str] = []

    if scenario.get("id"):
        satisfied.append("id")
    if scenario.get("description"):
        satisfied.append("description")
    if scenario.get("caller_goal"):
        satisfied.append("caller_goal")
    if requirements.expected_tools or (scenario.get("expectations") or {}):
        satisfied.append("expected_tools_or_outcome")

    missing = [item for item in required if item not in satisfied]
    return GateEvaluation(
        stage=DRAFT,
        status=GATE_READY if not missing else GATE_BLOCKED,
        required=required,
        satisfied=satisfied,
        missing=missing,
        evidence={
            "capability": requirements.capability,
            "expected_tools": requirements.expected_tools,
            "required_data_keys": requirements.required_data_keys,
        },
    )


def evaluate_validate_gate(
    run_record: Mapping[str, Any],
    requirements: CapabilityRequirements,
) -> GateEvaluation:
    required = ["completed_run", "expected_tools_seen", "assertions_passed"]
    satisfied: list[str] = []
    status = str(run_record.get("status") or "")
    result = str(run_record.get("result") or "")
    tools_seen = _as_list(run_record.get("tools_seen") or run_record.get("tools_fired"))
    failed_assertions = run_record.get("failed_assertions", [])

    if status in {"completed", "passed", "failed"}:
        satisfied.append("completed_run")
    if set(requirements.expected_tools).issubset(set(tools_seen)):
        satisfied.append("expected_tools_seen")
    if result in {"pass", "passed"} and not failed_assertions:
        satisfied.append("assertions_passed")

    missing = [item for item in required if item not in satisfied]
    if not tools_seen and status in {"queued", "not_started"}:
        gate_status = GATE_NOT_STARTED
    else:
        gate_status = GATE_PASSED if not missing else GATE_BLOCKED

    return GateEvaluation(
        stage=VALIDATE,
        status=gate_status,
        required=required,
        satisfied=satisfied,
        missing=missing,
        evidence={
            "tools_seen": tools_seen,
            "expected_tools": requirements.expected_tools,
            "result": result,
            "failed_assertions": failed_assertions,
        },
    )


def evaluate_publish_gate(
    draft_gate: GateEvaluation,
    validate_gate: GateEvaluation,
) -> GateEvaluation:
    required = ["draft_ready", "validation_passed"]
    satisfied: list[str] = []
    if draft_gate.status in {GATE_READY, GATE_PASSED}:
        satisfied.append("draft_ready")
    if validate_gate.status == GATE_PASSED:
        satisfied.append("validation_passed")
    missing = [item for item in required if item not in satisfied]
    return GateEvaluation(
        stage=PUBLISH,
        status=GATE_READY if not missing else GATE_BLOCKED,
        required=required,
        satisfied=satisfied,
        missing=missing,
        evidence={
            "draft_status": draft_gate.status,
            "validate_status": validate_gate.status,
        },
    )


def promotion_gates(
    scenario: Mapping[str, Any],
    run_record: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return draft, validate, publish gates for a scenario/run pair."""

    run_record = run_record or {"status": "not_started", "result": "not_run"}
    requirements = scenario_requirements(scenario)
    draft_gate = evaluate_draft_gate(scenario, requirements)
    validate_gate = evaluate_validate_gate(run_record, requirements)
    publish_gate = evaluate_publish_gate(draft_gate, validate_gate)
    return [draft_gate.to_dict(), validate_gate.to_dict(), publish_gate.to_dict()]


def create_run_record(
    scenario: Mapping[str, Any],
    run_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create a queued Builder scenario run record without executing the harness."""

    now = now or datetime.utcnow()
    requirements = scenario_requirements(scenario)
    record: dict[str, Any] = {
        "run_id": run_id,
        "scenario_id": scenario.get("id"),
        "status": "queued",
        "created_at": now.isoformat() + "Z",
        "tenant_id": scenario.get("tenant_id") or scenario.get("tenant"),
        "industry": scenario.get("industry", "restaurant"),
        "capability": scenario.get("capability"),
        "requirements": requirements.to_dict(),
        "expected_tools": requirements.expected_tools,
        "tools_seen": [],
        "turns": [],
        "result": "not_run",
        "message": "Run record created. Attach the regression harness to execute the scenario.",
    }
    record["promotion_gates"] = promotion_gates(scenario, record)
    return record


def update_run_record_from_regression_result(
    run_record: Mapping[str, Any],
    result: Mapping[str, Any],
    scenario: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach a completed regression-harness result to a Builder run record."""

    updated = dict(run_record)
    checks = result.get("checks") or []
    failed = [
        check
        for check in checks
        if isinstance(check, Mapping) and not bool(check.get("passed"))
    ]
    updated.update(
        {
            "status": "completed",
            "result": "pass" if bool(result.get("passed")) and not failed else "fail",
            "call_sid": result.get("call_sid", updated.get("call_sid", "")),
            "tools_seen": _as_list(result.get("tools_fired")),
            "turns": result.get("bot_responses", []),
            "failed_assertions": failed,
            "duration_s": result.get("duration_s") or result.get("total_duration_s"),
        }
    )
    updated["promotion_gates"] = promotion_gates(scenario, updated)
    return updated
