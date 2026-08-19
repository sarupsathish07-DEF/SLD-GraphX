"""Run the actual isolated detector on a held-out SLDForge style sheet."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.api.app.services.symbol_worker import detect

response = detect(Path("data/synthetic/symbol-v1/images/test-style_a-400.png"), 1, mode="tiled")
print(json.dumps(response.model_dump(mode="json"), indent=2))
