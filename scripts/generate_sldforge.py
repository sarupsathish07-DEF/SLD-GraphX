"""Write the deterministic Bootstrap 0 synthetic graph and reconstruction."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.sldgraph.reconstruction import render_svg
from sldforge.generator import build_radial_fixture

output = Path("data/demo")
output.mkdir(parents=True, exist_ok=True)
graph = build_radial_fixture()
(output / "bootstrap-radial.graph.json").write_text(
    graph.model_dump_json(indent=2), encoding="utf-8"
)
(output / "bootstrap-radial.svg").write_text(render_svg(graph), encoding="utf-8")
print(f"Wrote {output / 'bootstrap-radial.graph.json'} and {output / 'bootstrap-radial.svg'}")
