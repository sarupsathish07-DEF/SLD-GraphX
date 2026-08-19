"""Typed, explainable evidence contracts for physical topology reconstruction."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CrossingKind(str, Enum):
    CONNECTED_JUNCTION = "connected_junction"
    CROSSOVER_NO_CONNECTION = "crossover_no_connection"
    AMBIGUOUS_CROSSING = "ambiguous_crossing"


class TopologySymbol(BaseModel):
    id: str
    predicted_class: str
    bbox_normalized: tuple[float, float, float, float]
    confidence: float | None = None
    page: int = 1


class TopologyText(BaseModel):
    id: str
    bbox_normalized: tuple[float, float, float, float]
    page: int = 1


class ConductorEvidence(BaseModel):
    id: str
    page: int = 1
    polyline: list[tuple[float, float]]
    confidence: float = Field(ge=0, le=1)
    provenance: str = "raster_line_trace"
    masked_interruption: bool = False


class BusbarEvidence(BaseModel):
    id: str
    page: int = 1
    polyline: list[tuple[float, float]]
    bbox_normalized: tuple[float, float, float, float]
    confidence: float = Field(ge=0, le=1)
    provenance: str = "geometry"
    review_status: str = "pending"
    associated_symbol_id: str | None = None


class JunctionEvidence(BaseModel):
    id: str
    page: int = 1
    position: tuple[float, float]
    kind: CrossingKind
    degree: int
    confidence: float = Field(ge=0, le=1)
    provenance: str = "skeleton_degree"
    review_status: str = "pending"


class TerminalEvidence(BaseModel):
    id: str
    symbol_id: str
    symbol_class: str
    page: int = 1
    name: str
    position: tuple[float, float]
    orientation_deg: int
    orientation_confidence: float = Field(ge=0, le=1)
    provenance: str = "symbol_template"


class CandidateEdge(BaseModel):
    id: str
    page: int = 1
    from_node_id: str
    to_node_id: str
    conductor_id: str | None = None
    polyline: list[tuple[float, float]]
    visual_continuity_score: float = Field(ge=0, le=1)
    endpoint_distance_score: float = Field(ge=0, le=1)
    orientation_score: float = Field(ge=0, le=1)
    terminal_score: float = Field(ge=0, le=1)
    junction_score: float = Field(ge=0, le=1)
    electrical_structural_score: float = Field(ge=0, le=1)
    overall_confidence: float = Field(ge=0, le=1)
    provenance: str
    review_status: str = "pending"
    review_reason: str | None = None
    gap_bridge: bool = False


class TopologyIssue(BaseModel):
    id: str
    kind: str
    message: str
    related_edge_id: str | None = None
    severity: str = "review"


class TopologyResult(BaseModel):
    page: int = 1
    conductors: list[ConductorEvidence] = Field(default_factory=list)
    buses: list[BusbarEvidence] = Field(default_factory=list)
    junctions: list[JunctionEvidence] = Field(default_factory=list)
    terminals: list[TerminalEvidence] = Field(default_factory=list)
    candidates: list[CandidateEdge] = Field(default_factory=list)
    connections: list[CandidateEdge] = Field(default_factory=list)
    issues: list[TopologyIssue] = Field(default_factory=list)
    elapsed_ms: float = 0
