"""Measure real isolated symbol-worker detections on frozen controlled SLDForge manifests."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.sldgraph.symbols import SymbolClass
from engine.sldgraph.symbols.geometry import iou
from services.api.app.services.symbol_worker import detect

DATA = Path("data/synthetic/symbol-v1")
BENCHMARK = Path("data/benchmark/symbol-v1")
OUTPUT = Path("artifacts/experiments/symbol-v1")
MODEL = Path("models/detector/symbol-svm-v1.joblib")


def _metrics(entries: list[dict], label: str, image_root: Path | None = None) -> dict:
    classes = [item.value for item in SymbolClass]
    counts = {item: {"tp": 0, "fp": 0, "fn": 0} for item in classes}
    image_results = []
    image_root = image_root or DATA / "images"
    for entry in entries:
        response = detect(image_root / entry["image"], 1, mode="tiled")
        remaining = list(entry["objects"])
        matches = []
        for detection in sorted(
            response.detections, key=lambda item: item.confidence, reverse=True
        ):
            predicted = detection.predicted_class.value
            candidates = [
                (index, object_item)
                for index, object_item in enumerate(remaining)
                if object_item["class_name"] == predicted
            ]
            best = max(
                candidates,
                key=lambda item: iou(tuple(detection.bbox_normalized), tuple(item[1]["bbox"])),
                default=None,
            )
            if best and iou(tuple(detection.bbox_normalized), tuple(best[1]["bbox"])) >= 0.5:
                counts[predicted]["tp"] += 1
                matches.append(
                    {"detection": detection.id, "ground_truth": best[1]["id"], "class": predicted}
                )
                remaining.pop(best[0])
            else:
                counts[predicted]["fp"] += 1
        for missed in remaining:
            counts[missed["class_name"]]["fn"] += 1
        image_results.append(
            {
                "image": entry["image"],
                "elapsed_ms": response.elapsed_ms,
                "detections": len(response.detections),
                "matches": matches,
            }
        )
    per_class = {}
    for class_name, value in counts.items():
        precision = value["tp"] / (value["tp"] + value["fp"]) if value["tp"] + value["fp"] else 0.0
        recall = value["tp"] / (value["tp"] + value["fn"]) if value["tp"] + value["fn"] else 0.0
        per_class[class_name] = {
            **value,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(2 * precision * recall / (precision + recall), 4)
            if precision + recall
            else 0.0,
        }
    total_tp = sum(item["tp"] for item in counts.values())
    total_fp = sum(item["fp"] for item in counts.values())
    total_fn = sum(item["fn"] for item in counts.values())
    return {
        "label": label,
        "images": len(entries),
        "per_class": per_class,
        "mAP50": {
            "status": "not_available",
            "reason": "Classical SVM evaluation reports class-aware IoU@0.5 precision/recall/F1 rather than ranked detector AP.",
        },
        "mAP50_95": {
            "status": "not_available",
            "reason": "Classical SVM evaluation reports class-aware IoU@0.5 precision/recall/F1 rather than ranked detector AP.",
        },
        "component_semantic_match_rate": round(total_tp / (total_tp + total_fn), 4)
        if total_tp + total_fn
        else 0,
        "totals": {"tp": total_tp, "fp": total_fp, "fn": total_fn},
        "mean_inference_ms": round(
            sum(item["elapsed_ms"] for item in image_results) / len(image_results), 2
        ),
        "per_image": image_results,
    }


def _degrade(source: Path, target: Path, name: str) -> None:
    with Image.open(source) as original:
        image = original.convert("RGB")
    if name == "blur":
        image = image.filter(ImageFilter.GaussianBlur(1.2))
    elif name == "jpeg":
        scratch = target.with_suffix(".jpg")
        image.save(scratch, "JPEG", quality=45)
        with Image.open(scratch) as compressed:
            image = compressed.convert("RGB").copy()
        scratch.unlink(missing_ok=True)
    elif name == "contrast":
        image = ImageEnhance.Contrast(image).enhance(0.55)
    elif name == "brightness":
        image = ImageEnhance.Brightness(image).enhance(0.72)
    elif name == "skew":
        image = image.rotate(1.5, fillcolor="#f8f7f2")
    elif name == "faded_line":
        ImageDraw.Draw(image).line((200, 270, 540, 270), fill="#acb0a8", width=2)
    elif name == "low_resolution":
        image = image.resize((600, 410)).resize(image.size)
    image.save(target, "PNG", optimize=True)


def main() -> None:
    manifest = json.loads((DATA / "canonical-manifest.json").read_text(encoding="utf-8"))["entries"]
    in_style = [entry for entry in manifest if entry["split"] == "test"]
    holdout = [entry for entry in manifest if entry["split"] == "style_holdout"]
    synthetic = _metrics(in_style, "controlled_synthetic_test")
    style = _metrics(holdout, "style_holdout")
    degradations = {}
    # One frozen parent drawing per condition, never mixed into training.
    for name in (
        "clean",
        "blur",
        "jpeg",
        "contrast",
        "brightness",
        "skew",
        "faded_line",
        "low_resolution",
    ):
        source_entry = in_style[0]
        target = BENCHMARK / "degradation" / f"{name}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        _degrade(
            DATA / "images" / source_entry["image"], target, name
        ) if name != "clean" else target.write_bytes(
            (DATA / "images" / source_entry["image"]).read_bytes()
        )
        entry = {**source_entry, "image": target.name}
        degradations[name] = _metrics([entry], f"degradation_{name}", target.parent)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source_manifest = DATA / "canonical-manifest.json"
    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "model_sha256": hashlib.sha256(MODEL.read_bytes()).hexdigest(),
        "dataset_manifest_sha256": hashlib.sha256(source_manifest.read_bytes()).hexdigest(),
        "platform": platform.platform(),
        "in_style": synthetic,
        "style_holdout": style,
        "degradations": degradations,
        "real_validation": {
            "status": "not_run",
            "reason": "No legally verified real/public SLD microset is registered.",
        },
    }
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "in_style": synthetic["component_semantic_match_rate"],
                "style_holdout": style["component_semantic_match_rate"],
                "runtime_ms": synthetic["mean_inference_ms"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
