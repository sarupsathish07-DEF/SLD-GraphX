# Milestone 4R receipt — topology recall and generalization repair

Date: 2026-08-19

## Original M4

- Precision 0.9623; recall 0.4722; F1 0.6335; critical-edge recall 0.5306; physical reachability 0.3677; style-holdout F1 0.5200.

## False-negative analysis

- Development styles E/F are separate from frozen topology-v1. Automated diagnostics generate one overlay per missed ground-truth edge with truth edge, conductor traces, symbol boxes, terminals, and reason.
- Final frozen diagnostics found 18 terminal snap-distance failures and 11 symbol-detection propagation failures. Combined candidate-edge recall is 0.7986.

## Repairs

- Class-aware adaptive masks and reopened terminal corridors.
- Multi-scale directional extraction, projection of terminals onto conductor spans, conservative short corridor scans, endpoint-led component clustering, and bus-rooted T branch handling.
- T intersections are connected; undotted X intersections remain ambiguous.
- Thick-bus and paired-bus/coupler deterministic visual evidence avoid the prior grouped-contour failure.
- Detector thresholding now uses Otsu rather than a fixed brightness threshold.

## Frozen repaired benchmark

- Test: precision 0.9783, recall 0.8333, F1 0.9000, critical-edge recall 0.8334, reachability 0.7381, candidate-edge recall 0.8333, mean 1798.21 ms/drawing.
- Style-D holdout: precision 0.9615, recall 0.6944, F1 0.8065, critical-edge recall 0.7584, reachability 0.5529, candidate-edge recall 0.6944, mean 2352.82 ms/drawing.
- The test gate is met. Holdout F1 materially exceeds both original M4 (0.5200) and the rerun endpoint-only baseline (0.6552), but holdout reachability remains below the desired 0.70 target.

## Degradation and production checks

- One-parent degradation F1: clean, blur, JPEG, contrast, brightness, faded conductors, and low resolution 1.0000; 1.4-degree skew 0.7500. Brightness is fixed for this controlled condition.
- Existing unseen style-D radial upload remains 3/5 hidden edges with five detected symbols. It is persisted and survives restart; this is not claimed as improved.

## Decision

READY FOR MILESTONE 5, with explicit carry-forward limitations: style-D reachability, terminal-distance errors, and upstream symbol mapping still need engineering review. M4R adds no source/feeder semantics.
