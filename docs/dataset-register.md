# Dataset register

| Dataset | Source | Use | License/status |
| --- | --- | --- | --- |
| SLDForge radial, dual transformer, sectionalized bus, bus coupler, alternate supply, ring | Project-generated | deterministic graph, renderer, preprocessing, and local API loop tests | project-controlled synthetic |
| SLDForge controlled degradation smoke sample | Project-generated | blur/JPEG/skew/contrast/brightness/fading reproducibility | project-controlled synthetic |
| OCR-v1 frozen benchmark | Project-generated SLDForge radial, dual-transformer, sectionalized-bus drawings | local OCR regression, normalization/semantic checks, controlled association evaluation | project-controlled synthetic; test-only at drawing level |
| Symbol-v1 | Project-generated SLDForge P0-symbol scenes, 75 drawings / 750 objects / four styles | isolated detector training, controlled in-style test, unseen-style holdout, tiled-label accounting | project-controlled synthetic; whole-drawing split before tiles; no real-data claim |

OCR-v1 generation configuration is tracked in `data/benchmark/ocr-v1.spec.json`; generated PNGs and manifest are ignored because they are reproducible local evidence. It contains topology, fixed seed, degradation, string/type/entity links, coordinates, and drawing-level test split. No external SLD dataset has been downloaded or evaluated.

Symbol-v1 is specified in `data/benchmark/symbol-v1.spec.json`: styles A/B/C are split among train (45 drawings), validation (9), and test (9); style D is a 12-drawing holdout. Every drawing contains one instance of each ten-class P0 vocabulary item. Tiles are 640 px with 96 px overlap and require 0.60 object visibility. The held-out style and all degradation images remain out of training. No legally verified public/real SLD microset is registered or evaluated.
