from sqlalchemy import Column, String, Float, Integer, Text, Boolean, Index
from database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    ministry = Column(String, nullable=False)
    sector = Column(String, nullable=False)
    state = Column(String, nullable=False)
    agency = Column(String, nullable=False)
    district = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    nodal_officer = Column(String, nullable=True)
    contact_info = Column(String, nullable=True)
    original_cost = Column(Float, nullable=False)
    current_cost = Column(Float, nullable=False)
    expenditure = Column(Float, nullable=False)
    physical_progress = Column(Float, nullable=False)
    financial_progress = Column(Float, nullable=True)
    planned_progress = Column(Float, nullable=False)
    start_date = Column(String, nullable=False)
    expected_completion = Column(String, nullable=False)
    predicted_completion = Column(String, nullable=False)
    cost_overrun_probability = Column(Float, nullable=False)
    delay_probability = Column(Float, nullable=False)
    implementation_risk = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String, nullable=False)
    milestones_total = Column(Integer, nullable=False)
    milestones_delayed = Column(Integer, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    risk_factors = Column(Text, nullable=False)
    recommendations = Column(Text, nullable=False)
    risk_inputs = Column(Text, nullable=True, default="{}")
    risk_confidence = Column(Float, nullable=True)
    risk_report = Column(Text, nullable=True)
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)

    # --- Government-ingest provenance -------------------------------------------------
    # Filled by the ingestion pipeline (backend/ingest). Manual records created
    # through the API leave these NULL / defaulted.
    status = Column(String, nullable=False, default="ONGOING")  # ONGOING|COMPLETED|DELAYED|STALLED|CANCELLED
    scale = Column(String, nullable=True)  # MEDIUM|LARGE (see ingest/normalize.py)
    funding_source = Column(String, nullable=True)
    external_ref = Column(String, nullable=True)  # source record id (dedup key)
    source_name = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    retrieved_date = Column(String, nullable=True)
    data_confidence = Column(String, nullable=True)  # OFFICIAL|VERIFIED_SECONDARY|UNVERIFIED
    last_synced_at = Column(String, nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False)
    type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    description = Column(String, nullable=False)
    detected_date = Column(String, nullable=False)
    status = Column(String, nullable=False, default="ACTIVE")


class ProjectUpdate(Base):
    __tablename__ = "project_updates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    update_type = Column(String, nullable=False, default="GENERAL")
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)


class AIAnalysis(Base):
    """Persisted AI run history for a project (cache + audit trail)."""

    __tablename__ = "ai_analyses"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False, index=True)
    created_at = Column(String, nullable=False, index=True)
    analysis_type = Column(String, nullable=False)  # prediction|anomaly|emerging|explanation|insights
    model = Column(String, nullable=True)
    prediction_method = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    raw_result = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_ai_analyses_project_created", "project_id", "created_at"),
    )


class AIPrediction(Base):
    """Latest numeric prediction snapshot per project."""

    __tablename__ = "ai_predictions"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False, index=True)
    created_at = Column(String, nullable=False)
    horizon_days = Column(Integer, nullable=False, default=90)
    schedule_delay_probability = Column(Float, nullable=False)
    cost_overrun_probability = Column(Float, nullable=False)
    risk_escalation_probability = Column(Float, nullable=False)
    clearance_delay_probability = Column(Float, nullable=False)
    contractor_failure_probability = Column(Float, nullable=False)
    expected_delay_min = Column(Integer, nullable=True)
    expected_delay_max = Column(Integer, nullable=True)
    future_score = Column(Integer, nullable=True)
    current_score = Column(Integer, nullable=True)
    data_points_used = Column(Integer, nullable=True, default=0)
    confidence = Column(Float, nullable=False)
    prediction_method = Column(String, nullable=True)
    model_version = Column(String, nullable=True)
    drivers = Column(Text, nullable=True)  # JSON: list[str]

    __table_args__ = (
        Index("ix_ai_predictions_project_created", "project_id", "created_at"),
    )


class Anomaly(Base):
    """Statistical anomaly detected on a project."""

    __tablename__ = "ai_anomalies"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False, index=True)
    created_at = Column(String, nullable=False)
    type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    evidence = Column(Text, nullable=True)  # JSON: list[str]
    resolved = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_ai_anomalies_project_created", "project_id", "created_at"),
    )


class EmergingRisk(Base):
    """Emerging risk discovered from project updates (AI-extracted)."""

    __tablename__ = "ai_emerging_risks"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False, index=True)
    created_at = Column(String, nullable=False)
    category = Column(String, nullable=False)
    title = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    severity = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)  # JSON: list[str]
    recommendations = Column(Text, nullable=True)  # JSON: list[str]
    source_update_ids = Column(Text, nullable=True)  # JSON: list[int]
    status = Column(String, nullable=False, default="ACTIVE")  # ACTIVE|RESOLVED

    __table_args__ = (
        Index("ix_ai_emerging_risks_project_created", "project_id", "created_at"),
    )


class IngestAuditLog(Base):
    """Append-only provenance ledger for the ingestion pipeline.

    Every insert/update/skip/merge/reject writes a row here so every database
    state change is traceable to a source, a timestamp, and the changed
    record. No deletes: rows are soft-flagged via the audit record only.
    """

    __tablename__ = "ingest_audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, nullable=False)
    project_id = Column(String, nullable=True, index=True)
    action = Column(String, nullable=False)  # INSERT|UPDATE|SKIP|MERGE|REJECT
    detail = Column(Text, nullable=True)
    created_at = Column(String, nullable=False)
