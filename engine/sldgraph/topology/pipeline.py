"""Orchestrates local image evidence into a reviewable physical graph candidate set."""

from __future__ import annotations

import time

import cv2

from engine.sldgraph.topology.assemble import (
    build_candidates,
    build_gap_bridges,
    build_terminal_corridor_candidates,
    repair_and_select,
    validate_graph,
)
from engine.sldgraph.topology.models import TopologyResult, TopologySymbol, TopologyText
from engine.sldgraph.topology.raster import (
    classify_crossings,
    extract_buses,
    extract_conductors,
    extract_junctions,
)
from engine.sldgraph.topology.terminals import generate_terminals


def reconstruct(image_path: str, symbols: list[TopologySymbol], texts: list[TopologyText], page: int = 1) -> tuple[TopologyResult, dict[str, object]]:
    started = time.perf_counter()
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Topology working image is unavailable")
    conductors, line_map, skeleton, mask = extract_conductors(image, symbols, texts)
    buses = extract_buses(conductors, symbols)
    junctions = classify_crossings(conductors, extract_junctions(skeleton, image, mask))
    terminals = generate_terminals(symbols)
    candidates = build_candidates(conductors, terminals, symbols)
    candidates.extend(build_gap_bridges(conductors, terminals, symbols))
    candidates.extend(build_terminal_corridor_candidates(line_map, terminals, symbols, page))
    connections, issues = repair_and_select(candidates)
    issues = validate_graph(terminals, connections, issues)
    return TopologyResult(page=page, conductors=conductors, buses=buses, junctions=junctions, terminals=terminals, candidates=candidates, connections=connections, issues=issues, elapsed_ms=round((time.perf_counter() - started) * 1000, 2)), {"topology_line_map": line_map, "topology_skeleton": skeleton, "topology_protected_mask": mask}
