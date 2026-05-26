"""Pydantic schemas for lab-safe, config-driven graph documents.

These models describe the v4 pipeline as configuration data for builder/lab
tooling. They are intentionally not imported by the live brain runtime.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

try:
    from pydantic import BaseModel, ConfigDict, Field, validator

    _PYDANTIC_V2 = True
except ImportError:
    from pydantic import BaseModel, Field, validator  # type: ignore

    ConfigDict = None  # type: ignore
    _PYDANTIC_V2 = False


GraphNodeKind = Literal[
    "profile",
    "worker",
    "intent",
    "tool",
    "layer",
    "commit_gate",
    "guard",
    "global",
]
GraphEdgeKind = Literal[
    "intent_classification",
    "profile_reroute",
    "runs_worker",
    "schedules_tool",
    "requires_slot",
    "guards_tool",
    "contains",
    "documents",
]
GlobalNodeScope = Literal["tenant", "pipeline", "runtime", "layer", "fsm"]
GuardSeverity = Literal["info", "warning", "blocking"]
CapabilityKind = Literal["profile", "worker", "tool", "intent", "guard", "layer"]


class GraphSourceRef(BaseModel):
    """Optional source location for an exported graph element."""

    file: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None


class CapabilityRef(BaseModel):
    """Reference to a capability exposed by a profile, worker, tool, or guard."""

    id: str
    kind: CapabilityKind
    label: str = ""
    required: bool = False
    slots: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("id", "kind")
    def _must_not_be_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be blank")
        return value


class GraphGuard(BaseModel):
    """Guard or invariant that constrains graph execution."""

    id: str
    label: str = ""
    kind: Literal["commit_slot_gate", "guardian_precondition", "invariant"] = "invariant"
    severity: GuardSeverity = "blocking"
    applies_to: List[str] = Field(default_factory=list)
    required_slots: List[str] = Field(default_factory=list)
    optional_slots: List[str] = Field(default_factory=list)
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[GraphSourceRef] = None

    @validator("id")
    def _id_must_not_be_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("guard id must not be blank")
        return value


class GraphNode(BaseModel):
    """Node in the exported builder graph."""

    id: str
    label: str
    kind: GraphNodeKind
    description: str = ""
    capabilities: List[CapabilityRef] = Field(default_factory=list)
    guards: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[GraphSourceRef] = None

    @validator("id", "label", "kind")
    def _required_text_must_not_be_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be blank")
        return value


class GraphGlobalNode(GraphNode):
    """Top-level global node for tenant, pipeline, runtime, layer, or FSM state."""

    kind: Literal["global"] = "global"
    scope: GlobalNodeScope = "pipeline"


class GraphEdge(BaseModel):
    """Directed relationship between graph nodes."""

    id: str
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")
    kind: GraphEdgeKind
    label: str = ""
    condition: Optional[str] = None
    guard: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[GraphSourceRef] = None

    @validator("id", "from_node", "to_node", "kind")
    def _edge_text_must_not_be_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be blank")
        return value

    if _PYDANTIC_V2:
        model_config = ConfigDict(populate_by_name=True)  # type: ignore[misc]
    else:
        class Config:
            allow_population_by_field_name = True


class ConfigGraphDocument(BaseModel):
    """Serializable config graph document for builder/lab consumers."""

    schema_version: str = "config-graph.v1"
    graph_version: str = "v4"
    tenant: str = "default"
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    global_nodes: List[GraphGlobalNode] = Field(default_factory=list)
    guards: List[GraphGuard] = Field(default_factory=list)
    capabilities: List[CapabilityRef] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    if _PYDANTIC_V2:
        model_config = ConfigDict(populate_by_name=True)  # type: ignore[misc]
    else:
        class Config:
            allow_population_by_field_name = True

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-ready dict across Pydantic v1/v2."""

        if hasattr(self, "model_dump"):
            return self.model_dump(by_alias=True)  # type: ignore[attr-defined]
        return self.dict(by_alias=True)
