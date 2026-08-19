"""Persistence, graph payloads, and auditable review for Milestone 4 physical topology."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import select

from engine.sldgraph.topology.models import TopologyResult, TopologySymbol, TopologyText
from services.api.app.db.database import SessionLocal
from services.api.app.db.entities import (
    BusbarEvidenceRecord,
    ConductorEvidenceRecord,
    ConnectionCandidateRecord,
    JunctionEvidenceRecord,
    PhysicalConnectionRecord,
    SymbolEvidenceRecord,
    TerminalEvidenceRecord,
    TextEvidenceRecord,
    TopologyIssueRecord,
    TopologyReviewActionRecord,
)


def topology_inputs(session, analysis_run_id: str) -> tuple[list[TopologySymbol], list[TopologyText]]:
    symbols = [
        TopologySymbol(
            id=item.id,
            predicted_class=item.predicted_class,
            bbox_normalized=tuple(json.loads(item.bbox_normalized_json)),
            confidence=item.confidence,
            page=item.page,
        )
        for item in session.scalars(
            select(SymbolEvidenceRecord).where(
                SymbolEvidenceRecord.analysis_run_id == analysis_run_id,
                SymbolEvidenceRecord.review_status != "rejected",
            )
        )
    ]
    texts = [
        TopologyText(
            id=item.id,
            bbox_normalized=tuple(json.loads(item.bbox_normalized_json)),
            page=item.page,
        )
        for item in session.scalars(
            select(TextEvidenceRecord).where(TextEvidenceRecord.analysis_run_id == analysis_run_id)
        )
        if item.review_status != "rejected"
    ]
    return symbols, texts


def _id(analysis_run_id: str, raw: str) -> str:
    return f"{analysis_run_id}:{raw}"


def persist_topology(
    session, analysis_run_id: str, drawing_id: str, result: TopologyResult
) -> dict[str, int]:
    conductor_ids: dict[str, str] = {}
    candidate_ids: dict[str, str] = {}
    for item in result.conductors:
        record_id = _id(analysis_run_id, item.id)
        conductor_ids[item.id] = record_id
        session.add(ConductorEvidenceRecord(id=record_id, analysis_run_id=analysis_run_id, drawing_id=drawing_id, page=item.page, polyline_json=json.dumps(item.polyline), confidence=item.confidence, provenance=item.provenance, masked_interruption=item.masked_interruption))
    for item in result.buses:
        session.add(BusbarEvidenceRecord(id=_id(analysis_run_id, item.id), analysis_run_id=analysis_run_id, drawing_id=drawing_id, page=item.page, polyline_json=json.dumps(item.polyline), bbox_normalized_json=json.dumps(item.bbox_normalized), confidence=item.confidence, provenance=item.provenance, review_status=item.review_status, associated_symbol_id=item.associated_symbol_id))
    for item in result.junctions:
        session.add(JunctionEvidenceRecord(id=_id(analysis_run_id, item.id), analysis_run_id=analysis_run_id, drawing_id=drawing_id, page=item.page, position_json=json.dumps(item.position), kind=item.kind.value, degree=item.degree, confidence=item.confidence, provenance=item.provenance, review_status=item.review_status))
    for item in result.terminals:
        session.add(TerminalEvidenceRecord(id=item.id, analysis_run_id=analysis_run_id, drawing_id=drawing_id, symbol_evidence_id=item.symbol_id, page=item.page, symbol_class=item.symbol_class, name=item.name, position_json=json.dumps(item.position), orientation_deg=item.orientation_deg, orientation_confidence=item.orientation_confidence, provenance=item.provenance))
    for item in result.candidates:
        record_id = _id(analysis_run_id, item.id)
        candidate_ids[item.id] = record_id
        session.add(ConnectionCandidateRecord(id=record_id, analysis_run_id=analysis_run_id, drawing_id=drawing_id, page=item.page, from_node_id=item.from_node_id, to_node_id=item.to_node_id, conductor_evidence_id=conductor_ids.get(item.conductor_id or ""), polyline_json=json.dumps(item.polyline), visual_continuity_score=item.visual_continuity_score, endpoint_distance_score=item.endpoint_distance_score, orientation_score=item.orientation_score, terminal_score=item.terminal_score, junction_score=item.junction_score, electrical_structural_score=item.electrical_structural_score, overall_confidence=item.overall_confidence, provenance=item.provenance, review_status=item.review_status, review_reason=item.review_reason, gap_bridge=item.gap_bridge))
    for item in result.connections:
        candidate_id = candidate_ids.get(item.id)
        session.add(PhysicalConnectionRecord(id=_id(analysis_run_id, f"physical:{item.id}"), analysis_run_id=analysis_run_id, drawing_id=drawing_id, candidate_id=candidate_id, page=item.page, from_node_id=item.from_node_id, to_node_id=item.to_node_id, polyline_json=json.dumps(item.polyline), confidence=item.overall_confidence, provenance=item.provenance, review_status=item.review_status, review_reason=item.review_reason))
    for item in result.issues:
        session.add(TopologyIssueRecord(id=_id(analysis_run_id, item.id), analysis_run_id=analysis_run_id, kind=item.kind, message=item.message, related_edge_id=_id(analysis_run_id, f"physical:{item.related_edge_id}") if item.related_edge_id else None, severity=item.severity))
    return {"conductors": len(result.conductors), "buses": len(result.buses), "junctions": len(result.junctions), "terminals": len(result.terminals), "candidates": len(result.candidates), "connections": len(result.connections), "issues": len(result.issues)}


def _polyline(record) -> list[list[float]]:
    return json.loads(record.polyline_json)


def conductors_for_analysis(analysis_run_id: str) -> list[dict]:
    with SessionLocal() as session:
        return [{"id": item.id, "page": item.page, "polyline": _polyline(item), "confidence": item.confidence, "provenance": item.provenance, "masked_interruption": item.masked_interruption, "review_status": item.review_status} for item in session.scalars(select(ConductorEvidenceRecord).where(ConductorEvidenceRecord.analysis_run_id == analysis_run_id))]


def buses_for_analysis(analysis_run_id: str) -> list[dict]:
    with SessionLocal() as session:
        return [{"id": item.id, "page": item.page, "polyline": _polyline(item), "bbox_normalized": json.loads(item.bbox_normalized_json), "confidence": item.confidence, "provenance": item.provenance, "review_status": item.review_status, "associated_symbol_id": item.associated_symbol_id} for item in session.scalars(select(BusbarEvidenceRecord).where(BusbarEvidenceRecord.analysis_run_id == analysis_run_id))]


def junctions_for_analysis(analysis_run_id: str) -> list[dict]:
    with SessionLocal() as session:
        return [{"id": item.id, "page": item.page, "position": json.loads(item.position_json), "kind": item.kind, "degree": item.degree, "confidence": item.confidence, "provenance": item.provenance, "review_status": item.review_status} for item in session.scalars(select(JunctionEvidenceRecord).where(JunctionEvidenceRecord.analysis_run_id == analysis_run_id))]


def _serialize_connection(record: PhysicalConnectionRecord) -> dict:
    return {"id": record.id, "analysis_run_id": record.analysis_run_id, "drawing_id": record.drawing_id, "candidate_id": record.candidate_id, "page": record.page, "from_node_id": record.from_node_id, "to_node_id": record.to_node_id, "polyline": _polyline(record), "confidence": record.confidence, "provenance": record.provenance, "review_status": record.review_status, "review_reason": record.review_reason, "created_at": record.created_at.isoformat()}


def physical_graph(analysis_run_id: str) -> dict:
    with SessionLocal() as session:
        terminals = list(session.scalars(select(TerminalEvidenceRecord).where(TerminalEvidenceRecord.analysis_run_id == analysis_run_id)))
        symbols = {item.id: item for item in session.scalars(select(SymbolEvidenceRecord).where(SymbolEvidenceRecord.analysis_run_id == analysis_run_id))}
        connections = list(session.scalars(select(PhysicalConnectionRecord).where(PhysicalConnectionRecord.analysis_run_id == analysis_run_id)))
        issues = list(session.scalars(select(TopologyIssueRecord).where(TopologyIssueRecord.analysis_run_id == analysis_run_id)))
        return {"id": f"physical:{analysis_run_id}", "kind": "physical_connectivity", "nodes": [{"id": item.id, "symbol_id": item.symbol_evidence_id, "label": symbols[item.symbol_evidence_id].predicted_class if item.symbol_evidence_id in symbols else item.symbol_class, "symbol_class": item.symbol_class, "name": item.name, "position": json.loads(item.position_json), "orientation_deg": item.orientation_deg, "provenance": item.provenance} for item in terminals], "edges": [_serialize_connection(item) for item in connections], "issues": [{"id": item.id, "kind": item.kind, "message": item.message, "related_edge_id": item.related_edge_id, "severity": item.severity, "status": item.status} for item in issues]}


def connection_by_id(connection_id: str) -> dict:
    with SessionLocal() as session:
        record = session.get(PhysicalConnectionRecord, connection_id)
        if record is None:
            raise ValueError("Physical connection not found")
        return _serialize_connection(record)


def review_connection(connection_id: str, action: str) -> dict:
    if action not in {"accept", "reject", "verify"}:
        raise ValueError("Unsupported physical connection review action")
    with SessionLocal() as session:
        record = session.get(PhysicalConnectionRecord, connection_id)
        if record is None:
            raise ValueError("Physical connection not found")
        prior = record.review_status
        record.review_status = {"accept": "accepted", "reject": "rejected", "verify": "verified"}[action]
        session.add(TopologyReviewActionRecord(id=str(uuid.uuid4()), physical_connection_id=record.id, action=action, prior_status=prior, new_status=record.review_status, actor="engineer", created_at=datetime.utcnow()))
        session.commit()
        session.refresh(record)
        result, analysis_id = _serialize_connection(record), record.analysis_run_id
    from services.api.app.services.electrical import recompute_electrical

    recompute_electrical(analysis_id)
    return result


def add_manual_connection(analysis_run_id: str, drawing_id: str, from_node_id: str, to_node_id: str, page: int = 1) -> dict:
    if from_node_id == to_node_id:
        raise ValueError("A physical connection needs two distinct terminals")
    with SessionLocal() as session:
        terminals = set(
            session.scalars(
                select(TerminalEvidenceRecord.id).where(
                    TerminalEvidenceRecord.analysis_run_id == analysis_run_id,
                    TerminalEvidenceRecord.drawing_id == drawing_id,
                )
            )
        )
        if from_node_id not in terminals or to_node_id not in terminals:
            raise ValueError("Manual physical connections must reference two terminals in this analysis")
        record = PhysicalConnectionRecord(id=str(uuid.uuid4()), analysis_run_id=analysis_run_id, drawing_id=drawing_id, candidate_id=None, page=page, from_node_id=from_node_id, to_node_id=to_node_id, polyline_json="[]", confidence=1.0, provenance="engineer_added", review_status="verified", review_reason=None)
        session.add(record)
        session.add(TopologyReviewActionRecord(id=str(uuid.uuid4()), physical_connection_id=record.id, action="add", prior_status=None, new_status="verified", payload_json="{}", actor="engineer", created_at=datetime.utcnow()))
        session.commit()
        session.refresh(record)
        result = _serialize_connection(record)
    from services.api.app.services.electrical import recompute_electrical

    recompute_electrical(analysis_run_id)
    return result


def decide_crossing(junction_id: str, decision: str) -> dict:
    if decision not in {"connected", "unconnected", "unable_to_determine"}:
        raise ValueError("Unsupported crossing decision")
    with SessionLocal() as session:
        record = session.get(JunctionEvidenceRecord, junction_id)
        if record is None:
            raise ValueError("Junction evidence not found")
        prior = record.review_status
        record.kind = {"connected": "connected_junction", "unconnected": "crossover_no_connection", "unable_to_determine": "ambiguous_crossing"}[decision]
        record.review_status = "verified" if decision != "unable_to_determine" else "pending"
        session.add(TopologyReviewActionRecord(id=str(uuid.uuid4()), junction_evidence_id=record.id, action=f"crossing_{decision}", prior_status=prior, new_status=record.review_status, payload_json=json.dumps({"kind": record.kind}), actor="engineer", created_at=datetime.utcnow()))
        session.commit()
        result, analysis_id = {"id": record.id, "kind": record.kind, "review_status": record.review_status}, record.analysis_run_id
    from services.api.app.services.electrical import recompute_electrical

    recompute_electrical(analysis_id)
    return result
