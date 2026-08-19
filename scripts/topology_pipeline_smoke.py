"""Exercise the actual upload-to-persisted-physical-graph route on an unseen SLDForge scene."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.sldgraph.symbols.geometry import iou
from services.api.app.main import app


def _symbol_map(predicted: list[dict], truth_nodes: list[dict]) -> dict[str, str]:
    mapped = {}
    for item in predicted:
        candidates = [node for node in truth_nodes if node["class_name"] == item["predicted_class"]]
        best = max(candidates, key=lambda node: iou(tuple(item["bbox_normalized"]), tuple(node["bbox"])), default=None)
        if best and iou(tuple(item["bbox_normalized"]), tuple(best["bbox"])) >= 0.25:
            mapped[item["id"]] = best["id"]
    return mapped


def _symbol_id(terminal_id: str) -> str:
    return terminal_id.split(":")[1]


def main() -> None:
    image = Path("data/synthetic/topology-v1/images/style_holdout-style_d-radial-1.png")
    manifest = json.loads(Path("data/benchmark/topology-v1/manifest.json").read_text(encoding="utf-8"))
    truth = next(item for item in manifest["entries"] if item["image"] == image.name)
    with TestClient(app) as client:
        project = client.post("/api/projects", data={"name": "M4 real topology smoke", "description": "local"}).json()
        drawing = client.post(f"/api/projects/{project['id']}/drawings", files={"file": (image.name, image.read_bytes(), "image/png")}).json()
        analysis_id = client.post(f"/api/drawings/{drawing['id']}/analyze").json()["analysis_run_id"]
        analysis = client.get(f"/api/analyses/{analysis_id}").json()
        symbols = client.get(f"/api/analyses/{analysis_id}/symbols").json()
        conductors = client.get(f"/api/analyses/{analysis_id}/conductors").json()
        buses = client.get(f"/api/analyses/{analysis_id}/buses").json()
        junctions = client.get(f"/api/analyses/{analysis_id}/junctions").json()
        graph = client.get(f"/api/analyses/{analysis_id}/physical-graph").json()
    if analysis["status"] != "complete":
        raise RuntimeError(json.dumps(analysis, indent=2))
    mapping = _symbol_map(symbols, truth["nodes"])
    predicted = set()
    for edge in graph["edges"]:
        left, right = mapping.get(_symbol_id(edge["from_node_id"])), mapping.get(_symbol_id(edge["to_node_id"]))
        if left and right:
            predicted.add(tuple(sorted((left, right))))
    expected = {tuple(sorted((item["from"], item["to"]))) for item in truth["edges"]}
    # Fresh TestClient proves rows survive application lifespan/reload, not merely in-memory state.
    with TestClient(app) as reloaded:
        reloaded_graph = reloaded.get(f"/api/analyses/{analysis_id}/physical-graph").json()
    if len(reloaded_graph["edges"]) != len(graph["edges"]):
        raise RuntimeError("Topology evidence did not persist across reload")
    print(json.dumps({"analysis_id": analysis_id, "stages": [item["stage"] for item in analysis["stages"]], "symbols": len(symbols), "conductors": len(conductors), "buses": len(buses), "junctions": len(junctions), "physical_edges": len(graph["edges"]), "mapped_edges": len(predicted), "hidden_truth_edges": len(expected), "edge_matches": len(predicted & expected), "reload_edges": len(reloaded_graph["edges"])}, indent=2))


if __name__ == "__main__":
    main()
