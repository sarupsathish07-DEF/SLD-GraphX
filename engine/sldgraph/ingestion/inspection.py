from __future__ import annotations

from enum import Enum
from pathlib import Path

import fitz
from PIL import Image
from pydantic import BaseModel


class InputType(str, Enum):
    RASTER_IMAGE = "raster_image"
    RASTER_PDF = "raster_pdf"
    VECTOR_PDF = "vector_pdf"
    HYBRID_PDF = "hybrid_pdf"
    UNKNOWN = "unknown"


class InputInspection(BaseModel):
    input_type: InputType
    page_count: int
    width: int | None
    height: int | None
    has_native_text: bool
    native_text_count: int
    has_vector_drawings: bool
    vector_primitive_count: int
    embedded_image_count: int
    recommended_pipeline: str


def inspect_input(path: Path) -> InputInspection:
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg"}:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            return InputInspection(input_type=InputType.RASTER_IMAGE, page_count=1, width=image.width, height=image.height, has_native_text=False, native_text_count=0, has_vector_drawings=False, vector_primitive_count=0, embedded_image_count=1, recommended_pipeline="raster")
    if suffix != ".pdf":
        return InputInspection(input_type=InputType.UNKNOWN, page_count=0, width=None, height=None, has_native_text=False, native_text_count=0, has_vector_drawings=False, vector_primitive_count=0, embedded_image_count=0, recommended_pipeline="unsupported")
    # Use a memory stream: PyMuPDF can retain a Windows file handle after a
    # malformed-document exception, which would otherwise prevent cleanup.
    with fitz.open(stream=path.read_bytes(), filetype="pdf") as document:
        page_count = document.page_count
        text_count = vector_count = image_count = 0
        width = height = None
        for page in document:
            words = page.get_text("words")
            text_count += len(words)
            vector_count += len(page.get_drawings())
            image_count += len(page.get_images(full=True))
            width, height = round(page.rect.width), round(page.rect.height)
    kind = InputType.HYBRID_PDF if vector_count and image_count else InputType.VECTOR_PDF if vector_count else InputType.RASTER_PDF
    return InputInspection(input_type=kind, page_count=page_count, width=width, height=height, has_native_text=bool(text_count), native_text_count=text_count, has_vector_drawings=bool(vector_count), vector_primitive_count=vector_count, embedded_image_count=image_count, recommended_pipeline="hybrid_ready" if kind is InputType.HYBRID_PDF else "vector_ready" if kind is InputType.VECTOR_PDF else "raster")
