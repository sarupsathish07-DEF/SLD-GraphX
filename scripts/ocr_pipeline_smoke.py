"""Exercise the production API path with a real isolated OCR worker and SLDForge PNG."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.api.app.main import app


def main() -> None:
    image = Path("data/benchmark/ocr-v1/radial-clean.png")
    with TestClient(app) as client:
        project = client.post(
            "/api/projects", data={"name": "Real OCR pipeline smoke", "description": "local"}
        ).json()
        drawing = client.post(
            f"/api/projects/{project['id']}/drawings",
            files={"file": (image.name, image.read_bytes(), "image/png")},
        ).json()
        analysis_id = client.post(f"/api/drawings/{drawing['id']}/analyze").json()[
            "analysis_run_id"
        ]
        analysis = client.get(f"/api/analyses/{analysis_id}").json()
        texts = client.get(f"/api/analyses/{analysis_id}/texts").json()
        summary = client.get(f"/api/analyses/{analysis_id}/text-summary").json()
    if analysis["status"] != "complete" or not texts:
        raise RuntimeError(json.dumps({"analysis": analysis, "texts": texts}, indent=2))
    print(
        json.dumps(
            {
                "analysis_id": analysis_id,
                "status": analysis["status"],
                "stages": [stage["stage"] for stage in analysis["stages"]],
                "recognized": summary["recognized"],
                "first_text": texts[0]["raw_text"],
                "first_provenance": texts[0]["provenance"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
