# SLDGraph-X

Local-first electrical SLD intelligence for RMKECIHS93. Milestone 5 turns persisted OCR, symbol, and physical-topology evidence into a reviewable semantic electrical graph: source candidates, feeder records, exact physical source-to-feeder paths, switch-aware connectivity scenarios, validation, topology-criticality review, reconstructed SLD, and local JSON/CSV ZIP export. It does **not** claim power-flow, fault analysis, IEC certification, DXF parsing, or field validation.

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

## Milestone 5 workflow

Create Project → Import PDF/PNG/JPEG → inspect stored document evidence → Analyze Drawing → preprocessing → local OCR → symbol evidence → protected raster topology reconstruction → terminal-aware physical graph → semantic source/feeder reasoning → validation and topology-risk review → Trace & Explain / scenario → reconstructed SLD / graph → local export → reopen after restart.

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

## Electrical source/feeder intelligence

M5 preserves the physical graph as undirected evidence and derives separate operational and semantic graph views. OPEN switching devices block operational traversal; UNKNOWN remains explicitly uncertain rather than becoming CLOSED. Each path records equipment and connection IDs, source bus, switching devices, geometric-mean confidence, weakest edge, and uncertainty flags. A physical break produces an unresolved source, never an invented assignment.

Review risk is `uncertainty × configured topology impact`. For each uncertain connection the engine compares with/without-edge feeder reachability, source assignment, affected nodes, bridge status, and component count. Engineer connection/crossing/class/text/switch updates recompute semantic graph views only—OCR, detector, and raster topology are not rerun. See [source-feeder reasoning](docs/source-feeder-reasoning.md) and the [Milestone 5 receipt](docs/milestone-5-receipt.md).

## Physical topology reconstruction

M4 uses protected symbol/text masks, directional morphology, line tracing, Zhang-Suen skeletonization, compact-dot junction evidence, terminal templates with resolution-scaled snapping, scored candidate edges, deterministic duplicate repair, and explicit review-only gap bridges. Physical evidence and every review action persist in SQLite. The workspace keeps the original SLD overlay and undirected terminal graph synchronized; it never presents this as power flow or source-to-feeder analysis.

The frozen controlled-synthetic topology benchmark covers radial, dual-transformer, sectionalized-bus, bus-coupler, alternate-supply, and ring scenes. M4R records test edge precision 0.9783, recall 0.8333, F1 0.9000, and style-holdout F1 0.8065; holdout reachability remains 0.5529. M5 semantic figures are controlled canonical-graph evidence only, not end-to-end perception or real-drawing claims. See [topology reconstruction](docs/topology-reconstruction.md), [evaluation protocol](docs/evaluation-protocol.md), and the [Milestone 4R receipt](docs/milestone-4r-receipt.md).
