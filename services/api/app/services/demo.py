from engine.sldgraph.reconstruction import render_svg
from sldforge.generator import build_radial_fixture


def bootstrap_demo() -> dict:
    graph = build_radial_fixture()
    return {"graph": graph.model_dump(mode="json"), "svg": render_svg(graph)}
