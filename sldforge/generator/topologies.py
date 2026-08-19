"""Deterministic graph-first SLDForge topology fixtures for local development."""
from __future__ import annotations

from dataclasses import dataclass

from engine.sldgraph.electrical import derive_feeder_paths
from engine.sldgraph.models import (
    Connection,
    ElectricalGraph,
    Equipment,
    EquipmentType,
    Geometry,
    Provenance,
    SwitchState,
    Terminal,
)

PROVENANCE = [Provenance.SYNTHETIC_GROUND_TRUTH]


@dataclass(frozen=True)
class Item:
    id: str
    label: str
    kind: EquipmentType
    bbox: tuple[float, float, float, float]
    rating: str = "11 kV"


def _graph(name: str, items: list[Item], links: list[tuple[str, str, SwitchState | None]]) -> ElectricalGraph:
    equipment = [Equipment(id=item.id, equipment_id=item.label, type=item.kind, geometry=Geometry(bbox=item.bbox), attributes={"rating": item.rating, "manufacturer": "SLDForge"}, confidence=1.0, provenance=PROVENANCE) for item in items]
    terminals = []
    for item in items:
        x1, y1, x2, y2 = item.bbox
        terminals.extend([Terminal(id=f"{item.id}_in", equipment_id=item.id, name="IN", position=(x1, (y1 + y2) / 2)), Terminal(id=f"{item.id}_out", equipment_id=item.id, name="OUT", position=(x2, (y1 + y2) / 2))])
    by_id = {item.id: item for item in items}
    connections = []
    for index, (left, right, state) in enumerate(links, start=1):
        start, end = by_id[left], by_id[right]
        x1, y1 = start.bbox[2], (start.bbox[1] + start.bbox[3]) / 2
        x2, y2 = end.bbox[0], (end.bbox[1] + end.bbox[3]) / 2
        connections.append(Connection(id=f"edge_{index:02}", from_terminal_id=f"{left}_out", to_terminal_id=f"{right}_in", geometry=Geometry(polyline=[(x1, y1), (x2, y2)]), switch_state=state, confidence=1.0, provenance=PROVENANCE))
    graph = ElectricalGraph(id=f"fixture_{name}_01", equipment=equipment, terminals=terminals, connections=connections)
    graph.feeder_paths = derive_feeder_paths(graph)
    return graph


def build_dual_transformer_fixture() -> ElectricalGraph:
    items = [
        Item("source_a", "GRID-A", EquipmentType.ENERGY_SOURCE, (.03, .18, .12, .30)),
        Item("transformer_a", "TR-A", EquipmentType.POWER_TRANSFORMER, (.18, .13, .30, .35), "33/11 kV · 20 MVA"),
        Item("bus_a", "BUS-A", EquipmentType.BUSBAR, (.38, .19, .53, .25)),
        Item("source_b", "GRID-B", EquipmentType.ENERGY_SOURCE, (.03, .65, .12, .77)),
        Item("transformer_b", "TR-B", EquipmentType.POWER_TRANSFORMER, (.18, .60, .30, .82), "33/11 kV · 20 MVA"),
        Item("bus_b", "BUS-B", EquipmentType.BUSBAR, (.38, .70, .53, .76)),
        Item("breaker_a", "CB-A1", EquipmentType.CIRCUIT_BREAKER, (.63, .17, .72, .28)),
        Item("breaker_b", "CB-B1", EquipmentType.CIRCUIT_BREAKER, (.63, .68, .72, .79)),
        Item("feeder_a", "FDR-A", EquipmentType.FEEDER, (.84, .17, .97, .28), "11 kV · 630 A"),
        Item("feeder_b", "FDR-B", EquipmentType.FEEDER, (.84, .68, .97, .79), "11 kV · 630 A"),
    ]
    return _graph("dual_transformer", items, [("source_a", "transformer_a", None), ("transformer_a", "bus_a", None), ("bus_a", "breaker_a", SwitchState.CLOSED), ("breaker_a", "feeder_a", None), ("source_b", "transformer_b", None), ("transformer_b", "bus_b", None), ("bus_b", "breaker_b", SwitchState.CLOSED), ("breaker_b", "feeder_b", None)])


def build_sectionalized_bus_fixture() -> ElectricalGraph:
    items = [
        Item("source_grid", "GRID-01", EquipmentType.ENERGY_SOURCE, (.03, .40, .12, .52)),
        Item("transformer", "TR-01", EquipmentType.POWER_TRANSFORMER, (.17, .34, .29, .58), "33/11 kV · 25 MVA"),
        Item("bus_left", "BUS-1", EquipmentType.BUSBAR, (.36, .42, .49, .48)),
        Item("section", "S-01", EquipmentType.BUS_COUPLER, (.55, .39, .64, .51)),
        Item("bus_right", "BUS-2", EquipmentType.BUSBAR, (.69, .42, .81, .48)),
        Item("feeder_left", "FDR-1", EquipmentType.FEEDER, (.85, .18, .98, .30)),
        Item("feeder_right", "FDR-2", EquipmentType.FEEDER, (.85, .65, .98, .77)),
    ]
    return _graph("sectionalized_bus", items, [("source_grid", "transformer", None), ("transformer", "bus_left", None), ("bus_left", "section", SwitchState.CLOSED), ("section", "bus_right", SwitchState.CLOSED), ("bus_left", "feeder_left", SwitchState.CLOSED), ("bus_right", "feeder_right", SwitchState.CLOSED)])


def build_bus_coupler_fixture() -> ElectricalGraph:
    graph = build_dual_transformer_fixture()
    graph.id = "fixture_bus_coupler_01"
    left = next(item for item in graph.equipment if item.id == "bus_a")
    right = next(item for item in graph.equipment if item.id == "bus_b")
    coupler = Equipment(id="bus_coupler", equipment_id="BC-01", type=EquipmentType.BUS_COUPLER, geometry=Geometry(bbox=(.55, .43, .65, .55)), attributes={"rating": "11 kV · 1250 A"}, confidence=1.0, provenance=PROVENANCE)
    graph.equipment.append(coupler)
    graph.terminals.extend([Terminal(id="bus_coupler_in", equipment_id="bus_coupler", name="IN", position=(.55, .49)), Terminal(id="bus_coupler_out", equipment_id="bus_coupler", name="OUT", position=(.65, .49))])
    graph.connections.extend([Connection(id="edge_bc_01", from_terminal_id=f"{left.id}_out", to_terminal_id="bus_coupler_in", geometry=Geometry(polyline=[(.53, .22), (.55, .49)]), switch_state=SwitchState.CLOSED, confidence=1.0, provenance=PROVENANCE), Connection(id="edge_bc_02", from_terminal_id="bus_coupler_out", to_terminal_id=f"{right.id}_in", geometry=Geometry(polyline=[(.65, .49), (.38, .73)]), switch_state=SwitchState.CLOSED, confidence=1.0, provenance=PROVENANCE)])
    graph.feeder_paths = derive_feeder_paths(graph)
    return graph


def build_alternate_supply_fixture() -> ElectricalGraph:
    graph = build_bus_coupler_fixture()
    graph.id = "fixture_alternate_supply_01"
    for connection in graph.connections:
        if connection.id in {"edge_bc_01", "edge_bc_02"}:
            connection.switch_state = SwitchState.OPEN
    graph.feeder_paths = derive_feeder_paths(graph)
    return graph


def build_ring_fixture() -> ElectricalGraph:
    items = [
        Item("source_grid", "GRID-01", EquipmentType.ENERGY_SOURCE, (.04, .43, .13, .55)),
        Item("bus", "RING-BUS", EquipmentType.BUSBAR, (.26, .44, .39, .50)),
        Item("cb_1", "CB-01", EquipmentType.CIRCUIT_BREAKER, (.52, .17, .61, .28)),
        Item("cb_2", "CB-02", EquipmentType.CIRCUIT_BREAKER, (.52, .68, .61, .79)),
        Item("fdr_1", "FDR-01", EquipmentType.FEEDER, (.80, .17, .96, .28)),
        Item("fdr_2", "FDR-02", EquipmentType.FEEDER, (.80, .68, .96, .79)),
    ]
    return _graph("ring", items, [("source_grid", "bus", None), ("bus", "cb_1", SwitchState.CLOSED), ("cb_1", "fdr_1", None), ("bus", "cb_2", SwitchState.CLOSED), ("cb_2", "fdr_2", None)])


TOPOLOGIES = {"radial": None, "dual_transformer": build_dual_transformer_fixture, "sectionalized_bus": build_sectionalized_bus_fixture, "bus_coupler": build_bus_coupler_fixture, "alternate_supply": build_alternate_supply_fixture, "ring": build_ring_fixture}
