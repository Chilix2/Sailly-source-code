"""Validation helpers for config graph documents."""

from __future__ import annotations

from typing import Iterable, List

from server.builder.graph_foundation.schemas import ConfigGraphDocument, GraphEdge, GraphGuard


def validate_graph_document(document: ConfigGraphDocument) -> List[str]:
    """Return structural validation errors without mutating the document."""

    errors: List[str] = []
    node_ids = {node.id for node in document.nodes}
    node_ids.update(node.id for node in document.global_nodes)
    guard_ids = {guard.id for guard in document.guards}

    errors.extend(_duplicate_errors("node", [node.id for node in document.nodes]))
    errors.extend(_duplicate_errors("global_node", [node.id for node in document.global_nodes]))
    errors.extend(_duplicate_errors("edge", [edge.id for edge in document.edges]))
    errors.extend(_duplicate_errors("guard", [guard.id for guard in document.guards]))

    for edge in document.edges:
        errors.extend(_edge_reference_errors(edge, node_ids, guard_ids))

    for guard in document.guards:
        errors.extend(_guard_reference_errors(guard, node_ids))

    for node in document.nodes:
        for guard_id in node.guards:
            if guard_id not in guard_ids:
                errors.append(f"node {node.id} references unknown guard {guard_id}")

    return errors


def assert_valid_graph_document(document: ConfigGraphDocument) -> ConfigGraphDocument:
    """Raise ``ValueError`` when graph references are internally inconsistent."""

    errors = validate_graph_document(document)
    if errors:
        raise ValueError("Invalid config graph document: " + "; ".join(errors))
    return document


def _edge_reference_errors(edge: GraphEdge, node_ids: set[str], guard_ids: set[str]) -> List[str]:
    errors: List[str] = []
    if edge.from_node not in node_ids:
        errors.append(f"edge {edge.id} references unknown from node {edge.from_node}")
    if edge.to_node not in node_ids:
        errors.append(f"edge {edge.id} references unknown to node {edge.to_node}")
    if edge.guard and edge.guard not in guard_ids:
        errors.append(f"edge {edge.id} references unknown guard {edge.guard}")
    return errors


def _guard_reference_errors(guard: GraphGuard, node_ids: set[str]) -> List[str]:
    return [
        f"guard {guard.id} applies to unknown node {node_id}"
        for node_id in guard.applies_to
        if node_id not in node_ids
    ]


def _duplicate_errors(kind: str, ids: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item_id in ids:
        if item_id in seen:
            duplicates.add(item_id)
        seen.add(item_id)
    return [f"duplicate {kind} id {item_id}" for item_id in sorted(duplicates)]
