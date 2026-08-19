from engine.sldgraph.reconstruction import render_svg
from sldforge.generator import build_radial_fixture


def test_fixture_renders_to_svg() -> None:
    svg = render_svg(build_radial_fixture())
    assert "FDR-01" in svg
    assert 'role="img"' in svg
