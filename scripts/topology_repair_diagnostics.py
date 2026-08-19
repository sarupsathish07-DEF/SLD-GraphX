"""Development-only false-negative taxonomy, candidate ceiling, and visual evidence report."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from argparse import ArgumentParser
from collections import Counter
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.sldgraph.topology import TopologySymbol, reconstruct
from engine.sldgraph.topology.terminals import nearest_point_on_segment, snap_radius
from services.api.app.services.symbol_worker import detect

DATA = Path("data/synthetic/topology-repair-dev/images")
MANIFEST = Path("data/benchmark/topology-repair-dev/manifest.json")
OUTPUT = Path("artifacts/experiments/topology-repair")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _iou(left, right) -> float:
    x1, y1, x2, y2 = max(left[0], right[0]), max(left[1], right[1]), min(left[2], right[2]), min(left[3], right[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    union = (left[2] - left[0]) * (left[3] - left[1]) + (right[2] - right[0]) * (right[3] - right[1]) - intersection
    return intersection / union if union else 0.0


def _map_symbols(symbols: list[TopologySymbol], truth_nodes: list[dict]) -> dict[str, str]:
    output = {}
    for symbol in symbols:
        matches = [item for item in truth_nodes if item["class_name"] == symbol.predicted_class]
        best = max(matches, key=lambda item: _iou(symbol.bbox_normalized, item["bbox"]), default=None)
        if best and _iou(symbol.bbox_normalized, best["bbox"]) >= 0.25:
            output[symbol.id] = best["id"]
    return output


def _symbol_id(terminal_id: str) -> str:
    return terminal_id.split(":")[1]


def _pairs(items, mapping: dict[str, str]) -> set[frozenset[str]]:
    output = set()
    for item in items:
        left, right = mapping.get(_symbol_id(item.from_node_id)), mapping.get(_symbol_id(item.to_node_id))
        if left and right and left != right:
            output.add(frozenset((left, right)))
    return output


def _truth_segment_distance(result, symbols: list[TopologySymbol], mapped_inverse: dict[str, str], edge: frozenset[str]) -> tuple[float, float]:
    wanted = [item for item in result.terminals if mapped_inverse.get(item.symbol_id) in edge]
    by_id = {item.id: item for item in symbols}
    distances = []
    radii = []
    for terminal in wanted:
        nearest = min(
            (nearest_point_on_segment(terminal.position, conductor.polyline[0], conductor.polyline[-1])[1] for conductor in result.conductors),
            default=float("inf"),
        )
        distances.append(nearest)
        radii.append(snap_radius(by_id[terminal.symbol_id]))
    return (max(distances, default=float("inf")), max(radii, default=0.0))


def _reason(result, symbols, mapping: dict[str, str], edge: frozenset[str]) -> str:
    if not edge.issubset(set(mapping.values())):
        return "SYMBOL_DETECTION_ERROR_PROPAGATION"
    candidate_pairs = _pairs(result.candidates, mapping)
    if edge in candidate_pairs:
        return "GRAPH_REPAIR_DROPPED_EDGE"
    if not result.conductors:
        return "CONDUCTOR_NOT_EXTRACTED"
    inverse = {truth: predicted for predicted, truth in mapping.items()}
    distance, radius = _truth_segment_distance(result, symbols, inverse, edge)
    if distance > radius:
        return "TERMINAL_SNAP_DISTANCE_FAILURE"
    if any(item.symbol_class == "busbar" for item in result.terminals if inverse.get(item.symbol_id) in edge):
        return "BUS_ATTACHMENT_FAILURE"
    return "CONDUCTOR_FRAGMENTED"


def _overlay(entry: dict, image_path: Path, result, symbols: list[TopologySymbol], missed: list[dict], output: Path) -> None:
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    height, width = image.shape[:2]
    for conductor in result.conductors:
        points = [(round(x * width), round(y * height)) for x, y in conductor.polyline]
        cv2.line(image, points[0], points[-1], (240, 170, 30), 1)
    for symbol in symbols:
        x1, y1, x2, y2 = symbol.bbox_normalized
        cv2.rectangle(image, (round(x1 * width), round(y1 * height)), (round(x2 * width), round(y2 * height)), (35, 155, 230), 1)
    for terminal in result.terminals:
        cv2.circle(image, (round(terminal.position[0] * width), round(terminal.position[1] * height)), 4, (60, 200, 80), -1)
    nodes = {item["id"]: item for item in entry["nodes"]}
    for item in missed:
        left, right = (nodes[node] for node in item["edge"])
        lx = round((left["bbox"][0] + left["bbox"][2]) / 2 * width)
        ly = round((left["bbox"][1] + left["bbox"][3]) / 2 * height)
        rx = round((right["bbox"][0] + right["bbox"][2]) / 2 * width)
        ry = round((right["bbox"][1] + right["bbox"][3]) / 2 * height)
        cv2.line(image, (lx, ly), (rx, ry), (40, 40, 220), 2)
        cv2.putText(image, item["reason"], (min(lx, rx), max(20, min(ly, ry) - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (20, 20, 180), 1, cv2.LINE_AA)
    target = output / "errors" / image_path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(target), image)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--frozen", action="store_true", help="Analyze topology-v1 without changing it.")
    arguments = parser.parse_args()
    data = Path("data/synthetic/topology-v1/images") if arguments.frozen else DATA
    manifest_path = Path("data/benchmark/topology-v1/manifest.json") if arguments.frozen else MANIFEST
    output = OUTPUT / ("frozen" if arguments.frozen else "development")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))["entries"]
    all_missed, per_drawing, totals = [], [], Counter()
    candidate_tp = candidate_fn = selected_tp = selected_fn = 0
    for entry in manifest:
        path = data / entry["image"]
        response = detect(path, 1)
        symbols = [TopologySymbol(id=item.id, predicted_class=item.predicted_class.value, bbox_normalized=item.bbox_normalized, confidence=item.confidence) for item in response.detections]
        result, _ = reconstruct(str(path), symbols, [])
        mapping = _map_symbols(symbols, entry["nodes"])
        truth = {frozenset((item["from"], item["to"])) for item in entry["edges"]}
        candidates, selected = _pairs(result.candidates, mapping), _pairs(result.connections, mapping)
        candidate_tp += len(candidates & truth)
        candidate_fn += len(truth - candidates)
        selected_tp += len(selected & truth)
        selected_fn += len(truth - selected)
        missed = []
        for edge in sorted(truth - selected, key=lambda item: sorted(item)):
            reason = _reason(result, symbols, mapping, edge)
            record = {"image": entry["image"], "topology": entry["topology"], "split": entry["split"], "edge": sorted(edge), "reason": reason}
            all_missed.append(record)
            missed.append(record)
            totals[reason] += 1
        _overlay(entry, path, result, symbols, missed, output)
        per_drawing.append({"image": entry["image"], "topology": entry["topology"], "split": entry["split"], "symbols_mapped": len(mapping), "truth_edges": len(truth), "candidate_edges": len(candidates), "selected_edges": len(selected), "missed": missed})
    payload = {
        "pipeline_version": "m4r-development",
        "manifest_sha256": _sha256(manifest_path),
        "code_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "candidate_edge_recall": round(candidate_tp / (candidate_tp + candidate_fn), 4),
        "selected_edge_recall": round(selected_tp / (selected_tp + selected_fn), 4),
        "false_negative_counts": dict(totals),
        "false_negatives": all_missed,
        "per_drawing": per_drawing,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "diagnostics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("candidate_edge_recall", "selected_edge_recall", "false_negative_counts")}, indent=2))


if __name__ == "__main__":
    main()
