"""Train the isolated, project-owned HOG + linear-SVM electrical symbol classifier."""

from __future__ import annotations

import hashlib
import json
import platform
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.svm import LinearSVC

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.sldgraph.symbols import SymbolClass

ROOT = Path("data/synthetic/symbol-v1")
MODEL_ROOT = Path("models/detector")
MODEL_PATH = MODEL_ROOT / "symbol-svm-v1.joblib"
METADATA_PATH = MODEL_ROOT / "symbol-svm-v1.metadata.json"
LEARNED_CLASSES = [item.value for item in SymbolClass if item is not SymbolClass.BUSBAR]
HOG = cv2.HOGDescriptor((64, 64), (16, 16), (8, 8), (8, 8), 9)


def _feature(
    image: np.ndarray, bbox: list[float] | tuple[float, float, float, float]
) -> np.ndarray:
    height, width = image.shape[:2]
    x1, y1, x2, y2 = [
        int(value * scale) for value, scale in zip(bbox, (width, height, width, height))
    ]
    padding_x, padding_y = max(4, int((x2 - x1) * 0.15)), max(4, int((y2 - y1) * 0.15))
    crop = image[
        max(0, y1 - padding_y) : min(height, y2 + padding_y),
        max(0, x1 - padding_x) : min(width, x2 + padding_x),
    ]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
    return HOG.compute(gray).reshape(-1)


def _jittered_boxes(bbox: list[float], include_jitter: bool) -> list[list[float]]:
    if not include_jitter:
        return [bbox]
    x1, y1, x2, y2 = bbox
    width, height = x2 - x1, y2 - y1
    boxes = [bbox]
    for shift_x, shift_y, scale in ((-0.06, 0.0, 1.08), (0.06, 0.0, 1.08), (0.0, -0.06, 1.12), (0.0, 0.06, 1.12)):
        cx, cy = (x1 + x2) / 2 + shift_x * width, (y1 + y2) / 2 + shift_y * height
        boxes.append([max(0, cx - width * scale / 2), max(0, cy - height * scale / 2), min(1, cx + width * scale / 2), min(1, cy + height * scale / 2)])
    return boxes


def _load(split: str) -> tuple[np.ndarray, np.ndarray]:
    manifest = json.loads((ROOT / "canonical-manifest.json").read_text(encoding="utf-8"))
    features, labels = [], []
    for entry in manifest["entries"]:
        if entry["split"] != split:
            continue
        image = cv2.imread(str(ROOT / "images" / entry["image"]), cv2.IMREAD_COLOR)
        for item in entry["objects"]:
            if item["class_name"] not in LEARNED_CLASSES:
                continue
            for bbox in _jittered_boxes(item["bbox"], include_jitter=split == "train"):
                features.append(_feature(image, bbox))
                labels.append(item["class_name"])
    return np.asarray(features, dtype=np.float32), np.asarray(labels)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    random.seed(42)
    np.random.seed(42)
    started = datetime.now(timezone.utc)
    train_x, train_y = _load("train")
    validation_x, validation_y = _load("validation")
    classifier = CalibratedClassifierCV(
        LinearSVC(C=1.0, class_weight="balanced", dual="auto"), cv=3
    )
    classifier.fit(train_x, train_y)
    prediction = classifier.predict(validation_x)
    report = classification_report(
        validation_y, prediction, labels=LEARNED_CLASSES, output_dict=True, zero_division=0
    )
    MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {"classifier": classifier, "classes": LEARNED_CLASSES, "hog": {"window": 64, "cell": 8}},
        MODEL_PATH,
        compress=3,
    )
    manifest_path = ROOT / "canonical-manifest.json"
    metadata = {
        "name": "symbol-svm-v1",
        "task": "electrical-symbol-classification-with-contour-proposals",
        "architecture": "OpenCV HOG (64x64) + calibrated linear SVM",
        "training_framework": "scikit-learn==1.5.2",
        "deployment_runtime": "scikit-learn==1.5.2 in isolated detector worker",
        "training_date": started.isoformat(),
        "training_config": {
            "seed": 42,
            "C": 1.0,
            "class_weight": "balanced",
            "augmentation": "SLDForge style/domain randomization",
        },
        "dataset_manifest": str(manifest_path),
        "dataset_manifest_sha256": _sha256(manifest_path),
        "classes": LEARNED_CLASSES,
        "train_objects": int(len(train_y)),
        "validation_objects": int(len(validation_y)),
        "validation_report": report,
        "confusion_matrix": confusion_matrix(
            validation_y, prediction, labels=LEARNED_CLASSES
        ).tolist(),
        "model_sha256": _sha256(MODEL_PATH),
        "model_size_bytes": MODEL_PATH.stat().st_size,
        "hardware": {"platform": platform.platform(), "processor": platform.processor()},
        "started_at": started.isoformat(),
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "limitations": "Controlled synthetic styles only; busbar is handled by deterministic geometry rather than the learned classifier.",
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "model": str(MODEL_PATH),
                "sha256": metadata["model_sha256"],
                "macro_f1": report["macro avg"]["f1-score"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
