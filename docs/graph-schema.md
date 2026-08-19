# Canonical graph schema

`ElectricalGraph` contains equipment, terminals, connections, evidence, feeder paths, and review issues. Coordinates are normalized. Every inference-capable item carries `confidence`, `provenance`, and `review_status`.

M4 persists a separate `physical_connectivity` graph for each analysis. Nodes are named `TerminalEvidence` records (`symbol_evidence_id`, class, IN/OUT/ATTACH name, normalized position, orientation confidence, provenance). Edges are `PhysicalConnection` records with endpoint terminal IDs, polyline, candidate linkage when inferred, confidence, provenance, review status/reason, and an immutable review-action history. Raw `ConductorEvidence`, first-class `BusbarEvidence`, and `JunctionEvidence` are retained independently. `ConnectionCandidate` preserves visual continuity, endpoint-distance, orientation, terminal, junction, and structural scores plus `gap_bridge` state. `TopologyIssue` captures duplicate, low-confidence, orphan, degree, and review-needed conditions.

This physical graph is undirected image evidence only. It does not populate feeder paths or source fields, infer an energized state, or modify the canonical source/feeder graph.

Implemented graph fixture node types include energy source, transformer, busbar, circuit breaker, current transformer, feeder, load, bus coupler, junction, and generic equipment. The normalized-coordinate transform contract is reusable from master image geometry to canvas display geometry; uploaded-document overlays are intentionally unpopulated in Milestone 1.
