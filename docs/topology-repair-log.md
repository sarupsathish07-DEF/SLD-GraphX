# Topology recall repair log

The topology-v1 manifest remains frozen at SHA-256 `475a58d6d1f69bf1aa692ff9191e28f7363fbb8b22e0e6965dd3033a5bccf455`. Development uses the separate topology-repair-dev-v1 corpus (styles E/F), never topology-v1 test or style-D holdout.

| Repair | Hypothesis | Development evidence | Frozen result |
| --- | --- | --- | --- |
| Adaptive mask inset and terminal corridors | symbol padding hid short approaches | terminal-distance misses reduced | retained in final path |
| Segment components and bus-rooted T branches | Hough splits L/T feeders into fragments | development recall 0.5000 to 0.5556 | test F1 improved to 0.7283 before bus evidence repair |
| Terminal corridor scan | short source/device approaches can retain directional pixels without a Hough segment | removed development source-transformer misses | retained in final path |
| Thick-bus and paired-bus-coupler evidence | grouped proposals merged buses/couplers with branches | development candidate/selected recall reached 0.8333 | test F1 0.9000; style-D F1 0.8065 |
| Otsu thresholding | fixed 180 threshold interpreted dim backgrounds as ink | direct brightness run recovered 6 symbols and 5/5 edges | brightness degradation F1 1.0000 |

Final frozen diagnostics preserve every miss and overlay under ignored `artifacts/experiments/topology-repair/frozen/`. Combined candidate-edge recall is 0.7986. Remaining categories: 18 terminal snap-distance failures and 11 symbol-detection propagation failures. No threshold sweep was tuned on topology-v1 test or style-D holdout.
