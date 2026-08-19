# Milestone 3 P0 symbol taxonomy

The M3 detector is intentionally bounded. It emits visual candidates only; a class does not establish a conductor, terminal, equipment identity, connectivity, source, feeder, or switch state.

| Canonical class | Purpose in M3 | Detection route |
| --- | --- | --- |
| `power_transformer` | transformer visual evidence | learned classifier |
| `circuit_breaker` | breaker visual evidence | learned classifier |
| `disconnector` | isolator/disconnector visual evidence | learned classifier |
| `current_transformer` | CT visual evidence | learned classifier |
| `potential_transformer` | PT/VT visual evidence | learned classifier |
| `busbar` | busbar visual evidence | deterministic geometry rule |
| `feeder_terminal` | feeder/end-terminal visual evidence | learned classifier |
| `load` | load visual evidence | learned classifier |
| `energy_source` | source symbol visual evidence | learned classifier |
| `bus_coupler` | coupler visual evidence | learned classifier |

The stable API contract carries original/current class, confidence, normalized box/polygon, page, orientation, tile origin, engine/model, provenance, review state/reason, and related text associations. Engineer class changes, acceptance, rejection, verification, and manual additions are separate auditable actions. The canonical names are project vocabulary, not IEC conformance labels.
