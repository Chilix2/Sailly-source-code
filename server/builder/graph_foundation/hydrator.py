"""Hydration scaffolding for lab-only config graph documents.

Hydration here means "parse and validate a graph config document", not "install
it into the live runtime". The returned plan is inert and suitable for builder
experiments, previews, or future migration tooling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Union

import yaml

from server.builder.graph_foundation.schemas import ConfigGraphDocument
from server.builder.graph_foundation.validation import assert_valid_graph_document


@dataclass(frozen=True)
class HydratedGraphPlan:
    """Lab-safe plan derived from a config graph document."""

    document: ConfigGraphDocument
    profile_ids: List[str] = field(default_factory=list)
    tool_ids: List[str] = field(default_factory=list)
    worker_ids: List[str] = field(default_factory=list)
    guard_ids: List[str] = field(default_factory=list)

    @property
    def tenant(self) -> str:
        return self.document.tenant


def hydrate_graph_document(document: ConfigGraphDocument) -> HydratedGraphPlan:
    """Validate and summarize a config graph document without runtime side effects."""

    assert_valid_graph_document(document)
    return HydratedGraphPlan(
        document=document,
        profile_ids=_node_ids_by_kind(document, "profile"),
        tool_ids=_node_ids_by_kind(document, "tool"),
        worker_ids=_node_ids_by_kind(document, "worker"),
        guard_ids=sorted(guard.id for guard in document.guards),
    )


def hydrate_graph_config(data: Dict[str, Any]) -> HydratedGraphPlan:
    """Parse a dict into ``ConfigGraphDocument`` and return an inert plan."""

    document = _model_validate(ConfigGraphDocument, data)
    return hydrate_graph_document(document)


def hydrate_graph_config_file(path: Union[str, Path]) -> HydratedGraphPlan:
    """Load a YAML or JSON graph config file for lab validation."""

    config_path = Path(path)
    raw = config_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError(f"graph config must be a mapping: {config_path}")
    return hydrate_graph_config(data)


def _node_ids_by_kind(document: ConfigGraphDocument, kind: str) -> List[str]:
    return sorted(node.id for node in document.nodes if node.kind == kind)


def _model_validate(model_cls, data: Dict[str, Any]):
    if hasattr(model_cls, "model_validate"):
        return model_cls.model_validate(data)
    return model_cls(**data)
