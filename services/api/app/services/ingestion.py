from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select

from engine.sldgraph.ingestion.inspection import InputInspection, inspect_input
from services.api.app.db.database import SessionLocal
from services.api.app.db.entities import DrawingRecord, ProjectRecord

UPLOAD_ROOT = Path("var/uploads")
ALLOWED = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
}
MAX_BYTES = 50 * 1024 * 1024


def create_project(name: str, description: str = "") -> ProjectRecord:
    clean_name, clean_description = name.strip(), description.strip()
    if not clean_name:
        raise HTTPException(422, "Project name is required")
    if len(clean_name) > 200 or len(clean_description) > 2000:
        raise HTTPException(422, "Project name or description exceeds the configured limit")
    record = ProjectRecord(id=str(uuid.uuid4()), name=clean_name, description=clean_description)
    with SessionLocal() as session:
        session.add(record)
        session.commit()
        session.refresh(record)
    return record


def list_projects() -> list[ProjectRecord]:
    with SessionLocal() as session:
        return list(
            session.scalars(select(ProjectRecord).order_by(ProjectRecord.created_at.desc()))
        )


def get_project(project_id: str) -> ProjectRecord:
    with SessionLocal() as session:
        record = session.get(ProjectRecord, project_id)
        if record is None:
            raise HTTPException(404, "Project not found")
        session.expunge(record)
        return record


async def store_drawing(project_id: str, upload: UploadFile) -> DrawingRecord:
    get_project(project_id)
    original = Path(upload.filename or "upload").name
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(415, "Only PNG, JPG, JPEG, and PDF are supported")
    drawing_id = str(uuid.uuid4())
    destination = UPLOAD_ROOT / project_id / drawing_id / f"original{suffix}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest, total = hashlib.sha256(), 0
    with destination.open("wb") as output:
        while chunk := await upload.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_BYTES:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(413, "Upload exceeds 50 MiB limit")
            digest.update(chunk)
            output.write(chunk)
    try:
        inspection = inspect_input(destination)
    except Exception as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(422, f"File could not be decoded: {exc}") from exc
    record = DrawingRecord(
        id=drawing_id,
        project_id=project_id,
        original_filename=original,
        safe_filename=destination.name,
        mime_type=ALLOWED[suffix],
        sha256=digest.hexdigest(),
        file_size_bytes=total,
        input_type=inspection.input_type.value,
        page_count=inspection.page_count,
        width=inspection.width,
        height=inspection.height,
        inspection_json=inspection.model_dump_json(),
    )
    with SessionLocal() as session:
        session.add(record)
        session.commit()
        session.refresh(record)
    return record


def drawings_for_project(project_id: str) -> list[DrawingRecord]:
    with SessionLocal() as session:
        return list(
            session.scalars(select(DrawingRecord).where(DrawingRecord.project_id == project_id))
        )


def get_drawing(drawing_id: str) -> DrawingRecord:
    with SessionLocal() as session:
        record = session.get(DrawingRecord, drawing_id)
        if record is None:
            raise HTTPException(404, "Drawing not found")
        session.expunge(record)
        return record


def serialize_drawing(record: DrawingRecord) -> dict:
    inspection = InputInspection.model_validate_json(record.inspection_json)
    return {
        "id": record.id,
        "project_id": record.project_id,
        "original_filename": record.original_filename,
        "mime_type": record.mime_type,
        "sha256": record.sha256,
        "file_size_bytes": record.file_size_bytes,
        "created_at": record.created_at.isoformat(),
        **inspection.model_dump(mode="json"),
    }
