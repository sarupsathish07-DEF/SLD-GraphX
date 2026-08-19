"""Stable local OCR boundary; implementations must return evidence, never guesses."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field


class OcrTextEvidence(BaseModel):
    raw_text: str
    confidence: float = Field(ge=0, le=1)
    bbox: tuple[float, float, float, float]
    page: int = 1
    engine: str
    model_id: str | None = None


class OcrAdapter(Protocol):
    """Local OCR implementation contract for the later perception pipeline."""

    name: str

    def recognize(self, image_path: Path, page: int = 1) -> list[OcrTextEvidence]: ...


class UnavailableOcrAdapter:
    """Explicitly prevents accidental fallback to an online or fabricated OCR result."""

    name = "unavailable"

    def recognize(self, image_path: Path, page: int = 1) -> list[OcrTextEvidence]:
        raise RuntimeError("No local OCR adapter is installed; OCR has not run")
