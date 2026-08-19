"""Persistent symbol evidence, transparent text fusion, and auditable local review actions."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import select

from engine.sldgraph.ocr.text_intelligence import TextType
from engine.sldgraph.symbols import SymbolClass
from services.api.app.db.database import SessionLocal
from services.api.app.db.entities import (
    SymbolEvidenceRecord,
    SymbolReviewActionRecord,
    TextEvidenceRecord,
    TextSymbolAssociationRecord,
)


def _bbox(record) -> tuple[float, float, float, float]:
    return tuple(json.loads(record.bbox_normalized_json))


def _expected_classes(text: TextEvidenceRecord) -> set[str]:
    value = (text.engineer_value or text.normalized_text).upper()
    if text.text_type == TextType.FEEDER_ID.value:
        return {SymbolClass.FEEDER_TERMINAL.value}
    if text.text_type == TextType.BUS_ID.value:
        return {SymbolClass.BUSBAR.value}
    if text.text_type == TextType.POWER_RATING.value:
        return {SymbolClass.POWER_TRANSFORMER.value}
    if text.text_type == TextType.CURRENT_RATING.value:
        return {SymbolClass.CIRCUIT_BREAKER.value, SymbolClass.FEEDER_TERMINAL.value}
    if text.text_type == TextType.VOLTAGE.value:
        return {SymbolClass.POWER_TRANSFORMER.value, SymbolClass.ENERGY_SOURCE.value}
    prefixes = {
        "TR-": SymbolClass.POWER_TRANSFORMER.value,
        "CB-": SymbolClass.CIRCUIT_BREAKER.value,
        "DS-": SymbolClass.DISCONNECTOR.value,
        "CT-": SymbolClass.CURRENT_TRANSFORMER.value,
        "PT-": SymbolClass.POTENTIAL_TRANSFORMER.value,
        "BC-": SymbolClass.BUS_COUPLER.value,
        "GRID-": SymbolClass.ENERGY_SOURCE.value,
        "LOAD-": SymbolClass.LOAD.value,
    }
    return {symbol_class for prefix, symbol_class in prefixes.items() if value.startswith(prefix)}


def _score(text: TextEvidenceRecord, symbol: SymbolEvidenceRecord) -> tuple[float, dict]:
    text_box, symbol_box = _bbox(text), _bbox(symbol)
    tx, ty = (text_box[0] + text_box[2]) / 2, (text_box[1] + text_box[3]) / 2
    sx, sy = (symbol_box[0] + symbol_box[2]) / 2, (symbol_box[1] + symbol_box[3]) / 2
    distance = max(0.0, 1.0 - min(1.0, ((tx - sx) ** 2 + (ty - sy) ** 2) ** 0.5 / 0.24))
    alignment = 1.0 - min(1.0, abs(tx - sx) / 0.22)
    expected = _expected_classes(text)
    semantic = 1.0 if symbol.predicted_class in expected else 0.0
    score = 0.52 * distance + 0.3 * semantic + 0.18 * alignment
    return round(score, 4), {
        "distance": round(distance, 4),
        "orientation": 1.0,
        "semantic": semantic,
        "alignment": round(alignment, 4),
        "context": 0.0,
    }


def persist_symbol_detections(
    session, analysis_run_id: str, drawing_id: str, page: int, response
) -> list[SymbolEvidenceRecord]:
    records = []
    for detection in response.detections:
        reason = "LOW_DETECTION_CONFIDENCE" if detection.confidence < 0.55 else None
        record = SymbolEvidenceRecord(
            id=str(uuid.uuid4()),
            analysis_run_id=analysis_run_id,
            drawing_id=drawing_id,
            page=page,
            predicted_class=detection.predicted_class.value,
            original_predicted_class=detection.predicted_class.value,
            confidence=detection.confidence,
            bbox_normalized_json=json.dumps(detection.bbox_normalized),
            polygon_normalized_json=json.dumps(detection.polygon),
            orientation_deg=detection.orientation_deg,
            tile_origin_json=json.dumps(detection.tile_origin) if detection.tile_origin else None,
            engine=response.engine,
            model=response.model,
            provenance="local_symbol_detector",
            review_status="pending" if reason else "unreviewed",
            review_reason=reason,
        )
        session.add(record)
        records.append(record)
    return records


def associate_text_symbols(session, analysis_run_id: str) -> list[TextSymbolAssociationRecord]:
    # The pipeline creates OCR and symbol records in this transaction; ensure every candidate
    # is query-visible before association rather than relying on session autoflush settings.
    session.flush()
    texts = list(
        session.scalars(
            select(TextEvidenceRecord).where(TextEvidenceRecord.analysis_run_id == analysis_run_id)
        )
    )
    symbols = list(
        session.scalars(
            select(SymbolEvidenceRecord).where(
                SymbolEvidenceRecord.analysis_run_id == analysis_run_id,
                SymbolEvidenceRecord.review_status != "rejected",
            )
        )
    )
    associations = []
    for text in texts:
        candidates = []
        for symbol in symbols:
            score, factors = _score(text, symbol)
            candidates.append(
                {
                    "symbol_id": symbol.id,
                    "score": score,
                    "factors": factors,
                    "class": symbol.predicted_class,
                }
            )
        candidates.sort(key=lambda item: item["score"], reverse=True)
        selected = candidates[0] if candidates and candidates[0]["score"] >= 0.55 else None
        text.association_json = json.dumps(
            {
                "selected_entity": selected["symbol_id"] if selected else None,
                "selected_score": selected["score"] if selected else 0.0,
                "candidates": candidates,
                "provenance": "spatial_semantic_rules",
            }
        )
        if selected:
            record = TextSymbolAssociationRecord(
                id=str(uuid.uuid4()),
                analysis_run_id=analysis_run_id,
                text_evidence_id=text.id,
                symbol_evidence_id=selected["symbol_id"],
                score=selected["score"],
                factors_json=json.dumps(selected["factors"]),
                status="proposed",
                provenance="spatial_semantic_rules",
            )
            session.add(record)
            associations.append(record)
    return associations


def serialize_symbol(
    record: SymbolEvidenceRecord, associations: list[TextSymbolAssociationRecord] | None = None
) -> dict:
    return {
        "id": record.id,
        "analysis_run_id": record.analysis_run_id,
        "drawing_id": record.drawing_id,
        "page": record.page,
        "predicted_class": record.predicted_class,
        "original_predicted_class": record.original_predicted_class,
        "confidence": record.confidence,
        "bbox_normalized": json.loads(record.bbox_normalized_json),
        "polygon_normalized": json.loads(record.polygon_normalized_json),
        "orientation_deg": record.orientation_deg,
        "tile_origin": json.loads(record.tile_origin_json) if record.tile_origin_json else None,
        "engine": record.engine,
        "model": record.model,
        "provenance": record.provenance,
        "review_status": record.review_status,
        "review_reason": record.review_reason,
        "associations": [
            {"text_evidence_id": item.text_evidence_id, "score": item.score, "status": item.status}
            for item in associations or []
        ],
        "created_at": record.created_at.isoformat(),
    }


def symbols_for_analysis(analysis_run_id: str) -> list[dict]:
    with SessionLocal() as session:
        records = list(
            session.scalars(
                select(SymbolEvidenceRecord)
                .where(SymbolEvidenceRecord.analysis_run_id == analysis_run_id)
                .order_by(SymbolEvidenceRecord.created_at)
            )
        )
        associations = list(
            session.scalars(
                select(TextSymbolAssociationRecord).where(
                    TextSymbolAssociationRecord.analysis_run_id == analysis_run_id
                )
            )
        )
        return [
            serialize_symbol(
                record, [item for item in associations if item.symbol_evidence_id == record.id]
            )
            for record in records
        ]


def symbol_by_id(symbol_id: str) -> dict:
    with SessionLocal() as session:
        record = session.get(SymbolEvidenceRecord, symbol_id)
        if record is None:
            raise ValueError("Symbol evidence not found")
        associations = list(
            session.scalars(
                select(TextSymbolAssociationRecord).where(
                    TextSymbolAssociationRecord.symbol_evidence_id == symbol_id
                )
            )
        )
        return serialize_symbol(record, associations)


def symbol_summary(analysis_run_id: str) -> dict:
    symbols = symbols_for_analysis(analysis_run_id)
    return {
        "detected": len(symbols),
        "by_class": {
            name: sum(item["predicted_class"] == name for item in symbols)
            for name in sorted({item["predicted_class"] for item in symbols})
        },
        "associated_labels": sum(len(item["associations"]) for item in symbols),
        "needs_review": sum(item["review_status"] == "pending" for item in symbols),
    }


def update_symbol(
    symbol_id: str, action: str, predicted_class: str | None = None, bbox: list[float] | None = None
) -> dict:
    with SessionLocal() as session:
        record = session.get(SymbolEvidenceRecord, symbol_id)
        if record is None:
            raise ValueError("Symbol evidence not found")
        old_class, old_bbox = record.predicted_class, record.bbox_normalized_json
        if predicted_class is not None:
            record.predicted_class = SymbolClass(predicted_class).value
        if bbox is not None:
            if (
                len(bbox) != 4
                or any(value < 0 or value > 1 for value in bbox)
                or bbox[0] >= bbox[2]
                or bbox[1] >= bbox[3]
            ):
                raise ValueError("Invalid normalized symbol bounding box")
            record.bbox_normalized_json = json.dumps(bbox)
        record.review_status = {
            "accept": "accepted",
            "reject": "rejected",
            "verify": "verified",
        }.get(action, "edited")
        session.add(
            SymbolReviewActionRecord(
                id=str(uuid.uuid4()),
                symbol_evidence_id=record.id,
                action=action,
                old_class=old_class,
                new_class=record.predicted_class,
                old_bbox_json=old_bbox,
                new_bbox_json=record.bbox_normalized_json,
                actor="engineer",
                created_at=datetime.utcnow(),
            )
        )
        session.commit()
        session.refresh(record)
        return serialize_symbol(record)


def add_manual_symbol(
    analysis_run_id: str, drawing_id: str, page: int, predicted_class: str, bbox: list[float]
) -> dict:
    SymbolClass(predicted_class)
    if (
        len(bbox) != 4
        or any(value < 0 or value > 1 for value in bbox)
        or bbox[0] >= bbox[2]
        or bbox[1] >= bbox[3]
    ):
        raise ValueError("Invalid normalized symbol bounding box")
    with SessionLocal() as session:
        record = SymbolEvidenceRecord(
            id=str(uuid.uuid4()),
            analysis_run_id=analysis_run_id,
            drawing_id=drawing_id,
            page=page,
            predicted_class=predicted_class,
            original_predicted_class=None,
            confidence=None,
            bbox_normalized_json=json.dumps(bbox),
            polygon_normalized_json=json.dumps([]),
            orientation_deg=0,
            tile_origin_json=None,
            engine="engineer",
            model="none",
            provenance="engineer_added",
            review_status="verified",
            review_reason=None,
        )
        session.add(record)
        session.add(
            SymbolReviewActionRecord(
                id=str(uuid.uuid4()),
                symbol_evidence_id=record.id,
                action="add",
                old_class=None,
                new_class=predicted_class,
                old_bbox_json=None,
                new_bbox_json=json.dumps(bbox),
                actor="engineer",
                created_at=datetime.utcnow(),
            )
        )
        session.commit()
        session.refresh(record)
        return serialize_symbol(record)
