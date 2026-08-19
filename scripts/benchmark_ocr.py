"""Evaluate the isolated local OCR worker against frozen SLDForge OCR-v1."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.sldgraph.ocr.text_intelligence import (
    AssociationCandidate,
    TextType,
    associate_text,
    classify_text,
    normalize_engineering_text,
)
from services.api.app.services.ocr_worker import recognize


def _distance(left: str, right: str) -> int:
    """Small dependency-free Levenshtein distance for the frozen benchmark."""
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, 1):
        current = [left_index]
        for right_index, right_char in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _f1(true_positive: int, false_positive: int, false_negative: int) -> dict:
    precision = _rate(true_positive, true_positive + false_positive)
    recall = _rate(true_positive, true_positive + false_negative)
    return {
        "precision": precision,
        "recall": recall,
        "f1": round(2 * precision * recall / (precision + recall), 4)
        if precision is not None and recall is not None and precision + recall
        else None,
    }


def _canonical(value: str) -> str:
    return normalize_engineering_text(value).normalized_text.upper()


def _label_metrics(expected: list[dict], observed: list[str]) -> tuple[dict, list[dict]]:
    unmatched = list(observed)
    matched = []
    character_errors = 0
    character_total = 0
    for item in expected:
        target = _canonical(item["raw"])
        best_index, best_distance = None, None
        for index, value in enumerate(unmatched):
            distance = _distance(target, _canonical(value))
            if best_distance is None or distance < best_distance:
                best_index, best_distance = index, distance
        character_errors += best_distance if best_distance is not None else len(target)
        character_total += len(target)
        if best_index is not None and best_distance == 0:
            matched.append(item)
            unmatched.pop(best_index)
    true_positive = len(matched)
    return (
        {
            "expected": len(expected),
            "observed": len(observed),
            "exact_match": _rate(true_positive, len(expected)),
            "character_error_rate": _rate(character_errors, character_total),
            "detection": _f1(true_positive, len(unmatched), len(expected) - true_positive),
        },
        matched,
    )


def _typed_exact(expected: list[dict], matched: list[dict]) -> dict:
    matches = {item["linked_entity"] for item in matched}
    result = {}
    for text_type, label in (
        ("equipment_id", "equipment_id_exact_match"),
        ("feeder_id", "feeder_id_exact_match"),
        ("voltage", "voltage_exact_match"),
        ("current_rating", "current_rating_exact_match"),
        ("power_rating", "power_rating_exact_match"),
    ):
        eligible = [item for item in expected if item["semantic_type"] == text_type]
        result[label] = {
            "value": _rate(
                sum(item["linked_entity"] in matches for item in eligible), len(eligible)
            ),
            "eligible": len(eligible),
        }
    return result


def _rating_exact(expected: list[dict], observed: list[str]) -> dict:
    patterns = {
        "voltage": r"(?<![0-9/])(\d+(?:\.\d+)?)\s*k\s*v",
        "current_rating": r"(\d+(?:\.\d+)?)\s*a\b",
        "power_rating": r"(\d+(?:\.\d+)?)\s*([km])\s*va",
    }
    labels = {
        "voltage": "voltage_exact_match",
        "current_rating": "current_rating_exact_match",
        "power_rating": "power_rating_exact_match",
    }
    result = {}
    for semantic_type, pattern in patterns.items():
        expected_values = [
            _canonical(item["raw"]) for item in expected if item["semantic_type"] == semantic_type
        ]
        observed_values = []
        for value in observed:
            for groups in re.findall(pattern, value, re.I):
                groups = (groups,) if isinstance(groups, str) else groups
                if semantic_type == "power_rating":
                    observed_values.append(_canonical(f"{groups[0]} {groups[1].upper()}VA"))
                elif semantic_type == "voltage":
                    observed_values.append(_canonical(f"{groups[0]} kV"))
                else:
                    observed_values.append(_canonical(f"{groups[0]} A"))
        matched = sum((Counter(expected_values) & Counter(observed_values)).values())
        result[labels[semantic_type]] = {
            "value": _rate(matched, len(expected_values)),
            "eligible": len(expected_values),
            "scope": "domain-parser component extracted from OCR line",
        }
    return result


def _semantic_and_association(expected: list[dict], matched: list[dict]) -> tuple[dict, dict]:
    semantic_correct = sum(
        classify_text(item["normalized"]).text_type.value == item["semantic_type"]
        for item in matched
    )
    candidates = [
        AssociationCandidate(
            entity_id=item["linked_entity"],
            entity_type=item["linked_entity_type"],
            bbox_normalized=tuple(item["bbox"]),
        )
        for item in expected
    ]
    association_correct = 0
    for item in matched:
        chosen = associate_text(TextType(item["semantic_type"]), tuple(item["bbox"]), candidates)
        association_correct += chosen["selected_entity"] == item["linked_entity"]
    return (
        {
            "accuracy": _rate(semantic_correct, len(matched)),
            "eligible_exact_recognitions": len(matched),
            "scope": "exactly recognized ground-truth labels only",
        },
        {
            **_f1(
                association_correct,
                len(matched) - association_correct,
                len(matched) - association_correct,
            ),
            "eligible_exact_recognitions": len(matched),
            "scope": "controlled SLDForge ground-truth geometry only",
        },
    )


def _weighted_metric(results: list[dict], field: str) -> float | None:
    expected_count = sum(len(result["expected"]) for result in results)
    if not expected_count:
        return None
    return round(
        sum((result["metrics"][field] or 0) * len(result["expected"]) for result in results)
        / expected_count,
        4,
    )


def _aggregate_type_exact(results: list[dict], label: str) -> dict:
    eligible = sum(result["metrics"][label]["eligible"] for result in results)
    matched = sum(
        (result["metrics"][label]["value"] or 0) * result["metrics"][label]["eligible"]
        for result in results
    )
    return {"value": _rate(round(matched), eligible), "eligible": eligible}


def main() -> None:
    manifest_path = Path("data/benchmark/ocr-v1/manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results, grouped = [], defaultdict(list)
    for entry in manifest["entries"]:
        response = recognize(manifest_path.parent / entry["drawing"], 1)
        observed = [region.text for region in response.regions]
        metrics, matched = _label_metrics(entry["text_items"], observed)
        semantic, association = _semantic_and_association(entry["text_items"], matched)
        result = {
            "drawing": entry["drawing"],
            "topology": entry["topology"],
            "degradation": entry["degradation"],
            "elapsed_ms": response.elapsed_ms,
            "metrics": {
                **metrics,
                **_typed_exact(entry["text_items"], matched),
                **_rating_exact(entry.get("rating_items", []), observed),
                "semantic": semantic,
                "association": association,
            },
            "expected": [item["raw"] for item in entry["text_items"]],
            "observed": observed,
        }
        results.append(result)
        grouped[entry["degradation"]].append(result)
        print(
            f"completed {entry['drawing']} in {response.elapsed_ms:.2f} ms "
            f"({metrics['exact_match']!s} exact)",
            flush=True,
        )
    aggregate = {
        "mean_character_error_rate": _weighted_metric(results, "character_error_rate"),
        "mean_exact_match": _weighted_metric(results, "exact_match"),
        "mean_runtime_ms": round(sum(result["elapsed_ms"] for result in results) / len(results), 2),
        "equipment_id_exact_match": _aggregate_type_exact(results, "equipment_id_exact_match"),
        "feeder_id_exact_match": _aggregate_type_exact(results, "feeder_id_exact_match"),
        "voltage_exact_match": _aggregate_type_exact(results, "voltage_exact_match"),
        "current_rating_exact_match": _aggregate_type_exact(results, "current_rating_exact_match"),
        "power_rating_exact_match": _aggregate_type_exact(results, "power_rating_exact_match"),
    }
    by_degradation = {
        name: {
            "drawings": len(items),
            "character_error_rate": _weighted_metric(items, "character_error_rate"),
            "exact_match": _weighted_metric(items, "exact_match"),
            "mean_runtime_ms": round(sum(item["elapsed_ms"] for item in items) / len(items), 2),
        }
        for name, items in grouped.items()
    }
    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "engine": "paddleocr",
        "platform": platform.platform(),
        "dataset_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "configuration": {"mode": "full_page", "model": "PP-OCRv3-en"},
        "aggregate": aggregate,
        "by_degradation": by_degradation,
        "per_drawing": results,
    }
    output = Path("artifacts/experiments/ocr-v1")
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
