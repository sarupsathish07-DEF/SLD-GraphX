"""Deterministic tile mapping and NMS for normalized electrical symbol evidence."""

from __future__ import annotations


def iou(left: tuple[float, float, float, float], right: tuple[float, float, float, float]) -> float:
    x1 = max(left[0], right[0])
    y1 = max(left[1], right[1])
    x2 = min(left[2], right[2])
    y2 = min(left[3], right[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = (
        (left[2] - left[0]) * (left[3] - left[1])
        + (right[2] - right[0]) * (right[3] - right[1])
        - intersection
    )
    return intersection / union if union else 0.0


def tile_origins(width: int, height: int, size: int, overlap: int) -> list[tuple[int, int]]:
    stride = size - overlap
    xs = list(range(0, max(1, width - size + 1), stride))
    ys = list(range(0, max(1, height - size + 1), stride))
    if xs[-1] != max(0, width - size):
        xs.append(max(0, width - size))
    if ys[-1] != max(0, height - size):
        ys.append(max(0, height - size))
    return [(x, y) for y in ys for x in xs]


def nms(detections: list[dict], threshold: float = 0.45) -> list[dict]:
    kept: list[dict] = []
    for detection in sorted(detections, key=lambda item: item["confidence"], reverse=True):
        if any(
            detection["predicted_class"] == other["predicted_class"]
            and iou(tuple(detection["bbox_normalized"]), tuple(other["bbox_normalized"]))
            >= threshold
            for other in kept
        ):
            continue
        kept.append(detection)
    return kept
