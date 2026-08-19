# Product specification

SLDGraph-X will convert SLD evidence into a reviewable canonical electrical graph. Milestone 2 implements real local text intelligence atop the safe document foundation: asynchronous OCR, raw OCR evidence, deterministic engineering normalization, conservative semantic typing, review/audit persistence, and a synchronized Text workspace.

The current supported inputs are PNG, JPEG, and PDF. Input inspection records page count, dimensions where available, native-text and vector evidence counts, embedded image counts, and a recommended raster/vector/hybrid route. No semantic inference is presented as if it has run.

Current text types include equipment/feeder/bus IDs, voltage/current/power ratings, switch state, source/destination/description, and UNKNOWN. The workspace supports quiet text overlays, selection, raw/normalized evidence inspection, search, edit, accept/reject/unknown review, and persistence after refresh. Later milestones add symbol detection, raster association, topology reconstruction, DXF/vector support, and structured export. Local graph connectivity reasoning exists only for controlled SLDForge fixtures; it is not power-flow simulation.
