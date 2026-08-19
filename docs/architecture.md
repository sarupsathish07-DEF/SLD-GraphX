# Architecture

`apps/web` is a React/TypeScript client. `services/api` owns REST, SQLite persistence, controlled upload/artifact storage, and background preprocessing. `engine/sldgraph` owns canonical models, graph reasoning, inspection, validation, and exporters. `sldforge` creates graph-first controlled synthetic drawings and ground truth.

PNG/JPEG/PDF ingestion currently converges on persisted document evidence and preprocessing artifacts; later perception branches converge on the canonical `ElectricalGraph`. Evidence/provenance stays attached to inferred graph objects. Perception adapters may change without changing electrical reasoning.
