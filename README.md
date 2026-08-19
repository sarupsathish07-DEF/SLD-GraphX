# SLDGraph-X

Local-first electrical SLD intelligence for RMKECIHS93. Milestone 1 is a working document-engineering foundation: it creates persistent projects, accepts PNG/JPEG/PDF drawings, inspects and preprocesses them locally, and opens persisted drawing artifacts in an engineering workspace. It does **not** yet claim symbol detection, OCR, conductor reconstruction, or graph extraction from uploaded drawings.

## Run locally

```powershell
.\scripts\bootstrap.ps1
.\scripts\dev.ps1
```

Open `http://127.0.0.1:5173`. The API is at `http://127.0.0.1:8000`; it uses the project-local `.venv-sldgraphx` Python 3.10 environment and SQLite/local controlled storage under `var/`.

## Milestone 1 workflow

Create Project → Import PDF/PNG/JPEG → inspect stored document evidence → Analyze Drawing → persisted preprocessing artifacts → Intelligence Workspace → reopen after restart.

Artifacts are source reference, display render, analysis render, grayscale, contrast, binary, and line emphasis. Deskew is produced only when the conservative skew estimate crosses its configured threshold.

## SLDForge

`sldforge` is graph-first controlled synthetic data for development. It has deterministic radial, dual-transformer, sectionalized-bus, bus-coupler, normally-open alternate-supply, and ring fixtures, each with graph, SVG, PNG, and ground-truth manifest generation. Generate the ignored development corpus with:

```powershell
.\.venv-sldgraphx\Scripts\python.exe scripts\generate_sldforge_dev.py
```

See [Milestone 1 receipt](docs/milestone-1-receipt.md) and [limitations](docs/limitations.md) for evidence and boundaries.
