from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.api.app.db.database import Base


class ProjectRecord(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    drawings: Mapped[list["DrawingRecord"]] = relationship(back_populates="project")


class DrawingRecord(Base):
    __tablename__ = "drawings"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    safe_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    input_type: Mapped[str] = mapped_column(String(32), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    inspection_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    project: Mapped[ProjectRecord] = relationship(back_populates="drawings")
    analyses: Mapped[list["AnalysisRunRecord"]] = relationship(back_populates="drawing")


class AnalysisRunRecord(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    drawing_id: Mapped[str] = mapped_column(ForeignKey("drawings.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(32), nullable=False)
    error_stage: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    drawing: Mapped[DrawingRecord] = relationship(back_populates="analyses")
    stages: Mapped[list["AnalysisStageRecord"]] = relationship(back_populates="analysis_run")
    artifacts: Mapped[list["ArtifactRecord"]] = relationship(back_populates="analysis_run")
    texts: Mapped[list["TextEvidenceRecord"]] = relationship(back_populates="analysis_run")
    symbols: Mapped[list["SymbolEvidenceRecord"]] = relationship(back_populates="analysis_run")
    conductors: Mapped[list["ConductorEvidenceRecord"]] = relationship(back_populates="analysis_run")
    buses: Mapped[list["BusbarEvidenceRecord"]] = relationship(back_populates="analysis_run")
    junctions: Mapped[list["JunctionEvidenceRecord"]] = relationship(back_populates="analysis_run")
    terminals: Mapped[list["TerminalEvidenceRecord"]] = relationship(back_populates="analysis_run")
    connection_candidates: Mapped[list["ConnectionCandidateRecord"]] = relationship(back_populates="analysis_run")
    physical_connections: Mapped[list["PhysicalConnectionRecord"]] = relationship(back_populates="analysis_run")
    topology_issues: Mapped[list["TopologyIssueRecord"]] = relationship(back_populates="analysis_run")
    source_assignments: Mapped[list["SourceAssignmentRecord"]] = relationship(back_populates="analysis_run")
    feeders: Mapped[list["FeederRecord"]] = relationship(back_populates="analysis_run")
    feeder_paths: Mapped[list["FeederPathRecord"]] = relationship(back_populates="analysis_run")
    validation_issues: Mapped[list["ValidationIssueRecord"]] = relationship(back_populates="analysis_run")
    electrical_review_issues: Mapped[list["ElectricalReviewIssueRecord"]] = relationship(back_populates="analysis_run")
    switch_states: Mapped[list["SwitchStateRecord"]] = relationship(back_populates="analysis_run")
    scenarios: Mapped[list["ScenarioRunRecord"]] = relationship(back_populates="analysis_run")
    export_artifacts: Mapped[list["ExportArtifactRecord"]] = relationship(back_populates="analysis_run")


class AnalysisStageRecord(Base):
    __tablename__ = "analysis_stages"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    progress: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="stages")


class ArtifactRecord(Base):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="artifacts")


class TextEvidenceRecord(Base):
    __tablename__ = "text_evidence"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    drawing_id: Mapped[str] = mapped_column(ForeignKey("drawings.id"), index=True)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    text_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_ocr: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_normalization: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_semantic: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_normalized_json: Mapped[str] = mapped_column(Text, nullable=False)
    polygon_normalized_json: Mapped[str] = mapped_column(Text, nullable=False)
    rotation_deg: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engine: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    provenance: Mapped[str] = mapped_column(String(100), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    engineer_value: Mapped[str | None] = mapped_column(Text)
    engineer_text_type: Mapped[str | None] = mapped_column(String(64))
    association_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="texts")
    review_actions: Mapped[list["TextReviewActionRecord"]] = relationship(
        back_populates="text_evidence"
    )
    symbol_associations: Mapped[list["TextSymbolAssociationRecord"]] = relationship(
        back_populates="text_evidence"
    )


class TextReviewActionRecord(Base):
    __tablename__ = "text_review_actions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    text_evidence_id: Mapped[str] = mapped_column(ForeignKey("text_evidence.id"), index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    old_text_type: Mapped[str | None] = mapped_column(String(64))
    new_text_type: Mapped[str | None] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(64), default="engineer", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    text_evidence: Mapped[TextEvidenceRecord] = relationship(back_populates="review_actions")


class SymbolEvidenceRecord(Base):
    __tablename__ = "symbol_evidence"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    drawing_id: Mapped[str] = mapped_column(ForeignKey("drawings.id"), index=True)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_class: Mapped[str] = mapped_column(String(64), nullable=False)
    original_predicted_class: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[float | None] = mapped_column(Float)
    bbox_normalized_json: Mapped[str] = mapped_column(Text, nullable=False)
    polygon_normalized_json: Mapped[str] = mapped_column(Text, nullable=False)
    orientation_deg: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tile_origin_json: Mapped[str | None] = mapped_column(Text)
    engine: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    provenance: Mapped[str] = mapped_column(String(100), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    review_reason: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="symbols")
    review_actions: Mapped[list["SymbolReviewActionRecord"]] = relationship(
        back_populates="symbol_evidence"
    )
    text_associations: Mapped[list["TextSymbolAssociationRecord"]] = relationship(
        back_populates="symbol_evidence"
    )


class SymbolReviewActionRecord(Base):
    __tablename__ = "symbol_review_actions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol_evidence_id: Mapped[str] = mapped_column(ForeignKey("symbol_evidence.id"), index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    old_class: Mapped[str | None] = mapped_column(String(64))
    new_class: Mapped[str | None] = mapped_column(String(64))
    old_bbox_json: Mapped[str | None] = mapped_column(Text)
    new_bbox_json: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(64), default="engineer", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    symbol_evidence: Mapped[SymbolEvidenceRecord] = relationship(back_populates="review_actions")


class TextSymbolAssociationRecord(Base):
    __tablename__ = "text_symbol_associations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    text_evidence_id: Mapped[str] = mapped_column(ForeignKey("text_evidence.id"), index=True)
    symbol_evidence_id: Mapped[str] = mapped_column(ForeignKey("symbol_evidence.id"), index=True)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    factors_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="proposed", nullable=False)
    provenance: Mapped[str] = mapped_column(
        String(100), default="spatial_semantic_rules", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    text_evidence: Mapped[TextEvidenceRecord] = relationship(back_populates="symbol_associations")
    symbol_evidence: Mapped[SymbolEvidenceRecord] = relationship(back_populates="text_associations")


class ConductorEvidenceRecord(Base):
    __tablename__ = "conductor_evidence"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    drawing_id: Mapped[str] = mapped_column(ForeignKey("drawings.id"), index=True)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    polyline_json: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    provenance: Mapped[str] = mapped_column(String(100), nullable=False)
    masked_interruption: Mapped[bool] = mapped_column(default=False, nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), default="unreviewed", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="conductors")


class BusbarEvidenceRecord(Base):
    __tablename__ = "busbar_evidence"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    drawing_id: Mapped[str] = mapped_column(ForeignKey("drawings.id"), index=True)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    polyline_json: Mapped[str] = mapped_column(Text, nullable=False)
    bbox_normalized_json: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    provenance: Mapped[str] = mapped_column(String(100), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    associated_symbol_id: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="buses")


class JunctionEvidenceRecord(Base):
    __tablename__ = "junction_evidence"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    drawing_id: Mapped[str] = mapped_column(ForeignKey("drawings.id"), index=True)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    position_json: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(48), nullable=False)
    degree: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    provenance: Mapped[str] = mapped_column(String(100), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="junctions")


class TerminalEvidenceRecord(Base):
    __tablename__ = "terminal_evidence"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    drawing_id: Mapped[str] = mapped_column(ForeignKey("drawings.id"), index=True)
    symbol_evidence_id: Mapped[str] = mapped_column(ForeignKey("symbol_evidence.id"), index=True)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    symbol_class: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    position_json: Mapped[str] = mapped_column(Text, nullable=False)
    orientation_deg: Mapped[int] = mapped_column(Integer, nullable=False)
    orientation_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    provenance: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="terminals")


class ConnectionCandidateRecord(Base):
    __tablename__ = "connection_candidates"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    drawing_id: Mapped[str] = mapped_column(ForeignKey("drawings.id"), index=True)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    from_node_id: Mapped[str] = mapped_column(String(120), nullable=False)
    to_node_id: Mapped[str] = mapped_column(String(120), nullable=False)
    conductor_evidence_id: Mapped[str | None] = mapped_column(String(80))
    polyline_json: Mapped[str] = mapped_column(Text, nullable=False)
    visual_continuity_score: Mapped[float] = mapped_column(Float, nullable=False)
    endpoint_distance_score: Mapped[float] = mapped_column(Float, nullable=False)
    orientation_score: Mapped[float] = mapped_column(Float, nullable=False)
    terminal_score: Mapped[float] = mapped_column(Float, nullable=False)
    junction_score: Mapped[float] = mapped_column(Float, nullable=False)
    electrical_structural_score: Mapped[float] = mapped_column(Float, nullable=False)
    overall_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    provenance: Mapped[str] = mapped_column(String(120), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    review_reason: Mapped[str | None] = mapped_column(String(100))
    gap_bridge: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="connection_candidates")


class PhysicalConnectionRecord(Base):
    __tablename__ = "physical_connections"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    drawing_id: Mapped[str] = mapped_column(ForeignKey("drawings.id"), index=True)
    candidate_id: Mapped[str | None] = mapped_column(ForeignKey("connection_candidates.id"), index=True)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    from_node_id: Mapped[str] = mapped_column(String(120), nullable=False)
    to_node_id: Mapped[str] = mapped_column(String(120), nullable=False)
    polyline_json: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    provenance: Mapped[str] = mapped_column(String(120), nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    review_reason: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="physical_connections")
    review_actions: Mapped[list["TopologyReviewActionRecord"]] = relationship(back_populates="connection")


class TopologyIssueRecord(Base):
    __tablename__ = "topology_issues"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    kind: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    related_edge_id: Mapped[str | None] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="topology_issues")


class TopologyReviewActionRecord(Base):
    __tablename__ = "topology_review_actions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    physical_connection_id: Mapped[str | None] = mapped_column(ForeignKey("physical_connections.id"), index=True)
    junction_evidence_id: Mapped[str | None] = mapped_column(ForeignKey("junction_evidence.id"), index=True)
    action: Mapped[str] = mapped_column(String(48), nullable=False)
    prior_status: Mapped[str | None] = mapped_column(String(32))
    new_status: Mapped[str | None] = mapped_column(String(32))
    payload_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    actor: Mapped[str] = mapped_column(String(64), default="engineer", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    connection: Mapped[PhysicalConnectionRecord | None] = relationship(back_populates="review_actions")


class SourceAssignmentRecord(Base):
    __tablename__ = "source_assignments"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    feeder_id: Mapped[str | None] = mapped_column(String(120), index=True)
    source_equipment_id: Mapped[str] = mapped_column(String(120), nullable=False)
    source_role: Mapped[str] = mapped_column(String(80), nullable=False)
    resolution: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    provenance_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="source_assignments")


class FeederRecord(Base):
    __tablename__ = "feeders"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    equipment_id: Mapped[str] = mapped_column(String(120), nullable=False)
    feeder_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_bus_equipment_id: Mapped[str | None] = mapped_column(String(120))
    destination_equipment_id: Mapped[str | None] = mapped_column(String(120))
    voltage: Mapped[str | None] = mapped_column(String(100))
    rating: Mapped[str | None] = mapped_column(String(255))
    resolution: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    provenance_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    review_status: Mapped[str] = mapped_column(String(32), default="inferred", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="feeders")


class FeederPathRecord(Base):
    __tablename__ = "feeder_paths"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    feeder_record_id: Mapped[str] = mapped_column(ForeignKey("feeders.id"), index=True)
    source_equipment_id: Mapped[str | None] = mapped_column(String(120))
    equipment_path_json: Mapped[str] = mapped_column(Text, nullable=False)
    connection_path_json: Mapped[str] = mapped_column(Text, nullable=False)
    switching_equipment_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    weakest_connection_id: Mapped[str | None] = mapped_column(String(120))
    weakest_connection_confidence: Mapped[float | None] = mapped_column(Float)
    uncertainty_flags_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(nullable=False)
    provenance_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="feeder_paths")


class ValidationIssueRecord(Base):
    __tablename__ = "validation_issues"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="validation_issues")


class ElectricalReviewIssueRecord(Base):
    __tablename__ = "electrical_review_issues"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    issue_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(120), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    factors_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    affected_feeders_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    affected_nodes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    source_assignment_changes_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    component_change: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    review_action: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="electrical_review_issues")


class SwitchStateRecord(Base):
    __tablename__ = "switch_states"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    equipment_id: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    provenance: Mapped[str] = mapped_column(String(100), default="unresolved", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="switch_states")


class ScenarioRunRecord(Base):
    __tablename__ = "scenario_runs"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    name: Mapped[str | None] = mapped_column(String(200))
    overrides_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    saved: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="scenarios")


class ExportArtifactRecord(Base):
    __tablename__ = "export_artifacts"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    export_type: Mapped[str] = mapped_column(String(32), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    analysis_run: Mapped[AnalysisRunRecord] = relationship(back_populates="export_artifacts")
