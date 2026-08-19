from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Provenance(str, Enum):
    SYNTHETIC_GROUND_TRUTH = "synthetic_ground_truth"
    NATIVE_CAD = "native_cad"
    VECTOR_PDF = "vector_pdf"
    VISION = "vision"
    OCR = "ocr"
    GEOMETRY = "geometry"
    WIRE_TRACE = "wire_trace"
    TERMINAL_SNAP = "terminal_snap"
    GRAPH_INFERENCE = "graph_inference"
    ELECTRICAL_RULE = "electrical_rule"
    ENGINEER_VERIFIED = "engineer_verified"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    VERIFIED = "verified"
    REJECTED = "rejected"


class EquipmentType(str, Enum):
    ENERGY_SOURCE = "energy_source"
    GRID_INCOMER = "grid_incomer"
    GENERATOR = "generator"
    POWER_TRANSFORMER = "power_transformer"
    BUSBAR = "busbar"
    CIRCUIT_BREAKER = "circuit_breaker"
    DISCONNECTOR = "disconnector"
    CURRENT_TRANSFORMER = "current_transformer"
    POTENTIAL_TRANSFORMER = "potential_transformer"
    FEEDER = "feeder"
    LOAD = "load"
    BUS_COUPLER = "bus_coupler"
    OFFPAGE_CONNECTOR = "offpage_connector"
    JUNCTION = "junction"
    GENERIC_EQUIPMENT = "generic_equipment"


class SwitchState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    UNKNOWN = "unknown"


class Geometry(BaseModel):
    bbox: tuple[float, float, float, float] | None = None
    polyline: list[tuple[float, float]] = Field(default_factory=list)
    rotation: int = 0


class Evidence(BaseModel):
    id: str
    kind: str
    value: str | None = None
    confidence: float = Field(ge=0, le=1)
    provenance: list[Provenance]


class Equipment(BaseModel):
    id: str
    equipment_id: str
    type: EquipmentType
    page: int = 1
    geometry: Geometry = Field(default_factory=Geometry)
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0, le=1)
    provenance: list[Provenance]
    review_status: ReviewStatus = ReviewStatus.PENDING


class Terminal(BaseModel):
    id: str
    equipment_id: str
    name: str
    position: tuple[float, float]


class Connection(BaseModel):
    id: str
    from_terminal_id: str
    to_terminal_id: str
    geometry: Geometry = Field(default_factory=Geometry)
    switch_state: SwitchState | None = None
    confidence: float = Field(ge=0, le=1)
    provenance: list[Provenance]
    review_status: ReviewStatus = ReviewStatus.PENDING


class FeederPath(BaseModel):
    feeder_equipment_id: str
    source_equipment_id: str | None
    equipment_path: list[str]
    connection_path: list[str] = Field(default_factory=list)
    source_bus_equipment_id: str | None = None
    destination_equipment_id: str | None = None
    switching_equipment_ids: list[str] = Field(default_factory=list)
    weakest_connection_id: str | None = None
    weakest_connection_confidence: float | None = None
    uncertainty_flags: list[str] = Field(default_factory=list)
    provenance: list[Provenance] = Field(default_factory=lambda: [Provenance.GRAPH_INFERENCE])
    confidence: float = Field(ge=0, le=1)
    active: bool


class ReviewIssue(BaseModel):
    id: str
    kind: str
    message: str
    risk_score: float = Field(ge=0, le=1)
    related_connection_id: str | None = None
    status: ReviewStatus = ReviewStatus.PENDING


class ElectricalGraph(BaseModel):
    id: str
    equipment: list[Equipment]
    terminals: list[Terminal]
    connections: list[Connection]
    evidence: list[Evidence] = Field(default_factory=list)
    feeder_paths: list[FeederPath] = Field(default_factory=list)
    review_issues: list[ReviewIssue] = Field(default_factory=list)
