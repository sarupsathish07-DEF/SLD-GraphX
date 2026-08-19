"""Evaluate deterministic M5 reasoning on frozen graph-first SLDForge fixtures.

This is a semantic-graph benchmark, not an end-to-end perception claim.  The
separate production smoke records topology-induced source/feeder limitations.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.sldgraph.electrical import analyse, derive_feeder_paths
from engine.sldgraph.models import SwitchState
from sldforge.generator import (
    build_alternate_supply_fixture,
    build_bus_coupler_fixture,
    build_dual_transformer_fixture,
    build_radial_fixture,
    build_ring_fixture,
    build_sectionalized_bus_fixture,
)

SPEC = Path("data/benchmark/source-feeder-v1.spec.json")
OUTPUT = Path("artifacts/experiments/source-feeder-v1")
BUILDERS = {
    "radial": build_radial_fixture,
    "dual_transformer": build_dual_transformer_fixture,
    "sectionalized_bus": build_sectionalized_bus_fixture,
    "bus_coupler": build_bus_coupler_fixture,
    "alternate_supply": build_alternate_supply_fixture,
    "ring": build_ring_fixture,
}


def _score(correct: int, total: int) -> float:
    return round(correct / total, 4) if total else 1.0


def _baseline(graph, expected_paths: dict) -> dict:
    """Transparent structural baseline: class labels plus unweighted physical shortest paths.

    It deliberately ignores switch state, confidence, source-boundary fallback and ambiguity.
    This is a comparator, not an alternate product mode.
    """
    terminals = {item.id: item.equipment_id for item in graph.terminals}
    network = nx.Graph()
    network.add_nodes_from(item.id for item in graph.equipment)
    for connection in graph.connections:
        left, right = terminals.get(connection.from_terminal_id), terminals.get(connection.to_terminal_id)
        if left and right and left != right:
            network.add_edge(left, right, connection_id=connection.id)
    sources = sorted(item.id for item in graph.equipment if item.type.value in {"energy_source", "grid_incomer", "generator"})
    assignments = paths = reachable = 0
    for feeder_id, expected in expected_paths.items():
        candidates = [(source, nx.shortest_path(network, source, feeder_id)) for source in sources if nx.has_path(network, source, feeder_id)]
        if not candidates:
            continue
        reachable += 1
        source, nodes = min(candidates, key=lambda item: (len(item[1]), item[0]))
        assignments += source == expected.source_equipment_id
        edge_path = [network[left][right]["connection_id"] for left, right in zip(nodes, nodes[1:])]
        paths += nodes == expected.equipment_path and edge_path == expected.connection_path
    return {
        "name": "class_plus_unweighted_physical_shortest_path",
        "limitations": "ignores switch state, confidence, ambiguity and transformer-secondary fallback",
        "exact_source_assignment": _score(assignments, len(expected_paths)),
        "exact_source_to_feeder_path": _score(paths, len(expected_paths)),
        "reachable_feeders": reachable,
    }


def _metrics(name: str) -> dict:
    graph = BUILDERS[name]()
    started = time.perf_counter()
    result = analyse(graph)
    expected_paths = {item.feeder_equipment_id: item for item in graph.feeder_paths}
    predicted_paths = {item.feeder_equipment_id: item for item in result.paths}
    source_truth = {item.id for item in graph.equipment if item.type.value in {"energy_source", "grid_incomer", "generator"}}
    source_predicted = {item.equipment_id for item in result.sources if item.source_role != "transformer_secondary_source"}
    source_tp = len(source_truth & source_predicted)
    source_fp = len(source_predicted - source_truth)
    source_fn = len(source_truth - source_predicted)
    source_precision = source_tp / (source_tp + source_fp) if source_tp + source_fp else 1.0
    source_recall = source_tp / (source_tp + source_fn) if source_tp + source_fn else 1.0
    feeder_truth = set(expected_paths)
    feeder_predicted = {item.equipment_id for item in result.feeders}
    exact = sum(predicted_paths[key].equipment_path == expected.equipment_path for key, expected in expected_paths.items() if key in predicted_paths)
    assignments = sum(predicted_paths[key].source_equipment_id == expected.source_equipment_id for key, expected in expected_paths.items() if key in predicted_paths)
    edges_correct = sum(predicted_paths[key].connection_path == expected.connection_path for key, expected in expected_paths.items() if key in predicted_paths)
    scenario = _scenario(graph)
    return {
        "topology": name,
        "sources": {"truth": sorted(source_truth), "predicted": sorted(source_predicted), "precision": round(source_precision, 4), "recall": round(source_recall, 4), "f1": round(2 * source_precision * source_recall / (source_precision + source_recall), 4) if source_precision + source_recall else 0.0},
        "feeders": {"truth": sorted(feeder_truth), "predicted": sorted(feeder_predicted), "precision": _score(len(feeder_truth & feeder_predicted), len(feeder_predicted)), "recall": _score(len(feeder_truth & feeder_predicted), len(feeder_truth))},
        "exact_source_assignment": _score(assignments, len(expected_paths)),
        "exact_source_to_feeder_path": _score(exact, len(expected_paths)),
        "path_edge_exact": _score(edges_correct, len(expected_paths)),
        "operational_reachability": scenario,
        "baseline": _baseline(graph, expected_paths),
        "criticality": {"reviewed_connections": len(result.criticality), "top_priority": result.criticality[0].connection_id if result.criticality else None},
        "runtime_ms": round((time.perf_counter() - started) * 1000, 3),
    }


def _scenario(graph) -> dict:
    switches = [item for item in graph.equipment if item.type.value in {"circuit_breaker", "bus_coupler", "disconnector"}]
    if not switches:
        return {"status": "not_applicable", "accuracy": 1.0}
    target = switches[0]
    open_paths = derive_feeder_paths(graph, {target.id: SwitchState.OPEN})
    closed_paths = derive_feeder_paths(graph, {target.id: SwitchState.CLOSED})
    # Canonical graph containment is the oracle: opened device must not create a
    # new path; closed must not reduce baseline reachability.
    baseline = derive_feeder_paths(graph)
    open_count = sum(item.source_equipment_id is not None for item in open_paths)
    closed_count = sum(item.source_equipment_id is not None for item in closed_paths)
    baseline_count = sum(item.source_equipment_id is not None for item in baseline)
    return {"switch": target.id, "open_reachable_feeders": open_count, "closed_reachable_feeders": closed_count, "baseline_reachable_feeders": baseline_count, "accuracy": 1.0 if closed_count >= baseline_count and open_count <= closed_count else 0.0}


def main() -> None:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    results = [_metrics(name) for name in spec["topologies"]]
    total_feeders = sum(len(item["feeders"]["truth"]) for item in results)
    summary = {
        "pipeline_version": "m5-semantic-graph",
        "dataset_manifest_sha256": hashlib.sha256(SPEC.read_bytes()).hexdigest(),
        "scope": "controlled graph-first SLDForge semantics; not end-to-end perception or real utility validation",
        "drawings": len(results),
        "source_identification": {"precision": _score(sum(round(item["sources"]["precision"] * len(item["sources"]["truth"])) for item in results), sum(len(item["sources"]["truth"]) for item in results)), "recall": _score(sum(round(item["sources"]["recall"] * len(item["sources"]["truth"])) for item in results), sum(len(item["sources"]["truth"]) for item in results))},
        "feeder_identification": {"precision": _score(sum(len(set(item["feeders"]["truth"]) & set(item["feeders"]["predicted"])) for item in results), sum(len(item["feeders"]["predicted"]) for item in results)), "recall": _score(sum(len(set(item["feeders"]["truth"]) & set(item["feeders"]["predicted"])) for item in results), total_feeders)},
        "exact_source_assignment": _score(sum(round(item["exact_source_assignment"] * len(item["feeders"]["truth"])) for item in results), total_feeders),
        "exact_source_to_feeder_path": _score(sum(round(item["exact_source_to_feeder_path"] * len(item["feeders"]["truth"])) for item in results), total_feeders),
        "operational_reachability": _score(sum(item["operational_reachability"]["accuracy"] for item in results), len(results)),
        "criticality": {"method": "with/without edge affected feeder and component comparison; risk = uncertainty × configured topology impact", "controlled_checks": len(results)},
        "baseline": {
            "name": "class_plus_unweighted_physical_shortest_path",
            "comparison": "reported per drawing; it ignores operational state, uncertainty and source-boundary rules",
        },
        "real_validation": {"status": "not_available", "reason": "No legally verified real SLD evaluation set is registered."},
        "per_drawing": results,
    }
    source = summary["source_identification"]
    source["f1"] = round(2 * source["precision"] * source["recall"] / (source["precision"] + source["recall"]), 4) if source["precision"] + source["recall"] else 0.0
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("source_identification", "feeder_identification", "exact_source_assignment", "exact_source_to_feeder_path", "operational_reachability")}, indent=2))


if __name__ == "__main__":
    main()
