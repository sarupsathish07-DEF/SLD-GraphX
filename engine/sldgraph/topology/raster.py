"""Mask-aware raster conductor, busbar, and junction evidence extraction."""

from __future__ import annotations

from itertools import combinations

import cv2
import numpy as np

from engine.sldgraph.topology.models import (
    BusbarEvidence,
    ConductorEvidence,
    CrossingKind,
    JunctionEvidence,
    TopologySymbol,
    TopologyText,
)
from engine.sldgraph.topology.terminals import generate_terminals


def protected_mask(
    shape: tuple[int, int], symbols: list[TopologySymbol], texts: list[TopologyText]
) -> np.ndarray:
    """Protect visual symbols/text from skeletonization while retaining raw ink for bridge review."""
    height, width = shape
    mask = np.zeros(shape, dtype=np.uint8)
    for item in symbols:
        x1, y1, x2, y2 = item.bbox_normalized
        # A detector bbox is evidence, not an excuse to erase its approaches.
        # Protect the class interior with a small adaptive inset instead of padding it.
        inset = max(1, round(min(width, height) * 0.0018))
        cv2.rectangle(mask, (max(0, round(x1 * width) + inset), max(0, round(y1 * height) + inset)), (min(width - 1, round(x2 * width) - inset), min(height - 1, round(y2 * height) - inset)), 255, -1)
    for item in texts:
        x1, y1, x2, y2 = item.bbox_normalized
        inset = max(1, round(min(width, height) * 0.0015))
        cv2.rectangle(mask, (max(0, round(x1 * width) + inset), max(0, round(y1 * height) + inset)), (min(width - 1, round(x2 * width) - inset), min(height - 1, round(y2 * height) - inset)), 255, -1)
    # Re-open narrow terminal corridors. The device interior remains hidden, while
    # conductor approaches are preserved for segment-to-terminal association.
    corridor_length = max(14, round(min(width, height) * 0.032))
    corridor_width = max(3, round(min(width, height) * 0.0045))
    for terminal in generate_terminals(symbols):
        symbol = next(item for item in symbols if item.id == terminal.symbol_id)
        x1, y1, x2, y2 = symbol.bbox_normalized
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        tx, ty = terminal.position
        dx, dy = tx - cx, ty - cy
        magnitude = max(1e-6, float(np.hypot(dx, dy)))
        start = (round(tx * width), round(ty * height))
        end = (round((tx + dx / magnitude * corridor_length / width) * width), round((ty + dy / magnitude * corridor_length / height) * height))
        cv2.line(mask, start, end, 0, corridor_width)
    return mask


def morphology_skeleton(binary: np.ndarray) -> np.ndarray:
    """Vectorized Zhang-Suen thinning keeps degree logic from seeing double raster strokes."""
    image = (binary > 0).astype(np.uint8)
    for _ in range(100):
        changed = False
        for phase in range(2):
            p2 = np.zeros_like(image)
            p2[1:] = image[:-1]
            p3 = np.zeros_like(image)
            p3[1:, :-1] = image[:-1, 1:]
            p4 = np.zeros_like(image)
            p4[:, :-1] = image[:, 1:]
            p5 = np.zeros_like(image)
            p5[:-1, :-1] = image[1:, 1:]
            p6 = np.zeros_like(image)
            p6[:-1] = image[1:]
            p7 = np.zeros_like(image)
            p7[:-1, 1:] = image[1:, :-1]
            p8 = np.zeros_like(image)
            p8[:, 1:] = image[:, :-1]
            p9 = np.zeros_like(image)
            p9[1:, 1:] = image[:-1, :-1]
            neighbours = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
            transitions = ((p2 == 0) & (p3 == 1)).astype(np.uint8)
            for left, right in ((p3, p4), (p4, p5), (p5, p6), (p6, p7), (p7, p8), (p8, p9), (p9, p2)):
                transitions += ((left == 0) & (right == 1)).astype(np.uint8)
            if phase == 0:
                preserve = (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                preserve = (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            remove = (image == 1) & (neighbours >= 2) & (neighbours <= 6) & (transitions == 1) & preserve
            if np.any(remove):
                image[remove] = 0
                changed = True
        if not changed:
            break
    return image * 255


def _normal(point: tuple[int, int], width: int, height: int) -> tuple[float, float]:
    return round(point[0] / width, 6), round(point[1] / height, 6)


def _line_segments(line_map: np.ndarray, width: int, height: int) -> list[ConductorEvidence]:
    lines = cv2.HoughLinesP(
        line_map,
        rho=1,
        theta=np.pi / 360,
        threshold=max(18, min(width, height) // 45),
        minLineLength=max(16, min(width, height) // 38),
        maxLineGap=max(8, min(width, height) // 85),
    )
    output: list[ConductorEvidence] = []
    seen: set[tuple[int, int, int, int]] = set()
    if lines is None:
        return output
    for index, line in enumerate(lines[:, 0]):
        x1, y1, x2, y2 = (int(value) for value in line)
        length = float(np.hypot(x2 - x1, y2 - y1))
        if length < max(18, min(width, height) * 0.018):
            continue
        key = tuple(round(value / 5) * 5 for value in (x1, y1, x2, y2))
        reverse = (key[2], key[3], key[0], key[1])
        if key in seen or reverse in seen:
            continue
        seen.add(key)
        output.append(
            ConductorEvidence(
                id=f"conductor:{index:04}",
                polyline=[_normal((x1, y1), width, height), _normal((x2, y2), width, height)],
                confidence=round(min(0.95, 0.48 + length / max(width, height) * 0.85), 4),
            )
        )
    return output


def extract_conductors(
    image: np.ndarray, symbols: list[TopologySymbol], texts: list[TopologyText]
) -> tuple[list[ConductorEvidence], np.ndarray, np.ndarray, np.ndarray]:
    """Directional morphology first, then local segment tracing—not a one-shot whole-page Hough."""
    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    ink = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 9
    )
    mask = protected_mask((height, width), symbols, texts)
    masked = cv2.bitwise_and(ink, cv2.bitwise_not(mask))
    fine = max(9, width // 115)
    medium = max(17, width // 70)
    horizontal = cv2.bitwise_or(
        cv2.morphologyEx(masked, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (fine, 1))),
        cv2.morphologyEx(masked, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (medium, 1))),
    )
    vertical = cv2.bitwise_or(
        cv2.morphologyEx(masked, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, fine))),
        cv2.morphologyEx(masked, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, medium))),
    )
    directional = cv2.bitwise_or(horizontal, vertical)
    # Preserve angled feeders only where line evidence is strong; symbols/text remain masked.
    edges = cv2.Canny(masked, 45, 120)
    angled = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 360,
        threshold=max(24, min(width, height) // 40),
        minLineLength=max(25, min(width, height) // 32),
        maxLineGap=max(8, min(width, height) // 100),
    )
    if angled is not None:
        for x1, y1, x2, y2 in angled[:, 0]:
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1))) % 180
            if 8 < angle < 172 and not 82 < angle < 98:
                cv2.line(directional, (x1, y1), (x2, y2), 255, 1)
    skeleton = morphology_skeleton(directional)
    return _line_segments(directional, width, height), directional, skeleton, mask


def extract_buses(
    conductors: list[ConductorEvidence], symbols: list[TopologySymbol]
) -> list[BusbarEvidence]:
    buses: list[BusbarEvidence] = []
    for symbol in symbols:
        if symbol.predicted_class != "busbar":
            continue
        x1, y1, x2, y2 = symbol.bbox_normalized
        horizontal = (x2 - x1) >= (y2 - y1)
        polyline = [(x1, (y1 + y2) / 2), (x2, (y1 + y2) / 2)] if horizontal else [((x1 + x2) / 2, y1), ((x1 + x2) / 2, y2)]
        buses.append(BusbarEvidence(id=f"bus:{symbol.id}", page=symbol.page, polyline=polyline, bbox_normalized=symbol.bbox_normalized, confidence=min(0.98, (symbol.confidence or 0.5) * 0.75 + 0.25), provenance="symbol_geometry", associated_symbol_id=symbol.id))
    # Long line evidence remains a bus candidate only when it is substantially longer than ordinary traces.
    for conductor in conductors:
        (x1, y1), (x2, y2) = conductor.polyline[0], conductor.polyline[-1]
        length = float(np.hypot(x2 - x1, y2 - y1))
        if length < 0.18 or abs(y2 - y1) > 0.012:
            continue
        if any(abs(((bus.polyline[0][1] + bus.polyline[-1][1]) / 2) - y1) < 0.02 for bus in buses):
            continue
        buses.append(BusbarEvidence(id=f"bus:geometry:{conductor.id}", polyline=conductor.polyline, bbox_normalized=(min(x1, x2), min(y1, y2) - 0.004, max(x1, x2), max(y1, y2) + 0.004), confidence=0.54, provenance="long_line_geometry", review_status="pending"))
    return buses


def extract_junctions(
    skeleton: np.ndarray, image: np.ndarray | None = None, evidence_mask: np.ndarray | None = None
) -> list[JunctionEvidence]:
    height, width = skeleton.shape[:2]
    binary = (skeleton > 0).astype(np.uint8)
    degree = cv2.filter2D(binary, cv2.CV_16S, np.ones((3, 3), dtype=np.uint8)) - binary
    candidate = ((degree >= 3) & (binary > 0)).astype(np.uint8) * 255
    count, _, stats, centroids = cv2.connectedComponentsWithStats(candidate)
    output = []
    raw_ink = None
    if image is not None:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        raw_ink = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)[1]
        if evidence_mask is not None:
            raw_ink = cv2.bitwise_and(raw_ink, cv2.bitwise_not(evidence_mask))
    for index in range(1, count):
        if stats[index, cv2.CC_STAT_AREA] < 2:
            continue
        x, y = centroids[index]
        local_degree = int(degree[round(y), round(x)])
        # A skeleton branch is not enough: require dark compact dot evidence before
        # asserting a connected junction. Otherwise it remains an explicit ambiguity.
        if raw_ink is not None:
            radius = max(4, min(width, height) // 180)
            x1, x2 = max(0, round(x) - radius), min(width, round(x) + radius + 1)
            y1, y2 = max(0, round(y) - radius), min(height, round(y) + radius + 1)
            density = float(np.count_nonzero(raw_ink[y1:y2, x1:x2])) / max(1, (x2 - x1) * (y2 - y1))
            if density < 0.58:
                continue
        output.append(JunctionEvidence(id=f"junction:{len(output):03}", position=_normal((round(x), round(y)), width, height), kind=CrossingKind.CONNECTED_JUNCTION, degree=local_degree, confidence=round(min(0.82, 0.38 + local_degree * 0.11), 3)))
    return output


def _intersection(a1, a2, b1, b2) -> tuple[float, float] | None:
    x1, y1, x2, y2 = *a1, *a2
    x3, y3, x4, y4 = *b1, *b2
    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denominator) < 1e-9:
        return None
    px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denominator
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denominator
    def inside(point, left, right):
        return min(left[0], right[0]) - 0.003 <= point[0] <= max(left[0], right[0]) + 0.003 and min(left[1], right[1]) - 0.003 <= point[1] <= max(left[1], right[1]) + 0.003
    return (px, py) if inside((px, py), a1, a2) and inside((px, py), b1, b2) else None


def classify_crossings(conductors: list[ConductorEvidence], junctions: list[JunctionEvidence]) -> list[JunctionEvidence]:
    output = list(junctions)
    for left, right in combinations(conductors, 2):
        point = _intersection(left.polyline[0], left.polyline[-1], right.polyline[0], right.polyline[-1])
        if point is None:
            continue
        if any(np.hypot(point[0] - item.position[0], point[1] - item.position[1]) < 0.012 for item in junctions):
            continue
        if any(np.hypot(point[0] - item.position[0], point[1] - item.position[1]) < 0.008 for item in output):
            continue
        left_endpoint = min(np.hypot(point[0] - x, point[1] - y) for x, y in (left.polyline[0], left.polyline[-1])) < 0.006
        right_endpoint = min(np.hypot(point[0] - x, point[1] - y) for x, y in (right.polyline[0], right.polyline[-1])) < 0.006
        # A T has one terminating branch meeting a continuing path. This differs
        # from a bare X, which stays ambiguous without an explicit dot.
        t_intersection = left_endpoint ^ right_endpoint
        output.append(JunctionEvidence(id=f"crossing:{len(output):03}", position=(round(point[0], 6), round(point[1], 6)), kind=CrossingKind.CONNECTED_JUNCTION if t_intersection else CrossingKind.AMBIGUOUS_CROSSING, degree=3 if t_intersection else 4, confidence=0.64 if t_intersection else 0.42, provenance="t_endpoint_intersection" if t_intersection else "line_intersection", review_status="unreviewed" if t_intersection else "pending"))
    return output
