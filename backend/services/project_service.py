"""Project creation helpers: ID generation, rule-based risk scoring,
recommendations, and alert creation.

The risk model here is intentionally RULE-BASED / deterministic (demo
quality), not ML. The backend is the source of truth for riskScore,
riskLevel and riskFactors - client-supplied values are never trusted.
"""

import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models import Project, Alert


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def next_project_id(db: Session) -> str:
    """Generate the next sequential PRJ-ID based on the max existing ID.

    Using max-ID (not count) keeps IDs unique even after deletions.
    """
    highest = 0
    for (pid,) in db.query(Project.id).all():
        if pid and pid.startswith("PRJ-"):
            try:
                n = int(pid.split("-")[1])
                if n > highest:
                    highest = n
            except (ValueError, IndexError):
                continue
    return f"PRJ-{highest + 1:03d}"


def next_alert_id(db: Session) -> str:
    highest = 0
    for (aid,) in db.query(Alert.id).all():
        if aid and aid.startswith("ALR-"):
            try:
                n = int(aid.split("-")[1])
                if n > highest:
                    highest = n
            except (ValueError, IndexError):
                continue
    return f"ALR-{highest + 1:03d}"


def _parse_date(value: str):
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d")
    except (ValueError, AttributeError):
        return None


def planned_progress_from_dates(start_date: str, completion_date: str):
    """Estimate a reference planned progress from elapsed/total duration."""
    start = _parse_date(start_date)
    completion = _parse_date(completion_date)
    if not start or not completion:
        return None
    total = (completion - start).days
    if total <= 0:
        return None
    elapsed = (datetime.now() - start).days
    pct = elapsed / total * 100
    return round(min(100.0, max(0.0, pct)), 1)


def _shift_date(date_str: str, months: int):
    d = _parse_date(date_str)
    if not d:
        return date_str
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    try:
        shifted = d.replace(year=year, month=month)
    except ValueError:
        shifted = d.replace(year=year, month=month, day=28)
    return _fmt(shifted)


def compute_project_risk(
    physical_progress: float,
    planned_progress: float,
    original_cost: float,
    current_cost: float,
    financial_progress=None,
    completion_date: str = None,
):
    """Deterministic rule-based risk assessment for a project."""
    physical = round(float(physical_progress or 0), 1)
    gap = max(0.0, round(float(planned_progress or physical) - physical, 1))
    overrun_pct = 0.0
    if original_cost and original_cost > 0:
        overrun_pct = max(0.0, round((current_cost - original_cost) / original_cost * 100, 1))
    fin_lag = financial_progress is not None and (
        physical - float(financial_progress) >= 10
    )

    delay_probability = round(min(95, gap * 2.5 + (12 if fin_lag else 0)))
    cost_overrun_probability = round(min(95, overrun_pct * 2.0 + (8 if fin_lag else 0)))
    implementation_risk = round((delay_probability + cost_overrun_probability) / 2)
    risk_score = round(min(100, 4 + gap * 2.0 + overrun_pct * 1.6 + (12 if fin_lag else 0)))

    if risk_score >= 80:
        risk_level = "CRITICAL"
    elif risk_score >= 60:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    factors = []
    if gap > 5:
        factors.append(
            f"Physical progress is {gap:.0f}% behind planned progress"
        )
    if overrun_pct > 5:
        factors.append(
            f"Cost has increased by {overrun_pct:.1f}% from original estimate"
        )
    if fin_lag:
        factors.append(
            "Financial progress is below physical progress, indicating an expenditure slowdown"
        )
    if physical < 30:
        factors.append("Very low physical progress relative to project duration")
    if not factors:
        factors.append("Project is progressing broadly as planned")

    recommendations = []
    if gap > 5:
        recommendations.append("Review the schedule variance and prepare a recovery plan")
    if overrun_pct > 5:
        recommendations.append("Undertake a detailed cost review and tighten cost controls")
    if fin_lag:
        recommendations.append("Accelerate fund utilization and expedite approval processes")
    if risk_level in ("HIGH", "CRITICAL"):
        recommendations.append("Schedule a joint monitoring committee review")
    recommendations.append("Continue routine monitoring and monthly status reporting")

    predicted_completion = completion_date
    if delay_probability >= 60:
        predicted_completion = _shift_date(completion_date or "", 12)
    elif delay_probability >= 40:
        predicted_completion = _shift_date(completion_date or "", 6)

    return {
        "costOverrunProbability": cost_overrun_probability,
        "delayProbability": delay_probability,
        "implementationRisk": implementation_risk,
        "riskScore": risk_score,
        "riskLevel": risk_level,
        "riskFactors": factors,
        "recommendations": recommendations,
        "predictedCompletion": predicted_completion,
    }


def create_alert_for_new_project(db: Session, project: Project):
    """Generate an alert for HIGH/CRITICAL newly created projects."""
    if project.risk_level not in ("HIGH", "CRITICAL"):
        return None
    alert = Alert(
        id=next_alert_id(db),
        project_id=project.id,
        type="New Project Risk Assessment",
        severity=project.risk_level,
        description=(
            f"New project {project.name} classified as {project.risk_level} risk "
            f"with a risk score of {project.risk_score:.0f}/100."
        ),
        detected_date=_fmt(datetime.now()),
        status="ACTIVE",
    )
    db.add(alert)
    db.flush()
    return alert