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
