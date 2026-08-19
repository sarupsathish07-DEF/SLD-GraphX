from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from engine.sldgraph.models import ElectricalGraph, EquipmentType, SwitchState


def _font(size: int):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def render_png(graph: ElectricalGraph, target: Path | None = None, width: int = 1600, height: int = 900) -> Image.Image:
    """Render a clean, deterministic engineering test drawing from canonical geometry."""
    image = Image.new("RGB", (width, height), "#f8f7f2")
    draw = ImageDraw.Draw(image)
    draw.rectangle((22, 22, width - 22, height - 22), outline="#b9b8b0", width=2)
    draw.text((52, 48), f"SLDFORGE / {graph.id.replace('fixture_', '').replace('_', ' ').upper()}", fill="#222522", font=_font(22))
    draw.text((52, 78), "Synthetic ground-truth test drawing · local development only", fill="#656961", font=_font(14))
    terminal_map = {terminal.id: terminal for terminal in graph.terminals}
    for connection in graph.connections:
        start, end = terminal_map[connection.from_terminal_id], terminal_map[connection.to_terminal_id]
        points = [(round(x * width), round(y * height)) for x, y in (connection.geometry.polyline or [start.position, end.position])]
        if len(points) == 2:
            draw.line(points, fill="#a54224" if connection.switch_state is SwitchState.OPEN else "#30332f", width=4)
        else:
            draw.line(points, fill="#30332f", width=4)
        if connection.switch_state is SwitchState.OPEN:
            mid = points[len(points) // 2]
            draw.text((mid[0] + 8, mid[1] - 22), "OPEN", fill="#a54224", font=_font(13))
    for item in graph.equipment:
        x1, y1, x2, y2 = item.geometry.bbox or (.1, .1, .15, .15)
        box = (round(x1 * width), round(y1 * height), round(x2 * width), round(y2 * height))
        if item.type is EquipmentType.BUSBAR:
            draw.rectangle(box, fill="#30332f")
        elif item.type is EquipmentType.ENERGY_SOURCE:
            draw.ellipse(box, outline="#2c4e7a", width=4)
        elif item.type in {EquipmentType.CIRCUIT_BREAKER, EquipmentType.BUS_COUPLER}:
            draw.rectangle(box, outline="#30332f", width=4)
            draw.line((box[0] + 10, box[3] - 10, box[2] - 10, box[1] + 10), fill="#30332f", width=3)
        elif item.type is EquipmentType.POWER_TRANSFORMER:
            mid = (box[0] + box[2]) // 2
            radius = max(18, min(box[2] - box[0], box[3] - box[1]) // 4)
            cy = (box[1] + box[3]) // 2
            draw.ellipse((mid - radius - 10, cy - radius, mid - 10, cy + radius), outline="#30332f", width=3)
            draw.ellipse((mid + 10, cy - radius, mid + radius + 10, cy + radius), outline="#30332f", width=3)
        else:
            draw.rounded_rectangle(box, radius=5, outline="#30332f", width=3)
        label_y = box[3] + 9 if box[3] < height - 50 else box[1] - 22
        draw.text((box[0], label_y), item.equipment_id, fill="#222522", font=_font(17))
        rating = str(item.attributes.get("rating", ""))
        if rating:
            draw.text((box[0], label_y + 21), rating, fill="#656961", font=_font(12))
    draw.text((width - 320, height - 55), "Generated graph-first by SLDForge", fill="#656961", font=_font(13))
    if target is not None:
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, "PNG", optimize=True)
    return image
