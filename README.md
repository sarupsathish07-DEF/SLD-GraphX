# SLDGraph-X

Explainable Electrical SLD Intelligence Platform for RMKECIHS93: Source & Feeder Extraction.

SLDGraph-X is being built to turn controlled electrical SLD inputs into an attributed graph, source-to-feeder paths, reviewable topology issues, and structured exports. Bootstrap currently verifies only the deterministic graph-to-SVG/UI loop; JSON/CSV export endpoints are not implemented yet.

## Bootstrap demo

```powershell
.\scripts\bootstrap.ps1
.\scripts\dev.ps1
```

Open `http://127.0.0.1:5173`. The bootstrap workspace shows one deterministic radial fixture as both a clean SVG and an interactive topology graph. The backend health endpoint is `http://127.0.0.1:8000/api/health`.

The selected project environment is `.venv-sldgraphx` (Python 3.10).

## Status

Bootstrap implements the canonical graph contract, SQLite initialization, deterministic SLDForge radial fixture, SVG reconstruction, source-to-feeder reasoning, and the first UI shell. Raster/CAD perception, OCR, correction persistence, and evaluation are subsequent milestones; see [limitations](docs/limitations.md).
