"""Export deterministic SLDForge symbol scenes to canonical, COCO, and YOLO annotations."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sldforge.symbol_dataset import (
    CLASS_ORDER,
    STYLE_FAMILIES,
    render_symbol_scene,
    write_annotation,
)

ROOT = Path("data/synthetic/symbol-v1")
IMAGE_ROOT = ROOT / "images"
ANNOTATION_ROOT = ROOT / "annotations"
YOLO_ROOT = ROOT / "yolo"
BENCHMARK_ROOT = Path("data/benchmark/symbol-v1")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plan() -> list[tuple[str, str, int]]:
    records = []
    for split, styles, start, count in (
        ("train", ("style_a", "style_b", "style_c"), 100, 15),
        ("validation", ("style_a", "style_b", "style_c"), 300, 3),
        ("test", ("style_a", "style_b", "style_c"), 400, 3),
        ("style_holdout", ("style_d",), 500, 12),
    ):
        for style_index, style in enumerate(styles):
            for offset in range(count):
                records.append((split, style, start + style_index * 100 + offset))
    return records


def _yolo_line(class_index: int, bbox: list[float]) -> str:
    x1, y1, x2, y2 = bbox
    return f"{class_index} {(x1 + x2) / 2:.6f} {(y1 + y2) / 2:.6f} {x2 - x1:.6f} {y2 - y1:.6f}"


def _tile_records(entry: dict, tile_size: int = 640, overlap: int = 96) -> list[dict]:
    width, height, stride = entry["width"], entry["height"], tile_size - overlap
    xs = list(range(0, max(1, width - tile_size + 1), stride))
    ys = list(range(0, max(1, height - tile_size + 1), stride))
    if xs[-1] != max(0, width - tile_size):
        xs.append(max(0, width - tile_size))
    if ys[-1] != max(0, height - tile_size):
        ys.append(max(0, height - tile_size))
    records = []
    for x, y in ((x, y) for y in ys for x in xs):
        objects = []
        for item in entry["objects"]:
            x1, y1, x2, y2 = [
                value * scale for value, scale in zip(item["bbox"], (width, height, width, height))
            ]
            ix1, iy1, ix2, iy2 = (
                max(x, x1),
                max(y, y1),
                min(x + tile_size, x2),
                min(y + tile_size, y2),
            )
            visible = max(0, ix2 - ix1) * max(0, iy2 - iy1) / max(1, (x2 - x1) * (y2 - y1))
            if visible >= 0.6:
                objects.append({"id": item["id"], "visibility": round(visible, 4)})
        records.append({"parent_image": entry["image"], "origin": [x, y], "objects": objects})
    return records


def main() -> None:
    for directory in (IMAGE_ROOT, ANNOTATION_ROOT, YOLO_ROOT, BENCHMARK_ROOT):
        directory.mkdir(parents=True, exist_ok=True)
    canonical, coco_images, coco_annotations, categories = [], [], [], []
    for index, symbol_class in enumerate(CLASS_ORDER):
        categories.append({"id": index, "name": symbol_class.value})
    annotation_id = 1
    for split, style, seed in _plan():
        filename = f"{split}-{style}-{seed}.png"
        image, annotations = render_symbol_scene(seed, style, IMAGE_ROOT / filename)
        annotation_path = ANNOTATION_ROOT / f"{Path(filename).stem}.json"
        write_annotation(annotation_path, filename, image, annotations)
        entry = json.loads(annotation_path.read_text(encoding="utf-8"))
        entry.update(
            {
                "split": split,
                "seed": seed,
                "style_family": style,
                "sha256": _sha256(IMAGE_ROOT / filename),
            }
        )
        canonical.append(entry)
        image_id = len(coco_images) + 1
        coco_images.append(
            {"id": image_id, "file_name": filename, "width": image.width, "height": image.height}
        )
        lines = []
        for item in entry["objects"]:
            class_index = next(
                i for i, value in enumerate(CLASS_ORDER) if value.value == item["class_name"]
            )
            lines.append(_yolo_line(class_index, item["bbox"]))
            x1, y1, x2, y2 = item["bbox"]
            coco_annotations.append(
                {
                    "id": annotation_id,
                    "image_id": image_id,
                    "category_id": class_index,
                    "bbox": [
                        x1 * image.width,
                        y1 * image.height,
                        (x2 - x1) * image.width,
                        (y2 - y1) * image.height,
                    ],
                    "area": (x2 - x1) * (y2 - y1) * image.width * image.height,
                    "iscrowd": 0,
                    "sldforge_object_id": item["id"],
                }
            )
            annotation_id += 1
        (YOLO_ROOT / f"{Path(filename).stem}.txt").write_text("\n".join(lines), encoding="utf-8")
    manifests = {
        split: [entry for entry in canonical if entry["split"] == split]
        for split in {item[0] for item in _plan()}
    }
    tile_manifest = [tile for entry in canonical for tile in _tile_records(entry)]
    for split, entries in manifests.items():
        target = BENCHMARK_ROOT / f"{split}-manifest.json"
        target.write_text(
            json.dumps({"split": split, "entries": entries}, indent=2), encoding="utf-8"
        )
    (ROOT / "canonical-manifest.json").write_text(
        json.dumps({"entries": canonical}, indent=2), encoding="utf-8"
    )
    (ROOT / "coco.json").write_text(
        json.dumps(
            {"images": coco_images, "annotations": coco_annotations, "categories": categories},
            indent=2,
        ),
        encoding="utf-8",
    )
    (ROOT / "tile-manifest.json").write_text(
        json.dumps({"tile_size": 640, "overlap": 96, "entries": tile_manifest}, indent=2),
        encoding="utf-8",
    )
    distribution = Counter(item["class_name"] for entry in canonical for item in entry["objects"])
    summary = {
        "drawings": len(canonical),
        "objects": sum(distribution.values()),
        "class_distribution": distribution,
        "styles": STYLE_FAMILIES,
    }
    (ROOT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
