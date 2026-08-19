from pathlib import Path

import pytest

from engine.sldgraph.ocr import OcrRegion, OcrResponse


@pytest.fixture(autouse=True)
def isolated_ocr_worker(monkeypatch, request):
    """Unit/API tests stay deterministic; marked smoke tests use the real worker."""
    if request.node.get_closest_marker("real_ocr"):
        return

    def fake_recognize(path: Path, page: int, timeout_seconds: float = 120):
        return OcrResponse(
            request_id="test",
            engine="test-local-ocr",
            model="fixture",
            image_width=1600,
            image_height=900,
            elapsed_ms=1,
            regions=[
                OcrRegion(
                    id="text_001",
                    text="FDR-11KV-03",
                    confidence=0.91,
                    polygon=[(0.8, 0.2), (0.9, 0.2), (0.9, 0.24), (0.8, 0.24)],
                    bbox_normalized=(0.8, 0.2, 0.9, 0.24),
                    rotation_deg=0,
                )
            ],
        )

    monkeypatch.setattr("services.api.app.services.analysis.recognize", fake_recognize)
