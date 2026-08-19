from __future__ import annotations

import json
from pathlib import Path

from engine.sldgraph.reconstruction import render_svg
from sldforge.degradation import DegradationConfig, degrade
from sldforge.generator.radial import build_radial_fixture
from sldforge.generator.topologies import TOPOLOGIES
from sldforge.renderer import render_png


def graph_manifest(graph, topology_type: str, seed: int, width: int, height: int) -> dict:
    """Ground truth that preserves both canonical graph and rendered evidence links."""
    return {
        "drawing_id": graph.id,
        "seed": seed,
        "topology_type": topology_type,
        "image_dimensions": {"width": width, "height": height},
        "equipment": [item.model_dump(mode="json") for item in graph.equipment],
        "terminals": [item.model_dump(mode="json") for item in graph.terminals],
        "busbars": [item.model_dump(mode="json") for item in graph.equipment if item.type.value == "busbar"],
        "connections": [item.model_dump(mode="json") for item in graph.connections],
        "junctions": [item.model_dump(mode="json") for item in graph.equipment if item.type.value == "junction"],
        "switch_states": {item.id: item.switch_state.value if item.switch_state else None for item in graph.connections},
        "sources": [item.id for item in graph.equipment if item.type.value in {"energy_source", "grid_incomer", "generator"}],
        "feeders": [item.id for item in graph.equipment if item.type.value == "feeder"],
        "exact_source_to_feeder_paths": [item.model_dump(mode="json") for item in graph.feeder_paths],
        "source_assignments": [
            {
                "feeder": item.feeder_equipment_id,
                "source": item.source_equipment_id,
                "source_bus": item.source_bus_equipment_id,
                "destination": item.destination_equipment_id,
                "switching_equipment": item.switching_equipment_ids,
            }
            for item in graph.feeder_paths
        ],
        "text": [{"raw_rendered_string": item.equipment_id, "semantic_type": "equipment_id", "bbox": item.geometry.bbox, "linked_entity": item.id} for item in graph.equipment],
    }


def generate_development_corpus(output: Path, width: int = 1600, height: int = 900) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    builders = {"radial": build_radial_fixture, **{name: builder for name, builder in TOPOLOGIES.items() if builder is not None}}
    written = []
    for seed, (name, builder) in enumerate(builders.items(), start=1):
        graph = builder()
        base = output / name
        png = base.with_suffix(".png")
        render_png(graph, png, width, height)
        base.with_suffix(".svg").write_text(render_svg(graph, width, height), encoding="utf-8")
        base.with_suffix(".ground-truth.json").write_text(json.dumps(graph_manifest(graph, name, seed, width, height), indent=2), encoding="utf-8")
        written.extend([png, base.with_suffix(".svg"), base.with_suffix(".ground-truth.json")])
    radial = render_png(build_radial_fixture(), width=width, height=height)
    degraded, manifest = degrade(radial, DegradationConfig(seed=7, blur_radius=0.7, jpeg_quality=80, skew_degrees=0.6, contrast=0.82, brightness=1.05, faded_lines=0.08))
    degraded_path = output / "radial-degraded.png"
    degraded.save(degraded_path, "PNG", optimize=True)
    (output / "radial-degraded.manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    written.extend([degraded_path, output / "radial-degraded.manifest.json"])
    return written
