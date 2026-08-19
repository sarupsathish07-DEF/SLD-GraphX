"""Run the isolated local OCR worker on one generated SLDForge drawing."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.api.app.services.ocr_worker import recognize

image = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/benchmark/ocr-v1/radial-clean.png")
response = recognize(image, 1, timeout_seconds=180)
print(json.dumps(response.model_dump(mode="json"), indent=2))
