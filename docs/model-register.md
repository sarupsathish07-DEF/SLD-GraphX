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
