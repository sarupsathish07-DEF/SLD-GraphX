import cv2
import numpy as np

from engine.sldgraph.topology.assemble import (
    build_candidates,
    build_gap_bridges,
    build_terminal_corridor_candidates,
    repair_and_select,
    validate_graph,
)
from engine.sldgraph.topology.models import ConductorEvidence, CrossingKind, TopologySymbol
from engine.sldgraph.topology.raster import (
    classify_crossings,
    extract_buses,
    extract_conductors,
    extract_junctions,
    morphology_skeleton,
)
from engine.sldgraph.topology.terminals import generate_terminals


def _symbol(symbol_id: str, kind: str, box: tuple[float, float, float, float]) -> TopologySymbol:
    return TopologySymbol(id=symbol_id, predicted_class=kind, bbox_normalized=box, confidence=0.9)


def test_conductor_extraction_uses_masked_line_evidence() -> None:
    image = np.full((300, 500, 3), 255, dtype=np.uint8)
    cv2.line(image, (40, 150), (460, 150), (35, 35, 35), 3)
    symbols = [_symbol("left", "energy_source", (0.04, 0.36, 0.13, 0.64)), _symbol("right", "feeder_terminal", (0.87, 0.36, 0.96, 0.64))]
    conductors, line_map, skeleton, mask = extract_conductors(image, symbols, [])
    assert conductors
    assert line_map.any() and skeleton.any() and mask.any()


def test_crossing_without_explicit_junction_stays_ambiguous() -> None:
    conductors = [
        ConductorEvidence(id="horizontal", polyline=[(0.1, 0.5), (0.9, 0.5)], confidence=0.9),
        ConductorEvidence(id="vertical", polyline=[(0.5, 0.1), (0.5, 0.9)], confidence=0.9),
    ]
    crossings = classify_crossings(conductors, [])
    assert len(crossings) == 1
    assert crossings[0].kind is CrossingKind.AMBIGUOUS_CROSSING


def test_t_intersection_is_connected_without_turning_x_into_a_join() -> None:
    conductors = [
        ConductorEvidence(id="through", polyline=[(0.1, 0.5), (0.9, 0.5)], confidence=0.9),
        ConductorEvidence(id="branch", polyline=[(0.5, 0.2), (0.5, 0.5)], confidence=0.9),
    ]
    crossings = classify_crossings(conductors, [])
    assert crossings[0].kind is CrossingKind.CONNECTED_JUNCTION
    assert crossings[0].provenance == "t_endpoint_intersection"


def test_terminal_generation_and_snap_build_physical_candidate() -> None:
    symbols = [_symbol("source", "energy_source", (0.05, 0.4, 0.15, 0.6)), _symbol("transformer", "power_transformer", (0.25, 0.25, 0.4, 0.75))]
    terminals = generate_terminals(symbols)
    assert {item.name for item in terminals if item.symbol_id == "transformer"} == {"IN", "OUT"}
    conductor = ConductorEvidence(id="wire", polyline=[(0.15, 0.5), (0.25, 0.5)], confidence=0.9)
    candidates = build_candidates([conductor], terminals, symbols)
    selected, issues = repair_and_select(candidates)
    assert len(selected) == 1
    assert selected[0].from_node_id != selected[0].to_node_id
    assert validate_graph(terminals, selected, issues) is not None


def test_busbar_is_first_class_evidence() -> None:
    symbols = [_symbol("bus", "busbar", (0.25, 0.45, 0.72, 0.5))]
    buses = extract_buses([], symbols)
    assert buses[0].id == "bus:bus"
    assert buses[0].associated_symbol_id == "bus"


def test_connected_junction_requires_compact_dark_dot_evidence() -> None:
    image = np.full((120, 120, 3), 255, dtype=np.uint8)
    cv2.line(image, (15, 60), (105, 60), (0, 0, 0), 2)
    cv2.line(image, (60, 15), (60, 105), (0, 0, 0), 2)
    cv2.circle(image, (60, 60), 5, (0, 0, 0), -1)
    skeleton = morphology_skeleton(cv2.threshold(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), 150, 255, cv2.THRESH_BINARY_INV)[1])
    junctions = extract_junctions(skeleton, image, np.zeros((120, 120), dtype=np.uint8))
    assert any(item.kind is CrossingKind.CONNECTED_JUNCTION for item in junctions)


def test_masked_text_interruption_becomes_reviewable_gap_bridge() -> None:
    symbols = [_symbol("source", "energy_source", (0.05, 0.4, 0.15, 0.6)), _symbol("feeder", "feeder_terminal", (0.85, 0.4, 0.95, 0.6))]
    terminals = generate_terminals(symbols)
    conductors = [
        ConductorEvidence(id="left", polyline=[(0.15, 0.5), (0.47, 0.5)], confidence=0.9, masked_interruption=True),
        ConductorEvidence(id="right", polyline=[(0.50, 0.5), (0.85, 0.5)], confidence=0.9, masked_interruption=True),
    ]
    bridges = build_gap_bridges(conductors, terminals, symbols)
    selected, issues = repair_and_select(bridges)
    assert len(selected) == 1 and selected[0].gap_bridge
    assert any(item.kind == "GAP_BRIDGE_REVIEW" for item in issues)


def test_terminal_corridor_recovers_short_supported_device_approach() -> None:
    symbols = [_symbol("source", "energy_source", (0.05, 0.4, 0.12, 0.6)), _symbol("transformer", "power_transformer", (0.18, 0.4, 0.26, 0.6))]
    line_map = np.zeros((200, 400), dtype=np.uint8)
    cv2.line(line_map, (50, 100), (78, 100), 255, 2)
    candidates = build_terminal_corridor_candidates(line_map, generate_terminals(symbols), symbols)
    assert len(candidates) == 1
    assert candidates[0].provenance == "terminal_corridor_scan"
