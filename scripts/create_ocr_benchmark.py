"""Create the deterministic, drawing-level SLDForge OCR-v1 benchmark."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.sldgraph.ocr.text_intelligence import classify_text, normalize_engineering_text
from sldforge.generator import (
    build_dual_transformer_fixture,
    build_radial_fixture,
    build_sectionalized_bus_fixture,
)
from sldforge.renderer import render_png

OUTPUT = Path("data/benchmark/ocr-v1")


def _degrade(image: Image.Image, name: str) -> Image.Image:
    if name == "clean":
        return image
    if name == "blur":
        return image.filter(ImageFilter.GaussianBlur(radius=1.0))
    if name == "jpeg_compression":
        scratch = OUTPUT / ".jpeg-roundtrip.jpg"
        image.save(scratch, "JPEG", quality=45, optimize=True)
        with Image.open(scratch) as compressed:
            result = compressed.convert("RGB").copy()
        scratch.unlink(missing_ok=True)
        return result
    if name == "low_contrast":
        return ImageEnhance.Contrast(image).enhance(0.55)
    if name == "brightness_shift":
        return ImageEnhance.Brightness(image).enhance(0.72)
    if name == "small_skew":
        return image.rotate(1.5, resample=Image.Resampling.BICUBIC, fillcolor="#f8f7f2")
    if name == "faded_line_proximity":
        result = image.copy()
        draw = ImageDraw.Draw(result)
        draw.line((840, 182, 1110, 182), fill="#a6a7a1", width=2)
        return result
    raise ValueError(f"Unsupported degradation: {name}")


def _items(graph) -> list[dict]:
    records = []
    for item in graph.equipment:
        normalized = normalize_engineering_text(item.equipment_id)
        records.append(
            {
                "raw": item.equipment_id,
                "normalized": normalized.normalized_text,
                "semantic_type": classify_text(normalized.normalized_text).text_type.value,
                "linked_entity": item.id,
                "linked_entity_type": item.type.value,
                "bbox": item.geometry.bbox,
            }
        )
    return records


def _rating_items(graph) -> list[dict]:
    records = []
    for item in graph.equipment:
        rating = str(item.attributes.get("rating", ""))
        for value in re.findall(r"(?<![0-9/])(\d+(?:\.\d+)?)\s*k\s*v", rating, re.I):
            records.append(
                {"raw": f"{value} kV", "semantic_type": "voltage", "linked_entity": item.id}
            )
        for value in re.findall(r"(\d+(?:\.\d+)?)\s*a\b", rating, re.I):
            records.append(
                {"raw": f"{value} A", "semantic_type": "current_rating", "linked_entity": item.id}
            )
        for value, unit in re.findall(r"(\d+(?:\.\d+)?)\s*([km])\s*va", rating, re.I):
            records.append(
                {
                    "raw": f"{value} {unit.upper()}VA",
                    "semantic_type": "power_rating",
                    "linked_entity": item.id,
                }
            )
    return records


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fixtures = (
        ("radial", 101, build_radial_fixture),
        ("dual_transformer", 202, build_dual_transformer_fixture),
        ("sectionalized_bus", 303, build_sectionalized_bus_fixture),
    )
    degradations = (
        "clean",
        "blur",
        "jpeg_compression",
        "low_contrast",
        "brightness_shift",
        "small_skew",
        "faded_line_proximity",
    )
    entries = []
    for index, (topology, seed, builder) in enumerate(fixtures):
        graph = builder()
        base = render_png(graph)
        for degradation in degradations[index :: len(fixtures)]:
            filename = f"{topology}-{degradation}.png"
            image = _degrade(base, degradation)
            image.save(OUTPUT / filename, "PNG", optimize=True)
            entries.append(
                {
                    "drawing": filename,
                    "split": "test",
                    "seed": seed,
                    "topology": topology,
                    "degradation": degradation,
                    "sha256": hashlib.sha256((OUTPUT / filename).read_bytes()).hexdigest(),
                    "text_items": _items(graph),
                    "rating_items": _rating_items(graph),
                }
            )
    manifest = {
        "name": "ocr-v1",
        "version": 1,
        "split_policy": "drawing-level; no training use of this frozen test set",
        "entries": entries,
    }
    (OUTPUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(OUTPUT / "manifest.json")


if __name__ == "__main__":
    main()
