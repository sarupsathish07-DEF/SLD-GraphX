"""Topology-preserving SLDForge scenes with independently rendered raster evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from engine.sldgraph.symbols import SymbolClass
from sldforge.symbol_dataset import _draw_symbol, _font


@dataclass(frozen=True)
class TopologyNode:
    id: str
    symbol_class: SymbolClass
    box: tuple[int, int, int, int]


def _terminal(node: TopologyNode, side: str) -> tuple[int, int]:
    x1, y1, x2, y2 = node.box
    center_y = (y1 + y2) // 2
    if node.symbol_class in {SymbolClass.ENERGY_SOURCE, SymbolClass.LOAD}:
        return x2, center_y
    if node.symbol_class is SymbolClass.FEEDER_TERMINAL:
        return x1, center_y
    return (x1, center_y) if side == "in" else (x2, center_y)


def _scene(topology: str) -> tuple[list[TopologyNode], list[tuple[str, str]]]:
    if topology == "radial":
        nodes = [
            TopologyNode("source", SymbolClass.ENERGY_SOURCE, (60, 290, 145, 380)),
            TopologyNode("transformer", SymbolClass.POWER_TRANSFORMER, (245, 270, 350, 395)),
            TopologyNode("bus", SymbolClass.BUSBAR, (425, 317, 575, 353)),
            TopologyNode("breaker", SymbolClass.CIRCUIT_BREAKER, (650, 285, 745, 380)),
            TopologyNode("ct", SymbolClass.CURRENT_TRANSFORMER, (815, 290, 895, 370)),
            TopologyNode("feeder", SymbolClass.FEEDER_TERMINAL, (985, 280, 1060, 385)),
        ]
        return nodes, [("source", "transformer"), ("transformer", "bus"), ("bus", "breaker"), ("breaker", "ct"), ("ct", "feeder")]
    if topology == "dual_transformer":
        nodes = [
            TopologyNode("source_a", SymbolClass.ENERGY_SOURCE, (55, 150, 135, 235)), TopologyNode("transformer_a", SymbolClass.POWER_TRANSFORMER, (220, 135, 320, 250)), TopologyNode("bus_a", SymbolClass.BUSBAR, (395, 175, 540, 210)), TopologyNode("breaker_a", SymbolClass.CIRCUIT_BREAKER, (650, 145, 740, 235)), TopologyNode("feeder_a", SymbolClass.FEEDER_TERMINAL, (930, 140, 1005, 245)),
            TopologyNode("source_b", SymbolClass.ENERGY_SOURCE, (55, 510, 135, 595)), TopologyNode("transformer_b", SymbolClass.POWER_TRANSFORMER, (220, 495, 320, 610)), TopologyNode("bus_b", SymbolClass.BUSBAR, (395, 535, 540, 570)), TopologyNode("breaker_b", SymbolClass.CIRCUIT_BREAKER, (650, 505, 740, 595)), TopologyNode("feeder_b", SymbolClass.FEEDER_TERMINAL, (930, 500, 1005, 605)),
        ]
        return nodes, [("source_a", "transformer_a"), ("transformer_a", "bus_a"), ("bus_a", "breaker_a"), ("breaker_a", "feeder_a"), ("source_b", "transformer_b"), ("transformer_b", "bus_b"), ("bus_b", "breaker_b"), ("breaker_b", "feeder_b")]
    if topology in {"sectionalized_bus", "bus_coupler", "alternate_supply"}:
        nodes = [
            TopologyNode("source", SymbolClass.ENERGY_SOURCE, (55, 325, 135, 410)), TopologyNode("transformer", SymbolClass.POWER_TRANSFORMER, (205, 305, 310, 430)), TopologyNode("bus_left", SymbolClass.BUSBAR, (380, 345, 500, 380)), TopologyNode("coupler", SymbolClass.BUS_COUPLER, (565, 320, 650, 405)), TopologyNode("bus_right", SymbolClass.BUSBAR, (720, 345, 840, 380)), TopologyNode("feeder_left", SymbolClass.FEEDER_TERMINAL, (930, 190, 1005, 295)), TopologyNode("feeder_right", SymbolClass.FEEDER_TERMINAL, (930, 500, 1005, 605)),
        ]
        return nodes, [("source", "transformer"), ("transformer", "bus_left"), ("bus_left", "coupler"), ("coupler", "bus_right"), ("bus_left", "feeder_left"), ("bus_right", "feeder_right")]
    if topology == "ring":
        nodes = [
            TopologyNode("source", SymbolClass.ENERGY_SOURCE, (55, 325, 135, 410)), TopologyNode("bus", SymbolClass.BUSBAR, (300, 345, 455, 380)), TopologyNode("breaker_top", SymbolClass.CIRCUIT_BREAKER, (580, 165, 670, 255)), TopologyNode("breaker_bottom", SymbolClass.CIRCUIT_BREAKER, (580, 515, 670, 605)), TopologyNode("feeder_top", SymbolClass.FEEDER_TERMINAL, (900, 160, 975, 265)), TopologyNode("feeder_bottom", SymbolClass.FEEDER_TERMINAL, (900, 510, 975, 615)),
        ]
        return nodes, [("source", "bus"), ("bus", "breaker_top"), ("breaker_top", "feeder_top"), ("bus", "breaker_bottom"), ("breaker_bottom", "feeder_bottom")]
    raise ValueError(f"Unsupported topology {topology}")


def _wire(draw: ImageDraw.ImageDraw, left: TopologyNode, right: TopologyNode) -> list[tuple[int, int]]:
    start, end = _terminal(left, "out"), _terminal(right, "in")
    if abs(start[1] - end[1]) < 12:
        points = [start, end]
    else:
        mid_x = (start[0] + end[0]) // 2
        points = [start, (mid_x, start[1]), (mid_x, end[1]), end]
    # Keep a small raster gap at symbol boundaries. This prevents a connected
    # component proposal from swallowing a symbol while exercising gap-aware snapping.
    def inset(point: tuple[int, int], neighbour: tuple[int, int]) -> tuple[int, int]:
        dx, dy = neighbour[0] - point[0], neighbour[1] - point[1]
        length = max(1.0, (dx * dx + dy * dy) ** 0.5)
        return round(point[0] + dx / length * 24), round(point[1] + dy / length * 24)

    points[0] = inset(points[0], points[1])
    points[-1] = inset(points[-1], points[-2])
    draw.line(points, fill="#27312f", width=3, joint="curve")
    return points


def render_topology_scene(topology: str, style: str, seed: int, target: Path | None = None) -> dict:
    width, height = 1200, 820
    image = Image.new("RGB", (width, height), "#f8f7f2")
    draw = ImageDraw.Draw(image)
    draw.text((42, 34), f"SLDFORGE TOPOLOGY / {topology.upper()}", fill="#9a9d96", font=_font(14))
    nodes, links = _scene(topology)
    by_id = {item.id: item for item in nodes}
    edges = []
    for index, (left_id, right_id) in enumerate(links, start=1):
        polyline = _wire(draw, by_id[left_id], by_id[right_id])
        edges.append({"id": f"edge:{topology}:{index:02}", "from": left_id, "to": right_id, "from_terminal": f"{left_id}:out", "to_terminal": f"{right_id}:in", "polyline": [(x / width, y / height) for x, y in polyline], "critical": topology != "ring"})
    for node in nodes:
        _draw_symbol(draw, node.symbol_class, node.box, style, 3)
        draw.text((node.box[0], min(height - 30, node.box[3] + 14)), node.id.upper().replace("_", "-"), fill="#4b504b", font=_font(14))
    payload = {"topology": topology, "style": style, "seed": seed, "width": width, "height": height, "nodes": [{"id": item.id, "class_name": item.symbol_class.value, "bbox": tuple(value / scale for value, scale in zip(item.box, (width, height, width, height)))} for item in nodes], "edges": edges}
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, "PNG", optimize=True)
    return payload


def generate_topology_corpus(output: Path, manifest_target: Path) -> dict:
    entries = []
    for style, split in (("style_a", "test"), ("style_b", "test"), ("style_c", "test"), ("style_d", "style_holdout")):
        for seed, topology in enumerate(("radial", "dual_transformer", "sectionalized_bus", "bus_coupler", "alternate_supply", "ring"), start=1):
            name = f"{split}-{style}-{topology}-{seed}.png"
            payload = render_topology_scene(topology, style, seed, output / name)
            entries.append({"image": name, "split": split, **payload})
    manifest_target.parent.mkdir(parents=True, exist_ok=True)
    manifest_target.write_text(json.dumps({"entries": entries}, indent=2), encoding="utf-8")
    return {"entries": entries}


def generate_topology_repair_development_corpus(output: Path, manifest_target: Path) -> dict:
    """Generate repair-only styles which are never part of frozen v1 test/holdout."""
    entries = []
    for style, split in (("style_e", "development"), ("style_f", "validation")):
        for seed, topology in enumerate(
            ("radial", "dual_transformer", "sectionalized_bus", "bus_coupler", "alternate_supply", "ring"),
            start=101,
        ):
            name = f"{split}-{style}-{topology}-{seed}.png"
            payload = render_topology_scene(topology, style, seed, output / name)
            entries.append({"image": name, "split": split, **payload})
    manifest_target.parent.mkdir(parents=True, exist_ok=True)
    manifest_target.write_text(json.dumps({"entries": entries}, indent=2), encoding="utf-8")
    return {"entries": entries}
