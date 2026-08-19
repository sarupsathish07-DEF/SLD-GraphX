"""Small deterministic image degradations for controlled local experiments."""
from __future__ import annotations

import io
import random
from dataclasses import asdict, dataclass

from PIL import Image, ImageEnhance, ImageFilter


@dataclass(frozen=True)
class DegradationConfig:
    seed: int = 1
    blur_radius: float = 0.0
    jpeg_quality: int | None = None
    skew_degrees: float = 0.0
    contrast: float = 1.0
    brightness: float = 1.0
    faded_lines: float = 0.0


def degrade(image: Image.Image, config: DegradationConfig) -> tuple[Image.Image, dict]:
    """Return a deterministic degraded copy and its complete manifest metadata."""
    random.Random(config.seed)  # Seed is deliberately persisted for reproducibility.
    result = image.convert("RGB").copy()
    if config.blur_radius:
        result = result.filter(ImageFilter.GaussianBlur(config.blur_radius))
    if config.contrast != 1:
        result = ImageEnhance.Contrast(result).enhance(config.contrast)
    if config.brightness != 1:
        result = ImageEnhance.Brightness(result).enhance(config.brightness)
    if config.faded_lines:
        result = Image.blend(result, Image.new("RGB", result.size, "#f8f7f2"), config.faded_lines)
    if config.skew_degrees:
        result = result.rotate(config.skew_degrees, resample=Image.Resampling.BICUBIC, fillcolor="#f8f7f2")
    if config.jpeg_quality is not None:
        stream = io.BytesIO()
        result.save(stream, "JPEG", quality=config.jpeg_quality)
        result = Image.open(io.BytesIO(stream.getvalue())).convert("RGB")
    return result, {"kind": "controlled_degradation", "parameters": asdict(config)}


__all__ = ["DegradationConfig", "degrade"]
