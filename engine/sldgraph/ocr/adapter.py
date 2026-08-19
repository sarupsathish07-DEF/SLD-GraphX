"""Stable local OCR boundary; implementations must return evidence, never guesses."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, Field


class OcrTextEvidence(BaseModel):
    raw_text: str
    confidence: float = Field(ge=0, le=1)
    bbox: tuple[float, float, float, float]
    page: int = 1
    engine: str
    model_id: str | None = None


class OcrRequest(BaseModel):
    request_id: str
    image_path: str
    page: int = 1
    mode: Literal["full_page", "tiled"] = "full_page"
    tile_size: int = Field(default=1800, ge=512, le=4096)
    tile_overlap: int = Field(default=160, ge=0, le=512)
    timeout_seconds: float = Field(default=45, gt=0, le=180)


class OcrRegion(BaseModel):
    id: str
    text: str
    confidence: float = Field(ge=0, le=1)
    polygon: list[tuple[float, float]]
    bbox_normalized: tuple[float, float, float, float]
    rotation_deg: int = 0
    tile_origin: tuple[int, int] | None = None


class OcrResponse(BaseModel):
    request_id: str
    engine: str
    model: str
    image_width: int
    image_height: int
    elapsed_ms: float = Field(ge=0)
    regions: list[OcrRegion]


class OcrAdapter(Protocol):
    """Local OCR implementation contract for the later perception pipeline."""

    name: str

    def recognize(self, image_path: Path, page: int = 1) -> list[OcrTextEvidence]: ...


class UnavailableOcrAdapter:
    """Explicitly prevents accidental fallback to an online or fabricated OCR result."""

    name = "unavailable"

    def recognize(self, image_path: Path, page: int = 1) -> list[OcrTextEvidence]:
        raise RuntimeError("No local OCR adapter is installed; OCR has not run")
