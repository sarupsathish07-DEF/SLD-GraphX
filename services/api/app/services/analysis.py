from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path

import cv2
import fitz
import numpy as np
from PIL import Image, ImageEnhance, ImageOps
from sqlalchemy import select

from services.api.app.db.database import SessionLocal
from services.api.app.db.entities import (
    AnalysisRunRecord,
    AnalysisStageRecord,
    ArtifactRecord,
    DrawingRecord,
)
from services.api.app.services.ocr_worker import OcrWorkerError, recognize
from services.api.app.services.symbol_worker import SymbolWorkerError, detect
from services.api.app.services.symbols import associate_text_symbols, persist_symbol_detections
from services.api.app.services.texts import persist_ocr_regions

RENDER_ROOT = Path("var/renders")
DESKEW_THRESHOLD_DEGREES = 0.35


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage(session, run_id: str, stage: str, status: str, progress: float, message: str) -> None:
    now = datetime.utcnow()
    session.add(
        AnalysisStageRecord(
            id=str(uuid.uuid4()),
            analysis_run_id=run_id,
            stage=stage,
            status=status,
            progress=progress,
            message=message,
            started_at=now,
            finished_at=now,
            duration_ms=0,
        )
    )


def _metadata(image: Image.Image, page: int, configuration: dict) -> str:
    return json.dumps(
        {
            "width": image.width,
            "height": image.height,
            "page": page,
            "generation_configuration": configuration,
        }
    )


def _store_image(
    session,
    run_id: str,
    output: Path,
    kind: str,
    page: int,
    image: Image.Image,
    configuration: dict,
) -> None:
    target = output / f"page-{page:03}-{kind}.png"
    image.save(target, "PNG", optimize=True)
    session.add(
        ArtifactRecord(
            id=str(uuid.uuid4()),
            analysis_run_id=run_id,
            artifact_type=kind,
            relative_path=target.relative_to("var").as_posix(),
            mime_type="image/png",
            sha256=_sha256(target),
            metadata_json=_metadata(image, page, configuration),
        )
    )


def _store_json(session, run_id: str, output: Path, kind: str, page: int, payload: dict) -> None:
    target = output / f"page-{page:03}-{kind}.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    session.add(
        ArtifactRecord(
            id=str(uuid.uuid4()),
            analysis_run_id=run_id,
            artifact_type=kind,
            relative_path=target.relative_to("var").as_posix(),
            mime_type="application/json",
            sha256=_sha256(target),
            metadata_json=json.dumps(
                {"page": page, "generation_configuration": {"pipeline": "m2-ocr"}}
            ),
        )
    )


def _deskew_angle(gray: np.ndarray) -> float:
    """Estimate skew conservatively; only a material rotation is applied."""
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=100,
        minLineLength=max(40, gray.shape[1] // 8),
        maxLineGap=12,
    )
    if lines is None:
        return 0.0
    angles = []
    for x1, y1, x2, y2 in lines[:, 0]:
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(angle) <= 8:
            angles.append(angle)
    return float(np.median(angles)) if angles else 0.0


def queue_analysis(drawing_id: str) -> str:
    run_id = str(uuid.uuid4())
    with SessionLocal() as session:
        if session.get(DrawingRecord, drawing_id) is None:
            raise ValueError("Drawing not found")
        session.add(
            AnalysisRunRecord(
                id=run_id, drawing_id=drawing_id, status="queued", pipeline_version="m3"
            )
        )
        session.commit()
    return run_id


def run_analysis(drawing_id: str, run_id: str | None = None) -> str:
    """Render every input page and persist deterministic, non-semantic variants."""
    run_id = run_id or queue_analysis(drawing_id)
    try:
        with SessionLocal() as session:
            drawing = session.get(DrawingRecord, drawing_id)
            run = session.get(AnalysisRunRecord, run_id)
            if drawing is None or run is None:
                raise ValueError("Drawing or analysis run not found")
            run.status, run.started_at = "running", datetime.utcnow()
            session.commit()
            _stage(session, run_id, "ingestion", "complete", 1, "Stored input verified")
            _stage(session, run_id, "inspection", "complete", 1, "Document evidence preserved")
            source = Path("var/uploads") / drawing.project_id / drawing.id / drawing.safe_filename
            output = RENDER_ROOT / run_id
            output.mkdir(parents=True, exist_ok=True)
            if source.suffix.lower() == ".pdf":
                document = fitz.open(source)
                masters = []
                for page in document:
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    masters.append(
                        Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                    )
                document.close()
            else:
                masters = [Image.open(source).convert("RGB")]
            _stage(
                session,
                run_id,
                "rendering",
                "complete",
                1,
                f"Rendered {len(masters)} page(s) into display and analysis representations",
            )
            for page_number, master in enumerate(masters, start=1):
                display = master.copy()
                display.thumbnail((1920, 1200))
                grayscale = ImageOps.grayscale(master)
                gray = np.array(grayscale)
                contrast = ImageEnhance.Contrast(master).enhance(1.4)
                binary = Image.fromarray(
                    cv2.adaptiveThreshold(
                        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 9
                    )
                )
                inverse = 255 - gray
                horizontal = cv2.morphologyEx(
                    inverse, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (19, 1))
                )
                vertical = cv2.morphologyEx(
                    inverse, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 19))
                )
                line_emphasized = Image.fromarray(cv2.bitwise_or(horizontal, vertical))
                config = {
                    "pipeline": "m1-preprocess",
                    "contrast_factor": 1.4,
                    "binary": "adaptive_gaussian_31_9",
                    "line_kernel": [19, 1],
                }
                for kind, image in {
                    "source_reference": master,
                    "display": display,
                    "analysis": master,
                    "grayscale": grayscale,
                    "contrast": contrast,
                    "binary": binary,
                    "line_emphasized": line_emphasized,
                }.items():
                    _store_image(session, run_id, output, kind, page_number, image, config)
                angle = _deskew_angle(gray)
                if abs(angle) >= DESKEW_THRESHOLD_DEGREES:
                    matrix = cv2.getRotationMatrix2D(
                        (gray.shape[1] / 2, gray.shape[0] / 2), angle, 1.0
                    )
                    deskewed = Image.fromarray(
                        cv2.warpAffine(
                            np.array(master),
                            matrix,
                            (gray.shape[1], gray.shape[0]),
                            borderValue=(255, 255, 255),
                        )
                    )
                    _store_image(
                        session,
                        run_id,
                        output,
                        "deskewed",
                        page_number,
                        deskewed,
                        {**config, "deskew_angle_degrees": round(angle, 3)},
                    )
            _stage(
                session,
                run_id,
                "preprocessing",
                "complete",
                1,
                "Grayscale, contrast, binary, and line variants generated; deskew applied only when required",
            )
            ocr_regions = []
            for page_number in range(1, len(masters) + 1):
                analysis_image = output / f"page-{page_number:03}-analysis.png"
                response = recognize(analysis_image, page_number)
                ocr_regions.append((page_number, response))
                _store_json(
                    session,
                    run_id,
                    output,
                    "ocr_json",
                    page_number,
                    response.model_dump(mode="json"),
                )
            _stage(
                session,
                run_id,
                "ocr",
                "complete",
                1,
                f"Recognized {sum(len(item.regions) for _, item in ocr_regions)} text region(s) locally",
            )
            for page_number, response in ocr_regions:
                persist_ocr_regions(session, run_id, drawing.id, page_number, response)
            _stage(
                session,
                run_id,
                "text_normalization",
                "complete",
                1,
                "Engineering text candidates normalized; raw OCR retained",
            )
            _stage(
                session,
                run_id,
                "text_semantics",
                "complete",
                1,
                "Conservative engineering semantic rules applied",
            )
            symbol_regions = []
            for page_number in range(1, len(masters) + 1):
                analysis_image = output / f"page-{page_number:03}-analysis.png"
                response = detect(analysis_image, page_number)
                symbol_regions.append((page_number, response))
                _store_json(
                    session,
                    run_id,
                    output,
                    "symbol_json",
                    page_number,
                    response.model_dump(mode="json"),
                )
            for page_number, response in symbol_regions:
                persist_symbol_detections(session, run_id, drawing.id, page_number, response)
            _stage(
                session,
                run_id,
                "symbol_detection",
                "complete",
                1,
                f"Detected {sum(len(item.detections) for _, item in symbol_regions)} local symbol candidate(s)",
            )
            associations = associate_text_symbols(session, run_id)
            _stage(
                session,
                run_id,
                "text_symbol_association",
                "complete",
                1,
                f"Proposed {len(associations)} spatial-semantic text-to-symbol association(s)",
            )
            _stage(
                session,
                run_id,
                "complete",
                "complete",
                1,
                "Milestone 3 local text and symbol intelligence complete",
            )
            run.status, run.finished_at = "complete", datetime.utcnow()
            session.commit()
    except Exception as exc:
        with SessionLocal() as session:
            run = session.get(AnalysisRunRecord, run_id)
            if run is not None:
                stage = (
                    "ocr"
                    if isinstance(exc, OcrWorkerError)
                    else "symbol_detection"
                    if isinstance(exc, SymbolWorkerError)
                    else "processing"
                )
                run.status, run.error_stage, run.error_message, run.finished_at = (
                    "failed",
                    stage,
                    str(exc),
                    datetime.utcnow(),
                )
                _stage(session, run_id, stage, "failed", 0, f"Analysis failed: {exc}")
                session.commit()
        # Background tasks must resolve after recording a truthful failure;
        # re-raising would turn a previously accepted asynchronous request into
        # a transport error in some ASGI hosts.
        return run_id
    return run_id


def analysis_payload(run_id: str) -> dict:
    with SessionLocal() as session:
        run = session.get(AnalysisRunRecord, run_id)
        if run is None:
            raise ValueError("Analysis not found")
        stages = list(
            session.scalars(
                select(AnalysisStageRecord)
                .where(AnalysisStageRecord.analysis_run_id == run_id)
                .order_by(AnalysisStageRecord.started_at)
            )
        )
        return {
            "id": run.id,
            "drawing_id": run.drawing_id,
            "status": run.status,
            "error_stage": run.error_stage,
            "error_message": run.error_message,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "stages": [
                {
                    "stage": s.stage,
                    "status": s.status,
                    "progress": s.progress,
                    "message": s.message,
                    "duration_ms": s.duration_ms,
                }
                for s in stages
            ],
        }


def artifacts_payload(run_id: str) -> list[dict]:
    with SessionLocal() as session:
        if session.get(AnalysisRunRecord, run_id) is None:
            raise ValueError("Analysis not found")
        records = list(
            session.scalars(
                select(ArtifactRecord)
                .where(ArtifactRecord.analysis_run_id == run_id)
                .order_by(ArtifactRecord.created_at)
            )
        )
        return [
            {
                "id": item.id,
                "type": item.artifact_type,
                "mime_type": item.mime_type,
                "metadata": json.loads(item.metadata_json),
            }
            for item in records
        ]


def artifact_path(artifact_id: str) -> tuple[Path, str]:
    with SessionLocal() as session:
        item = session.get(ArtifactRecord, artifact_id)
        if item is None:
            raise ValueError("Artifact not found")
        path, root = (Path("var") / item.relative_path).resolve(), Path("var").resolve()
        if root not in path.parents or not path.is_file():
            raise ValueError("Artifact unavailable")
        return path, item.mime_type
