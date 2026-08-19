"""OCR evidence adapters and engineering normalization."""

from .adapter import (
    OcrAdapter,
    OcrRegion,
    OcrRequest,
    OcrResponse,
    OcrTextEvidence,
    UnavailableOcrAdapter,
)

__all__ = [
    "OcrAdapter",
    "OcrRegion",
    "OcrRequest",
    "OcrResponse",
    "OcrTextEvidence",
    "UnavailableOcrAdapter",
]
