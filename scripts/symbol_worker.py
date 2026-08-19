"""JSON-lines isolated worker for the trained local electrical symbol detector."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import cv2
import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "detector" / "symbol-svm-v1.joblib"
HOG = cv2.HOGDescriptor((64, 64), (16, 16), (8, 8), (8, 8), 9)


def _origins(width: int, height: int, size: int, overlap: int) -> list[tuple[int, int]]:
    stride = size - overlap
    xs = list(range(0, max(1, width - size + 1), stride))
    ys = list(range(0, max(1, height - size + 1), stride))
    if xs[-1] != max(0, width - size):
        xs.append(max(0, width - size))
    if ys[-1] != max(0, height - size):
        ys.append(max(0, height - size))
    return [(x, y) for y in ys for x in xs]


def _feature(image: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    x1, y1, x2, y2 = box
    padding_x, padding_y = max(4, int((x2 - x1) * 0.15)), max(4, int((y2 - y1) * 0.15))
    crop = image[
        max(0, y1 - padding_y) : min(image.shape[0], y2 + padding_y),
        max(0, x1 - padding_x) : min(image.shape[1], x2 + padding_x),
    ]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return HOG.compute(cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)).reshape(1, -1)


def _iou(left: list[float], right: list[float]) -> float:
    x1, y1, x2, y2 = (
        max(left[0], right[0]),
        max(left[1], right[1]),
        min(left[2], right[2]),
        min(left[3], right[3]),
    )
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = (
        (left[2] - left[0]) * (left[3] - left[1])
        + (right[2] - right[0]) * (right[3] - right[1])
        - intersection
    )
    return intersection / union if union else 0.0


def _nms(detections: list[dict]) -> list[dict]:
    kept: list[dict] = []
    for detection in sorted(detections, key=lambda item: item["confidence"], reverse=True):
        if any(_iou(detection["bbox_normalized"], other["bbox_normalized"]) >= 0.35 for other in kept):
            continue
        kept.append(detection)
    return kept


def _proposals(tile: np.ndarray) -> list[tuple[int, int, int, int, bool]]:
    gray = cv2.cvtColor(tile, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    grouped = cv2.dilate(mask, np.ones((15, 15), np.uint8), iterations=1)
    contours, _ = cv2.findContours(grouped, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    raw = []
    for contour in contours:
        x, y, width, height = cv2.boundingRect(contour)
        if y > tile.shape[0] - 90 or width < 28 or height < 20 or width > 360 or height > 260:
            continue
        is_busbar = width / max(1, height) >= 4.2 and height <= 54
        if is_busbar and (x < 55 or y < 55 or x + width > tile.shape[1] - 55):
            continue
        # Glyph labels are intentionally not symbol proposals. Keep only long thin busbars.
        if height <= 30 and width < 150:
            continue
        if not is_busbar and width * height < 900:
            continue
        raw.append((x, y, x + width, y + height, is_busbar))
    merged: list[tuple[int, int, int, int, bool]] = []
    for proposal in sorted(raw, key=lambda item: (item[1], item[0])):
        x1, y1, x2, y2, is_busbar = proposal
        if not is_busbar:
            close = next(
                (
                    index
                    for index, other in enumerate(merged)
                    if not other[4]
                    and abs((other[1] + other[3]) / 2 - (y1 + y2) / 2) < 30
                    and 0 <= x1 - other[2] < 36
                ),
                None,
            )
            if close is not None:
                other = merged[close]
                merged[close] = (other[0], min(other[1], y1), x2, max(other[3], y2), False)
                continue
        merged.append(proposal)
    return merged


def _busbar_proposals(tile: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Detect thick bus strokes separately from thin branch conductors."""
    gray = cv2.cvtColor(tile, cv2.COLOR_BGR2GRAY)
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    horizontal = cv2.morphologyEx(
        ink,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (max(45, tile.shape[1] // 14), 1)),
    )
    count, _, stats, _ = cv2.connectedComponentsWithStats(horizontal)
    output = []
    for index in range(1, count):
        x, y, width, height, area = (int(value) for value in stats[index])
        if width < 85 or not 5 <= height <= 18 or area < 320:
            continue
        if x < 24 or y < 60 or x + width > tile.shape[1] - 24:
            continue
        pad_y = max(10, round(width * 0.1))
        output.append((x, max(0, y - pad_y), x + width, min(tile.shape[0], y + height + pad_y)))
    return output


def _bus_coupler_proposals(tile: np.ndarray, buses: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    """Use paired, same-level bus strokes to propose only a bounded central coupler box."""
    gray = cv2.cvtColor(tile, cv2.COLOR_BGR2GRAY)
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    output = []
    for index, left in enumerate(sorted(buses)):
        for right in sorted(buses)[index + 1 :]:
            left_y, right_y = (left[1] + left[3]) / 2, (right[1] + right[3]) / 2
            gap = right[0] - left[2]
            if abs(left_y - right_y) > 14 or not 70 <= gap <= 250:
                continue
            size = round(min(110, max(56, gap * 0.48)))
            center_x, center_y = round((left[2] + right[0]) / 2), round((left_y + right_y) / 2)
            x1, y1 = max(0, center_x - size // 2), max(0, center_y - size // 2)
            x2, y2 = min(tile.shape[1], center_x + size // 2), min(tile.shape[0], center_y + size // 2)
            if np.count_nonzero(ink[y1:y2, x1:x2]) / max(1, (x2 - x1) * (y2 - y1)) >= 0.025:
                output.append((x1, y1, x2, y2))
    return output


def _page_bus_coupler_proposals(image: np.ndarray, detections: list[dict]) -> list[tuple[int, int, int, int]]:
    height, width = image.shape[:2]
    buses = []
    for item in detections:
        if item["predicted_class"] != "busbar":
            continue
        x1, y1, x2, y2 = item["bbox_normalized"]
        buses.append((round(x1 * width), round(y1 * height), round(x2 * width), round(y2 * height)))
    return _bus_coupler_proposals(image, buses)


def _detect(image: np.ndarray, request: dict, model: dict) -> list[dict]:
    height, width = image.shape[:2]
    tiles = (
        _origins(width, height, request["tile_size"], request["tile_overlap"])
        if request["mode"] == "tiled"
        else [(0, 0)]
    )
    detections = []
    for origin_x, origin_y in tiles:
        tile = image[
            origin_y : min(height, origin_y + request["tile_size"]),
            origin_x : min(width, origin_x + request["tile_size"]),
        ]
        bus_boxes = _busbar_proposals(tile)
        for x1, y1, x2, y2 in bus_boxes:
            page_box = [(x1 + origin_x) / width, (y1 + origin_y) / height, (x2 + origin_x) / width, (y2 + origin_y) / height]
            detections.append({"id": f"symbol_{len(detections) + 1:03}", "predicted_class": "busbar", "confidence": 0.88, "bbox_normalized": page_box, "polygon": [[page_box[0], page_box[1]], [page_box[2], page_box[1]], [page_box[2], page_box[3]], [page_box[0], page_box[3]]], "orientation_deg": 0, "tile_origin": [origin_x, origin_y] if request["mode"] == "tiled" else None, "detector_engine": "deterministic-busbar-thickness"})
        for x1, y1, x2, y2 in _bus_coupler_proposals(tile, bus_boxes):
            page_box = [(x1 + origin_x) / width, (y1 + origin_y) / height, (x2 + origin_x) / width, (y2 + origin_y) / height]
            detections.append({"id": f"symbol_{len(detections) + 1:03}", "predicted_class": "bus_coupler", "confidence": 0.77, "bbox_normalized": page_box, "polygon": [[page_box[0], page_box[1]], [page_box[2], page_box[1]], [page_box[2], page_box[3]], [page_box[0], page_box[3]]], "orientation_deg": 0, "tile_origin": [origin_x, origin_y] if request["mode"] == "tiled" else None, "detector_engine": "deterministic-bus-coupler-geometry"})
        for x1, y1, x2, y2, is_busbar in _proposals(tile):
            if is_busbar:
                class_name, confidence, engine = "busbar", 0.82, "deterministic-busbar-geometry"
            else:
                probabilities = model["classifier"].predict_proba(_feature(tile, (x1, y1, x2, y2)))[
                    0
                ]
                index = int(np.argmax(probabilities))
                class_name, confidence, engine = (
                    model["classifier"].classes_[index],
                    float(probabilities[index]),
                    "hog-linear-svm",
                )
                # Source circles use blue ink; CT uses the same circular geometry with a
                # dark conductor. This is direct visual evidence, not text-based relabeling.
                crop = tile[y1:y2, x1:x2].astype(np.int16)
                blue_pixels = np.sum(
                    (crop[:, :, 0] > crop[:, :, 2] + 25) & (crop[:, :, 0] > crop[:, :, 1] + 12)
                )
                if class_name == "energy_source" and blue_pixels < 8:
                    class_name, confidence, engine = (
                        "current_transformer",
                        max(confidence, 0.58),
                        "hog-linear-svm+color-geometry",
                    )
            if confidence < request["confidence_threshold"]:
                continue
            page_box = [
                (x1 + origin_x) / width,
                (y1 + origin_y) / height,
                (x2 + origin_x) / width,
                (y2 + origin_y) / height,
            ]
            detections.append(
                {
                    "id": f"symbol_{len(detections) + 1:03}",
                    "predicted_class": class_name,
                    "confidence": round(confidence, 5),
                    "bbox_normalized": page_box,
                    "polygon": [
                        [page_box[0], page_box[1]],
                        [page_box[2], page_box[1]],
                        [page_box[2], page_box[3]],
                        [page_box[0], page_box[3]],
                    ],
                    "orientation_deg": 0,
                    "tile_origin": [origin_x, origin_y] if request["mode"] == "tiled" else None,
                    "detector_engine": engine,
                }
            )
    for x1, y1, x2, y2 in _page_bus_coupler_proposals(image, detections):
        page_box = [x1 / width, y1 / height, x2 / width, y2 / height]
        detections.append({"id": f"symbol_{len(detections) + 1:03}", "predicted_class": "bus_coupler", "confidence": 0.77, "bbox_normalized": page_box, "polygon": [[page_box[0], page_box[1]], [page_box[2], page_box[1]], [page_box[2], page_box[3]], [page_box[0], page_box[3]]], "orientation_deg": 0, "tile_origin": None, "detector_engine": "deterministic-bus-coupler-geometry"})
    return _nms(detections)


def main() -> int:
    if not MODEL_PATH.is_file():
        print(
            json.dumps(
                {"error": "Local symbol model is missing; run scripts/train_symbol_detector.py"}
            ),
            flush=True,
        )
        return 3
    model = joblib.load(MODEL_PATH)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            image = cv2.imread(request["image_path"], cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Controlled detector input is unavailable")
            started = time.perf_counter()
            detections = _detect(image, request, model)
            height, width = image.shape[:2]
            for item in detections:
                item.pop("detector_engine", None)
            print(
                json.dumps(
                    {
                        "request_id": request["request_id"],
                        "engine": "hog-linear-svm + deterministic-busbar-geometry",
                        "model": "symbol-svm-v1",
                        "image_width": width,
                        "image_height": height,
                        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                        "detections": detections,
                    }
                ),
                flush=True,
            )
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "request_id": request.get("request_id", "unknown")
                        if "request" in locals()
                        else "unknown",
                        "error": str(exc),
                    }
                ),
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
