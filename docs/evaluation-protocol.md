# Evaluation protocol

Milestone 1 validates document integrity, persistence, inspection, deterministic rendering/preprocessing, artifact retrieval, and restart recovery. It does not report model-quality metrics because no perception model is implemented.

Future evaluation must separately measure symbol detection, OCR/normalization, text association, edge connectivity, source assignment, and exact source-to-feeder paths against held-out SLDForge manifests. Controlled degradations must retain their configuration and seed. Do not publish metrics until outputs and ground truth comparisons are stored.
