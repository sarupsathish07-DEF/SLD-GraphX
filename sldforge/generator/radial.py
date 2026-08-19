from engine.sldgraph.electrical import derive_feeder_paths
from engine.sldgraph.models import (
    Connection,
    ElectricalGraph,
    Equipment,
    EquipmentType,
    Geometry,
    Provenance,
    Terminal,
)


def build_radial_fixture() -> ElectricalGraph:
    provenance = [Provenance.SYNTHETIC_GROUND_TRUTH]
    specs = [
        ("source_grid", "GRID-01", EquipmentType.ENERGY_SOURCE, (0.04, 0.43, 0.14, 0.57)),
        ("transformer_01", "TR-01", EquipmentType.POWER_TRANSFORMER, (0.21, 0.36, 0.34, 0.64)),
        ("bus_a", "BUS-A", EquipmentType.BUSBAR, (0.42, 0.46, 0.56, 0.54)),
        ("breaker_01", "CB-01", EquipmentType.CIRCUIT_BREAKER, (0.63, 0.36, 0.74, 0.48)),
        ("ct_01", "CT-01", EquipmentType.CURRENT_TRANSFORMER, (0.80, 0.36, 0.90, 0.48)),
        ("feeder_01", "FDR-01", EquipmentType.FEEDER, (0.92, 0.34, 0.99, 0.50)),
    ]
    equipment = [
        Equipment(
            id=item_id,
            equipment_id=label,
            type=kind,
            geometry=Geometry(bbox=bbox),
            confidence=1.0,
            provenance=provenance,
        )
        for item_id, label, kind, bbox in specs
    ]
    terminals = []
    for item_id, _, _, bbox in specs:
        x1, y1, x2, y2 = bbox
        terminals.extend(
            [
                Terminal(
                    id=f"{item_id}_in",
                    equipment_id=item_id,
                    name="IN",
                    position=(x1, (y1 + y2) / 2),
                ),
                Terminal(
                    id=f"{item_id}_out",
                    equipment_id=item_id,
                    name="OUT",
                    position=(x2, (y1 + y2) / 2),
                ),
            ]
        )
    connections = [
        Connection(
            id=f"edge_{index:02}",
            from_terminal_id=f"{left}_out",
            to_terminal_id=f"{right}_in",
            confidence=1.0,
            provenance=provenance,
        )
        for index, (left, right) in enumerate(
            zip([item[0] for item in specs], [item[0] for item in specs][1:]), start=1
        )
    ]
    graph = ElectricalGraph(
        id="fixture_radial_01", equipment=equipment, terminals=terminals, connections=connections
    )
    graph.feeder_paths = derive_feeder_paths(graph)
    return graph
