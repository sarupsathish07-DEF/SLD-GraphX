# Milestone 2 receipt — local OCR and engineering text intelligence

Date: 2026-08-19

## Goal

Deliver a local, reviewable text-evidence path from an SLD page through OCR, conservative engineering interpretation, persistence, and correction. This receipt does not claim symbol recognition, raster topology, or source-to-feeder extraction.

## VERIFIED

- **Architecture and isolation:** core `.venv-sldgraphx` remains free of Paddle packages. A JSON-lines worker in `.venv-sldgraphx-ocr-clean` uses PaddlePaddle 2.6.2 and PaddleOCR 2.7.3 with explicit project-local model folders.
- **Model readiness:** detector PP-OCRv3 English, recognizer PP-OCRv4 English, and angle classifier are stored at `models/ocr/paddle` after one-time preparation. Payloads are ignored; `models/ocr/manifest.json` tracks file SHA-256. Normal worker inference uses those explicit paths and has no cloud fallback.
- **Worker supervision:** health reports OCR separately from core health. Missing worker/models, worker crash, timeout, and malformed output are represented as a human-readable `ocr` analysis-stage failure rather than a FastAPI failure.
- **OCR evidence:** raw text, normalized candidate, semantic type, three separate confidence dimensions, normalized geometry, page/rotation, engine/model/provenance, review status, and association evidence persist in SQLite. Raw OCR is never overwritten.
- **Engineering text:** voltage/current/power, equipment/feeder/bus IDs, switch state, ambiguous character corrections, UNKNOWN, exact duplicate merging, and transparent candidate association scoring are implemented and tested. Ground-truth association is limited to SLDForge geometry; uploads stay unassigned until symbol candidates exist.
- **Review workspace:** text overlays, selection, search, provenance/confidence inspection, edit, accept/reject/unknown actions, and immutable review audit records are available through the API and React workspace.
- **Real OCR smoke:** all required generated labels were recognized exactly: `FDR-11KV-03`, `CB-07`, `TR-01`, `11 kV`, `630 A`, and `25 MVA`. The measured inference portion was 456.64 ms; this is one local smoke observation, not a throughput claim.
- **Real production path:** `scripts/ocr_pipeline_smoke.py` uploaded an SLDForge radial PNG through the API, completed all nine persisted stages, and stored 15 real local-OCR regions with `local_ocr` provenance.
- **Full-page and tiled modes:** full-page SLDForge and tiled known-label requests both ran through the same worker contract; tiled responses retain mapped tile-origin evidence and deduplicate overlapping equal-text regions.
- **Benchmark:** OCR-v1 is generated at drawing level from fixed-seed SLDForge fixtures and records clean, blur, JPEG compression, low contrast, brightness shift, small skew, and faded-line proximity independently. A completed local run reported CER 0.0, label exact match 1.0, and 681.05 ms mean OCR inference across seven drawings. Equipment-ID (28), feeder-ID (11), voltage (43), current (19), and power (9) eligible exact-match components were each 1.0. Association F1 was 1.0 only on exactly recognized controlled-ground-truth labels.

## Validation

| Check | Result |
| --- | --- |
| Core tests | `26 passed` (`.venv-sldgraphx\Scripts\python.exe -m pytest -q`) |
| Ruff | passed (`.venv-sldgraphx\Scripts\python.exe -m ruff check engine sldforge services scripts`) |
| Frontend tests | `5 passed` (`npm.cmd test` in `apps/web`) |
| Frontend lint / production build | passed (`npm.cmd run lint`; `npm.cmd run build`) |
| Isolated runtime | Paddle 2.6.2 / PaddleOCR 2.7.3 imports; `pip check` passed |
| Fresh local runtime | core health `ok`, OCR `available`, web HTTP 200 |

## PARTIAL

- Browser-driven screenshot QA could not start: the in-app browser connection failed before page inspection. No screenshot or browser interaction pass is claimed.
- The worker process is launched per page/request. The contract supports multiple JSON-lines requests and explicit local models, but a long-lived warm supervisor is not yet implemented.
- Orientation relies on PaddleOCR angle classification. Controlled crop-rotation candidates for uncertain regions are not implemented.

## NOT IMPLEMENTED

- Electrical symbol detection, real-upload text-to-symbol association, conductor/junction extraction, topology reconstruction, source/feeder inference from uploads, DXF/vector evidence, graph export for uploads, power-flow/fault analysis, or IEC-compliance claims.

## Checkpoint

The coherent Milestone 2 checkpoint is committed and pushed on `main` after this receipt's final validation. Its identity is reported by the Git handoff, rather than duplicating a self-referential commit hash here.
