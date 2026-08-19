"""Stable symbol-detection boundary. Core business logic never imports an ML framework."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, Field


class SymbolClass(str, Enum):
    POWER_TRANSFORMER = "power_transformer"
    CIRCUIT_BREAKER = "circuit_breaker"
    DISCONNECTOR = "disconnector"
    CURRENT_TRANSFORMER = "current_transformer"
    POTENTIAL_TRANSFORMER = "potential_transformer"
    BUSBAR = "busbar"
    FEEDER_TERMINAL = "feeder_terminal"
    LOAD = "load"
    ENERGY_SOURCE = "energy_source"
    BUS_COUPLER = "bus_coupler"


class SymbolRequest(BaseModel):
    request_id: str
    image_path: str
    page: int = 1
    mode: Literal["full_page", "tiled"] = "tiled"
    tile_size: int = Field(default=800, ge=256, le=2048)
    tile_overlap: int = Field(default=96, ge=0, le=512)
    confidence_threshold: float = Field(default=0.35, ge=0, le=1)
    timeout_seconds: float = Field(default=90, gt=0, le=300)


class SymbolDetection(BaseModel):
    id: str
    predicted_class: SymbolClass
    confidence: float = Field(ge=0, le=1)
    bbox_normalized: tuple[float, float, float, float]
    polygon: list[tuple[float, float]] = Field(default_factory=list)
    orientation_deg: int = 0
    tile_origin: tuple[int, int] | None = None


class SymbolResponse(BaseModel):
    request_id: str
    engine: str
    model: str
    image_width: int
    image_height: int
    elapsed_ms: float = Field(ge=0)
    detections: list[SymbolDetection]


class SymbolDetector(Protocol):
    name: str

    def detect(self, image_path: Path, page: int = 1) -> SymbolResponse: ...


class UnavailableSymbolDetector:
    name = "unavailable"

    def detect(self, image_path: Path, page: int = 1) -> SymbolResponse:
        raise RuntimeError("No local symbol detector is installed; symbol detection has not run")
