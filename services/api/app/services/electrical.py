"""Persistent M5 source/feeder intelligence derived from M4 physical evidence."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
import zipfile
from datetime import datetime

from sqlalchemy import delete, select

from engine.sldgraph.electrical import analyse
from engine.sldgraph.models import (
    Connection,
    ElectricalGraph,
    Equipment,
    EquipmentType,
    Geometry,
    Provenance,
    ReviewStatus,
    SwitchState,
    Terminal,
)
from engine.sldgraph.reconstruction import render_svg
from services.api.app.db.database import SessionLocal
from services.api.app.db.entities import (
    AnalysisRunRecord,
    DrawingRecord,
    ElectricalReviewIssueRecord,
    ExportArtifactRecord,
    FeederPathRecord,
    FeederRecord,
    JunctionEvidenceRecord,
    PhysicalConnectionRecord,
    SourceAssignmentRecord,
    SwitchStateRecord,
    SymbolEvidenceRecord,
    TerminalEvidenceRecord,
    TextEvidenceRecord,
    TopologyReviewActionRecord,
    ValidationIssueRecord,
)

TYPE_MAP = {"feeder_terminal": EquipmentType.FEEDER, "busbar": EquipmentType.BUSBAR}
SWITCH_TYPES = {EquipmentType.CIRCUIT_BREAKER, EquipmentType.DISCONNECTOR, EquipmentType.BUS_COUPLER}


def _status(value: str) -> ReviewStatus:
    return {
        "accepted": ReviewStatus.ACCEPTED,
        "verified": ReviewStatus.VERIFIED,
        "rejected": ReviewStatus.REJECTED,
    }.get(value, ReviewStatus.PENDING)


def _equipment_type(value: str) -> EquipmentType:
    try:
        return EquipmentType(value)
    except ValueError:
        return TYPE_MAP.get(value, EquipmentType.GENERIC_EQUIPMENT)


def _labels(session, analysis_id: str) -> dict[str, tuple[str, str, float]]:
    output: dict[str, tuple[str, str, float]] = {}
    for text in session.scalars(select(TextEvidenceRecord).where(TextEvidenceRecord.analysis_run_id == analysis_id)):
        association = json.loads(text.association_json)
        symbol_id = association.get("selected_entity")
        confidence = float(association.get("selected_score", 0))
        value = text.engineer_value or text.normalized_text
        if symbol_id and value and (symbol_id not in output or confidence > output[symbol_id][2]):
            output[symbol_id] = (value, text.engineer_text_type or text.text_type, confidence)
    return output


def graph_from_analysis(session, analysis_id: str) -> ElectricalGraph:
    symbols = list(session.scalars(select(SymbolEvidenceRecord).where(SymbolEvidenceRecord.analysis_run_id == analysis_id)))
    labels = _labels(session, analysis_id)
    states = {item.equipment_id: item.state for item in session.scalars(select(SwitchStateRecord).where(SwitchStateRecord.analysis_run_id == analysis_id))}
    equipment: list[Equipment] = []
    for symbol in symbols:
        label, text_type, text_confidence = labels.get(symbol.id, (symbol.predicted_class, "unknown", 0.0))
        kind = _equipment_type(symbol.predicted_class)
        attributes = {"text_type": text_type, "text_association_confidence": text_confidence}
        if kind in SWITCH_TYPES:
            attributes["switch_state"] = states.get(symbol.id, "unknown")
        if text_type in {"voltage", "current_rating", "power_rating"}:
            attributes["rating"] = label
        equipment.append(Equipment(
            id=symbol.id,
            equipment_id=label,
            type=kind,
            page=symbol.page,
            geometry=Geometry(bbox=tuple(json.loads(symbol.bbox_normalized_json))),
            attributes=attributes,
            confidence=float(symbol.confidence or 0.45),
            provenance=[Provenance.OCR, Provenance.VISION] if symbol.id in labels else [Provenance.VISION],
            review_status=_status(symbol.review_status),
        ))
    terminals = [Terminal(id=item.id, equipment_id=item.symbol_evidence_id, name=item.name, position=tuple(json.loads(item.position_json))) for item in session.scalars(select(TerminalEvidenceRecord).where(TerminalEvidenceRecord.analysis_run_id == analysis_id))]
    connections = [Connection(
        id=item.id,
        from_terminal_id=item.from_node_id,
        to_terminal_id=item.to_node_id,
        geometry=Geometry(polyline=[tuple(point) for point in json.loads(item.polyline_json)]),
        confidence=float(item.confidence),
        provenance=[Provenance.WIRE_TRACE, Provenance.TERMINAL_SNAP],
        review_status=_status(item.review_status),
    ) for item in session.scalars(select(PhysicalConnectionRecord).where(
        PhysicalConnectionRecord.analysis_run_id == analysis_id,
        PhysicalConnectionRecord.review_status != "rejected",
    ))]
    return ElectricalGraph(id=f"electrical:{analysis_id}", equipment=equipment, terminals=terminals, connections=connections)


def _clear(session, analysis_id: str) -> None:
    for model in (SourceAssignmentRecord, FeederPathRecord, FeederRecord, ValidationIssueRecord, ElectricalReviewIssueRecord):
        session.execute(delete(model).where(model.analysis_run_id == analysis_id))


def persist_electrical(session, analysis_id: str) -> dict:
    """Recompute semantic views only; perception artifacts are never rerun here."""
    session.flush()
    graph = graph_from_analysis(session, analysis_id)
    intelligence = analyse(graph)
    _clear(session, analysis_id)
    for source in intelligence.sources:
        session.add(SourceAssignmentRecord(id=f"source:{analysis_id}:{source.equipment_id}", analysis_run_id=analysis_id, feeder_id=None, source_equipment_id=source.equipment_id, source_role=source.source_role, resolution="candidate", confidence=source.confidence, evidence_json=json.dumps(source.evidence), provenance_json=json.dumps(source.provenance)))
    for feeder in intelligence.feeders:
        record_id = f"feeder:{analysis_id}:{feeder.equipment_id}"
        session.add(FeederRecord(id=record_id, analysis_run_id=analysis_id, equipment_id=feeder.equipment_id, feeder_id=feeder.feeder_id, source_bus_equipment_id=feeder.source_bus_equipment_id, destination_equipment_id=feeder.destination_equipment_id, voltage=feeder.voltage, rating=feeder.rating, resolution=feeder.resolution.value, confidence=feeder.confidence, provenance_json=json.dumps(feeder.provenance)))
    for path in intelligence.paths:
        feeder_id = f"feeder:{analysis_id}:{path.feeder_equipment_id}"
        session.add(FeederPathRecord(id=f"path:{analysis_id}:{path.feeder_equipment_id}", analysis_run_id=analysis_id, feeder_record_id=feeder_id, source_equipment_id=path.source_equipment_id, equipment_path_json=json.dumps(path.equipment_path), connection_path_json=json.dumps(path.connection_path), switching_equipment_ids_json=json.dumps(path.switching_equipment_ids), weakest_connection_id=path.weakest_connection_id, weakest_connection_confidence=path.weakest_connection_confidence, uncertainty_flags_json=json.dumps(path.uncertainty_flags), confidence=path.confidence, active=path.active, provenance_json=json.dumps([item.value for item in path.provenance])))
        if path.source_equipment_id:
            session.add(SourceAssignmentRecord(id=f"assignment:{analysis_id}:{path.feeder_equipment_id}", analysis_run_id=analysis_id, feeder_id=path.feeder_equipment_id, source_equipment_id=path.source_equipment_id, source_role="path_assignment", resolution="ambiguous" if "MULTIPLE_SOURCE_OR_PATH_CANDIDATES" in path.uncertainty_flags else "resolved", confidence=path.confidence, evidence_json=json.dumps(["exact physical equipment path", *path.uncertainty_flags]), provenance_json=json.dumps(["graph_reasoning"])))
    for index, finding in enumerate(intelligence.validation):
        session.add(ValidationIssueRecord(id=f"validation:{analysis_id}:{index:03}", analysis_run_id=analysis_id, code=finding.code, severity=finding.severity, message=finding.message, target_type=finding.target_type, target_id=finding.target_id))
    validation_index = len(intelligence.validation)
    for junction in session.scalars(select(JunctionEvidenceRecord).where(JunctionEvidenceRecord.analysis_run_id == analysis_id, JunctionEvidenceRecord.kind == "ambiguous_crossing")):
        session.add(ValidationIssueRecord(id=f"validation:{analysis_id}:{validation_index:03}", analysis_run_id=analysis_id, code="AMBIGUOUS_CROSSING", severity="warning", message="Crossing remains unresolved and is excluded from forced electrical connectivity.", target_type="junction", target_id=junction.id))
        validation_index += 1
    for item in intelligence.criticality:
        session.add(ElectricalReviewIssueRecord(id=f"review:{analysis_id}:{item.connection_id}", analysis_run_id=analysis_id, issue_type="TOPOLOGY_CRITICAL_CONNECTION", target_type="connection", target_id=item.connection_id, confidence=item.confidence, risk_score=item.risk_score, priority=item.priority, factors_json=json.dumps(item.risk_factors), affected_feeders_json=json.dumps(item.affected_feeders), affected_nodes_json=json.dumps(item.affected_nodes), source_assignment_changes_json=json.dumps(item.source_assignment_changes), component_change=item.component_change))
    for item in graph.equipment:
        if item.type in SWITCH_TYPES and item.id not in {state.equipment_id for state in session.scalars(select(SwitchStateRecord).where(SwitchStateRecord.analysis_run_id == analysis_id))}:
            session.add(SwitchStateRecord(id=f"switch:{analysis_id}:{item.id}", analysis_run_id=analysis_id, equipment_id=item.id, state="unknown", provenance="unresolved"))
    session.flush()
    return intelligence_payload(session, analysis_id, intelligence.health)


def recompute_electrical(analysis_id: str) -> dict:
    with SessionLocal() as session:
        if session.get(AnalysisRunRecord, analysis_id) is None:
            raise ValueError("Analysis not found")
        result = persist_electrical(session, analysis_id)
        session.commit()
        return result


def _source(record: SourceAssignmentRecord) -> dict:
    return {"equipment_id": record.source_equipment_id, "feeder_id": record.feeder_id, "source_role": record.source_role, "resolution": record.resolution, "confidence": record.confidence, "evidence": json.loads(record.evidence_json), "provenance": json.loads(record.provenance_json)}


def _feeder(session, record: FeederRecord) -> dict:
    path = session.get(FeederPathRecord, f"path:{record.analysis_run_id}:{record.equipment_id}")
    return {"id": record.id, "equipment_id": record.equipment_id, "feeder_id": record.feeder_id, "source_bus_equipment_id": record.source_bus_equipment_id, "destination_equipment_id": record.destination_equipment_id, "voltage": record.voltage, "rating": record.rating, "resolution": record.resolution, "confidence": record.confidence, "provenance": json.loads(record.provenance_json), "review_status": record.review_status, "path": _path(path) if path else None}


def _path(record: FeederPathRecord) -> dict:
    return {"id": record.id, "source_equipment_id": record.source_equipment_id, "equipment_path": json.loads(record.equipment_path_json), "connection_path": json.loads(record.connection_path_json), "switching_equipment_ids": json.loads(record.switching_equipment_ids_json), "weakest_connection_id": record.weakest_connection_id, "weakest_connection_confidence": record.weakest_connection_confidence, "uncertainty_flags": json.loads(record.uncertainty_flags_json), "confidence": record.confidence, "active": record.active, "provenance": json.loads(record.provenance_json)}


def _validation(record: ValidationIssueRecord) -> dict:
    return {"id": record.id, "code": record.code, "severity": record.severity, "message": record.message, "target_type": record.target_type, "target_id": record.target_id, "status": record.status}


def _review(record: ElectricalReviewIssueRecord) -> dict:
    return {"id": record.id, "issue_type": record.issue_type, "target_type": record.target_type, "target_id": record.target_id, "confidence": record.confidence, "risk_score": record.risk_score, "priority": record.priority, "risk_factors": json.loads(record.factors_json), "affected_feeders": json.loads(record.affected_feeders_json), "affected_nodes": json.loads(record.affected_nodes_json), "source_assignment_changes": json.loads(record.source_assignment_changes_json), "component_change": record.component_change, "status": record.status, "review_action": record.review_action}


def intelligence_payload(session, analysis_id: str, health: dict | None = None) -> dict:
    equipment_labels = {
        item.id: item.equipment_id for item in graph_from_analysis(session, analysis_id).equipment
    }
    feeders = list(session.scalars(select(FeederRecord).where(FeederRecord.analysis_run_id == analysis_id).order_by(FeederRecord.feeder_id)))
    validation = list(session.scalars(select(ValidationIssueRecord).where(ValidationIssueRecord.analysis_run_id == analysis_id)))
    review = list(session.scalars(select(ElectricalReviewIssueRecord).where(ElectricalReviewIssueRecord.analysis_run_id == analysis_id).order_by(ElectricalReviewIssueRecord.risk_score.desc())))
    sources = list(session.scalars(select(SourceAssignmentRecord).where(SourceAssignmentRecord.analysis_run_id == analysis_id, SourceAssignmentRecord.feeder_id.is_(None))))
    if health is None:
        health = {"status": "Critical" if any(item.severity == "error" for item in validation) else "Review Needed" if validation or review else "Healthy", "sources": len(sources), "feeders": len(feeders), "resolved_paths": sum(item.resolution == "resolved" for item in feeders), "review_items": len(review), "critical_issues": sum(item.priority == "CRITICAL" for item in review)}
    return {"id": f"electrical:{analysis_id}", "kind": "semantic_electrical", "equipment_labels": equipment_labels, "sources": [_source(item) for item in sources], "feeders": [_feeder(session, item) for item in feeders], "validation": [_validation(item) for item in validation], "review_issues": [_review(item) for item in review], "switch_states": [{"equipment_id": item.equipment_id, "state": item.state, "provenance": item.provenance} for item in session.scalars(select(SwitchStateRecord).where(SwitchStateRecord.analysis_run_id == analysis_id))], "health": health}


def electrical_graph(analysis_id: str) -> dict:
    with SessionLocal() as session:
        return intelligence_payload(session, analysis_id)


def sources_for_analysis(analysis_id: str) -> list[dict]:
    return electrical_graph(analysis_id)["sources"]


def feeders_for_analysis(analysis_id: str) -> list[dict]:
    return electrical_graph(analysis_id)["feeders"]


def feeder_trace(feeder_id: str) -> dict:
    with SessionLocal() as session:
        feeder = session.get(FeederRecord, feeder_id)
        if feeder is None:
            raise ValueError("Feeder not found")
        payload = _feeder(session, feeder)
        assignment = session.get(SourceAssignmentRecord, f"assignment:{feeder.analysis_run_id}:{feeder.equipment_id}")
        payload["assignment"] = _source(assignment) if assignment else None
        payload["affecting_reviews"] = [_review(item) for item in session.scalars(select(ElectricalReviewIssueRecord).where(ElectricalReviewIssueRecord.analysis_run_id == feeder.analysis_run_id)) if feeder.equipment_id in json.loads(item.affected_feeders_json)]
        return payload


def set_switch_state(analysis_id: str, equipment_id: str, state: str, provenance: str = "engineer") -> dict:
    if state not in {item.value for item in SwitchState}:
        raise ValueError("Unsupported switch state")
    with SessionLocal() as session:
        record = session.get(SwitchStateRecord, f"switch:{analysis_id}:{equipment_id}")
        if record is None:
            raise ValueError("Switch equipment not found")
        record.state, record.provenance, record.updated_at = state, provenance, datetime.utcnow()
        persist_electrical(session, analysis_id)
        session.commit()
        return intelligence_payload(session, analysis_id)


def simulate(analysis_id: str, overrides: dict[str, str], save: bool = False, name: str | None = None) -> dict:
    parsed = {key: SwitchState(value) for key, value in overrides.items()}
    with SessionLocal() as session:
        graph = graph_from_analysis(session, analysis_id)
        result = analyse(graph, parsed)
        payload = {"analysis_run_id": analysis_id, "overrides": {key: value.value for key, value in parsed.items()}, "health": result.health, "feeders": [{"equipment_id": item.equipment_id, "feeder_id": item.feeder_id, "resolution": item.resolution.value, "source_bus_equipment_id": item.source_bus_equipment_id, "confidence": item.confidence} for item in result.feeders], "paths": [{"feeder_equipment_id": item.feeder_equipment_id, "source_equipment_id": item.source_equipment_id, "equipment_path": item.equipment_path, "uncertainty_flags": item.uncertainty_flags} for item in result.paths]}
        if save:
            from services.api.app.db.entities import ScenarioRunRecord
            session.add(ScenarioRunRecord(id=str(uuid.uuid4()), analysis_run_id=analysis_id, name=name, overrides_json=json.dumps(payload["overrides"]), result_json=json.dumps(payload), saved=True))
            session.commit()
        return payload


def review_issue(issue_id: str, action: str) -> dict:
    if action not in {"accept", "reject"}:
        raise ValueError("Unsupported review action")
    with SessionLocal() as session:
        issue = session.get(ElectricalReviewIssueRecord, issue_id)
        if issue is None:
            raise ValueError("Review issue not found")
        issue.status, issue.review_action = ("accepted" if action == "accept" else "rejected"), action
        result_status = issue.status
        connection = session.get(PhysicalConnectionRecord, issue.target_id)
        if connection is not None:
            prior = connection.review_status
            connection.review_status = "accepted" if action == "accept" else "rejected"
            session.add(TopologyReviewActionRecord(
                id=str(uuid.uuid4()), physical_connection_id=connection.id,
                action=f"electrical_review_{action}", prior_status=prior,
                new_status=connection.review_status,
                payload_json=json.dumps({"electrical_review_issue_id": issue_id}),
                actor="engineer", created_at=datetime.utcnow(),
            ))
        persist_electrical(session, issue.analysis_run_id)
        session.commit()
        return {"id": issue_id, "status": result_status, "action": action}


def export_json(analysis_id: str) -> dict:
    with SessionLocal() as session:
        run = session.get(AnalysisRunRecord, analysis_id)
        if run is None:
            raise ValueError("Analysis not found")
        drawing = session.get(DrawingRecord, run.drawing_id)
        graph = graph_from_analysis(session, analysis_id)
        payload = intelligence_payload(session, analysis_id)
        return {"schema_version": "sldgraph-x/electrical-1", "project": {"id": drawing.project_id}, "drawing": {"id": drawing.id, "filename": drawing.original_filename, "sha256": drawing.sha256}, "analysis": {"id": analysis_id, "pipeline_version": run.pipeline_version}, "equipment": [item.model_dump(mode="json") for item in graph.equipment], "terminals": [item.model_dump(mode="json") for item in graph.terminals], "connections": [item.model_dump(mode="json") for item in graph.connections], **payload}


def reconstructed_svg(analysis_id: str) -> str:
    with SessionLocal() as session:
        if session.get(AnalysisRunRecord, analysis_id) is None:
            raise ValueError("Analysis not found")
        graph = graph_from_analysis(session, analysis_id)
        return render_svg(graph, 1600, 900)


def export_bundle(analysis_id: str) -> tuple[bytes, str]:
    payload = export_json(analysis_id)
    output = io.BytesIO()
    rows = {"equipment.csv": payload["equipment"], "connections.csv": payload["connections"], "feeders.csv": payload["feeders"], "sources.csv": payload["sources"], "validation_issues.csv": payload["validation"], "review_history.csv": payload["review_issues"]}
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("project.json", json.dumps({"project": payload["project"], "drawing": payload["drawing"], "analysis": payload["analysis"]}, indent=2))
        archive.writestr("graph.json", json.dumps(payload, indent=2))
        for name, values in rows.items():
            stream = io.StringIO()
            fields = sorted({key for value in values for key in value}) if values else ["id"]
            writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for value in values:
                writer.writerow({key: json.dumps(item) if isinstance(item, (dict, list)) else item for key, item in value.items()})
            archive.writestr(name, stream.getvalue())
        graph = ElectricalGraph(id=payload["id"], equipment=[Equipment.model_validate(item) for item in payload["equipment"]], terminals=[Terminal.model_validate(item) for item in payload["terminals"]], connections=[Connection.model_validate(item) for item in payload["connections"]])
        archive.writestr("reconstructed_sld.svg", render_svg(graph, 1600, 900))
        manifest = {"schema_version": payload["schema_version"], "graph_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest(), "files": sorted(["project.json", "graph.json", *rows, "reconstructed_sld.svg"])}
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
    contents = output.getvalue()
    with SessionLocal() as session:
        session.merge(ExportArtifactRecord(id=f"export:{analysis_id}:bundle", analysis_run_id=analysis_id, export_type="bundle", sha256=hashlib.sha256(contents).hexdigest(), manifest_json=json.dumps({"files": sorted(["project.json", "graph.json", *rows, "reconstructed_sld.svg", "manifest.json"])})))
        session.commit()
    return contents, f"sldgraph-x-{analysis_id}.zip"
