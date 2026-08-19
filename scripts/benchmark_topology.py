"""Evaluate actual local detector plus topology extraction against frozen SLDForge endpoint truth."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import cv2
from PIL import Image, ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.sldgraph.topology import TopologySymbol, reconstruct
from engine.sldgraph.topology.assemble import build_endpoint_candidates, repair_and_select
from engine.sldgraph.topology.raster import extract_conductors
from engine.sldgraph.topology.terminals import generate_terminals
from services.api.app.services.symbol_worker import detect

DATA = Path("data/synthetic/topology-v1/images")
MANIFEST = Path("data/benchmark/topology-v1/manifest.json")
OUTPUT = Path("artifacts/experiments/topology-v1")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _iou(left, right) -> float:
    x1, y1, x2, y2 = max(left[0], right[0]), max(left[1], right[1]), min(left[2], right[2]), min(left[3], right[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    union = (left[2] - left[0]) * (left[3] - left[1]) + (right[2] - right[0]) * (right[3] - right[1]) - intersection
    return intersection / union if union else 0.0


def _symbols(path: Path):
    response = detect(path, 1)
    return response, [TopologySymbol(id=item.id, predicted_class=item.predicted_class.value, bbox_normalized=item.bbox_normalized, confidence=item.confidence) for item in response.detections]


def _map_symbols(symbols: list[TopologySymbol], truth_nodes: list[dict]) -> dict[str, str]:
    mapping = {}
    for symbol in symbols:
        choices = [item for item in truth_nodes if item["class_name"] == symbol.predicted_class]
        best = max(choices, key=lambda item: _iou(symbol.bbox_normalized, item["bbox"]), default=None)
        if best and _iou(symbol.bbox_normalized, best["bbox"]) >= 0.25:
            mapping[symbol.id] = best["id"]
    return mapping


def _symbol_id(terminal_id: str) -> str:
    return terminal_id.split(":")[1]


def _pairs(connections, mapping: dict[str, str]) -> set[frozenset[str]]:
    result = set()
    for item in connections:
        left, right = mapping.get(_symbol_id(item.from_node_id)), mapping.get(_symbol_id(item.to_node_id))
        if left and right and left != right:
            result.add(frozenset((left, right)))
    return result


def _baseline(path: Path, symbols: list[TopologySymbol]):
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    conductors, _, _, _ = extract_conductors(image, [], [])
    candidates = build_endpoint_candidates(conductors, generate_terminals(symbols), symbols)
    return repair_and_select(candidates)[0]


def _metrics(entry: dict, path: Path) -> dict:
    started = time.perf_counter()
    detector_response, symbols = _symbols(path)
    result, _ = reconstruct(str(path), symbols, [])
    mapping = _map_symbols(symbols, entry["nodes"])
    truth = {frozenset((item["from"], item["to"])) for item in entry["edges"]}
    predicted = _pairs(result.connections, mapping)
    candidate = _pairs(result.candidates, mapping)
    baseline = _pairs(_baseline(path, symbols), mapping)
    tp, fp, fn = len(predicted & truth), len(predicted - truth), len(truth - predicted)
    base_tp, base_fp, base_fn = len(baseline & truth), len(baseline - truth), len(truth - baseline)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    base_precision = base_tp / (base_tp + base_fp) if base_tp + base_fp else 0.0
    base_recall = base_tp / (base_tp + base_fn) if base_tp + base_fn else 0.0
    base_f1 = 2 * base_precision * base_recall / (base_precision + base_recall) if base_precision + base_recall else 0.0
    critical = {frozenset((item["from"], item["to"])) for item in entry["edges"] if item["critical"]}
    critical_recall = len(predicted & critical) / len(critical) if critical else 1.0
    all_nodes = [item["id"] for item in entry["nodes"]]
    truth_components = _components(all_nodes, truth)
    predicted_components = _components(all_nodes, predicted)
    pair_checks = [(left, right) for index, left in enumerate(all_nodes) for right in all_nodes[index + 1 :]]
    reachability = sum((_connected(left, right, truth_components) == _connected(left, right, predicted_components)) for left, right in pair_checks) / len(pair_checks) if pair_checks else 1.0
    connected_junctions = [item for item in result.junctions if item.kind.value == "connected_junction"]
    return {"image": entry["image"], "topology": entry["topology"], "style": entry["style"], "symbols_detected": len(symbols), "symbols_mapped": len(mapping), "tp": tp, "fp": fp, "fn": fn, "candidate_tp": len(candidate & truth), "candidate_fn": len(truth - candidate), "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4), "critical_edge_recall": round(critical_recall, 4), "physical_reachability_accuracy": round(reachability, 4), "connected_component_correct": truth_components == predicted_components, "junction_accuracy": 1.0 if not connected_junctions else 0.0, "baseline": {"tp": base_tp, "fp": base_fp, "fn": base_fn, "precision": round(base_precision, 4), "recall": round(base_recall, 4), "f1": round(base_f1, 4)}, "runtime_ms": round((time.perf_counter() - started) * 1000, 2), "detector_inference_ms": detector_response.elapsed_ms, "topology_inference_ms": result.elapsed_ms, "errors": _errors(tp, fp, fn, len(mapping), len(entry["nodes"]))}


def _components(nodes: list[str], edges: set[frozenset[str]]) -> list[frozenset[str]]:
    unseen, components = set(nodes), []
    while unseen:
        seed, component, queue = unseen.pop(), set(), []
        queue.append(seed)
        while queue:
            node = queue.pop()
            if node in component:
                continue
            component.add(node)
            neighbours = {next(iter(edge - {node})) for edge in edges if node in edge}
            queue.extend(neighbours - component)
        unseen -= component
        components.append(frozenset(component))
    return sorted(components, key=lambda item: sorted(item))


def _connected(left: str, right: str, components: list[frozenset[str]]) -> bool:
    return any(left in item and right in item for item in components)


def _errors(tp: int, fp: int, fn: int, mapped: int, truth_nodes: int) -> list[str]:
    errors = []
    if fn:
        errors.append("MISSED_CONDUCTOR")
    if fp:
        errors.append("FALSE_CONDUCTOR")
    if mapped < truth_nodes:
        errors.append("TERMINAL_SNAP_ERROR")
    if not errors and tp:
        errors.append("NONE")
    return errors


def _aggregate(results: list[dict]) -> dict:
    tp, fp, fn = (sum(item[key] for item in results) for key in ("tp", "fp", "fn"))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    candidate_tp, candidate_fn = (sum(item[key] for item in results) for key in ("candidate_tp", "candidate_fn"))
    return {"drawings": len(results), "tp": tp, "fp": fp, "fn": fn, "candidate_edge_recall": round(candidate_tp / (candidate_tp + candidate_fn), 4) if candidate_tp + candidate_fn else 0.0, "edge_precision": round(precision, 4), "edge_recall": round(recall, 4), "edge_f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0, "critical_edge_recall": round(sum(item["critical_edge_recall"] for item in results) / len(results), 4) if results else 0.0, "physical_reachability_accuracy": round(sum(item["physical_reachability_accuracy"] for item in results) / len(results), 4) if results else 0.0, "connected_component_accuracy": round(sum(item["connected_component_correct"] for item in results) / len(results), 4) if results else 0.0, "junction_accuracy": round(sum(item["junction_accuracy"] for item in results) / len(results), 4) if results else 0.0, "mean_runtime_ms": round(sum(item["runtime_ms"] for item in results) / len(results), 2) if results else 0.0, "baseline": _aggregate_baseline(results), "error_categories": Counter(error for item in results for error in item["errors"])}


def _aggregate_baseline(results: list[dict]) -> dict:
    tp, fp, fn = (sum(item["baseline"][key] for item in results) for key in ("tp", "fp", "fn"))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"edge_precision": round(precision, 4), "edge_recall": round(recall, 4), "edge_f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0}


def _degrade(source: Path, target: Path, name: str) -> None:
    with Image.open(source) as original:
        image = original.convert("RGB")
    if name == "blur":
        image = image.filter(ImageFilter.GaussianBlur(1.1))
    elif name == "jpeg":
        scratch = target.with_suffix(".jpg")
        image.save(scratch, "JPEG", quality=48)
        with Image.open(scratch) as compressed:
            image = compressed.convert("RGB").copy()
        scratch.unlink(missing_ok=True)
    elif name == "contrast":
        image = ImageEnhance.Contrast(image).enhance(0.62)
    elif name == "brightness":
        image = ImageEnhance.Brightness(image).enhance(0.72)
    elif name == "skew":
        image = image.rotate(1.4, fillcolor="#f8f7f2")
    elif name == "faded_conductors":
        overlay = Image.new("RGB", image.size, "#f8f7f2")
        image = Image.blend(image, overlay, 0.12)
    elif name == "low_resolution":
        image = image.resize((600, 410)).resize(image.size)
    image.save(target, "PNG", optimize=True)


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))["entries"]
    test = [item for item in manifest if item["split"] == "test"]
    holdout = [item for item in manifest if item["split"] == "style_holdout"]
    test_results = [_metrics(item, DATA / item["image"]) for item in test]
    holdout_results = [_metrics(item, DATA / item["image"]) for item in holdout]
    degradation = {}
    source = test[0]
    degradation_root = Path("data/benchmark/topology-v1/degradation")
    degradation_root.mkdir(parents=True, exist_ok=True)
    for name in ("clean", "blur", "jpeg", "contrast", "brightness", "skew", "faded_conductors", "low_resolution"):
        target = degradation_root / f"{name}.png"
        if name == "clean":
            target.write_bytes((DATA / source["image"]).read_bytes())
        else:
            _degrade(DATA / source["image"], target, name)
        degradation[name] = _metrics(source, target)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    summary = {"pipeline_version": "m4", "dataset_manifest_sha256": _sha256(MANIFEST), "test": _aggregate(test_results), "style_holdout": _aggregate(holdout_results), "degradations": degradation, "per_drawing": test_results + holdout_results, "real_validation": {"status": "not_run", "reason": "No legally verified public/real SLD microset is registered."}}
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2, default=dict), encoding="utf-8")
    print(json.dumps({"test": summary["test"], "style_holdout": summary["style_holdout"]}, indent=2, default=dict))


if __name__ == "__main__":
    main()
