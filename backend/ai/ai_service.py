"""AI orchestration: runs the prediction/anomaly/emerging-risk pipeline,
persists results, caches them, and generates insights + alerts.

All heavy work happens inside short-lived sessions; functions never extend
a request-bound transaction longer than needed. Failures anywhere in the
AI layer are caught and degraded gracefully - the deterministic engine
keeps serving regardless.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from config import (
    AI_ALERT_DEDUP_HOURS,
    AI_ANALYSIS_TTL_HOURS,
    ai_logger,
)
from database import SessionLocal
from models import (
    AIPrediction,
    AIAnalysis,
    Anomaly,
    EmergingRisk,
    Project,
    ProjectUpdate,
    Alert,
)
from ai.schemas import (
    InsightsResponse,
    PredictionResult,
    ExplanationResponse,
    PREDICTION_METHOD_RULE,
)
from ai.predictor import predict
from ai.anomaly_detector import detect_anomalies, top_anomaly
from ai import emerging_risk
from ai import llm_service


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fresh(created_at: str) -> bool:
    """True when an AI record is inside the configured freshness window."""
    if not created_at:
        return False
    try:
        ts = datetime.fromisoformat(created_at)
    except (TypeError, ValueError):
        return False
    return (datetime.now(timezone.utc) - ts) < timedelta(hours=AI_ANALYSIS_TTL_HOURS)


def _prepare_update_list(db: Session, project_id: str):
    return (
        db.query(ProjectUpdate)
        .filter(ProjectUpdate.project_id == project_id)
        .order_by(ProjectUpdate.created_at.asc())
        .all()
    )


def _prepare_alert_list(db: Session, project_id: str):
    return (
        db.query(Alert)
        .filter(Alert.project_id == project_id, Alert.status == "ACTIVE")
        .all()
    )


def _load_project(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError("Project not found")
    return project


def latest_prediction(db: Session, project_id: str):
    return (
        db.query(AIPrediction)
        .filter(AIPrediction.project_id == project_id)
        .order_by(AIPrediction.created_at.desc())
        .first()
    )


def _prediction_to_dict(record) -> dict:
    return {
        "schedule_delay_probability": record.schedule_delay_probability,
        "cost_overrun_probability": record.cost_overrun_probability,
        "risk_escalation_probability": record.risk_escalation_probability,
        "clearance_delay_probability": record.clearance_delay_probability,
        "contractor_failure_probability": record.contractor_failure_probability,
        "expected_delay_months": {
            "min": record.expected_delay_min,
            "max": record.expected_delay_max,
        },
        "risk_horizon_days": record.horizon_days,
        "prediction_confidence": record.confidence,
        "future_score": record.future_score,
        "current_score": record.current_score,
        "prediction_method": record.prediction_method,
        "model_version": record.model_version,
        "top_drivers": _safe_json(record.drivers, []),
        "data_points_used": record.data_points_used,
        "generated_at": record.created_at,
    }


def _safe_json(raw, fallback):
    if not raw:
        return fallback
    try:
        value = json.loads(raw)
        return value if value is not None else fallback
    except (TypeError, ValueError):
        return fallback


def _anomaly_to_dict(record) -> dict:
    return {
        "type": record.type,
        "severity": record.severity,
        "score": record.score,
        "title": record.title,
        "description": record.description,
        "evidence": _safe_json(record.evidence, []),
        "generated_at": record.created_at,
    }


def _risk_to_dict(record) -> dict:
    return {
        "category": record.category,
        "title": record.title,
        "confidence": record.confidence,
        "severity": record.severity,
        "description": record.description,
        "evidence": _safe_json(record.evidence, []),
        "recommended_actions": _safe_json(record.recommendations, []),
        "source_update_ids": _safe_json(record.source_update_ids, []),
        "status": record.status,
        "generated_at": record.created_at,
    }


def _recent_anomalies(db: Session, project_id: str) -> list:
    rows = db.query(Anomaly).filter(Anomaly.project_id == project_id).all()
    if not rows:
        return []
    latest = max(r.created_at for r in rows)
    return [_anomaly_to_dict(r) for r in rows if r.created_at == latest]


def _active_emerging_risks(db: Session, project_id: str) -> list:
    rows = (
        db.query(EmergingRisk)
        .filter(EmergingRisk.project_id == project_id, EmergingRisk.status == "ACTIVE")
        .order_by(EmergingRisk.created_at.desc())
        .all()
    )
    return [_risk_to_dict(r) for r in rows]


def _clear_stale_predictions(db: Session, project_id: str) -> None:
    """Keep only the newest prediction per project (rolling history cap)."""
    rows = (
        db.query(AIPrediction)
        .filter(AIPrediction.project_id == project_id)
        .order_by(AIPrediction.created_at.desc())
        .all()
    )
    for stale in rows[3:]:
        db.delete(stale)


def _build_explanation(db: Session, project, prediction: PredictionResult) -> dict:
    """Deterministic explanation, optionally enriched by the LLM."""
    from services.risk_service import assess_project

    assessment = assess_project(project)
    drivers = prediction.top_drivers or ["No dominant risk driver identified"]

    deterministic = (
        f"Risk score {assessment['riskScore']}/100 ({assessment['riskLevel']}). "
        f"Top risks: {', '.join(assessment['topRisks'][:3])}. "
        f"Recommendations: {'; '.join(assessment['recommendations'][:3])}."
    )

    site = getattr(project, "state", "") or "the project"
    future = prediction.future_score if prediction.future_score is not None else assessment["riskScore"]
    summary = (
        f"{project.name} in {site} is assessed at {assessment['riskScore']}/100 "
        f"({assessment['riskLevel']}) today. Based on the latest trend signals it is "
        f"projected to reach ~{future}/100 within the next {prediction.risk_horizon_days} days. "
        f"{' '.join(drivers[:2])}."
    )

    predicted_events = []
    if prediction.schedule_delay_probability >= 0.5:
        predicted_events.append("Further schedule slippage and delayed milestones")
    if prediction.cost_overrun_probability >= 0.5:
        predicted_events.append("Continued cost escalation beyond sanctioned estimate")
    if prediction.risk_escalation_probability >= 0.5:
        predicted_events.append("Upward repricing of the project risk level")
    if not predicted_events:
        predicted_events.append("Stable trend with no imminent major event")

    li = {}
    if llm_service.is_llm_available():
        updates = db.query(ProjectUpdate).filter(
            ProjectUpdate.project_id == project.id,
        ).order_by(ProjectUpdate.created_at.desc()).limit(5).all()
        history = "\n".join(
            f"- {u.created_at}: {u.content[:200]}" for u in updates
        ) or "No historical updates available."
        li = llm_service.explain_project(deterministic, history)
        summary = li.get("summary") or summary
        predicted_events = li.get("predicted_events") or predicted_events

    return ExplanationResponse(
        summary=summary,
        current_risk=int(assessment["riskScore"]),
        future_risk=future,
        main_drivers=drivers,
        predicted_events=predicted_events,
        recommended_interventions=assessment["recommendations"],
        ai_evidence=li.get("ai_evidence", []),
    ).model_dump()


def persist_prediction(db: Session, project_id: str, result: PredictionResult) -> AIPrediction:
    record = AIPrediction(
        id=str(uuid.uuid4()),
        project_id=project_id,
        created_at=_now_iso(),
        horizon_days=result.risk_horizon_days,
        schedule_delay_probability=result.schedule_delay_probability,
        cost_overrun_probability=result.cost_overrun_probability,
        risk_escalation_probability=result.risk_escalation_probability,
        clearance_delay_probability=result.clearance_delay_probability,
        contractor_failure_probability=result.contractor_failure_probability,
        expected_delay_min=result.expected_delay_months.get("min"),
        expected_delay_max=result.expected_delay_months.get("max"),
        future_score=result.future_score,
        confidence=result.prediction_confidence,
        prediction_method=result.prediction_method,
        model_version=result.model_version,
        drivers=json.dumps(result.top_drivers),
        data_points_used=result.data_points_used,
        current_score=result.current_score,
    )
    db.add(record)
    return record


def persist_anomalies(db: Session, project_id: str, anomalies: list) -> None:
    for a in anomalies:
        db.add(
            Anomaly(
                id=str(uuid.uuid4()),
                project_id=project_id,
                created_at=_now_iso(),
                type=a["type"],
                severity=a["severity"],
                score=a["score"],
                title=a["title"],
                description=a["description"],
                evidence=json.dumps(a.get("evidence", [])),
                resolved=False,
            )
        )


def persist_emerging_risks(db: Session, project_id: str, risks: list) -> None:
    """Dedup by category for ACTIVE records; skip already-open categories."""
    existing = {
        r.category
        for r in db.query(EmergingRisk).filter(
            EmergingRisk.project_id == project_id,
            EmergingRisk.status == "ACTIVE",
        ).all()
    }
    for r in risks:
        if r.get("category") in existing:
            continue
        db.add(
            EmergingRisk(
                id=str(uuid.uuid4()),
                project_id=project_id,
                created_at=_now_iso(),
                category=r.get("category", "OTHER"),
                title=r.get("title", ""),
                confidence=r.get("confidence", 0.5),
                severity=r.get("severity", "MEDIUM"),
                description=r.get("description", ""),
                evidence=json.dumps(r.get("evidence", [])),
                recommendations=json.dumps(r.get("recommended_actions", [])),
                source_update_ids=json.dumps(r.get("source_update_ids", [])),
                status="ACTIVE",
            )
        )
        existing.add(r.get("category"))


def persist_insight_log(db: Session, project_id: str, insights: dict, summary: str) -> None:
    db.add(
        AIAnalysis(
            id=str(uuid.uuid4()),
            project_id=project_id,
            created_at=_now_iso(),
            analysis_type="insights",
            model=insights["prediction"].get("model_version", "") if insights.get("prediction") else "",
            prediction_method=insights["prediction"].get("prediction_method", "") if insights.get("prediction") else "",
            confidence=insights["prediction"].get("prediction_confidence") if insights.get("prediction") else None,
            summary=summary,
            raw_result=json.dumps(insights),
        )
    )


def build_insights(
    db: Session,
    project: Project,
    prediction_result: PredictionResult,
    anomaly_records: list,
    emerging_records: list,
    explanation: dict,
    analysis_kind: str,
) -> InsightsResponse:
    insights = InsightsResponse(
        project_id=project.id,
        prediction=prediction_result.model_dump(),
        anomalies=anomaly_records,
        emerging_risks=emerging_records,
        explanation=explanation,
        generated_at=_now_iso(),
        ai_available=llm_service.is_llm_available(),
        analysis_kind=analysis_kind,
    )
    persist_insight_log(db, project.id, insights.model_dump(), explanation.get("summary", ""))
    return insights


def project_for_analyze(db: Session, project_id: str):
    """Compute/refresh deterministic cached risk columns before AI use."""
    from services.risk_service import apply_assessment

    project = _load_project(db, project_id)
    apply_assessment(project)
    db.flush()
    return project


def analyze_project(db: Session, project_id: str) -> InsightsResponse:
    """Run the full AI pipeline and persist everything (fresh analysis)."""
    from ai.feature_engineering import build_features

    project = project_for_analyze(db, project_id)
    updates = _prepare_update_list(db, project_id)
    alerts = _prepare_alert_list(db, project_id)
    previous = latest_prediction(db, project_id)
    previous_score = previous.current_score if previous else None

    features = build_features(project, updates, alerts, previous_score)
    prediction = predict(project, updates, alerts, previous_score)

    anomaly_records = detect_anomalies(project, updates, alerts)
    persist_anomalies(db, project_id, anomaly_records)
    persist_prediction(db, project_id, prediction)

    emerging_records = emerging_risk.extract_from_updates(updates)
    persist_emerging_risks(db, project_id, emerging_records)

    explanation = _build_explanation(db, project, prediction)
    insights = build_insights(
        db, project,
        prediction_result=prediction,
        anomaly_records=anomaly_records,
        emerging_records=_active_emerging_risks(db, project_id),
        explanation=explanation,
        analysis_kind="fresh",
    )
    _clear_stale_predictions(db, project_id)
    db.commit()

    ai_logger.info(
        "ai analyze project=%s score=%s future=%s method=%s anomalies=%d emergent=%d",
        project_id, features["current_risk_score"], prediction.future_score,
        prediction.prediction_method, len(anomaly_records), len(emerging_records),
    )
    return insights


def get_cached_or_analyze(db: Session, project_id: str, force: bool = False) -> InsightsResponse:
    """Serve a cached analysis when fresh, else recompute."""
    latest = latest_prediction(db, project_id)
    if latest and not force and _fresh(latest.created_at):
        project = _load_project(db, project_id)
        prediction = _prediction_to_dict(latest)
        explanation = _build_explanation(db, project, PredictionResult(**prediction))
        insights = InsightsResponse(
            project_id=project_id,
            prediction=prediction,
            anomalies=_recent_anomalies(db, project_id),
            emerging_risks=_active_emerging_risks(db, project_id),
            explanation=explanation,
            generated_at=latest.created_at,
            ai_available=llm_service.is_llm_available(),
            analysis_kind="cached",
        )
        return insights
    return analyze_project(db, project_id)


def analyze_update_in_background(project_id: str, update_id: int) -> None:
    """Background task (fresh session): analyze one update for emerging
    risks + trigger a full project re-analysis. Never raises."""
    from services.project_service import next_alert_id

    try:
        with SessionLocal() as db:
            update = (
                db.query(ProjectUpdate)
                .filter(
                    ProjectUpdate.id == update_id,
                    ProjectUpdate.project_id == project_id,
                )
                .first()
            )
            if not update:
                ai_logger.warning("ai background update not found %s/%s", project_id, update_id)
                return

            result = emerging_risk.analyze_update(
                update.id, update.update_type, update.created_at, update.content
            )
            if not result.get("risk_detected"):
                ai_logger.info("ai background update %s: no emerging risk", update_id)
            else:
                block = [
                    r for r in db.query(EmergingRisk).filter(
                        EmergingRisk.project_id == project_id,
                        EmergingRisk.status == "ACTIVE",
                        EmergingRisk.category == result["category"],
                    ).all()
                ]
                if block:
                    ai_logger.info(
                        "ai emerging risk %s already active for %s (dedup)",
                        result["category"], project_id,
                    )
                else:
                    db.add(
                        EmergingRisk(
                            id=str(uuid.uuid4()),
                            project_id=project_id,
                            created_at=_now_iso(),
                            category=result["category"],
                            title=result["title"],
                            confidence=result["confidence"],
                            severity=result["severity"],
                            description=result["description"],
                            evidence=json.dumps(result.get("evidence", [])),
                            recommendations=json.dumps(result.get("recommended_actions", [])),
                            source_update_ids=json.dumps(result.get("source_update_ids", [])),
                            status="ACTIVE",
                        )
                    )
                    if result["severity"] in ("HIGH", "CRITICAL"):
                        alert_exists = db.query(Alert).filter(
                            Alert.project_id == project_id,
                            Alert.type == "AI Emerging Risk",
                            Alert.description.like(f"%{result['title']}%"),
                        ).first()
                        if not alert_exists:
                            db.add(
                                Alert(
                                    id=next_alert_id(db),
                                    project_id=project_id,
                                    type="AI Emerging Risk",
                                    severity=result["severity"],
                                    description=(
                                        f"AI detected emerging {result['category'].replace('_', ' ')} "
                                        f"risk: {result['title']}."
                                    ),
                                    detected_date=_now_iso(),
                                    status="ACTIVE",
                                )
                            )
                    db.commit()
                    ai_logger.info(
                        "ai emerging risk persisted %s severity=%s project=%s",
                        result["category"], result["severity"], project_id,
                    )

            try:
                analyze_project(db, project_id)
            except Exception as exc:  # noqa: BLE001
                ai_logger.warning("ai re-analysis failed project=%s err=%s", project_id, type(exc).__name__)
    except Exception as exc:  # noqa: BLE001 - background tasks must never crash the request
        ai_logger.error(
            "ai background analysis crashed project=%s err=%s",
            project_id, type(exc).__name__,
        )


def resolve_emerging_risk(db: Session, project_id: str, risk_id: str) -> bool:
    record = (
        db.query(EmergingRisk)
        .filter(
            EmergingRisk.id == risk_id,
            EmergingRisk.project_id == project_id,
            EmergingRisk.status == "ACTIVE",
        )
        .first()
    )
    if not record:
        return False
    record.status = "RESOLVED"
    record.updated_at = _now_iso()
    db.commit()
    return True


def resolve_anomaly(db: Session, project_id: str, anomaly_id: str) -> bool:
    record = (
        db.query(Anomaly)
        .filter(
            Anomaly.id == anomaly_id,
            Anomaly.project_id == project_id,
            Anomaly.resolved.is_(False),
        )
        .first()
    )
    if not record:
        return False
    record.resolved = True
    record.updated_at = _now_iso()
    db.commit()
    return True


__all__ = [
    "analyze_project",
    "get_cached_or_analyze",
    "analyze_update_in_background",
    "resolve_emerging_risk",
    "resolve_anomaly",
    "latest_prediction",
    "project_for_analyze",
]