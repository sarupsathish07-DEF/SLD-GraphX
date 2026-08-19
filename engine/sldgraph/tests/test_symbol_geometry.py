from engine.sldgraph.symbols.geometry import iou, nms, tile_origins


def test_tile_origins_cover_both_image_edges() -> None:
    origins = tile_origins(1500, 1100, 800, 96)
    assert (0, 0) in origins
    assert (700, 300) in origins


def test_iou_and_class_aware_nms() -> None:
    assert iou((0, 0, 1, 1), (0.5, 0.5, 1, 1)) == 0.25
    detections = [
        {"predicted_class": "circuit_breaker", "confidence": 0.9, "bbox_normalized": [0, 0, 0.5, 0.5]},
        {"predicted_class": "circuit_breaker", "confidence": 0.8, "bbox_normalized": [0.02, 0.02, 0.52, 0.52]},
        {"predicted_class": "disconnector", "confidence": 0.7, "bbox_normalized": [0.02, 0.02, 0.52, 0.52]},
    ]
    kept = nms(detections, threshold=0.45)
    assert [item["predicted_class"] for item in kept] == ["circuit_breaker", "disconnector"]
