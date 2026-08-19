from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import select

from engine.sldgraph.ocr.text_intelligence import classify_text, normalize_engineering_text
from services.api.app.db.database import SessionLocal
from services.api.app.db.entities import TextEvidenceRecord, TextReviewActionRecord


def persist_ocr_regions(
    session, analysis_run_id: str, drawing_id: str, page: int, response
) -> list[TextEvidenceRecord]:
    records = []
    for region in response.regions:
        normalized = normalize_engineering_text(region.text)
        semantic = classify_text(normalized.normalized_text)
        record = TextEvidenceRecord(
            id=str(uuid.uuid4()),
            analysis_run_id=analysis_run_id,
            drawing_id=drawing_id,
            page=page,
            raw_text=region.text,
            normalized_text=normalized.normalized_text,
            text_type=semantic.text_type.value,
            confidence_ocr=region.confidence,
            confidence_normalization=normalized.confidence,
            confidence_semantic=semantic.confidence,
            bbox_normalized_json=json.dumps(region.bbox_normalized),
            polygon_normalized_json=json.dumps(region.polygon),
            rotation_deg=region.rotation_deg,
            engine=response.engine,
            model=response.model,
            provenance="local_ocr",
            review_status="pending" if normalized.requires_review else "unreviewed",
            association_json=json.dumps(
                {
                    "selected_entity": None,
                    "candidates": [],
                    "normalization_evidence": normalized.evidence,
                    "semantic_evidence": semantic.evidence,
                }
            ),
        )
        session.add(record)
        records.append(record)
    return records


def serialize_text(record: TextEvidenceRecord) -> dict:
    return {
        "id": record.id,
        "analysis_run_id": record.analysis_run_id,
        "drawing_id": record.drawing_id,
        "page": record.page,
        "raw_text": record.raw_text,
        "normalized_text": record.normalized_text,
        "text_type": record.text_type,
        "confidence_ocr": record.confidence_ocr,
        "confidence_normalization": record.confidence_normalization,
        "confidence_semantic": record.confidence_semantic,
        "bbox_normalized": json.loads(record.bbox_normalized_json),
        "polygon_normalized": json.loads(record.polygon_normalized_json),
        "rotation_deg": record.rotation_deg,
        "engine": record.engine,
        "model": record.model,
        "provenance": record.provenance,
        "review_status": record.review_status,
        "engineer_value": record.engineer_value,
        "engineer_text_type": record.engineer_text_type,
        "association": json.loads(record.association_json),
        "created_at": record.created_at.isoformat(),
    }


def texts_for_analysis(analysis_run_id: str) -> list[dict]:
    with SessionLocal() as session:
        records = list(
            session.scalars(
                select(TextEvidenceRecord)
                .where(TextEvidenceRecord.analysis_run_id == analysis_run_id)
                .order_by(TextEvidenceRecord.created_at)
            )
        )
        return [serialize_text(record) for record in records]


def text_by_id(text_id: str) -> dict:
    with SessionLocal() as session:
        record = session.get(TextEvidenceRecord, text_id)
        if record is None:
            raise ValueError("Text evidence not found")
        return serialize_text(record)


def text_summary(analysis_run_id: str) -> dict:
    records = texts_for_analysis(analysis_run_id)
    by_type: dict[str, int] = {}
    for record in records:
        by_type[record["text_type"]] = by_type.get(record["text_type"], 0) + 1
    return {
        "recognized": len(records),
        "by_type": by_type,
        "needs_review": sum(item["review_status"] == "pending" for item in records),
    }


def update_text(
    text_id: str, value: str | None, text_type: str | None, action: str = "edit"
) -> dict:
    with SessionLocal() as session:
        record = session.get(TextEvidenceRecord, text_id)
        if record is None:
            raise ValueError("Text evidence not found")
        old_value, old_type = (
            record.engineer_value or record.normalized_text,
            record.engineer_text_type or record.text_type,
        )
        if value is not None:
            record.engineer_value = value.strip()
        if text_type is not None:
            record.engineer_text_type = text_type
        if action == "accept":
            record.review_status = "accepted"
        elif action == "reject":
            record.review_status = "rejected"
        elif action == "unknown":
            record.engineer_text_type, record.review_status = "unknown", "accepted"
        else:
            record.review_status = "edited"
        session.add(
            TextReviewActionRecord(
                id=str(uuid.uuid4()),
                text_evidence_id=text_id,
                action=action,
                old_value=old_value,
                new_value=record.engineer_value or record.normalized_text,
                old_text_type=old_type,
                new_text_type=record.engineer_text_type or record.text_type,
                actor="engineer",
                created_at=datetime.utcnow(),
            )
        )
        session.commit()
        session.refresh(record)
        return serialize_text(record)
