# Model register

| Field | Registered value |
| --- | --- |
| Engine | PaddleOCR 2.7.3, isolated CPU worker |
| Runtime | PaddlePaddle 2.6.2; Python 3.10 Windows x64 |
| Models | en_PP-OCRv3 detector; en_PP-OCRv4 recognizer; ch_ppocr_mobile_v2.0 classifier |
| Source | PaddleOCR model preparation through `scripts/prepare_ocr_models.py` |
| License | PaddleOCR repository/model terms must be retained with the selected distribution; no claim of separate independent legal review |
| Local storage | `models/ocr/paddle/` (ignored payloads, explicit worker paths) |
| Checksum register | `models/ocr/manifest.json` contains SHA-256 for inference parameters/models |
| Hardware validated | local Windows CPU; GPU is disabled |
| Known limits | English OCR only; benchmarked only on small controlled SLDForge diagrams; no cloud fallback |

`scripts/bootstrap_ocr.ps1` creates the isolated environment, installs pinned packages, performs the one-time preparation download, copies model folders to the project-local store, and runs a real smoke test. The runtime worker refuses to run when these local model folders are absent.

| Field | Registered value |
| --- | --- |
| Engine | OpenCV HOG 64×64 + calibrated linear SVM; deterministic busbar geometry |
| Runtime | isolated `.venv-sldgraphx-detector`; Python 3.10 Windows x64 |
| Artifact | `models/detector/symbol-svm-v1.joblib`, ignored local payload; checksum in `models/detector/manifest.json` |
| Training/runtime packages | `opencv-python-headless==4.10.0.84`, `scikit-learn==1.5.2`, `numpy==1.26.4`, `pydantic==2.13.4` |
| License record | installed package metadata records scikit-learn BSD-3-Clause and OpenCV Apache-2.0; NumPy binary notices remain package-distribution obligations. This is a record, not legal advice. |
| Excluded option | Ultralytics was not adopted because its AGPL option needs a separate project licensing decision. |
| Hardware validated | local Intel Core Ultra 9 285H CPU; GPU not used |
| Known limits | contour-proposal/classifier detector, controlled synthetic data only, per-request worker start, no ONNX/OpenVINO package or real-drawing validation |

`scripts/bootstrap_detector.ps1` regenerates the corpus, trains from scratch in a separate environment, checks dependency consistency, and invokes the actual deployment worker. The detector has no model downloader or cloud fallback; a missing local model makes the `symbol_detection` stage fail explicitly.
