# Canonical graph schema

`ElectricalGraph` contains equipment, terminals, connections, evidence, feeder paths, and review issues. Coordinates are normalized. Every inference-capable item carries `confidence`, `provenance`, and `review_status`.

Implemented graph fixture node types include energy source, transformer, busbar, circuit breaker, current transformer, feeder, load, bus coupler, junction, and generic equipment. The normalized-coordinate transform contract is reusable from master image geometry to canvas display geometry; uploaded-document overlays are intentionally unpopulated in Milestone 1.
