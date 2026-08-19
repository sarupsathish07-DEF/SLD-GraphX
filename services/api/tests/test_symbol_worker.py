import subprocess
from pathlib import Path

import pytest

from services.api.app.services import symbol_worker


def test_detector_unavailable_is_explicit(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(symbol_worker, "DETECTOR_PYTHON", tmp_path / "missing.exe")
    with pytest.raises(symbol_worker.SymbolWorkerError, match="unavailable"):
        symbol_worker.detect(Path("drawing.png"), 1)


def test_detector_malformed_response_is_rejected(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "python.exe"
    executable.touch()
    model = tmp_path / "model.joblib"
    model.touch()
    monkeypatch.setattr(symbol_worker, "DETECTOR_PYTHON", executable)
    monkeypatch.setattr(symbol_worker, "MODEL_PATH", model)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: type(
            "Done", (), {"stdout": "not json\n", "stderr": "", "returncode": 0}
        )(),
    )
    with pytest.raises(symbol_worker.SymbolWorkerError, match="malformed JSON"):
        symbol_worker.detect(Path("drawing.png"), 1)


def test_detector_timeout_is_rewritten_as_domain_error(monkeypatch, tmp_path) -> None:
    executable = tmp_path / "python.exe"
    executable.touch()
    model = tmp_path / "model.joblib"
    model.touch()
    monkeypatch.setattr(symbol_worker, "DETECTOR_PYTHON", executable)
    monkeypatch.setattr(symbol_worker, "MODEL_PATH", model)

    def expired(*args, **kwargs):
        raise subprocess.TimeoutExpired("detector", 1)

    monkeypatch.setattr(subprocess, "run", expired)
    with pytest.raises(symbol_worker.SymbolWorkerError, match="timed out"):
        symbol_worker.detect(Path("drawing.png"), 1, timeout_seconds=1)
