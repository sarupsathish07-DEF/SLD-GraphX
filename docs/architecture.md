# Architecture

`apps/web` is a React/TypeScript client. `services/api` owns REST and SQLite persistence. `engine/sldgraph` owns canonical models, graph reasoning, validation, and exporters. `sldforge` creates controlled synthetic drawings and ground truth.

All ingestion branches converge on the canonical `ElectricalGraph`. Evidence/provenance stays attached to inferred graph objects. Perception adapters may change without changing electrical reasoning.
