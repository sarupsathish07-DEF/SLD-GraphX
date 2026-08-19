# Product specification

SLDGraph-X will convert SLD evidence into a reviewable canonical electrical graph. Milestone 4 implements local physical topology evidence atop the safe document/text/symbol foundation: raw conductor/bus/junction evidence, symbol terminals, scored terminal-aware physical edges, deterministic structural checks, audit persistence, and synchronized drawing/graph review.

The current supported inputs are PNG, JPEG, and PDF. Input inspection records page count, dimensions where available, native-text and vector evidence counts, embedded image counts, and a recommended raster/vector/hybrid route. No semantic inference is presented as if it has run.

Current text types include equipment/feeder/bus IDs, voltage/current/power ratings, switch state, source/destination/description, and UNKNOWN. The workspace supports text, symbol, conductor, bus, junction, and physical-edge overlays; selection; raw evidence inspection; graph edge/crossing review; terminal-validated manual edges; and persistence after refresh. Symbol candidates and topology edges remain evidence, not electrical conclusions. Physical connectivity is undirected and does not identify sources, feeders, energized paths, switch state, direction, or flow. DXF/vector support, source/feeder reasoning, structured export, and electrical consistency beyond local topology checks remain later work.
