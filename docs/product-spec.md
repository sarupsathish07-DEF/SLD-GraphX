# Product specification

SLDGraph-X converts SLD evidence into a reviewable canonical electrical graph. Milestone 5 preserves M4 physical topology as undirected evidence and adds separate operational and semantic graph views: source candidates, buses, feeders, exact path records, switch-state scenarios, deterministic validation, topology-impact review, correction/recompute, reconstruction, and export.

The current supported inputs are PNG, JPEG, and PDF. Input inspection records page count, dimensions where available, native-text and vector evidence counts, embedded image counts, and a recommended raster/vector/hybrid route. No semantic inference is presented as if it has run.

Current text types include equipment/feeder/bus IDs, voltage/current/power ratings, switch state, source/destination/description, and UNKNOWN. The workspace supports Original/Reconstructed/Graph modes, path highlighting, Trace & Explain, topology-risk review, non-destructive scenarios, exports, and validation. A result remains unresolved where physical evidence is incomplete; it never receives an invented source. Operational connectivity is not power flow or energization physics. DXF/vector support and IEC/power-flow claims remain out of scope.
