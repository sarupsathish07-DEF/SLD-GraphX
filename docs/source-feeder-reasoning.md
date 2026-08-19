# Source / feeder electrical reasoning

Milestone 5 derives electrical intelligence from the persisted M4 physical graph. It is deterministic local graph reasoning, not power-flow, fault, protection, voltage-drop, or an IEC certification engine.

## Three graph views

- **Physical:** undirected terminal/equipment connection evidence with confidence and audit status.
- **Operational:** the physical graph after OPEN/CLOSED/UNKNOWN switching policy. OPEN blocks traversal; UNKNOWN is retained as possible-path uncertainty and is excluded by a definite-path policy.
- **Semantic electrical:** source candidates, buses, feeder records, source assignments, exact node/edge paths, destination/rating/voltage where evidence supports them, validation, and review risk.

## Source and feeder rules

Explicit energy source, grid incomer, and generator classes are source candidates. A transformer can be a secondary boundary candidate only when its physical component has no explicit external source; terminal side is otherwise unknown unless supporting voltage/text evidence exists. A feeder requires feeder-terminal class plus physical graph support. Missing evidence yields `unresolved`, not a fabricated source or destination.

Paths retain equipment and physical connection IDs, source bus, switching equipment, geometric-mean path confidence, weakest edge, and uncertainty flags. Alternate sources/paths remain `ambiguous`; cycles are not forced into a tree.

## Validation and review risk

Validation is warning-oriented and includes self loops, duplicate equipment IDs/parallel edges, unresolved terminals, disconnection, source/feeder reachability, simple device degree sanity, unknown switch on a path, voltage transition without transformer, and unresolved crossings. It does not delete unusual topology.

For each uncertain physical connection, criticality compares with/without-edge reachable feeders, affected nodes, source assignment, connected components, and bridge importance. Initial risk is:

`(1 - edge confidence) × configured topology impact`

The weights are transparent engineering design values, not learned/calibrated probabilities. Review priority is CRITICAL/HIGH/MEDIUM/LOW from this risk.

## Corrections, scenarios, export

Connection/crossing/class/text/switch corrections preserve audit records and recompute only semantic/operational/validation/criticality views. A scenario is temporary unless deliberately saved and never mutates the physical graph. JSON and ZIP CSV exports carry stable IDs, confidence, provenance, and review status but never storage paths. The package also contains the reconstructed SVG.

## Evidence boundary

`source-feeder-v1` evaluates reasoning against six graph-first SLDForge canonical fixtures. Its figures demonstrate semantic correctness conditioned on correct graph evidence; the production unseen smoke separately measures the full OCR/symbol/topology path. Neither is real utility validation.
