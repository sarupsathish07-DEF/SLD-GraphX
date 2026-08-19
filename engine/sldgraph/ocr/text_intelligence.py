"""Deterministic engineering text parsing, classification, and association."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class TextType(str, Enum):
    EQUIPMENT_ID = "equipment_id"
    FEEDER_ID = "feeder_id"
    BUS_ID = "bus_id"
    VOLTAGE = "voltage"
    CURRENT_RATING = "current_rating"
    POWER_RATING = "power_rating"
    SWITCH_STATE = "switch_state"
    DESTINATION_LABEL = "destination_label"
    SOURCE_LABEL = "source_label"
    DESCRIPTION = "description"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class NormalizationResult:
    raw_text: str
    normalized_text: str
    confidence: float
    requires_review: bool
    evidence: str


@dataclass(frozen=True)
class SemanticResult:
    text_type: TextType
    confidence: float
    evidence: str


@dataclass(frozen=True)
class AssociationCandidate:
    entity_id: str
    entity_type: str
    bbox_normalized: tuple[float, float, float, float]


def association_score(
    text_type: TextType,
    text_bbox: tuple[float, float, float, float],
    candidate: AssociationCandidate,
) -> tuple[float, dict[str, float]]:
    """Transparent heuristic score, deliberately not presented as a learned model."""
    tx = (text_bbox[0] + text_bbox[2]) / 2
    ty = (text_bbox[1] + text_bbox[3]) / 2
    ex = (candidate.bbox_normalized[0] + candidate.bbox_normalized[2]) / 2
    ey = (candidate.bbox_normalized[1] + candidate.bbox_normalized[3]) / 2
    distance = max(0.0, 1.0 - min(1.0, ((tx - ex) ** 2 + (ty - ey) ** 2) ** 0.5 / 0.32))
    expected = {
        TextType.FEEDER_ID: "feeder",
        TextType.BUS_ID: "busbar",
        TextType.POWER_RATING: "power_transformer",
        TextType.VOLTAGE: "power_transformer",
        TextType.CURRENT_RATING: "circuit_breaker",
        TextType.EQUIPMENT_ID: candidate.entity_type,
    }
    semantic = (
        1.0
        if expected.get(text_type) == candidate.entity_type
        else (0.45 if text_type in {TextType.VOLTAGE, TextType.CURRENT_RATING} else 0.0)
    )
    alignment = 1.0 - min(1.0, abs(ty - ey) / 0.2)
    factors = {
        "distance": round(distance, 4),
        "orientation": 1.0,
        "semantic": semantic,
        "alignment": round(alignment, 4),
        "context": 0.0,
    }
    return round(0.55 * distance + 0.25 * semantic + 0.20 * alignment, 4), factors


def associate_text(
    text_type: TextType,
    text_bbox: tuple[float, float, float, float],
    candidates: list[AssociationCandidate],
) -> dict:
    scored = [
        {"entity_id": candidate.entity_id, "score": score, "factors": factors}
        for candidate in candidates
        for score, factors in [association_score(text_type, text_bbox, candidate)]
    ]
    scored.sort(key=lambda item: item["score"], reverse=True)
    selected = scored[0] if scored and scored[0]["score"] >= 0.55 else None
    return {
        "selected_entity": selected["entity_id"] if selected else None,
        "selected_score": selected["score"] if selected else 0.0,
        "candidates": scored,
    }


def _compact(text: str) -> str:
    return re.sub(r"[\s_]+", "", text.upper().strip())


def parse_voltage(text: str) -> str | None:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*K\s*V\s*", text, re.I)
    return f"{match.group(1)} kV" if match else None


def parse_current(text: str) -> str | None:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*A\s*", text, re.I)
    return f"{match.group(1)} A" if match else None


def parse_power(text: str) -> str | None:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(K|M)\s*VA\s*", text, re.I)
    return f"{match.group(1)} {match.group(2).upper()}VA" if match else None


def _parse_prefixed(text: str, prefixes: tuple[str, ...]) -> tuple[str, bool] | None:
    compact = _compact(text)
    # Avoid attempting the flexible suffix expression for arbitrary OCR prose/title text.
    if not any(compact.startswith(prefix) for prefix in prefixes):
        return None
    match = re.fullmatch(r"([A-Z]+)-?([A-Z0-9]+(?:-?[A-Z0-9]+)*)", compact)
    if not match or match.group(1) not in prefixes:
        return None
    prefix, suffix = match.groups()
    ambiguous = bool(re.search(r"[OILSB]", suffix))
    corrected = suffix
    if ambiguous and re.fullmatch(r"[OILSB0-9]+", suffix):
        corrected = suffix.translate(
            str.maketrans({"O": "0", "I": "1", "L": "1", "S": "5", "B": "8"})
        )
    return f"{prefix}-{corrected}", ambiguous


def parse_equipment_id(text: str) -> tuple[str, bool] | None:
    return _parse_prefixed(text, ("TR", "CB", "DS", "CT", "PT", "VT", "GEN", "GRID", "BC"))


def parse_feeder_id(text: str) -> tuple[str, bool] | None:
    return _parse_prefixed(text, ("FDR",))


def parse_bus_id(text: str) -> tuple[str, bool] | None:
    return _parse_prefixed(text, ("BUS",))


def parse_switch_state(text: str) -> str | None:
    value = text.strip().upper()
    return value if value in {"OPEN", "CLOSED", "N/O", "N/C"} else None


def normalize_engineering_text(raw_text: str) -> NormalizationResult:
    raw = raw_text.strip()
    for parser, evidence in (
        (parse_voltage, "voltage format"),
        (parse_current, "current format"),
        (parse_power, "power format"),
    ):
        parsed = parser(raw)
        if parsed:
            return NormalizationResult(raw, parsed, 1.0, False, evidence)
    for parser, evidence in (
        (parse_feeder_id, "feeder syntax"),
        (parse_bus_id, "bus syntax"),
        (parse_equipment_id, "equipment syntax"),
    ):
        parsed = parser(raw)
        if parsed:
            value, ambiguous = parsed
            return NormalizationResult(
                raw,
                value,
                0.62 if ambiguous else 0.98,
                ambiguous,
                f"{evidence}{'; ambiguous character candidate' if ambiguous else ''}",
            )
    return NormalizationResult(raw, raw, 1.0, False, "raw text retained")


def classify_text(text: str) -> SemanticResult:
    if parse_voltage(text):
        return SemanticResult(TextType.VOLTAGE, 0.99, "voltage parser")
    if parse_current(text):
        return SemanticResult(TextType.CURRENT_RATING, 0.99, "current parser")
    if parse_power(text):
        return SemanticResult(TextType.POWER_RATING, 0.99, "power parser")
    if parse_feeder_id(text):
        return SemanticResult(TextType.FEEDER_ID, 0.99, "feeder prefix")
    if parse_bus_id(text):
        return SemanticResult(TextType.BUS_ID, 0.99, "bus prefix")
    if parse_equipment_id(text):
        return SemanticResult(TextType.EQUIPMENT_ID, 0.98, "equipment prefix")
    if parse_switch_state(text):
        return SemanticResult(TextType.SWITCH_STATE, 0.99, "switch-state lexicon")
    return SemanticResult(TextType.UNKNOWN, 0.0, "no conservative semantic rule")


def bbox_iou(
    left: tuple[float, float, float, float], right: tuple[float, float, float, float]
) -> float:
    lx1, ly1, lx2, ly2 = left
    rx1, ry1, rx2, ry2 = right
    intersection = max(0, min(lx2, rx2) - max(lx1, rx1)) * max(0, min(ly2, ry2) - max(ly1, ry1))
    union = (lx2 - lx1) * (ly2 - ly1) + (rx2 - rx1) * (ry2 - ry1) - intersection
    return intersection / union if union else 0.0


def merge_regions(regions: list[dict]) -> list[dict]:
    """Merge only overlapping detections with exactly matching normalized text."""
    merged: list[dict] = []
    for region in sorted(regions, key=lambda item: item["confidence"], reverse=True):
        if any(
            item["normalized_text"] == region["normalized_text"]
            and bbox_iou(tuple(item["bbox_normalized"]), tuple(region["bbox_normalized"])) >= 0.55
            for item in merged
        ):
            continue
        merged.append(region)
    return merged
