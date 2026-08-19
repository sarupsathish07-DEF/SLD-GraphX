from __future__ import annotations

from html import escape

from engine.sldgraph.models import ElectricalGraph


def render_svg(graph: ElectricalGraph, width: int = 1280, height: int = 680) -> str:
    """Render a compact clean diagram from normalized fixture geometry."""
    terminal_map = {terminal.id: terminal for terminal in graph.terminals}
    strokes = []
    for connection in graph.connections:
        start, end = (
            terminal_map[connection.from_terminal_id],
            terminal_map[connection.to_terminal_id],
        )
        state = (
            "#f0a542"
            if connection.switch_state and connection.switch_state.value == "open"
            else "#47d7c8"
        )
        strokes.append(
            "<line "
            f'x1="{start.position[0] * width:.0f}" '
            f'y1="{start.position[1] * height:.0f}" '
            f'x2="{end.position[0] * width:.0f}" '
            f'y2="{end.position[1] * height:.0f}" '
            f'stroke="{state}" stroke-width="4"/>'
        )
    nodes = []
    for item in graph.equipment:
        x1, y1, x2, y2 = item.geometry.bbox or (0.1, 0.1, 0.15, 0.15)
        x, y, w, h = x1 * width, y1 * height, (x2 - x1) * width, (y2 - y1) * height
        nodes.append(
            "<rect "
            f'x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" '
            'rx="8" fill="#162435" stroke="#7ee6db" stroke-width="2"/>'
        )
        nodes.append(
            "<text "
            f'x="{x + w / 2:.0f}" y="{y + h / 2 + 5:.0f}" '
            'fill="#f1f8fa" font-size="15" text-anchor="middle" font-family="Arial">'
            f"{escape(item.equipment_id)}</text>"
        )
    opening = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" role="img" '
        'aria-label="Clean reconstructed electrical single line diagram">'
        '<rect width="100%" height="100%" fill="#0c1420"/>'
    )
    return opening + "".join(strokes) + "".join(nodes) + "</svg>"
