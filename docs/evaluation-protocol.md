# Evaluation protocol

Milestone 1 validates document integrity, persistence, inspection, deterministic rendering/preprocessing, artifact retrieval, and restart recovery. It does not report model-quality metrics because no perception model is implemented.

Milestone 2 uses `scripts/create_ocr_benchmark.py` to make the small frozen, drawing-level `ocr-v1` SLDForge test set. `scripts/benchmark_ocr.py` records manifest hash, local engine/runtime, per-drawing OCR output, runtime, character error rate, exact match, type-specific exact match, semantic accuracy on exact recognitions, and controlled-ground-truth association precision/recall/F1. The set covers clean, blur, JPEG compression, low contrast, brightness shift, small skew, and faded-line proximity; its generated drawing payloads and results are intentionally ignored.

The association figures are explicitly limited to exactly recognized labels with SLDForge entity geometry. They do not measure real-upload association because this milestone does not create equipment detections. Future evaluation must separately measure symbol detection, broader OCR/normalization, text association, edge connectivity, source assignment, and exact source-to-feeder paths against held-out SLDForge manifests. Do not publish metrics until outputs and ground truth comparisons are stored.
