# Models

Model payloads are not committed. The tracked `manifest.json` indexes model families; each family records reproducibility metadata and checksums without adding binary weights. OCR payloads are prepared locally, while the Milestone 3 symbol detector is rebuilt with `scripts/bootstrap_detector.ps1` and registered in `detector/manifest.json`.
