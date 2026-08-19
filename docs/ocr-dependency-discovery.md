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

`engine.sldgraph.ocr.adapter` defines a dependency-free local `OcrAdapter` protocol and an explicit `UnavailableOcrAdapter`. It raises instead of inventing text or making an online fallback.

## Isolated runtime result

The initially evaluated Paddle 3.3.1 / legacy PaddleOCR 2.7.3 pairing failed during real CPU oneDNN model export. That failure remained confined to the disposable OCR environment. The accepted local worker is `.venv-sldgraphx-ocr-clean` with `paddlepaddle==2.6.2`, `paddleocr==2.7.3`, `numpy==1.26.4`, `protobuf==3.20.2`, and OpenCV 4.6.0.66 packages. Both imports and `pip check` passed.

The real six-label smoke initialized PP-OCRv3 detection, PP-OCRv4 recognition, and angle classification and recognized `FDR-11KV-03`, `CB-07`, `TR-01`, `11 kV`, `630 A`, and `25 MVA` exactly. Prepared models are copied to `models/ocr/paddle` and referenced explicitly by the worker, so normal inference does not require the user-profile cache or a network request. See the model manifest for file hashes.
