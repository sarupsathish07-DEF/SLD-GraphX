# OCR dependency discovery — Milestone 2 preparation

Date: 2026-08-19

## Environment checked

- Python: 3.10.10 on Windows x64 (`.venv-sldgraphx`).
- Installed before discovery: neither `paddlepaddle` nor `paddleocr`.
- Package-index availability: `paddlepaddle` 3.3.1 exposes a CPython 3.10 Windows x64 wheel; `paddleocr` 3.7.0 is available as a Python wheel.

## Compatibility decision

`pip install --dry-run paddlepaddle==3.3.1 paddleocr==3.7.0` selected PaddleX OCR dependencies including `opencv-contrib-python==4.10.0.84`, while the stable Milestone 1 environment already uses `opencv-python-headless==4.11.0.86` for preprocessing. The prospective dependency closure also adds PaddleX, ModelScope, Hugging Face Hub, SDK and network-client packages.

This is a meaningful native OpenCV and dependency-surface conflict. PaddleOCR was **not installed** into the stable Milestone 1 environment; therefore no model download, initialization, or OCR label result is claimed. The source checked was the package index metadata, and licenses/model terms have not yet been independently recorded.

## Resulting boundary

`engine.sldgraph.ocr.adapter` now defines a dependency-free local `OcrAdapter` protocol and an explicit `UnavailableOcrAdapter`. It raises instead of inventing text or making an online fallback. A later isolated environment or compatibility-tested lockfile is required before an actual PaddleOCR smoke run.
