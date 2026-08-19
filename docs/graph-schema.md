# Canonical graph schema

`ElectricalGraph` contains equipment, terminals, connections, evidence, feeder paths, and review issues. Coordinates are normalized. Every inference-capable item carries `confidence`, `provenance`, and `review_status`.

Implemented bootstrap node types include energy source, transformer, busbar, circuit breaker, current transformer, feeder, load, bus coupler, junction, and generic equipment.
