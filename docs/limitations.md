# Limitations

## Milestone 5 source/feeder boundaries

M5 performs graph connectivity reasoning only. It does not calculate power flow, voltage drop, fault current, protection coordination, electrical energization, or IEC compliance. Source/feeder assignments are only as strong as persisted M4 topology; a broken graph returns unresolved paths rather than guesses. `source-feeder-v1` measures canonical SLDForge graph reasoning, not end-to-end perception. The unseen style-D full-pipeline smoke still recovers 3/5 truth edges and produces source candidates but no feeder record. No legally verified real utility SLD corpus, field validation, SCADA validation, or GIS validation is available.

Milestone 2 is a local ingestion, preprocessing, and OCR/text-review workspace. It does not detect electrical symbols, reconstruct conductors or junctions, create a graph from an uploaded image, parse DXF, export project graph data, or run power-flow/fault/IEC-compliance calculations.

PaddleOCR is evaluated on a small controlled SLDForge benchmark, not utility drawings. Full-page OCR is implemented and text-orientation classification is delegated to the selected local engine; high-resolution tiled OCR is an interface/configuration extension reserved for measured follow-up. Raster uploads deliberately remain text-to-equipment UNASSIGNED until a detector supplies real candidate geometry. Ground-truth association metrics apply only to controlled SLDForge fixtures. OCR model preparation needs a connected one-time download; after the explicit project-local model store is prepared, the worker uses local paths and has no cloud fallback.

The Graph Explorer is a deterministic SLDForge fixture; it is not inferred from user uploads. SLDForge output is controlled synthetic ground truth, not a utility drawing corpus or a claim of field performance. PDF pages are rendered and preprocessed independently, but the current UI selects the produced artifact page through persisted metadata rather than offering complete multi-page page controls.

Automated browser screenshot execution remains partial in this environment: the repository-local Playwright command launches but does not attach/complete within a bounded run. The E2E specification is retained; no visual pass is claimed from it.

## Milestone 3 symbol-intelligence boundaries

Milestone 3 is a local OCR/text-review and visual symbol-evidence workspace. It now detects bounded P0 component candidates, but it does not reconstruct conductors, junctions, or terminals; derive an electrical graph from an uploaded image; parse DXF; export an uploaded-drawing graph; or run power-flow, fault, or IEC-compliance calculations. Text-to-symbol association uses nearby geometry plus explicit semantic rules and is reviewable; it is not a connection assertion.

Symbol-v1 is wholly controlled synthetic. The recorded detector run achieved 77.78% in-style and 63.33% unseen-style component semantic match rate at IoU 0.5. A brightness degradation condition produced 0.0 on its one parent drawing. No legally verified public/real SLD microset is registered; no real-world validation or generalization claim is made. The current worker starts per request, uses OpenCV/scikit-learn rather than an ONNX/OpenVINO package, and busbar is a deterministic geometry rule. Candidate confidence must remain subject to engineering review.

## Milestone 4 physical-topology boundaries

M4 reconstructs only an undirected, image-derived physical candidate graph. It does not identify sources or feeders, calculate exact source-to-feeder paths, apply switch states, infer energized/de-energized connectivity, parse DXF/vector evidence, export an uploaded-drawing graph, simulate power flow/faults, or claim IEC compliance. Crossing geometry without a compact dark junction dot remains ambiguous until an engineer decides it. Masked gap bridges remain pending review and are never auto-verified.

Topology-v1 is controlled synthetic, not a utility-drawing evaluation. The frozen in-style test reports edge precision 0.9623, recall 0.4722, F1 0.6335, critical-edge recall 0.5306, and physical-reachability accuracy 0.3677. The unseen style-D holdout reports F1 0.5200 and reachability 0.2862; its baseline F1 (0.5490) is higher than the current method. Missed conductor and terminal/symbol mapping errors dominate. Brightness degradation on its one parent drawing yielded no symbols and F1 0.0. No real SLD corpus or human-reviewed field validation has run. These metrics are useful regression evidence, not readiness or generalization claims.

## Milestone 4R repair boundaries

M4R raises controlled-synthetic test F1 to 0.9000 and style-D F1 to 0.8065, but this is still not utility-drawing validation. Style-D reachability is 0.5529, below the 0.70 engineering target. Frozen diagnostics retain 18 terminal-distance misses and 11 upstream symbol-mapping misses. The repaired brightness result is one controlled parent condition, not a claim of illumination robustness. Source/feeder semantics, switch-state reasoning, vector/DXF evidence, export, and electrical simulation remain unimplemented.
