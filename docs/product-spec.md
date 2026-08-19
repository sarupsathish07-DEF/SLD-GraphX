# Product specification

SLDGraph-X will convert SLD evidence into a reviewable canonical electrical graph. Milestone 3 implements local symbol intelligence atop the safe document/text foundation: asynchronous local OCR and symbol workers, raw evidence, deterministic engineering normalization, conservative semantic typing, transparent text-to-symbol association, review/audit persistence, and synchronized drawing overlays.

The current supported inputs are PNG, JPEG, and PDF. Input inspection records page count, dimensions where available, native-text and vector evidence counts, embedded image counts, and a recommended raster/vector/hybrid route. No semantic inference is presented as if it has run.

Current text types include equipment/feeder/bus IDs, voltage/current/power ratings, switch state, source/destination/description, and UNKNOWN. The workspace supports quiet text and symbol overlays, selection, raw/normalized evidence inspection, search, symbol class correction, accept/reject/verify review, and persistence after refresh. Symbol candidates are bounded to the M3 taxonomy and are clearly labelled as visual evidence, not electrical connections. Later milestones add conductor/junction/terminal reconstruction, topology, DXF/vector support, and structured export. Local graph connectivity reasoning exists only for controlled SLDForge fixtures; it is not power-flow simulation.
