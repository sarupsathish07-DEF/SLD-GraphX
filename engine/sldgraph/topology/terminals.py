"""Symbol-template terminals and resolution-scaled terminal snapping."""

from __future__ import annotations

from math import hypot

from engine.sldgraph.topology.models import TerminalEvidence, TopologySymbol

ONE_TERMINAL_RIGHT = {"energy_source", "load"}
ONE_TERMINAL_LEFT = {"feeder_terminal"}


def generate_terminals(symbols: list[TopologySymbol]) -> list[TerminalEvidence]:
    terminals: list[TerminalEvidence] = []
    for symbol in symbols:
        x1, y1, x2, y2 = symbol.bbox_normalized
        # Transformers are commonly drawn as tall paired coils while their physical
        # through terminals remain lateral; bbox aspect alone is not their orientation.
        horizontal = symbol.predicted_class == "power_transformer" or (x2 - x1) >= (y2 - y1) * 0.5
        orientation = 0 if horizontal else 90
        center_y, center_x = (y1 + y2) / 2, (x1 + x2) / 2
        if symbol.predicted_class in ONE_TERMINAL_RIGHT:
            points = [("ATTACH", (x2, center_y))]
        elif symbol.predicted_class in ONE_TERMINAL_LEFT:
            points = [("ATTACH", (x1, center_y))]
        elif horizontal:
            points = [("IN", (x1, center_y)), ("OUT", (x2, center_y))]
        else:
            points = [("IN", (center_x, y1)), ("OUT", (center_x, y2))]
        for name, position in points:
            terminals.append(
                TerminalEvidence(
                    id=f"terminal:{symbol.id}:{name.lower()}",
                    symbol_id=symbol.id,
                    symbol_class=symbol.predicted_class,
                    page=symbol.page,
                    name=name,
                    position=position,
                    orientation_deg=orientation,
                    orientation_confidence=0.7 if horizontal else 0.55,
                )
            )
    return terminals


def snap_radius(symbol: TopologySymbol) -> float:
    x1, y1, x2, y2 = symbol.bbox_normalized
    diagonal = hypot(x2 - x1, y2 - y1)
    # Detector boxes vary more than renderer ground-truth boxes. Low-confidence
    # boxes receive a bounded tolerance increase, never an unbounded global radius.
    uncertainty = 1 + max(0.0, 0.82 - (symbol.confidence or 0.5)) * 0.3
    return max(0.018, min(0.07, (0.009 + diagonal * 0.46) * uncertainty))


def nearest_terminal(
    point: tuple[float, float], terminals: list[TerminalEvidence], symbols: dict[str, TopologySymbol]
) -> tuple[TerminalEvidence | None, float]:
    best: tuple[TerminalEvidence | None, float] = (None, float("inf"))
    for terminal in terminals:
        distance = hypot(point[0] - terminal.position[0], point[1] - terminal.position[1])
        if distance < best[1] and distance <= snap_radius(symbols[terminal.symbol_id]):
            best = (terminal, distance)
    return best


def nearest_point_on_segment(
    point: tuple[float, float], start: tuple[float, float], end: tuple[float, float]
) -> tuple[tuple[float, float], float]:
    """Return the clamped projection and perpendicular distance in normalized space."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    denominator = dx * dx + dy * dy
    if denominator <= 1e-12:
        return start, hypot(point[0] - start[0], point[1] - start[1])
    fraction = max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / denominator))
    projected = (start[0] + fraction * dx, start[1] + fraction * dy)
    return projected, hypot(point[0] - projected[0], point[1] - projected[1])


def nearest_terminal_on_segment(
    start: tuple[float, float],
    end: tuple[float, float],
    terminals: list[TerminalEvidence],
    symbols: dict[str, TopologySymbol],
) -> tuple[TerminalEvidence | None, tuple[float, float], float]:
    """Snap a terminal to a conductor span, not only to a simplified endpoint."""
    best: tuple[TerminalEvidence | None, tuple[float, float], float] = (None, start, float("inf"))
    for terminal in terminals:
        projected, distance = nearest_point_on_segment(terminal.position, start, end)
        if distance <= snap_radius(symbols[terminal.symbol_id]) and distance < best[2]:
            best = terminal, projected, distance
    return best
