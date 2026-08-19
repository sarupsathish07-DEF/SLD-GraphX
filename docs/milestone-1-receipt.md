# Milestone 1 receipt — raster SLD ingestion and engineering workspace

Date: 2026-08-19

## Implemented

- Persistent SQLite Project, Drawing, AnalysisRun, AnalysisStage, and Artifact records.
- Local PNG/JPEG/PDF upload with suffix allowlist, filename sanitization, streaming size limit, decode validation, SHA-256, and controlled local storage.
- PDF/raster inspection evidence: classification, page count, dimensions, native text/vector/image evidence, and recommended route.
- Persisted asynchronous stages for document inspection, rendering, and preprocessing; failures are recorded with stage and message.
- Per-page source reference, display, analysis, grayscale, contrast, binary, line-emphasis, and conditionally-produced deskew artifacts. Artifact records contain opaque ID, MIME type, SHA-256, safe relative path, page, dimensions, and generation configuration.
- Command Center, project creation dialog, Import Studio drop/file flow, inspection, honest analysis progress, persisted history reopening, drawing workspace, pan/zoom/fit controls, normalized geometry utilities, layer architecture, artifact switcher, and drawing inspector.
- Graph-first SLDForge radial, dual-transformer, sectionalized-bus, bus-coupler, normally-open alternate-supply, and ring fixtures; SVG/PNG/manifest output plus deterministic degradation smoke output.
- API loop test from SLDForge PNG through the real upload/analysis path.

## Validated

| Check | Evidence/result |
| --- | --- |
| Backend suite | `.venv-sldgraphx\Scripts\python.exe -m pytest -q` — 16 passed |
| Static analysis | `.venv-sldgraphx\Scripts\python.exe -m ruff check engine sldforge services scripts` — passed |
| Frontend unit tests | `npm.cmd run test -- --run --testTimeout=5000 --reporter=verbose` — 4 passed |
| Frontend lint/build | `npm.cmd run lint` and `npm.cmd run build` — passed |
| Local startup | `scripts\dev.ps1`; health returned `status: ok`, `mode: local`; web returned HTTP 200 |
| Restart persistence | API test creates, analyzes, closes/reopens app lifespan, reads history, and retrieves artifact — passed |
| Real loop | API test uploads `render_png(build_radial_fixture())`, persists run, and completes — passed |

## Measured local run

Measured through the live API using `data/synthetic/dev/radial.png` (SLDForge), not a mocked pipeline:

| Measurement | Result |
| --- | --- |
| Sample input | 24,133 bytes, 1600 × 900 PNG |
| Upload and validation | 70.8 ms observed |
| Full queued-to-complete analysis | 681.8 ms observed, including 100 ms polling interval |
| Display / analysis dimensions | 1600 × 900 / 1600 × 900 |
| Source/display/analysis artifact size | 24,133 bytes each |
| Grayscale / contrast / binary / line-emphasis size | 11,531 / 22,874 / 6,642 / 3,055 bytes |

These measurements are local, single-sample observations and are not throughput or model-performance claims.

## Partial

- The repository-local Playwright Milestone 1 flow and screenshot specification are implemented. In this environment `npx playwright test --reporter=line` launched but did not attach/complete during the bounded attempt, so no automated visual screenshot pass is claimed and no screenshots were generated.
- PDF processing is per page and artifacts include page metadata. The current workspace defaults to the persisted display artifact and does not yet provide complete document page-navigation controls.

## Not implemented

- Symbol detection, OCR, text association, conductor/junction extraction, topology reconstruction from upload evidence, DXF, manual correction, graph export for uploads, power-flow/fault analysis, and IEC compliance claims.
