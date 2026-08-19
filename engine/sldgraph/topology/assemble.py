"""Candidate physical edges, deterministic repair, and structural validation."""

from __future__ import annotations

import networkx as nx

from engine.sldgraph.topology.models import (
    CandidateEdge,
    ConductorEvidence,
    TerminalEvidence,
    TopologyIssue,
    TopologySymbol,
)
from engine.sldgraph.topology.terminals import nearest_terminal


def _score(distance: float, radius: float, conductor: ConductorEvidence) -> tuple[float, float, float, float, float, float, float]:
    endpoint = max(0.0, 1 - distance / max(radius, 1e-6))
    visual = conductor.confidence
    orientation = 0.86 if len(conductor.polyline) >= 2 else 0.55
    terminal = (endpoint + orientation) / 2
    junction = 0.7
    structural = 0.8
    overall = 0.28 * visual + 0.24 * endpoint + 0.18 * orientation + 0.17 * terminal + 0.07 * junction + 0.06 * structural
    return visual, endpoint, orientation, terminal, junction, structural, overall


def build_candidates(
    conductors: list[ConductorEvidence], terminals: list[TerminalEvidence], symbols: list[TopologySymbol]
) -> list[CandidateEdge]:
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
