"""JSON-lines local PaddleOCR worker; launched only by the core application."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

MODEL_ROOT = Path(__file__).resolve().parents[1] / "models" / "ocr" / "paddle"
DET_MODEL = MODEL_ROOT / "det" / "en_PP-OCRv3_det_infer"
REC_MODEL = MODEL_ROOT / "rec" / "en_PP-OCRv4_rec_infer"
CLS_MODEL = MODEL_ROOT / "cls" / "ch_ppocr_mobile_v2.0_cls_infer"


def _bbox(points: list[list[float]], width: int, height: int) -> tuple[float, float, float, float]:
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    return min(xs) / width, min(ys) / height, max(xs) / width, max(ys) / height


def _normalized_polygon(points: list[list[float]], width: int, height: int) -> list[list[float]]:
    """Return canonical page coordinates; worker-local pixels never leave this boundary."""
    return [[x / width, y / height] for x, y in points]


def _tile_origins(width: int, height: int, size: int, overlap: int) -> list[tuple[int, int]]:
    stride = size - overlap
    xs = list(range(0, max(1, width - size + 1), stride))
    ys = list(range(0, max(1, height - size + 1), stride))
    if xs[-1] != max(0, width - size):
        xs.append(max(0, width - size))
    if ys[-1] != max(0, height - size):
        ys.append(max(0, height - size))
    return [(x, y) for y in ys for x in xs]


def _is_duplicate(region: dict, kept: list[dict]) -> bool:
    left = region["bbox_normalized"]
    for other in kept:
        if other["text"] != region["text"]:
            continue
        right = other["bbox_normalized"]
        x_overlap = max(0, min(left[2], right[2]) - max(left[0], right[0]))
        y_overlap = max(0, min(left[3], right[3]) - max(left[1], right[1]))
        union = (
            (left[2] - left[0]) * (left[3] - left[1])
            + (right[2] - right[0]) * (right[3] - right[1])
            - x_overlap * y_overlap
        )
        if union and x_overlap * y_overlap / union >= 0.55:
            return True
    return False


def main() -> int:
    try:
        from paddleocr import PaddleOCR
    except Exception as exc:
        print(json.dumps({"error": f"PaddleOCR import failed: {exc}"}), flush=True)
        return 2
    required_models = (DET_MODEL, REC_MODEL, CLS_MODEL)
    if not all(path.is_dir() for path in required_models):
        print(
            json.dumps(
                {"error": "Local OCR model files are missing; run scripts/ocr_smoke.py once online"}
            ),
            flush=True,
        )
        return 3
    ocr = PaddleOCR(
        use_angle_cls=True,
        lang="en",
        use_gpu=False,
        show_log=False,
        det_model_dir=str(DET_MODEL),
        rec_model_dir=str(REC_MODEL),
        cls_model_dir=str(CLS_MODEL),
    )
    for line in sys.stdin:
        try:
            request = json.loads(line)
            image_path = Path(request["image_path"])
            if not image_path.is_file():
                raise ValueError("Controlled OCR input is unavailable")
            with Image.open(image_path) as source_image:
                image = source_image.convert("RGB")
            width, height = image.size
            started = time.perf_counter()
            regions = []
            if request["mode"] == "tiled":
                sources = [
                    (
                        x,
                        y,
                        image.crop(
                            (
                                x,
                                y,
                                min(width, x + request["tile_size"]),
                                min(height, y + request["tile_size"]),
                            )
                        ),
                    )
                    for x, y in _tile_origins(
                        width, height, request["tile_size"], request["tile_overlap"]
                    )
                ]
            else:
                sources = [(0, 0, image_path)]
            for origin_x, origin_y, source in sources:
                input_value = np.asarray(source) if isinstance(source, Image.Image) else str(source)
                result = ocr.ocr(input_value, cls=True)[0] or []
                for polygon, (text, confidence) in result:
                    points = [[float(x) + origin_x, float(y) + origin_y] for x, y in polygon]
                    region = {
                        "id": f"text_{len(regions) + 1:03}",
                        "text": str(text),
                        "confidence": float(confidence),
                        "polygon": _normalized_polygon(points, width, height),
                        "bbox_normalized": _bbox(points, width, height),
                        "rotation_deg": 0,
                        "tile_origin": [origin_x, origin_y] if request["mode"] == "tiled" else None,
                    }
                    if not _is_duplicate(region, regions):
                        regions.append(region)
            print(
                json.dumps(
                    {
                        "request_id": request["request_id"],
                        "engine": "paddleocr",
                        "model": "PP-OCRv3-det + PP-OCRv4-rec + cls",
                        "image_width": width,
                        "image_height": height,
                        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                        "regions": regions,
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
