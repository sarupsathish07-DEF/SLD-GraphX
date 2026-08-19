# Limitations

Milestone 1 is a local ingestion and deterministic preprocessing workspace. It does not detect electrical symbols, run OCR, associate text, reconstruct conductors or junctions, create a graph from an uploaded image, parse DXF, accept correction edits, export project graph data, or run power-flow/fault/IEC-compliance calculations.

The Graph Explorer is a deterministic SLDForge fixture; it is not inferred from user uploads. SLDForge output is controlled synthetic ground truth, not a utility drawing corpus or a claim of field performance. PDF pages are rendered and preprocessed independently, but the current UI selects the produced artifact page through persisted metadata rather than offering complete multi-page page controls.

Automated browser screenshot execution remains partial in this environment: the repository-local Playwright command launches but does not attach/complete within a bounded run. The E2E specification is retained; no visual pass is claimed from it.
