import json

from sldforge.degradation import DegradationConfig, degrade
from sldforge.generator import (
    build_alternate_supply_fixture,
    build_bus_coupler_fixture,
    build_dual_transformer_fixture,
    build_radial_fixture,
    build_sectionalized_bus_fixture,
    generate_development_corpus,
)
from sldforge.renderer import render_png


def test_required_topologies_have_ground_truth_paths_and_rendering(tmp_path) -> None:
    for builder in [build_radial_fixture, build_dual_transformer_fixture, build_sectionalized_bus_fixture, build_bus_coupler_fixture, build_alternate_supply_fixture]:
        graph = builder()
        assert graph.terminals and graph.connections and graph.feeder_paths
        image = render_png(graph, tmp_path / f"{graph.id}.png")
        assert image.size == (1600, 900)


def test_alternate_supply_preserves_open_switch_evidence() -> None:
    graph = build_alternate_supply_fixture()
    assert any(connection.switch_state and connection.switch_state.value == "open" for connection in graph.connections)
    assert all(path.active for path in graph.feeder_paths)


def test_corpus_is_small_reproducible_and_has_manifest(tmp_path) -> None:
    written = generate_development_corpus(tmp_path)
    assert len(written) >= 20
    manifest = json.loads((tmp_path / "radial.ground-truth.json").read_text())
    assert manifest["terminals"] and manifest["exact_source_to_feeder_paths"]


def test_degradation_is_deterministic() -> None:
    image = render_png(build_radial_fixture())
    first, metadata = degrade(image, DegradationConfig(seed=3, blur_radius=0.5, jpeg_quality=85))
    second, _ = degrade(image, DegradationConfig(seed=3, blur_radius=0.5, jpeg_quality=85))
    assert first.tobytes() == second.tobytes()
    assert metadata["parameters"]["seed"] == 3
