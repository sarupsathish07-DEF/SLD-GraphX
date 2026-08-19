import subprocess
from pathlib import Path

import pytest

from services.api.app.services import ocr_worker


def test_worker_unavailable_is_explicit(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(ocr_worker, "OCR_PYTHON", tmp_path / "missing.exe")
    with pytest.raises(ocr_worker.OcrWorkerError, match="unavailable"):
        ocr_worker.recognize(Path("drawing.png"), 1)


def test_worker_malformed_response_is_rejected(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "python.exe"
    executable.touch()
    monkeypatch.setattr(ocr_worker, "OCR_PYTHON", executable)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: type(
            "Done", (), {"stdout": "not json\n", "stderr": "", "returncode": 0}
        )(),
    )
    with pytest.raises(ocr_worker.OcrWorkerError, match="malformed JSON"):
        ocr_worker.recognize(Path("drawing.png"), 1)


def test_worker_timeout_is_rewritten_as_domain_error(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "python.exe"
    executable.touch()
    monkeypatch.setattr(ocr_worker, "OCR_PYTHON", executable)

    def expired(*args, **kwargs):
        raise subprocess.TimeoutExpired("ocr", 1)

    monkeypatch.setattr(subprocess, "run", expired)
    with pytest.raises(ocr_worker.OcrWorkerError, match="timed out"):
        ocr_worker.recognize(Path("drawing.png"), 1, timeout_seconds=1)
