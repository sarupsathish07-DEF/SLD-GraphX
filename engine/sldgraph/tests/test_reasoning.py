from sldforge.generator import build_radial_fixture


def test_radial_fixture_has_one_active_source_to_feeder_path() -> None:
    graph = build_radial_fixture()
    assert len(graph.feeder_paths) == 1
    path = graph.feeder_paths[0]
    assert path.active
    assert path.source_equipment_id == "source_grid"
    assert path.equipment_path[-1] == "feeder_01"
