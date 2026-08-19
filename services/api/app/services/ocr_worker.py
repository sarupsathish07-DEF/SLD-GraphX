from __future__ import annotations

import json
import os
import subprocess
import uuid
from pathlib import Path

from engine.sldgraph.ocr import OcrRequest, OcrResponse

PROJECT_ROOT = Path(__file__).resolve().parents[4]
OCR_PYTHON = PROJECT_ROOT / ".venv-sldgraphx-ocr-clean" / "Scripts" / "python.exe"
WORKER_SCRIPT = PROJECT_ROOT / "scripts" / "ocr_worker.py"
MODEL_HOME = PROJECT_ROOT / "models" / "ocr" / "paddle"


class OcrWorkerError(RuntimeError):
    pass


def health() -> dict:
    if not OCR_PYTHON.is_file() or not WORKER_SCRIPT.is_file():
        return {"status": "unavailable", "detail": "Local OCR worker environment is not installed"}
    try:
        check = subprocess.run(
            [
                str(OCR_PYTHON),
                "-c",
                "import paddle, paddleocr; print(paddle.__version__, paddleocr.__version__)",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            env={**os.environ, "PADDLE_HOME": str(MODEL_HOME)},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "unavailable", "detail": f"OCR worker check failed: {exc}"}
    return {
        "status": "available" if check.returncode == 0 else "unavailable",
        "detail": check.stdout.strip() if check.returncode == 0 else check.stderr.strip()[-300:],
    }


def recognize(
    image_path: Path,
    page: int,
    timeout_seconds: float = 120,
    mode: str = "full_page",
) -> OcrResponse:
    request = OcrRequest(
        request_id=str(uuid.uuid4()),
        image_path=str(image_path.resolve()),
        page=page,
        mode=mode,
        timeout_seconds=timeout_seconds,
    )
    if not OCR_PYTHON.is_file():
        raise OcrWorkerError("Local OCR worker is unavailable; run scripts/bootstrap_ocr.ps1")
    try:
        completed = subprocess.run(
            [str(OCR_PYTHON), str(WORKER_SCRIPT)],
            input=request.model_dump_json() + "\n",
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env={**os.environ, "PADDLE_HOME": str(MODEL_HOME), "PADDLEOCR_HOME": str(MODEL_HOME)},
        )
    except subprocess.TimeoutExpired as exc:
        raise OcrWorkerError(f"Local OCR worker timed out after {timeout_seconds:.0f}s") from exc
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise OcrWorkerError(f"OCR worker returned no response: {completed.stderr[-300:]}")
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise OcrWorkerError("OCR worker returned malformed JSON") from exc
    if payload.get("error"):
        raise OcrWorkerError(f"OCR worker failed: {payload['error']}")
    try:
        return OcrResponse.model_validate(payload)
    except Exception as exc:
        raise OcrWorkerError(f"OCR worker response failed validation: {exc}") from exc
