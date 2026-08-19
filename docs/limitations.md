# Limitations

Milestone 2 is a local ingestion, preprocessing, and OCR/text-review workspace. It does not detect electrical symbols, reconstruct conductors or junctions, create a graph from an uploaded image, parse DXF, export project graph data, or run power-flow/fault/IEC-compliance calculations.

PaddleOCR is evaluated on a small controlled SLDForge benchmark, not utility drawings. Full-page OCR is implemented and text-orientation classification is delegated to the selected local engine; high-resolution tiled OCR is an interface/configuration extension reserved for measured follow-up. Raster uploads deliberately remain text-to-equipment UNASSIGNED until a detector supplies real candidate geometry. Ground-truth association metrics apply only to controlled SLDForge fixtures. OCR model preparation needs a connected one-time download; after the explicit project-local model store is prepared, the worker uses local paths and has no cloud fallback.

The Graph Explorer is a deterministic SLDForge fixture; it is not inferred from user uploads. SLDForge output is controlled synthetic ground truth, not a utility drawing corpus or a claim of field performance. PDF pages are rendered and preprocessed independently, but the current UI selects the produced artifact page through persisted metadata rather than offering complete multi-page page controls.

Automated browser screenshot execution remains partial in this environment: the repository-local Playwright command launches but does not attach/complete within a bounded run. The E2E specification is retained; no visual pass is claimed from it.

## Milestone 3 symbol-intelligence boundaries

Milestone 3 is a local OCR/text-review and visual symbol-evidence workspace. It now detects bounded P0 component candidates, but it does not reconstruct conductors, junctions, or terminals; derive an electrical graph from an uploaded image; parse DXF; export an uploaded-drawing graph; or run power-flow, fault, or IEC-compliance calculations. Text-to-symbol association uses nearby geometry plus explicit semantic rules and is reviewable; it is not a connection assertion.

Symbol-v1 is wholly controlled synthetic. The recorded detector run achieved 77.78% in-style and 63.33% unseen-style component semantic match rate at IoU 0.5. A brightness degradation condition produced 0.0 on its one parent drawing. No legally verified public/real SLD microset is registered; no real-world validation or generalization claim is made. The current worker starts per request, uses OpenCV/scikit-learn rather than an ONNX/OpenVINO package, and busbar is a deterministic geometry rule. Candidate confidence must remain subject to engineering review.
