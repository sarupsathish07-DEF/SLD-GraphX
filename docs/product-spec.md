# Product specification

SLDGraph-X will convert SLD evidence into a reviewable canonical electrical graph. Milestone 1 implements the safe local document foundation: persistent projects/drawings/analysis runs, controlled storage, SHA-256, PDF/raster inspection, asynchronous persisted stages, deterministic preprocessing, and an engineering drawing workspace.

The current supported inputs are PNG, JPEG, and PDF. Input inspection records page count, dimensions where available, native-text and vector evidence counts, embedded image counts, and a recommended raster/vector/hybrid route. No semantic inference is presented as if it has run.

Later milestones add OCR, symbol detection, text association, topology reconstruction, review/correction, DXF/vector support, and structured export. Local graph connectivity reasoning exists only for controlled SLDForge fixtures; it is not power-flow simulation.
