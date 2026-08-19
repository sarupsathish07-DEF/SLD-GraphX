"""Exercise upload, OCR, symbol detection, fusion persistence, and component summary without mocks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.api.app.main import app


def main() -> None:
    image = Path("data/synthetic/symbol-v1/images/test-style_a-400.png")
    with TestClient(app) as client:
        project = client.post("/api/projects", data={"name": "Real symbol pipeline", "description": "local"}).json()
        drawing = client.post(f"/api/projects/{project['id']}/drawings", files={"file": (image.name, image.read_bytes(), "image/png")}).json()
        analysis_id = client.post(f"/api/drawings/{drawing['id']}/analyze").json()["analysis_run_id"]
        analysis = client.get(f"/api/analyses/{analysis_id}").json()
        texts = client.get(f"/api/analyses/{analysis_id}/texts").json()
        symbols = client.get(f"/api/analyses/{analysis_id}/symbols").json()
        summary = client.get(f"/api/analyses/{analysis_id}/symbol-summary").json()
    if analysis["status"] != "complete" or not symbols:
        raise RuntimeError(json.dumps({"analysis": analysis, "symbols": symbols}, indent=2))
    print(json.dumps({"analysis_id": analysis_id, "stages": [item["stage"] for item in analysis["stages"]], "texts": len(texts), "symbols": summary["detected"], "associated_labels": summary["associated_labels"]}, indent=2))


if __name__ == "__main__":
    main()
