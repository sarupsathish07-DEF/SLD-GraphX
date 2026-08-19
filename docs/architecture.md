# Architecture

`apps/web` is a React/TypeScript client. `services/api` owns REST, SQLite persistence, controlled upload/artifact storage, background preprocessing, and the OCR subprocess supervisor. `engine/sldgraph` owns canonical models, graph reasoning, inspection, text intelligence, validation, and exporters. `sldforge` creates graph-first controlled synthetic drawings and ground truth.

The stable core Python environment communicates by JSON-lines stdin/stdout with `scripts/ocr_worker.py` in `.venv-sldgraphx-ocr-clean`. The worker uses explicit model paths under `models/ocr/paddle`, returns normalized page geometry, and cannot expose worker paths through the API. Worker unavailability, timeout, crash, or malformed output fails only the `ocr` analysis stage; `/api/health` still reports the core as healthy.

OCR regions become immutable `TextEvidence` records with separate OCR, normalization, and semantic confidence plus `TextReviewAction` audit records. Raster uploads remain unassigned until a future detector exists. The association engine is exercised only against controlled SLDForge ground-truth geometry in this milestone. Later perception branches converge on the canonical `ElectricalGraph`.
