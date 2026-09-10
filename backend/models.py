from sqlalchemy import Column, String, Float, Integer, Text
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
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)


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
