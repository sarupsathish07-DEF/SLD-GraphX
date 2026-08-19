"""Core-owned supervisor for the isolated local symbol-detection worker."""

from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

from engine.sldgraph.symbols import SymbolRequest, SymbolResponse

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DETECTOR_PYTHON = PROJECT_ROOT / ".venv-sldgraphx-detector" / "Scripts" / "python.exe"
WORKER_SCRIPT = PROJECT_ROOT / "scripts" / "symbol_worker.py"
MODEL_PATH = PROJECT_ROOT / "models" / "detector" / "symbol-svm-v1.joblib"


class SymbolWorkerError(RuntimeError):
    pass


def health() -> dict:
    if not DETECTOR_PYTHON.is_file() or not WORKER_SCRIPT.is_file() or not MODEL_PATH.is_file():
        return {
            "status": "unavailable",
            "detail": "Local detector runtime or model is not installed",
        }
    try:
        completed = subprocess.run(
            [
                str(DETECTOR_PYTHON),
                "-c",
                "import cv2, sklearn; print(cv2.__version__, sklearn.__version__)",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "detail": f"Detector worker check failed: {exc}"}
    return {
        "status": "available" if completed.returncode == 0 else "unavailable",
        "detail": completed.stdout.strip()
        if completed.returncode == 0
        else completed.stderr.strip()[-300:],
    }


def detect(
    image_path: Path, page: int, timeout_seconds: float = 120, mode: str = "tiled"
) -> SymbolResponse:
    request = SymbolRequest(
        request_id=str(uuid.uuid4()),
        image_path=str(image_path.resolve()),
        page=page,
        mode=mode,
        timeout_seconds=timeout_seconds,
    )
    if not DETECTOR_PYTHON.is_file() or not MODEL_PATH.is_file():
        raise SymbolWorkerError(
            "Local symbol detector is unavailable; run scripts/bootstrap_detector.ps1"
        )
    try:
        completed = subprocess.run(
            [str(DETECTOR_PYTHON), str(WORKER_SCRIPT)],
            input=request.model_dump_json() + "\n",
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise SymbolWorkerError(
            f"Local symbol detector timed out after {timeout_seconds:.0f}s"
        ) from exc
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise SymbolWorkerError(f"Symbol worker returned no response: {completed.stderr[-300:]}")
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise SymbolWorkerError("Symbol worker returned malformed JSON") from exc
    if payload.get("error"):
        raise SymbolWorkerError(f"Symbol worker failed: {payload['error']}")
    try:
        return SymbolResponse.model_validate(payload)
    except Exception as exc:
        raise SymbolWorkerError(f"Symbol worker response failed validation: {exc}") from exc
