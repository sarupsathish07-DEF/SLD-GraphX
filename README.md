# SLDGraph-X

Local-first electrical SLD intelligence for RMKECIHS93. Milestone 4 adds local, reviewable physical-topology reconstruction to the existing OCR and symbol-evidence path: PNG/JPEG/PDF pages yield mask-aware conductor traces, bus candidates, explicit junction/crossover evidence, symbol terminals, scored physical edges, and a synchronized review graph. It does **not** claim source/feeder reasoning, switch-state semantics, DXF parsing, power flow, or IEC compliance.

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

## Milestone 4 workflow

Create Project → Import PDF/PNG/JPEG → inspect stored document evidence → Analyze Drawing → preprocessing → local OCR → symbol evidence → protected raster topology reconstruction → terminal-aware physical graph → original-SLD/graph review → correction/audit → reopen after restart.

Artifacts are source reference, display render, analysis render, grayscale, contrast, binary, line emphasis, OCR JSON, topology JSON, and topology debug masks. Deskew is produced only when the conservative skew estimate crosses its configured threshold.

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

## Physical topology reconstruction

M4 uses protected symbol/text masks, directional morphology, line tracing, Zhang-Suen skeletonization, compact-dot junction evidence, terminal templates with resolution-scaled snapping, scored candidate edges, deterministic duplicate repair, and explicit review-only gap bridges. Physical evidence and every review action persist in SQLite. The workspace keeps the original SLD overlay and undirected terminal graph synchronized; it never presents this as power flow or source-to-feeder analysis.

The frozen controlled-synthetic topology benchmark covers radial, dual-transformer, sectionalized-bus, bus-coupler, alternate-supply, and ring scenes. Latest in-style test results are edge precision 0.9623, recall 0.4722, F1 0.6335, and physical reachability accuracy 0.3677. Style-holdout F1 is 0.5200. These are low-recall early-prototype results, not a real-drawing claim. See [topology reconstruction](docs/topology-reconstruction.md), [evaluation protocol](docs/evaluation-protocol.md), and the [Milestone 4 receipt](docs/milestone-4-receipt.md).
