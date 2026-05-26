"""Export the current v4 introspection graph into config graph schemas.

The exporter is deliberately read-only. It consumes the existing
``server.builder.graph_introspect.build_graph`` payload and produces a typed
document for builder/lab workflows.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from server.builder.graph_foundation.schemas import (
    CapabilityRef,
    ConfigGraphDocument,
    GraphEdge,
    GraphGlobalNode,
    GraphGuard,
    GraphNode,
    GraphSourceRef,
)


def export_v4_graph(
    tenant_id: Optional[str] = None,
    introspection: Optional[Dict[str, Any]] = None,
) -> ConfigGraphDocument:
    """Describe the current v4 graph from existing builder introspection data."""

    if introspection is None:
        from server.builder.graph_introspect import build_graph

        introspection = build_graph(tenant_id=tenant_id)

    tenant = str(introspection.get("tenant") or tenant_id or "default")
    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    guards = _export_guards(introspection)
    guard_ids = {guard.id for guard in guards}

    nodes.extend(_profile_nodes(introspection, guard_ids))
    nodes.extend(_worker_nodes(introspection))
    nodes.extend(_intent_nodes(introspection))
    tool_nodes = _tool_nodes(introspection, guard_ids)
    nodes.extend(tool_nodes)
    nodes.extend(_implicit_tool_nodes(introspection, {node.id for node in tool_nodes}, guard_ids))
    nodes.extend(_layer_nodes(introspection))
    nodes.extend(_commit_gate_nodes(introspection, guard_ids))

    edges.extend(_intent_edges(introspection))
    edges.extend(_profile_reroute_edges(introspection))
    edges.extend(_profile_worker_edges(introspection))
    edges.extend(_profile_tool_edges(introspection))
    edges.extend(_commit_gate_edges(introspection))
    edges.extend(_guardian_edges(introspection))
    edges.extend(_layer_edges(introspection))

    global_nodes = _global_nodes(tenant, introspection)
    capabilities = _capability_refs(nodes, guards)

    return ConfigGraphDocument(
        graph_version=str(introspection.get("schema_version") or "v4"),
        tenant=tenant,
        nodes=_dedupe_nodes(nodes),
        edges=_dedupe_edges(edges),
        global_nodes=global_nodes,
        guards=guards,
        capabilities=capabilities,
        metadata={
            "source": "server.builder.graph_introspect.build_graph",
            "lab_safe": True,
            "runtime_behavior": "unchanged",
            "introspection_keys": sorted(str(k) for k in introspection.keys()),
        },
    )


def export_v4_graph_dict(
    tenant_id: Optional[str] = None,
    introspection: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return ``export_v4_graph`` as a JSON-ready dict."""

    return export_v4_graph(tenant_id=tenant_id, introspection=introspection).to_dict()


def _profile_nodes(introspection: Dict[str, Any], guard_ids: set[str]) -> List[GraphNode]:
    nodes: List[GraphNode] = []
    for profile in introspection.get("profiles", []):
        profile_id = str(profile.get("id") or "")
        if not profile_id:
            continue
        scheduled_tools = [str(x) for x in profile.get("scheduled_tools", [])]
        profile_guards = [f"commit_gate:{tool}" for tool in scheduled_tools if f"commit_gate:{tool}" in guard_ids]
        nodes.append(
            GraphNode(
                id=f"profile:{profile_id}",
                label=str(profile.get("label") or profile_id),
                kind="profile",
                capabilities=[
                    CapabilityRef(id=f"profile:{profile_id}", kind="profile", label=profile_id),
                    *[
                        CapabilityRef(id=f"tool:{tool}", kind="tool", label=tool)
                        for tool in scheduled_tools
                    ],
                ],
                guards=profile_guards,
                metadata={
                    "profile": profile_id,
                    "required_workers": profile.get("required_workers", []),
                    "optional_workers": profile.get("optional_workers", []),
                    "background_workers": profile.get("background_workers", []),
                    "scheduled_tools": scheduled_tools,
                    "deadline_required_ms": profile.get("deadline_required_ms"),
                    "deadline_optional_ms": profile.get("deadline_optional_ms"),
                    "orphan": bool(profile.get("orphan", False)),
                },
            )
        )
    return nodes


def _worker_nodes(introspection: Dict[str, Any]) -> List[GraphNode]:
    nodes: List[GraphNode] = []
    for worker in introspection.get("workers", []):
        name = str(worker.get("name") or "")
        if not name:
            continue
        nodes.append(
            GraphNode(
                id=f"worker:{name}",
                label=name,
                kind="worker",
                description=str(worker.get("description") or ""),
                capabilities=[CapabilityRef(id=f"worker:{name}", kind="worker", label=name)],
                source=_source_ref(worker.get("source")),
                metadata={"worker": name},
            )
        )
    return nodes


def _intent_nodes(introspection: Dict[str, Any]) -> List[GraphNode]:
    intent_names = {str(row.get("intent")) for row in introspection.get("intent_profiles", []) if row.get("intent")}
    for edge in introspection.get("intent_edges", []):
        label = str(edge.get("label") or "")
        if label:
            intent_names.add(label)
    return [
        GraphNode(
            id=f"intent:{intent}",
            label=intent,
            kind="intent",
            capabilities=[CapabilityRef(id=f"intent:{intent}", kind="intent", label=intent)],
            metadata={"intent": intent},
        )
        for intent in sorted(intent_names)
    ]


def _tool_nodes(introspection: Dict[str, Any], guard_ids: set[str]) -> List[GraphNode]:
    nodes: List[GraphNode] = []
    for tool in introspection.get("tool_catalog", []):
        name = str(tool.get("name") or "")
        if not name:
            continue
        guards = [guard_id for guard_id in (f"commit_gate:{name}", f"guardian:{name}") if guard_id in guard_ids]
        nodes.append(
            GraphNode(
                id=f"tool:{name}",
                label=name,
                kind="tool",
                description=str(tool.get("description") or ""),
                capabilities=[
                    CapabilityRef(
                        id=f"tool:{name}",
                        kind="tool",
                        label=name,
                        required=bool(tool.get("is_commit_tool", False)),
                        slots=[str(x) for x in tool.get("required_slots", [])],
                    )
                ],
                guards=guards,
                source=_source_ref(tool.get("source")),
                metadata={
                    "tool": name,
                    "is_commit_tool": bool(tool.get("is_commit_tool", False)),
                    "required_slots": tool.get("required_slots", []),
                    "optional_slots": tool.get("optional_slots", []),
                    "guardian": tool.get("guardian", {}),
                },
            )
        )
    return nodes


def _implicit_tool_nodes(
    introspection: Dict[str, Any],
    existing_tool_node_ids: set[str],
    guard_ids: set[str],
) -> List[GraphNode]:
    tool_names: set[str] = set()
    for profile in introspection.get("profiles", []):
        tool_names.update(str(tool) for tool in profile.get("scheduled_tools", []) if tool)
    tool_names.update(str(gate.get("tool")) for gate in introspection.get("commit_gates", []) if gate.get("tool"))
    tool_names.update(str(rule.get("tool")) for rule in introspection.get("guardian_rules", []) if rule.get("tool"))

    nodes: List[GraphNode] = []
    for name in sorted(tool_names):
        node_id = f"tool:{name}"
        if node_id in existing_tool_node_ids:
            continue
        guards = [guard_id for guard_id in (f"commit_gate:{name}", f"guardian:{name}") if guard_id in guard_ids]
        nodes.append(
            GraphNode(
                id=node_id,
                label=name,
                kind="tool",
                capabilities=[CapabilityRef(id=node_id, kind="tool", label=name)],
                guards=guards,
                metadata={"tool": name, "implicit_from_introspection": True},
            )
        )
    return nodes


def _layer_nodes(introspection: Dict[str, Any]) -> List[GraphNode]:
    nodes: List[GraphNode] = []
    for layer in introspection.get("layers", []):
        layer_id = str(layer.get("id") or "")
        if not layer_id:
            continue
        nodes.append(
            GraphNode(
                id=f"layer:{layer_id}",
                label=str(layer.get("name") or layer_id),
                kind="layer",
                description=str(layer.get("description") or ""),
                capabilities=[CapabilityRef(id=f"layer:{layer_id}", kind="layer", label=str(layer.get("name") or layer_id))],
                metadata={"components": layer.get("components", [])},
            )
        )
    return nodes


def _commit_gate_nodes(introspection: Dict[str, Any], guard_ids: set[str]) -> List[GraphNode]:
    nodes: List[GraphNode] = []
    for gate in introspection.get("commit_gates", []):
        tool = str(gate.get("tool") or "")
        if not tool:
            continue
        guard_id = f"commit_gate:{tool}"
        nodes.append(
            GraphNode(
                id=f"commit_gate:{tool}",
                label=f"{tool} commit gate",
                kind="commit_gate",
                guards=[guard_id] if guard_id in guard_ids else [],
                metadata={
                    "tool": tool,
                    "required_slots": gate.get("required_slots", []),
                    "optional_slots": gate.get("optional_slots", []),
                },
            )
        )
    return nodes


def _export_guards(introspection: Dict[str, Any]) -> List[GraphGuard]:
    guards: List[GraphGuard] = []
    for gate in introspection.get("commit_gates", []):
        tool = str(gate.get("tool") or "")
        if not tool:
            continue
        required_slots = [str(x) for x in gate.get("required_slots", [])]
        optional_slots = [str(x) for x in gate.get("optional_slots", [])]
        guards.append(
            GraphGuard(
                id=f"commit_gate:{tool}",
                label=f"{tool} required slots",
                kind="commit_slot_gate",
                applies_to=[f"tool:{tool}", f"commit_gate:{tool}"],
                required_slots=required_slots,
                optional_slots=optional_slots,
                description="Commit is allowed only after required slots are present.",
            )
        )
    for rule in introspection.get("guardian_rules", []):
        tool = str(rule.get("tool") or "")
        if not tool:
            continue
        guards.append(
            GraphGuard(
                id=f"guardian:{tool}",
                label=f"{tool} guardian preconditions",
                kind="guardian_precondition",
                applies_to=[f"tool:{tool}"],
                description="Executor-level guard exported from GUARDIAN preconditions.",
                metadata={
                    "required_from_args": rule.get("required_from_args", []),
                    "min_prior_assistant_turns": rule.get("min_prior_assistant_turns", 0),
                },
            )
        )
    return guards


def _intent_edges(introspection: Dict[str, Any]) -> List[GraphEdge]:
    edges: List[GraphEdge] = []
    for edge in introspection.get("intent_edges", []):
        intent_label = str(edge.get("label") or "")
        target = str(edge.get("to") or "").replace("profile_", "profile:", 1)
        if not intent_label or not target:
            continue
        edges.append(
            GraphEdge(
                id=f"intent:{intent_label}->profile:{target.removeprefix('profile:')}",
                from_node=f"intent:{intent_label}",
                to_node=target,
                kind="intent_classification",
                label=intent_label,
                metadata={"raw": edge},
            )
        )
    return edges


def _profile_reroute_edges(introspection: Dict[str, Any]) -> List[GraphEdge]:
    edges: List[GraphEdge] = []
    for reroute in introspection.get("profile_reroutes", []):
        reroute_id = str(reroute.get("id") or "")
        to_profile = str(reroute.get("to_profile") or "")
        if not reroute_id or not to_profile:
            continue
        for from_profile in reroute.get("from_profiles", []):
            from_id = str(from_profile)
            edges.append(
                GraphEdge(
                    id=f"reroute:{reroute_id}:{from_id}->{to_profile}",
                    from_node=f"profile:{from_id}",
                    to_node=f"profile:{to_profile}",
                    kind="profile_reroute",
                    label=reroute_id,
                    condition=reroute.get("condition"),
                    metadata={"source": reroute.get("source")},
                )
            )
    return edges


def _profile_worker_edges(introspection: Dict[str, Any]) -> List[GraphEdge]:
    edges: List[GraphEdge] = []
    for profile in introspection.get("profiles", []):
        profile_id = str(profile.get("id") or "")
        if not profile_id:
            continue
        worker_roles = (
            ("required", profile.get("required_workers", [])),
            ("optional", profile.get("optional_workers", [])),
            ("background", profile.get("background_workers", [])),
        )
        for role, workers in worker_roles:
            for worker in workers:
                worker_id = str(worker)
                edges.append(
                    GraphEdge(
                        id=f"profile:{profile_id}->worker:{worker_id}:{role}",
                        from_node=f"profile:{profile_id}",
                        to_node=f"worker:{worker_id}",
                        kind="runs_worker",
                        label=role,
                        metadata={"worker_role": role},
                    )
                )
    return edges


def _profile_tool_edges(introspection: Dict[str, Any]) -> List[GraphEdge]:
    edges: List[GraphEdge] = []
    for profile in introspection.get("profiles", []):
        profile_id = str(profile.get("id") or "")
        if not profile_id:
            continue
        for tool in profile.get("scheduled_tools", []):
            tool_id = str(tool)
            edges.append(
                GraphEdge(
                    id=f"profile:{profile_id}->tool:{tool_id}",
                    from_node=f"profile:{profile_id}",
                    to_node=f"tool:{tool_id}",
                    kind="schedules_tool",
                    label="scheduled_tool",
                )
            )
    return edges


def _commit_gate_edges(introspection: Dict[str, Any]) -> List[GraphEdge]:
    edges: List[GraphEdge] = []
    for gate in introspection.get("commit_gates", []):
        tool = str(gate.get("tool") or "")
        if not tool:
            continue
        edges.append(
            GraphEdge(
                id=f"commit_gate:{tool}->tool:{tool}",
                from_node=f"commit_gate:{tool}",
                to_node=f"tool:{tool}",
                kind="requires_slot",
                label="commit gate",
                guard=f"commit_gate:{tool}",
            )
        )
    return edges


def _guardian_edges(introspection: Dict[str, Any]) -> List[GraphEdge]:
    edges: List[GraphEdge] = []
    for rule in introspection.get("guardian_rules", []):
        tool = str(rule.get("tool") or "")
        if not tool:
            continue
        edges.append(
            GraphEdge(
                id=f"guardian:{tool}->tool:{tool}",
                from_node=f"global:runtime_guards",
                to_node=f"tool:{tool}",
                kind="guards_tool",
                label="guardian",
                guard=f"guardian:{tool}",
            )
        )
    return edges


def _layer_edges(introspection: Dict[str, Any]) -> List[GraphEdge]:
    edges: List[GraphEdge] = []
    for layer in introspection.get("layers", []):
        layer_id = str(layer.get("id") or "")
        if not layer_id:
            continue
        edges.append(
            GraphEdge(
                id=f"global:pipeline->layer:{layer_id}",
                from_node="global:pipeline",
                to_node=f"layer:{layer_id}",
                kind="contains",
                label="pipeline layer",
            )
        )
    return edges


def _global_nodes(tenant: str, introspection: Dict[str, Any]) -> List[GraphGlobalNode]:
    fsm = introspection.get("commit_gate_fsm", {})
    return [
        GraphGlobalNode(
            id="global:pipeline",
            label="v4 pipeline",
            scope="pipeline",
            description="Read-only exported description of the live v4 pipeline.",
            metadata={"schema_version": introspection.get("schema_version")},
        ),
        GraphGlobalNode(
            id=f"global:tenant:{tenant}",
            label=f"tenant {tenant}",
            scope="tenant",
            metadata=introspection.get("meta", {}),
        ),
        GraphGlobalNode(
            id="global:runtime_guards",
            label="runtime guards",
            scope="runtime",
            description="Executor-level guard collection described from introspection.",
        ),
        GraphGlobalNode(
            id="global:commit_gate_fsm",
            label="commit gate FSM",
            scope="fsm",
            metadata=fsm if isinstance(fsm, dict) else {},
        ),
    ]


def _capability_refs(nodes: Iterable[GraphNode], guards: Iterable[GraphGuard]) -> List[CapabilityRef]:
    refs: Dict[str, CapabilityRef] = {}
    for node in nodes:
        for capability in node.capabilities:
            refs[capability.id] = capability
    for guard in guards:
        refs[guard.id] = CapabilityRef(
            id=guard.id,
            kind="guard",
            label=guard.label or guard.id,
            required=guard.severity == "blocking",
            slots=guard.required_slots,
        )
    return [refs[key] for key in sorted(refs)]


def _source_ref(value: Any) -> Optional[GraphSourceRef]:
    if not isinstance(value, dict) or not value.get("file"):
        return None
    return GraphSourceRef(
        file=str(value["file"]),
        start_line=value.get("start_line"),
        end_line=value.get("end_line"),
    )


def _dedupe_nodes(nodes: Iterable[GraphNode]) -> List[GraphNode]:
    deduped: Dict[str, GraphNode] = {}
    for node in nodes:
        deduped.setdefault(node.id, node)
    return [deduped[key] for key in sorted(deduped)]


def _dedupe_edges(edges: Iterable[GraphEdge]) -> List[GraphEdge]:
    deduped: Dict[str, GraphEdge] = {}
    for edge in edges:
        deduped.setdefault(edge.id, edge)
    return [deduped[key] for key in sorted(deduped)]
