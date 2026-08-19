# Symbol-v1 evaluation protocol

Evaluation runs `scripts/benchmark_symbols.py` against the isolated deployment worker—not training-time crops. Ground truth comes from the frozen canonical manifest. Matching is class-aware one-to-one box matching at IoU ≥ 0.50. The report gives per-class TP/FP/FN, precision, recall, F1, totals, component semantic match rate (TP divided by TP plus FN), and worker-reported inference time. It explicitly marks mAP@0.50 and mAP@0.50:0.95 as not available because this classical evaluation does not calculate ranked detector AP.

Split policy is whole drawing before tiling: train 45 drawings, validation 9, test 9 (styles A/B/C), and style holdout 12 (unseen style D). No parent drawing crosses splits. Tiles are 640 px with 96 px overlap and labels below 0.60 visible fraction are omitted. One test parent is rendered into clean, blur, JPEG, contrast, brightness, small skew, faded-line, and low-resolution conditions; these conditions do not train the detector.

Recorded local run (2026-08-19, model `a9f862350459dfd87adeddcceb931c891216debd468f34efed620f30d83d74a2`):

| Set | TP / FP / FN | Component semantic match | Mean worker inference |
| --- | ---: | ---: | ---: |
| controlled synthetic test | 70 / 21 / 20 | 0.7778 | 61.84 ms |
| unseen style holdout | 76 / 47 / 44 | 0.6333 | reported in artifact |

The one-drawing degradation component-match values were clean 0.80, blur 0.70, JPEG 0.80, contrast 0.80, brightness 0.00, skew 0.90, faded line 0.70, and low resolution 0.90. They are stress signals, not population metrics. There is no registered legally verified public/real SLD microset; real validation is `not_run`.
