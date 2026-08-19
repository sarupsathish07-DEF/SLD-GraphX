from __future__ import annotations

import networkx as nx

from engine.sldgraph.models import ElectricalGraph, EquipmentType, FeederPath, SwitchState


def _terminal_equipment(graph: ElectricalGraph) -> dict[str, str]:
    return {terminal.id: terminal.equipment_id for terminal in graph.terminals}


def derive_feeder_paths(graph: ElectricalGraph) -> list[FeederPath]:
    """Return shortest active equipment paths from any source to each feeder."""
    terminal_map = _terminal_equipment(graph)
    network = nx.Graph()
    for equipment in graph.equipment:
        network.add_node(equipment.id)
    for connection in graph.connections:
        if connection.switch_state is SwitchState.OPEN:
            continue
        network.add_edge(
            terminal_map[connection.from_terminal_id],
            terminal_map[connection.to_terminal_id],
            connection_id=connection.id,
            confidence=connection.confidence,
        )

    sources = [
        item.id
        for item in graph.equipment
        if item.type
        in {EquipmentType.ENERGY_SOURCE, EquipmentType.GRID_INCOMER, EquipmentType.GENERATOR}
    ]
    paths: list[FeederPath] = []
    for feeder in (item for item in graph.equipment if item.type is EquipmentType.FEEDER):
        candidates = []
        for source in sources:
            if nx.has_path(network, source, feeder.id):
                candidates.append((source, nx.shortest_path(network, source, feeder.id)))
        if not candidates:
            paths.append(
                FeederPath(
                    feeder_equipment_id=feeder.id,
                    source_equipment_id=None,
                    equipment_path=[],
                    confidence=0.0,
                    active=False,
                )
            )
            continue
        source, path = min(candidates, key=lambda candidate: len(candidate[1]))
        edge_confidence = [network[a][b]["confidence"] for a, b in zip(path, path[1:])]
        paths.append(
            FeederPath(
                feeder_equipment_id=feeder.id,
                source_equipment_id=source,
                equipment_path=path,
                confidence=min(edge_confidence, default=1.0),
                active=True,
            )
        )
    return paths
