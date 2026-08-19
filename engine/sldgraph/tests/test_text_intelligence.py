from engine.sldgraph.ocr.text_intelligence import (
    AssociationCandidate,
    TextType,
    associate_text,
    classify_text,
    merge_regions,
    normalize_engineering_text,
)


def test_engineering_normalization_preserves_raw_and_surfaces_ambiguity() -> None:
    assert normalize_engineering_text("11KV").normalized_text == "11 kV"
    assert normalize_engineering_text("630A").normalized_text == "630 A"
    assert normalize_engineering_text("25MVA").normalized_text == "25 MVA"
    result = normalize_engineering_text("CB-O7")
    assert result.raw_text == "CB-O7" and result.normalized_text == "CB-07"
    assert result.requires_review and result.confidence < 1


def test_semantic_classification_is_conservative() -> None:
    assert classify_text("FDR-11KV-03").text_type is TextType.FEEDER_ID
    assert classify_text("BUS-A").text_type is TextType.BUS_ID
    assert classify_text("unstructured note").text_type is TextType.UNKNOWN


def test_unrelated_ocr_title_does_not_enter_identifier_suffix_matching() -> None:
    title = "SLDFORGE / DUAL TRANSFORMER 01 — LOCAL DEVELOPMENT ONLY"
    assert classify_text(title).text_type is TextType.UNKNOWN


def test_duplicate_merge_does_not_merge_adjacent_labels() -> None:
    regions = [
        {"normalized_text": "CB-01", "confidence": 0.8, "bbox_normalized": [0.1, 0.1, 0.2, 0.2]},
        {"normalized_text": "CB-01", "confidence": 0.9, "bbox_normalized": [0.11, 0.1, 0.21, 0.2]},
        {"normalized_text": "CB-02", "confidence": 0.9, "bbox_normalized": [0.22, 0.1, 0.32, 0.2]},
    ]
    assert [item["normalized_text"] for item in merge_regions(regions)] == ["CB-01", "CB-02"]


def test_ground_truth_candidate_association_prefers_matching_feeder() -> None:
    association = associate_text(
        TextType.FEEDER_ID,
        (0.85, 0.2, 0.95, 0.25),
        [
            AssociationCandidate("bus_a", "busbar", (0.35, 0.4, 0.5, 0.5)),
            AssociationCandidate("feeder_01", "feeder", (0.84, 0.17, 0.98, 0.30)),
        ],
    )
    assert association["selected_entity"] == "feeder_01"
