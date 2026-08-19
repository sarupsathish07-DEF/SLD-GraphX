# Dataset register

| Dataset | Source | Use | License/status |
| --- | --- | --- | --- |
| SLDForge radial, dual transformer, sectionalized bus, bus coupler, alternate supply, ring | Project-generated | deterministic graph, renderer, preprocessing, and local API loop tests | project-controlled synthetic |
| SLDForge controlled degradation smoke sample | Project-generated | blur/JPEG/skew/contrast/brightness/fading reproducibility | project-controlled synthetic |
| OCR-v1 frozen benchmark | Project-generated SLDForge radial, dual-transformer, sectionalized-bus drawings | local OCR regression, normalization/semantic checks, controlled association evaluation | project-controlled synthetic; test-only at drawing level |

OCR-v1 generation configuration is tracked in `data/benchmark/ocr-v1.spec.json`; generated PNGs and manifest are ignored because they are reproducible local evidence. It contains topology, fixed seed, degradation, string/type/entity links, coordinates, and drawing-level test split. No external SLD dataset has been downloaded or evaluated.
