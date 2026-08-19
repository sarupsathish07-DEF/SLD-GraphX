"""Candidate physical edges, deterministic repair, and structural validation."""

from __future__ import annotations

import networkx as nx
import numpy as np

from engine.sldgraph.topology.models import (
    CandidateEdge,
    ConductorEvidence,
    TerminalEvidence,
    TopologyIssue,
    TopologySymbol,
)
from engine.sldgraph.topology.terminals import (
    nearest_point_on_segment,
    nearest_terminal,
)


def _score(distance: float, radius: float, conductor: ConductorEvidence) -> tuple[float, float, float, float, float, float, float]:
    endpoint = max(0.0, 1 - distance / max(radius, 1e-6))
    visual = conductor.confidence
    orientation = 0.86 if len(conductor.polyline) >= 2 else 0.55
    terminal = (endpoint + orientation) / 2
    junction = 0.7
    structural = 0.8
    overall = 0.28 * visual + 0.24 * endpoint + 0.18 * orientation + 0.17 * terminal + 0.07 * junction + 0.06 * structural
    return visual, endpoint, orientation, terminal, junction, structural, overall


def build_endpoint_candidates(
    conductors: list[ConductorEvidence], terminals: list[TerminalEvidence], symbols: list[TopologySymbol]
) -> list[CandidateEdge]:
    """Original endpoint-only baseline retained for fair M4R comparisons."""
    by_symbol = {item.id: item for item in symbols}
    candidates = []
    for conductor in conductors:
        left, left_distance = nearest_terminal(conductor.polyline[0], terminals, by_symbol)
        right, right_distance = nearest_terminal(conductor.polyline[-1], terminals, by_symbol)
        if left is None or right is None or left.symbol_id == right.symbol_id:
            continue
        radius = max(0.014, left_distance, right_distance)
        visual, endpoint, orientation, terminal, junction, structural, overall = _score((left_distance + right_distance) / 2, radius * 1.8, conductor)
        candidates.append(CandidateEdge(id=f"candidate:{conductor.id}", page=conductor.page, from_node_id=left.id, to_node_id=right.id, conductor_id=conductor.id, polyline=conductor.polyline, visual_continuity_score=round(visual, 4), endpoint_distance_score=round(endpoint, 4), orientation_score=round(orientation, 4), terminal_score=round(terminal, 4), junction_score=junction, electrical_structural_score=structural, overall_confidence=round(overall, 4), provenance="line_trace+terminal_snap", review_status="unreviewed" if overall >= 0.72 else "pending", review_reason=None if overall >= 0.72 else "LOW_CONNECTIVITY_CONFIDENCE"))
    return candidates


def build_candidates(
    conductors: list[ConductorEvidence], terminals: list[TerminalEvidence], symbols: list[TopologySymbol]
) -> list[CandidateEdge]:
    by_symbol = {item.id: item for item in symbols}
    candidates = build_endpoint_candidates(conductors, terminals, symbols)
    # Hough/skeleton simplification often leaves a terminal beside the middle of
    # a segment or splits a right-angle feeder into several traces. Build a small
    # local segment graph and attach terminals to spans, not merely endpoints.
    components = _conductor_components(conductors)
    for component_index, component in enumerate(components):
        attachments: dict[str, tuple[TerminalEvidence, tuple[float, float], float]] = {}
        for conductor in component:
            for terminal in terminals:
                point, distance = nearest_point_on_segment(
                    terminal.position, conductor.polyline[0], conductor.polyline[-1]
                )
                if distance > snap_radius_for(terminal, by_symbol):
                    continue
                existing = attachments.get(terminal.id)
                if existing is None or distance < existing[2]:
                    attachments[terminal.id] = (terminal, point, distance)
        by_symbol_attachment: dict[str, tuple[TerminalEvidence, tuple[float, float], float]] = {}
        for attachment in attachments.values():
            existing = by_symbol_attachment.get(attachment[0].symbol_id)
            if existing is None or attachment[2] < existing[2]:
                by_symbol_attachment[attachment[0].symbol_id] = attachment
        if len(by_symbol_attachment) < 2:
            continue
        attached = sorted(by_symbol_attachment.values(), key=lambda item: item[0].id)
        bus_attachments = [item for item in attached if item[0].symbol_class == "busbar"]
        # A masked bus can be the deliberate T root for several branches. Preserve
        # those bus-to-branch attachments, but never turn an arbitrary multi-way
        # component into an all-to-all electrical clique.
        pairs = (
            [(bus_attachments[0], item) for item in attached if item[0].symbol_id != bus_attachments[0][0].symbol_id]
            if len(attached) > 2 and len(bus_attachments) == 1
            else [(attached[0], attached[1])]
            if len(attached) == 2
            else []
        )
        if not pairs:
            continue
        line_confidence = min(item.confidence for item in component)
        for pair_index, (left, right) in enumerate(pairs):
            distance = (left[2] + right[2]) / 2
            radius = max(snap_radius_for(left[0], by_symbol), snap_radius_for(right[0], by_symbol))
            visual, endpoint, orientation, terminal, junction, structural, overall = _score(
                distance, radius * 1.45, ConductorEvidence(id="component", polyline=[left[1], right[1]], confidence=line_confidence)
            )
            candidates.append(
                CandidateEdge(
                    id=f"candidate:component:{component_index:03}:{pair_index}",
                    page=component[0].page,
                    from_node_id=left[0].id,
                    to_node_id=right[0].id,
                    polyline=[left[1], right[1]],
                    visual_continuity_score=round(visual, 4),
                    endpoint_distance_score=round(endpoint, 4),
                    orientation_score=round(orientation, 4),
                    terminal_score=round(terminal, 4),
                    junction_score=junction,
                    electrical_structural_score=structural,
                    overall_confidence=round(max(0.76, overall), 4),
                    provenance="segment_component+terminal_projection",
                    review_status="unreviewed",
                )
            )
    return candidates


def snap_radius_for(terminal: TerminalEvidence, symbols: dict[str, TopologySymbol]) -> float:
    """Avoid duplicating terminal scaling policy at component association sites."""
    symbol = symbols[terminal.symbol_id]
    x1, y1, x2, y2 = symbol.bbox_normalized
    return max(0.018, min(0.07, 0.009 + float(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5) * 0.46))


def _segment_distance(left: ConductorEvidence, right: ConductorEvidence) -> float:
    """Endpoint-to-span distance admits deliberate L bends but not X crossings."""
    distances = []
    for point in (left.polyline[0], left.polyline[-1]):
        _, distance = nearest_point_on_segment(point, right.polyline[0], right.polyline[-1])
        distances.append(distance)
    for point in (right.polyline[0], right.polyline[-1]):
        _, distance = nearest_point_on_segment(point, left.polyline[0], left.polyline[-1])
        distances.append(distance)
    return min(distances)


def _conductor_components(conductors: list[ConductorEvidence]) -> list[list[ConductorEvidence]]:
    """Cluster only endpoint-led continuity; full X intersections stay separate."""
    graph = nx.Graph()
    graph.add_nodes_from(item.id for item in conductors)
    by_id = {item.id: item for item in conductors}
    for index, left in enumerate(conductors):
        for right in conductors[index + 1 :]:
            if _segment_distance(left, right) <= 0.012:
                graph.add_edge(left.id, right.id)
    return [[by_id[item] for item in member] for member in nx.connected_components(graph)]


def build_terminal_corridor_candidates(
    line_map: np.ndarray, terminals: list[TerminalEvidence], symbols: list[TopologySymbol], page: int = 1
) -> list[CandidateEdge]:
    """Recover short, masked device approaches from directional pixel support.

    This is intentionally limited to nearby, axis-aligned terminal pairs and retains
    independent raster support; it is not a generic proximity join.
    """
    height, width = line_map.shape[:2]
    output: list[CandidateEdge] = []
    for index, left in enumerate(terminals):
        for right in terminals[index + 1 :]:
            if left.symbol_id == right.symbol_id:
                continue
            dx, dy = right.position[0] - left.position[0], right.position[1] - left.position[1]
            distance = float((dx * dx + dy * dy) ** 0.5)
            if distance > 0.11 or min(abs(dx), abs(dy)) > 0.008:
                continue
            samples = max(12, round(distance * max(width, height) * 1.4))
            xs = np.linspace(left.position[0] * width, right.position[0] * width, samples).astype(int)
            ys = np.linspace(left.position[1] * height, right.position[1] * height, samples).astype(int)
            supported = []
            for x, y in zip(xs, ys):
                x1, x2 = max(0, x - 2), min(width, x + 3)
                y1, y2 = max(0, y - 2), min(height, y + 3)
                supported.append(bool(np.any(line_map[y1:y2, x1:x2])))
            coverage = sum(supported) / len(supported)
            runs = np.diff(np.r_[False, supported, False].astype(np.int8))
            longest = max(np.where(runs == -1)[0] - np.where(runs == 1)[0], default=0) / len(supported)
            if coverage < 0.2 or longest < 0.16:
                continue
            output.append(
                CandidateEdge(
                    id=f"candidate:corridor:{left.id}:{right.id}",
                    page=page,
                    from_node_id=left.id,
                    to_node_id=right.id,
                    polyline=[left.position, right.position],
                    visual_continuity_score=round(coverage, 4),
                    endpoint_distance_score=round(min(1.0, longest + 0.35), 4),
                    orientation_score=0.9,
                    terminal_score=0.92,
                    junction_score=0.7,
                    electrical_structural_score=0.76,
                    overall_confidence=round(min(0.9, 0.45 + coverage * 0.38 + longest * 0.18), 4),
                    provenance="terminal_corridor_scan",
                    review_status="unreviewed" if coverage >= 0.36 else "pending",
                    review_reason=None if coverage >= 0.36 else "CORRIDOR_REVIEW",
                )
            )
    return output


def build_gap_bridges(
    conductors: list[ConductorEvidence], terminals: list[TerminalEvidence], symbols: list[TopologySymbol]
) -> list[CandidateEdge]:
    """Propose only simple, collinear trace interruptions for engineer review.

    Text and protected symbol masks can split an otherwise direct feeder.  A bridge is
    deliberately never auto-verified: each half must already snap at its outside end,
    the free ends must be close, and their directions must be opposed/collinear.
    """
    by_symbol = {item.id: item for item in symbols}
    partials: list[tuple[ConductorEvidence, TerminalEvidence, tuple[float, float], tuple[float, float]]] = []
    for conductor in conductors:
        start, start_distance = nearest_terminal(conductor.polyline[0], terminals, by_symbol)
        end, end_distance = nearest_terminal(conductor.polyline[-1], terminals, by_symbol)
        if (start is None) == (end is None):
            continue
        terminal, distance, anchored, free = (
            (start, start_distance, conductor.polyline[0], conductor.polyline[-1])
            if start is not None
            else (end, end_distance, conductor.polyline[-1], conductor.polyline[0])
        )
        if terminal is not None and distance <= 0.055:
            partials.append((conductor, terminal, anchored, free))

    bridges: list[CandidateEdge] = []
    for index, (left, left_terminal, left_anchor, left_free) in enumerate(partials):
        left_vector = (left_free[0] - left_anchor[0], left_free[1] - left_anchor[1])
        left_norm = max(1e-6, float((left_vector[0] ** 2 + left_vector[1] ** 2) ** 0.5))
        for right, right_terminal, right_anchor, right_free in partials[index + 1 :]:
            if left_terminal.symbol_id == right_terminal.symbol_id:
                continue
            gap_vector = (right_free[0] - left_free[0], right_free[1] - left_free[1])
            gap = float((gap_vector[0] ** 2 + gap_vector[1] ** 2) ** 0.5)
            if gap > 0.035:
                continue
            right_vector = (right_free[0] - right_anchor[0], right_free[1] - right_anchor[1])
            right_norm = max(1e-6, float((right_vector[0] ** 2 + right_vector[1] ** 2) ** 0.5))
            alignment = abs((left_vector[0] * right_vector[0] + left_vector[1] * right_vector[1]) / (left_norm * right_norm))
            if alignment < 0.94:
                continue
            bridges.append(
                CandidateEdge(
                    id=f"candidate:gap:{left.id}:{right.id}",
                    page=left.page,
                    from_node_id=left_terminal.id,
                    to_node_id=right_terminal.id,
                    polyline=[left_anchor, left_free, right_free, right_anchor],
                    visual_continuity_score=round(min(left.confidence, right.confidence) * alignment, 4),
                    endpoint_distance_score=0.82,
                    orientation_score=round(alignment, 4),
                    terminal_score=0.82,
                    junction_score=0.5,
                    electrical_structural_score=0.62,
                    overall_confidence=round(0.38 + 0.18 * alignment + 0.15 * min(left.confidence, right.confidence), 4),
                    provenance="masked_gap_bridge",
                    review_status="pending",
                    review_reason="GAP_BRIDGE_REVIEW",
                    gap_bridge=True,
                )
            )
    return bridges


def repair_and_select(candidates: list[CandidateEdge]) -> tuple[list[CandidateEdge], list[TopologyIssue]]:
    """Keep strongest evidence for duplicate terminal pairs; emit issues instead of forcing weak repairs."""
    selected: list[CandidateEdge] = []
    issues: list[TopologyIssue] = []
    by_pair: dict[tuple[str, str], CandidateEdge] = {}
    for candidate in sorted(candidates, key=lambda item: item.overall_confidence, reverse=True):
        pair = tuple(sorted((candidate.from_node_id, candidate.to_node_id)))
        existing = by_pair.get(pair)
        if existing is None:
            by_pair[pair] = candidate
            continue
        issues.append(TopologyIssue(id=f"issue:duplicate:{candidate.id}", kind="DUPLICATE_EDGE", message="Competing raster traces map to the same terminal pair; strongest trace retained.", related_edge_id=candidate.id))
    selected.extend(by_pair.values())
    graph = nx.Graph()
    graph.add_edges_from((edge.from_node_id, edge.to_node_id) for edge in selected)
    for edge in selected:
        if edge.gap_bridge:
            issues.append(TopologyIssue(id=f"issue:gap:{edge.id}", kind="GAP_BRIDGE_REVIEW", message="A masked/interrupted trace was bridged conservatively and requires engineer review.", related_edge_id=edge.id))
        if edge.overall_confidence < 0.58:
            issues.append(TopologyIssue(id=f"issue:low:{edge.id}", kind="LOW_CONFIDENCE_EDGE", message="Physical connection is retained for review with separated evidence scores.", related_edge_id=edge.id))
    return selected, issues


def validate_graph(
    terminals: list[TerminalEvidence], connections: list[CandidateEdge], issues: list[TopologyIssue]
) -> list[TopologyIssue]:
    graph = nx.Graph()
    graph.add_edges_from((item.from_node_id, item.to_node_id) for item in connections)
    for terminal in terminals:
        degree = graph.degree(terminal.id) if terminal.id in graph else 0
        if degree == 0:
            issues.append(TopologyIssue(id=f"issue:orphan:{terminal.id}", kind="ORPHAN_TERMINAL", message="No accepted raster connection reaches this generated terminal.", severity="review"))
        if terminal.symbol_class in {"circuit_breaker", "disconnector", "bus_coupler"} and degree > 2:
            issues.append(TopologyIssue(id=f"issue:degree:{terminal.id}", kind="DEVICE_DEGREE_WARNING", message="Through-device terminal has more than two physical attachments.", severity="review"))
    return issues


def manual_candidate(from_node_id: str, to_node_id: str, page: int = 1) -> CandidateEdge:
    return CandidateEdge(id="manual", page=page, from_node_id=from_node_id, to_node_id=to_node_id, polyline=[], visual_continuity_score=1.0, endpoint_distance_score=1.0, orientation_score=1.0, terminal_score=1.0, junction_score=1.0, electrical_structural_score=1.0, overall_confidence=1.0, provenance="engineer_added", review_status="verified")
