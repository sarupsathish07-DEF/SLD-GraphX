"""Deterministic, local source-to-feeder reasoning over attributed graphs.

This module models connectivity only: it does not perform power-flow,
fault-current, protection, or voltage-drop calculations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from math import prod

import networkx as nx

from engine.sldgraph.models import (
    ElectricalGraph,
    Equipment,
    EquipmentType,
    FeederPath,
    Provenance,
    SwitchState,
)


class Resolution(str, Enum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


SWITCH_TYPES = {EquipmentType.CIRCUIT_BREAKER, EquipmentType.DISCONNECTOR, EquipmentType.BUS_COUPLER}
SOURCE_TYPES = {EquipmentType.ENERGY_SOURCE, EquipmentType.GRID_INCOMER, EquipmentType.GENERATOR}


@dataclass(frozen=True)
class SourceCandidate:
    equipment_id: str
    equipment_label: str
    source_role: str
    confidence: float
    evidence: list[str]
    provenance: list[str] = field(default_factory=lambda: ["graph_reasoning"])


@dataclass(frozen=True)
class SemanticFeeder:
    id: str
    feeder_id: str
    equipment_id: str
    source_bus_equipment_id: str | None
    destination_equipment_id: str | None
    voltage: str | None
    rating: str | None
    resolution: Resolution
    confidence: float
    provenance: list[str]


@dataclass(frozen=True)
class ValidationFinding:
    code: str
    severity: str
    message: str
    target_type: str | None = None
    target_id: str | None = None


@dataclass(frozen=True)
class Criticality:
    connection_id: str
    confidence: float
    uncertainty: float
    affected_feeders: list[str]
    affected_nodes: list[str]
    source_assignment_changes: list[str]
    component_change: int
    bridge_importance: float
    risk_factors: dict[str, float]
    risk_score: float
    priority: str


@dataclass
class ElectricalIntelligence:
    sources: list[SourceCandidate]
    feeders: list[SemanticFeeder]
    paths: list[FeederPath]
    validation: list[ValidationFinding]
    criticality: list[Criticality]
    health: dict[str, object]


def _terminal_equipment(graph: ElectricalGraph) -> dict[str, str]:
    return {terminal.id: terminal.equipment_id for terminal in graph.terminals}


def _switch_state(equipment: Equipment, overrides: dict[str, SwitchState]) -> SwitchState:
    if equipment.id in overrides:
        return overrides[equipment.id]
    try:
        return SwitchState(str(equipment.attributes.get("switch_state", "unknown")).lower())
    except ValueError:
        return SwitchState.UNKNOWN


def _network(graph: ElectricalGraph, overrides: dict[str, SwitchState] | None = None, unknown_policy: str = "possible", omit_connection: str | None = None) -> nx.Graph:
    """Build an equipment graph without silently treating UNKNOWN as CLOSED."""
    overrides = overrides or {}
    terminal_map = _terminal_equipment(graph)
    equipment = {item.id: item for item in graph.equipment}
    network = nx.Graph()
    for item in graph.equipment:
        network.add_node(item.id, equipment=item)
    for connection in graph.connections:
        if connection.id == omit_connection:
            continue
        left, right = terminal_map.get(connection.from_terminal_id), terminal_map.get(connection.to_terminal_id)
        if not left or not right or left == right:
            continue
        states = [_switch_state(equipment[node], overrides) for node in (left, right) if equipment[node].type in SWITCH_TYPES]
        if connection.switch_state is SwitchState.OPEN or SwitchState.OPEN in states:
            continue
        unknown = connection.switch_state is SwitchState.UNKNOWN or SwitchState.UNKNOWN in states
        if unknown_policy == "definite" and unknown:
            continue
        network.add_edge(left, right, connection_id=connection.id, confidence=connection.confidence, unknown_switch=unknown)
    return network


def source_candidates(graph: ElectricalGraph) -> list[SourceCandidate]:
    output: list[SourceCandidate] = []
    for item in graph.equipment:
        if item.type not in SOURCE_TYPES:
            continue
        role = "grid_incomer" if item.type is EquipmentType.GRID_INCOMER else "generator" if item.type is EquipmentType.GENERATOR else "energy_source"
        output.append(SourceCandidate(item.id, item.equipment_id, role, round(item.confidence, 4), [f"symbol class {item.type.value}", "connected graph candidate"]))
    # Transformer secondary is a boundary candidate only in a component that has
    # no explicit external source. This avoids falsely equating grid and TR.
    physical = _network(graph)
    explicit = {item.equipment_id for item in output}
    for item in graph.equipment:
        if item.type is not EquipmentType.POWER_TRANSFORMER:
            continue
        component = next((nodes for nodes in nx.connected_components(physical) if item.id in nodes), {item.id})
        if not any(node in explicit for node in component):
            output.append(SourceCandidate(item.id, item.equipment_id, "transformer_secondary_source", round(item.confidence * 0.82, 4), ["transformer class", "no explicit upstream source in physical component", "terminal side unknown without voltage evidence"]))
    return output


def _path(network: nx.Graph, nodes: list[str]) -> tuple[list[str], list[str], float, str | None, float | None]:
    edges = [network[left][right] for left, right in zip(nodes, nodes[1:])]
    ids = [str(edge["connection_id"]) for edge in edges]
    confidences = [float(edge["confidence"]) for edge in edges]
    flags = ["UNKNOWN_SWITCH_ON_PATH"] if any(edge["unknown_switch"] for edge in edges) else []
    if not confidences:
        return ids, flags, 1.0, None, None
    weakest = min(range(len(confidences)), key=confidences.__getitem__)
    return ids, flags, round(prod(confidences) ** (1 / len(confidences)), 4), ids[weakest], round(confidences[weakest], 4)


def _nearest_bus(nodes: list[str], equipment: dict[str, Equipment]) -> str | None:
    return next((node for node in reversed(nodes[:-1]) if equipment[node].type is EquipmentType.BUSBAR), None)


def derive_feeder_paths(graph: ElectricalGraph, overrides: dict[str, SwitchState] | None = None, unknown_policy: str = "possible", max_alternates: int = 3, omit_connection: str | None = None) -> list[FeederPath]:
    """Return exact equipment and connection paths, with uncertainty preserved."""
    network = _network(graph, overrides, unknown_policy, omit_connection)
    equipment = {item.id: item for item in graph.equipment}
    sources = [item.equipment_id for item in source_candidates(graph)]
    paths: list[FeederPath] = []
    for feeder in (item for item in graph.equipment if item.type is EquipmentType.FEEDER):
        found = [(source, nx.shortest_path(network, source, feeder.id)) for source in sources if source in network and feeder.id in network and nx.has_path(network, source, feeder.id)]
        if not found:
            paths.append(FeederPath(feeder_equipment_id=feeder.id, source_equipment_id=None, equipment_path=[], confidence=0.0, active=False, uncertainty_flags=["PHYSICAL_TOPOLOGY_BREAK"], provenance=[Provenance.GRAPH_INFERENCE]))
            continue
        found.sort(key=lambda item: (len(item[1]), item[0]))
        primary_source, nodes = found[0]
        edge_ids, flags, confidence, weak_id, weak_confidence = _path(network, nodes)
        if any(len(candidate[1]) <= len(nodes) + 2 for candidate in found[1:max_alternates + 1]):
            flags.append("MULTIPLE_SOURCE_OR_PATH_CANDIDATES")
        switch_ids = [node for node in nodes if equipment[node].type in SWITCH_TYPES]
        destination = next((node for node in network.neighbors(feeder.id) if node not in sources and equipment[node].type in {EquipmentType.LOAD, EquipmentType.OFFPAGE_CONNECTOR}), None)
        paths.append(FeederPath(feeder_equipment_id=feeder.id, source_equipment_id=primary_source, equipment_path=nodes, connection_path=edge_ids, source_bus_equipment_id=_nearest_bus(nodes, equipment), destination_equipment_id=destination, switching_equipment_ids=switch_ids, weakest_connection_id=weak_id, weakest_connection_confidence=weak_confidence, uncertainty_flags=flags, provenance=[Provenance.GRAPH_INFERENCE], confidence=confidence, active=True))
    return paths


def feeder_records(graph: ElectricalGraph, paths: list[FeederPath]) -> list[SemanticFeeder]:
    by_path = {item.feeder_equipment_id: item for item in paths}
    output: list[SemanticFeeder] = []
    for item in graph.equipment:
        if item.type is not EquipmentType.FEEDER:
            continue
        path = by_path[item.id]
        rating = str(item.attributes.get("rating")) if item.attributes.get("rating") else None
        voltage = next((part.strip() for part in (rating or "").split("·") if "v" in part.lower()), None)
        state = Resolution.UNRESOLVED if not path.source_equipment_id else Resolution.AMBIGUOUS if "MULTIPLE_SOURCE_OR_PATH_CANDIDATES" in path.uncertainty_flags else Resolution.RESOLVED
        output.append(SemanticFeeder(item.id, item.equipment_id, item.id, path.source_bus_equipment_id, path.destination_equipment_id, voltage, rating, state, path.confidence, ["symbol+text association", "graph_reasoning"]))
    return output


def validate(graph: ElectricalGraph, paths: list[FeederPath]) -> list[ValidationFinding]:
    terminals = _terminal_equipment(graph)
    network = _network(graph)
    equipment = {item.id: item for item in graph.equipment}
    findings: list[ValidationFinding] = []
    seen_pairs: set[frozenset[str]] = set()
    labels: dict[str, list[str]] = {}
    for item in graph.equipment:
        labels.setdefault(item.equipment_id.upper(), []).append(item.id)
    for label, ids in labels.items():
        if label and len(ids) > 1:
            findings.append(ValidationFinding("DUPLICATE_EQUIPMENT_ID", "warning", f"Equipment ID {label} occurs {len(ids)} times", "equipment", ids[0]))
    for connection in graph.connections:
        left, right = terminals.get(connection.from_terminal_id), terminals.get(connection.to_terminal_id)
        if not left or not right:
            findings.append(ValidationFinding("UNRESOLVED_TERMINAL", "error", f"Connection {connection.id} references an unresolved terminal", "connection", connection.id))
            continue
        if left == right:
            findings.append(ValidationFinding("NO_SELF_LOOP", "error", f"Connection {connection.id} creates an equipment self loop", "connection", connection.id))
        pair = frozenset((left, right))
        if pair in seen_pairs:
            findings.append(ValidationFinding("DUPLICATE_PARALLEL_EDGE", "warning", f"Duplicate physical connection between {left} and {right}", "connection", connection.id))
        seen_pairs.add(pair)
    for item in graph.equipment:
        degree = network.degree(item.id) if item.id in network else 0
        if item.type is EquipmentType.FEEDER and degree == 0:
            findings.append(ValidationFinding("DISCONNECTED_EQUIPMENT", "warning", f"Feeder {item.equipment_id} is disconnected", "equipment", item.id))
        if item.type in SWITCH_TYPES and degree not in {0, 2}:
            code = "BUS_COUPLER_SANITY" if item.type is EquipmentType.BUS_COUPLER else "BREAKER_TERMINAL_SANITY" if item.type is EquipmentType.CIRCUIT_BREAKER else "DISCONNECTOR_TERMINAL_SANITY"
            findings.append(ValidationFinding(code, "warning", f"{item.equipment_id} has {degree} physical attachments; expected two for a simple device", "equipment", item.id))
        if item.type is EquipmentType.POWER_TRANSFORMER and degree not in {0, 2}:
            findings.append(ValidationFinding("TRANSFORMER_TERMINAL_SANITY", "warning", f"{item.equipment_id} has {degree} physical attachments", "equipment", item.id))
    for path in paths:
        label = equipment[path.feeder_equipment_id].equipment_id
        if not path.source_equipment_id:
            findings.append(ValidationFinding("FEEDER_WITHOUT_UPSTREAM_PATH", "warning", f"Feeder {label} has no supported upstream source path", "equipment", path.feeder_equipment_id))
        if "MULTIPLE_SOURCE_OR_PATH_CANDIDATES" in path.uncertainty_flags:
            findings.append(ValidationFinding("FEEDER_MULTIPLE_UNRESOLVED_SOURCES", "warning", f"Feeder {label} has multiple candidate sources or routes", "equipment", path.feeder_equipment_id))
        if "UNKNOWN_SWITCH_ON_PATH" in path.uncertainty_flags:
            findings.append(ValidationFinding("UNKNOWN_SWITCH_ON_REQUIRED_PATH", "warning", f"Feeder {label} depends on unknown switch state", "equipment", path.feeder_equipment_id))
        voltages = {
            float(match.group(1))
            for node in path.equipment_path
            for match in [re.search(r"(\d+(?:\.\d+)?)\s*kV", str(equipment[node].attributes.get("rating", "")), re.IGNORECASE)]
            if match
        }
        has_transformer = any(equipment[node].type is EquipmentType.POWER_TRANSFORMER for node in path.equipment_path)
        if len(voltages) > 1 and not has_transformer:
            findings.append(ValidationFinding("VOLTAGE_TRANSITION_WITHOUT_TRANSFORMER", "warning", f"Feeder {label} path contains multiple voltage labels without transformer evidence", "equipment", path.feeder_equipment_id))
    return findings


def criticality(graph: ElectricalGraph, paths: list[FeederPath]) -> list[Criticality]:
    base = _network(graph)
    original = {item.feeder_equipment_id: item.source_equipment_id for item in paths}
    result: list[Criticality] = []
    for connection in graph.connections:
        if connection.review_status.value in {"accepted", "verified"}:
            continue
        without = derive_feeder_paths(graph, omit_connection=connection.id)
        changed = [item.feeder_equipment_id for item in without if item.source_equipment_id != original.get(item.feeder_equipment_id)]
        affected_nodes: set[str] = set()
        for path in paths:
            if path.feeder_equipment_id in changed:
                affected_nodes.update(path.equipment_path)
        before, after = nx.number_connected_components(base), nx.number_connected_components(_network(graph, omit_connection=connection.id))
        terminals = _terminal_equipment(graph)
        left, right = terminals.get(connection.from_terminal_id), terminals.get(connection.to_terminal_id)
        bridges = {frozenset(edge) for edge in nx.bridges(base)}
        bridge = 1.0 if left and right and base.has_edge(left, right) and frozenset((left, right)) in bridges else 0.0
        feeder_fraction = len(changed) / max(1, len(original))
        node_fraction = len(affected_nodes) / max(1, len(graph.equipment))
        component_factor = min(1.0, max(0, after - before) / 2)
        impact = .35 * feeder_fraction + .2 * node_fraction + .2 * feeder_fraction + .15 * bridge + .1 * component_factor
        uncertainty = max(0.0, 1 - connection.confidence)
        risk = round(uncertainty * impact, 4)
        priority = "CRITICAL" if risk >= .36 else "HIGH" if risk >= .18 else "MEDIUM" if risk >= .06 else "LOW"
        result.append(Criticality(connection.id, connection.confidence, round(uncertainty, 4), sorted(changed), sorted(affected_nodes), sorted(changed), after - before, bridge, {"affected_feeder_fraction": round(feeder_fraction, 4), "affected_node_fraction": round(node_fraction, 4), "source_assignment_change": round(feeder_fraction, 4), "bridge_importance": bridge, "component_change": round(component_factor, 4)}, risk, priority))
    return sorted(result, key=lambda item: (-item.risk_score, item.connection_id))


def analyse(graph: ElectricalGraph, overrides: dict[str, SwitchState] | None = None) -> ElectricalIntelligence:
    paths = derive_feeder_paths(graph, overrides)
    feeders = feeder_records(graph, paths)
    findings = validate(graph, paths)
    review = criticality(graph, paths)
    errors, critical = sum(item.severity == "error" for item in findings), sum(item.priority == "CRITICAL" for item in review)
    unresolved = sum(item.resolution is Resolution.UNRESOLVED for item in feeders)
    health = {"status": "Critical" if errors or critical else "Review Needed" if findings or unresolved else "Healthy", "sources": len(source_candidates(graph)), "feeders": len(feeders), "resolved_paths": sum(item.resolution is Resolution.RESOLVED for item in feeders), "review_items": len(review), "critical_issues": critical, "factors": {"validation_errors": errors, "unresolved_feeders": unresolved, "topology_review_items": len(review)}}
    return ElectricalIntelligence(source_candidates(graph), feeders, paths, findings, review, health)
