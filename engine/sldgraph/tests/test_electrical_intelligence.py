from engine.sldgraph.electrical import analyse, derive_feeder_paths
from engine.sldgraph.models import (
    Connection,
    Equipment,
    EquipmentType,
    Geometry,
    Provenance,
    ReviewStatus,
    SwitchState,
    Terminal,
)
from sldforge.generator import (
    build_alternate_supply_fixture,
    build_bus_coupler_fixture,
    build_dual_transformer_fixture,
    build_radial_fixture,
)


def test_radial_reasoning_returns_explainable_source_feeder_lineage() -> None:
    intelligence = analyse(build_radial_fixture())
    assert [item.equipment_label for item in intelligence.sources] == ["GRID-01"]
    feeder = intelligence.feeders[0]
    path = intelligence.paths[0]
    assert feeder.resolution.value == "resolved"
    assert feeder.source_bus_equipment_id == "bus_a"
    assert path.equipment_path == ["source_grid", "transformer_01", "bus_a", "breaker_01", "ct_01", "feeder_01"]
    assert path.weakest_connection_confidence == 1.0


def test_open_switch_breaks_operational_path_without_mutating_physical_graph() -> None:
    graph = build_radial_fixture()
    closed = derive_feeder_paths(graph, {"breaker_01": SwitchState.CLOSED})[0]
    open_path = derive_feeder_paths(graph, {"breaker_01": SwitchState.OPEN})[0]
    assert closed.source_equipment_id == "source_grid"
    assert open_path.source_equipment_id is None
    assert graph.connections[3].switch_state is None


def test_dual_source_and_coupler_paths_preserve_ambiguity() -> None:
    intelligence = analyse(build_bus_coupler_fixture())
    assert len(intelligence.sources) == 2
    assert any("MULTIPLE_SOURCE_OR_PATH_CANDIDATES" in item.uncertainty_flags for item in intelligence.paths)
    alternate = analyse(build_alternate_supply_fixture())
    assert all(item.source_equipment_id for item in alternate.paths)


def test_critical_bridge_outranks_harmless_low_confidence_connection() -> None:
    graph = build_dual_transformer_fixture()
    graph.connections[2].confidence = 0.72
    graph.connections.append(
        Connection(
            id="harmless_parallel",
            from_terminal_id="source_a_out",
            to_terminal_id="transformer_a_in",
            confidence=0.35,
            provenance=[Provenance.SYNTHETIC_GROUND_TRUTH],
        )
    )
    ranked = analyse(graph).criticality
    assert ranked[0].connection_id == graph.connections[2].id
    assert ranked[0].risk_score > ranked[-1].risk_score


def test_verified_connection_leaves_criticality_queue_even_when_low_confidence() -> None:
    graph = build_radial_fixture()
    graph.connections[2].confidence = 0.2
    graph.connections[2].review_status = ReviewStatus.VERIFIED
    assert graph.connections[2].id not in {item.connection_id for item in analyse(graph).criticality}


def test_destination_is_recorded_only_when_real_downstream_load_exists() -> None:
    graph = build_radial_fixture()
    graph.equipment.append(
        Equipment(
            id="load_01",
            equipment_id="LOAD-CENTER-A",
            type=EquipmentType.LOAD,
            geometry=Geometry(bbox=(0.995, 0.34, 1.0, 0.5)),
            confidence=1.0,
            provenance=[Provenance.SYNTHETIC_GROUND_TRUTH],
        )
    )
    graph.terminals.append(Terminal(id="load_01_in", equipment_id="load_01", name="IN", position=(0.995, 0.42)))
    graph.connections.append(Connection(id="edge_load", from_terminal_id="feeder_01_out", to_terminal_id="load_01_in", confidence=1.0, provenance=[Provenance.SYNTHETIC_GROUND_TRUTH]))
    feeder = analyse(graph).feeders[0]
    assert feeder.destination_equipment_id == "load_01"
