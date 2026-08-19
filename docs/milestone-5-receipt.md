# Milestone 5 receipt — source / feeder electrical intelligence

Date: 2026-08-19

## Delivered scope

- Local NetworkX reasoning derives physical, operational, and semantic electrical views from persisted M4 evidence without mutating perception results.
- Persisted source candidates, feeder records, exact source-to-feeder equipment/connection paths, switch states, validation findings, topology-criticality review issues, scenarios, and export receipts.
- OPEN switching devices block traversal; UNKNOWN is retained as an explicit path warning. No unresolved physical path receives an invented source assignment.
- Workspace supports synchronized original/reconstructed/graph views; trace search; validation; ranked review and inspect/accept/reject; temporary switch scenarios and saved engineer switch state; and local JSON/CSV ZIP export. Text, class, physical-edge, crossing, and switch corrections recompute only semantic views.
- SLDForge exposes M5 source assignments and exact feeder paths in its graph-first manifest.

## Controlled semantic benchmark

Command: `.\\.venv-sldgraphx\\Scripts\\python.exe scripts\\benchmark_source_feeder.py`

- Frozen `source-feeder-v1`: six graph-first SLDForge fixtures — radial, dual transformer, sectionalized bus, bus coupler, alternate supply, and ring.
- Source precision / recall / F1: 1.0000 / 1.0000 / 1.0000.
- Feeder precision / recall: 1.0000 / 1.0000.
- Exact source assignment and source-to-feeder equipment/edge path: 1.0000 / 1.0000.
- Controlled switch-state reachability: 1.0000. Six controlled with/without-edge criticality checks executed.
- Comparator: class plus unweighted physical shortest path. It ties on these canonical fixtures but intentionally cannot represent switch state, confidence, ambiguity, or transformer-secondary boundary behavior. This benchmark measures deterministic semantics conditional on canonical graph truth; it is not end-to-end perception or real-data validation.

## Real pipeline smoke

Command: `.\\.venv-sldgraphx\\Scripts\\python.exe scripts\\source_feeder_pipeline_smoke.py`

- The real API upload → preprocessing → OCR → local symbols → physical topology → persisted semantic reasoning → ZIP export → fresh-app reload path completed.
- On the unseen style-D radial drawing: 5 symbols, 14 conductors, 1 bus, 5 junctions, 3 mapped physical edges of 5 truth edges, 2 source candidates, 0 persisted feeder records, 0 resolved paths, and 3 review issues. ZIP export was 5,917 bytes and reloaded physical/semantic evidence persisted.
- This is an expected limitation carried from M4R: missing topology evidence prevents an exact feeder path, so the product returns no feeder/source assignment rather than guessing.

## Regression evidence

- `ruff check engine services sldforge scripts`: pass.
- `pytest -q`: 46 passed.
- `npm.cmd test`: 8 passed.
- `npm.cmd run lint`: pass.
- `npm.cmd run build`: pass.

## Explicit boundaries

M5 does not perform power flow, voltage drop, fault studies, protection coordination, electrical energization, IEC certification, SCADA/GIS validation, DXF parsing, or field validation. No legally verified real SLD evaluation corpus is registered. See [limitations](limitations.md), [evaluation protocol](evaluation-protocol.md), and [source-feeder reasoning](source-feeder-reasoning.md).
