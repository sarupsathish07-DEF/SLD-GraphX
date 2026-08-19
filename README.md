# SLDGraph-X

Local-first electrical SLD intelligence for RMKECIHS93. Milestone 3 adds local, reviewable electrical-symbol evidence to the existing OCR path: PNG/JPEG/PDF pages can be recognized through isolated workers, persisted with confidence/provenance, associated to nearby text with transparent rules, and corrected in the engineering workspace. It does **not** claim conductor reconstruction or graph extraction from uploaded drawings.

## Run locally

```powershell
.\scripts\bootstrap.ps1
.\scripts\dev.ps1
```

Open `http://127.0.0.1:5173`. The API is at `http://127.0.0.1:8000`; it uses the project-local `.venv-sldgraphx` Python 3.10 environment and SQLite/local controlled storage under `var/`.

## Local OCR setup

The core backend intentionally has no Paddle dependencies. Prepare its separate local worker and project-local model store once while connected:

```powershell
.\scripts\bootstrap_ocr.ps1
```

Then OCR runs only with explicit model paths under `models/ocr/paddle/`; it has no cloud fallback. Verify the six-label smoke image with `.\.venv-sldgraphx\Scripts\python.exe scripts\ocr_smoke.py`.

## Milestone 2 workflow

Create Project → Import PDF/PNG/JPEG → inspect stored document evidence → Analyze Drawing → preprocessing → local OCR → normalization and semantic typing → Text layer/search/inspector → review correction → reopen after restart.

Artifacts are source reference, display render, analysis render, grayscale, contrast, binary, line emphasis, and OCR JSON. Deskew is produced only when the conservative skew estimate crosses its configured threshold.

## Local symbol detector setup

The electrical-symbol runtime is isolated from both the core API and OCR worker. Bootstrap creates separate training and deployment environments, regenerates the deterministic SLDForge corpus, trains the project-owned HOG + calibrated linear-SVM detector, and runs a real local smoke:

```powershell
.\scripts\bootstrap_detector.ps1
```

The detector supports the bounded P0 vocabulary: power transformer, circuit breaker, disconnector, current transformer, potential transformer, busbar, feeder terminal, load, energy source, and bus coupler. It emits candidate boxes, confidence, tile origin, engine/model provenance, review state, and text-association evidence. Busbar is deterministic geometry, not a learned classifier. See [symbol taxonomy](docs/symbol-taxonomy.md), [training/runtime](docs/symbol-detector-training.md), [evaluation protocol](docs/symbol-evaluation.md), and the [Milestone 3 receipt](docs/milestone-3-receipt.md).

## SLDForge

`sldforge` is graph-first controlled synthetic data for development. It has deterministic radial, dual-transformer, sectionalized-bus, bus-coupler, normally-open alternate-supply, and ring fixtures, each with graph, SVG, PNG, and ground-truth manifest generation. Generate the ignored development corpus with:

```powershell
.\.venv-sldgraphx\Scripts\python.exe scripts\generate_sldforge_dev.py
```

See the milestone receipts and [limitations](docs/limitations.md) for evidence and boundaries.
