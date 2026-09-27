"""Feature engineering for the AI layer.

Turns raw project rows, project updates (text history) and alerts into a
flat, numeric feature vector used by the predictor and anomaly detector.
Every feature is computed from real data - nothing is hardcoded.

Time-series features are derived from the actual `ProjectUpdate` log
(text polarity + chronology), not fabricated snapshots.
"""

import json
from datetime import datetime, timezone
from typing import List, Optional

from services.risk_service import _derived, _normalize_inputs

# --------------------------------------------------------------------------
# update text polarity
# --------------------------------------------------------------------------

_NEGATIVE_TERMS = (
    "delay", "delayed", "slippage", "overrun", "escalat", "dispute", "objection",
    "land", "blocked", "block", "shortage", "stalled", "stall", "risk", "problem",
    "issue", "slow", "pending", "cost increas", "price rise", "unresolved",
    "compensation", "review", "non-complian", "quality issue", "rework",
    "approval pending", "stopped", "pause", "suspended", "failure", "failed",
    "rejected", "shortfall", "below plan", "behind schedule", "protest",
)

_POSITIVE_TERMS = (
    "on track", "on-track", "ahead", "completed", "cleared", "resolved",
    "improved", "improving", "good progress", "within budget", "achieved",
    "successful", "delivered", "finalized", "expedited", "resolved issue",
)

_DELAY_TERMS = (
    "delay", "delayed", "slippage", "behind schedule", "postpone", "postponed",
)


def classify_update(text: str) -> float:
    """Return update polarity in [-1, 1].

    -1 strongly negative, +1 strongly positive, 0 neutral/unknown.
    """
    lowered = (text or "").lower()
    hits = sum(lowered.count(t) for t in _NEGATIVE_TERMS)
    positive = sum(lowered.count(t) for t in _POSITIVE_TERMS)
    if hits == 0 and positive == 0:
        return 0.0
    raw = (positive - hits) / max(1, hits + positive)
    return max(-1.0, min(1.0, raw))


def mentions_delay(text: str) -> bool:
    lowered = (text or "").lower()
    return any(t in lowered for t in _DELAY_TERMS)


def _parse_dt(value: Optional[str]):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


# --------------------------------------------------------------------------
# project-level features
# --------------------------------------------------------------------------

def extract_risk_inputs(project) -> dict:
    """Same 11-branch risk_inputs normalization the deterministic engine uses."""
    return _normalize_inputs(project)


def contractor_score(inputs: dict) -> Optional[float]:
    """0..1 contractor failure propensity (higher = worse) from risk_inputs."""
    c = inputs.get("contractor") or {}
    score = 0.0
    n = 0
    mapping = {"GOOD": 0.1, "FAIR": 0.5, "POOR": 0.85}
    if c.get("performance"):
        score += mapping.get(str(c["performance"]), 0.5)
        n += 1
    if c.get("financialStress"):
        score += 0.3 if str(c["financialStress"]).upper() in ("HIGH", "CRITICAL") else 0.1
        n += 1
    if isinstance(c.get("delayedMilestoneCount"), (int, float)):
        score += min(1.0, float(c["delayedMilestoneCount"]) / 10.0) * 0.5
        n += 1
    return round(score / n, 3) if n else None


def _enum_risk(mapping: dict, value) -> Optional[float]:
    if value is None:
        return None
    normalized = str(value).upper()
    return mapping.get(normalized)


def branch_risk_level(inputs: dict, branch: str, mapping: dict) -> Optional[float]:
    """Worst recognised severity in a branch, or None if the branch has none.

    Scans every value in the branch and keeps the highest score, so the result
    does not depend on the order the keys happen to be stored in. A branch whose
    values are all unknown to `mapping` returns None (the caller decides the
    fallback) rather than silently reporting a mid-range risk.
    """
    b = inputs.get(branch) or {}
    if not isinstance(b, dict):
        return None
    worst: Optional[float] = None
    for value in b.values():
        if not isinstance(value, str):
            continue
        r = _enum_risk(mapping, value)
        if r is None:
            continue
        if worst is None or r > worst:
            worst = r
    return worst


def _risk_or(inputs: dict, branch: str, mapping: dict, default: float) -> float:
    """`branch_risk_level` with an explicit default.

    A real score of 0.0 (a fully cleared branch, for example) is a valid answer
    and must not be replaced by the default.
    """
    r = branch_risk_level(inputs, branch, mapping)
    return default if r is None else r


_RISK4 = {"LOW": 0.2, "MODERATE": 0.45, "HIGH": 0.7, "CRITICAL": 0.9}
_RISK5 = {
    "NONE": 0.0, "LOW": 0.2, "MODERATE": 0.45, "HIGH": 0.7, "SEVERE": 0.9,
    "CRITICAL": 0.95, "VERY LOW": 0.1,
}

# Vocabularies below mirror the values the app actually persists in
# `Project.risk_inputs` (see the seed data / risk-input form), not an
# invented scale. Anything missing here silently fell through to a fixed
# mid-range default, which scored healthy branches as moderate risk.

# weather.condition / weather.disruption
_WEATHER = {
    **_RISK5,
    "CLEAR": 0.05, "MILD": 0.25, "UNFAVOURABLE": 0.7,
}
# ground.condition / ground.groundwater
_GROUND = {
    **_RISK5,
    "FAVOURABLE": 0.1, "DIFFICULT": 0.7,
}
# material.availability
_MATERIAL = {
    **_RISK5,
    "ADEQUATE": 0.15, "TIGHT": 0.6, "SHORTAGE": 0.8, "SEVERE_SHORTAGE": 0.92,
}
# workforce.availability / workforce.productivity / workforce.absenteeism
_WORKFORCE = {
    **_RISK5,
    "ADEQUATE": 0.15, "NORMAL": 0.3, "TIGHT": 0.6,
    "SHORTAGE": 0.8, "SEVERE_SHORTAGE": 0.92,
}
# clearance.environmentalClearance
_CLEARANCE = {
    "CLEARED": 0.0, "NOT_REQUIRED": 0.0, "PENDING": 0.5, "REJECTED": 0.9,
}
# administrative.turnaround / administrative.interDepartmentDependency
_ADMIN = {
    **_RISK4,
    "FAST": 0.1, "NORMAL": 0.3, "SLOW": 0.75, "BLOCKED": 0.95,
}
# supplyChain.accessibility / .equipmentAvailability / .supplierDependency
_SUPPLY = {
    **_RISK4,
    "GOOD": 0.1, "ADEQUATE": 0.15, "TIGHT": 0.6,
    "SHORTAGE": 0.8, "SEVERE_SHORTAGE": 0.92, "POOR": 0.85,
}
# legalSocial.oppositionLevel
_LEGAL = {"NONE": 0.0, "LOW": 0.2, "MODERATE": 0.5, "HIGH": 0.8}


def build_features(
    project,
    updates: Optional[List] = None,
    alerts: Optional[List] = None,
    previous_risk_score: Optional[float] = None,
) -> dict:
    """Compute the full feature vector for a project snapshot."""
    updates = updates or []
    alerts = alerts or []
    d = _derived(project)
    inputs = extract_risk_inputs(project)

    current_risk = float(getattr(project, "risk_score", 0) or 0)

    parsed_updates = []
    for u in updates:
        dt = _parse_dt(getattr(u, "created_at", None))
        polarity = classify_update(getattr(u, "content", ""))
        parsed_updates.append(
            {
                "id": getattr(u, "id", None),
                "polarity": polarity,
                "delay": mentions_delay(getattr(u, "content", "")),
                "dt": dt,
                "update_type": getattr(u, "update_type", "GENERAL"),
            }
        )
    parsed_updates.sort(key=lambda x: (x["dt"] is not None, x["dt"] or datetime.min.replace(tzinfo=timezone.utc)))

    polarities = [u["polarity"] for u in parsed_updates]
    n_updates = len(parsed_updates)

    consecutive_negative = 0
    consecutive_delays = 0
    for u in reversed(parsed_updates):
        if u["polarity"] < 0:
            consecutive_negative += 1
        else:
            break
    for u in reversed(parsed_updates):
        if u["delay"]:
            consecutive_delays += 1
        else:
            break

    # rate of deterioration: negative-ratio in most recent half vs the rest
    rate_of_deterioration = 0.0
    if n_updates >= 4:
        split = n_updates // 2
        recent = polarities[-split:]
        earlier = polarities[: n_updates - split]
        recent_avg = sum(recent) / len(recent) if recent else 0.0
        earlier_avg = sum(earlier) / len(earlier) if earlier else 0.0
        rate_of_deterioration = round(max(-1.0, min(1.0, earlier_avg - recent_avg)), 3)

    # update span / frequency
    span_months = 0.0
    timestamps = [u["dt"] for u in parsed_updates if u["dt"]]
    if len(timestamps) >= 2:
        span_days = max(1, (max(timestamps) - min(timestamps)).days)
        span_months = span_days / 30.44
    update_frequency = round(n_updates / span_months, 3) if span_months > 0 else (n_updates or 0)

    days_since_last_update = None
    if timestamps:
        days_since_last_update = max(0, (datetime.now(timezone.utc) - max(timestamps)).days)

    severity_ratio = 0.0
    if polarities:
        neg_count = sum(1 for p in polarities if p < 0)
        severity_ratio = neg_count / len(polarities)

    active_alerts = [a for a in alerts if str(getattr(a, "status", "ACTIVE")).upper() == "ACTIVE"]
    risk_dist_penalty = round(sum(abs(p) for p in polarities) / max(1, n_updates), 3)

    features = {
        # --- snapshot numerics ---
        "budget": d["original"],
        "current_budget": d["current"],
        "revised_budget": d["current"],
        "expenditure": d["expenditure"],
        "cost_variance": d["overrun_pct"] if d["overrun_pct"] is not None else 0.0,
        "overrun_pct": d["overrun_pct"] if d["overrun_pct"] is not None else 0.0,
        "planned_progress": d["planned"],
        "actual_progress": d["physical"],
        "progress_gap": d["gap"],
        "schedule_variance": d["gap"],
        "financial_progress": d["financial"] if d["financial"] is not None else 0.0,
        "fin_gap": d["fin_gap"] if d["fin_gap"] is not None else 0.0,
        "burn_pct": d["burn_pct"] if d["burn_pct"] is not None else 0.0,
        "slippage_months": d["slippage_months"] or 0,
        "milestone_frac": d["milestone_frac"] or 0.0,
        "elapsed_pct": d["elapsed_pct"] or 0.0,
        "current_risk_score": current_risk,
        # --- risk-input branches ---
        "contractor_score": contractor_score(inputs) or 0.0,
        "clearance_status": _risk_or(
            inputs, "clearance", _CLEARANCE, 0.3
        ),
        "material_status": _risk_or(
            inputs, "material", _MATERIAL, 0.3
        ),
        "workforce_status": _risk_or(
            inputs, "workforce", _WORKFORCE, 0.3
        ),
        "weather_risk": _risk_or(inputs, "weather", _WEATHER, 0.3),
        "ground_risk": _risk_or(inputs, "ground", _GROUND, 0.3),
        "legal_risk": _risk_or(inputs, "legal_social", _LEGAL, 0.2),
        "administrative_risk": _risk_or(inputs, "administrative", _ADMIN, 0.3),
        "supply_chain_risk": _risk_or(inputs, "supply_chain", _SUPPLY, 0.3),
        "calamity_risk": _risk_or(inputs, "calamity", _RISK4, 0.3),
        "forecast_anchor": (
            (float(getattr(project, "delay_probability", 0) or 0) / 100.0)
            + (float(getattr(project, "cost_overrun_probability", 0) or 0) / 100.0)
        ) / 2.0,
        # --- alerts ---
        "number_of_alerts": len(alerts),
        "number_of_active_alerts": len(active_alerts),
        # --- update history ---
        "number_of_updates": n_updates,
        "update_frequency": update_frequency,
        "update_polarity_mean": round(sum(polarities) / len(polarities), 3) if polarities else 0.0,
        "negative_update_ratio": round(severity_ratio, 3),
        "risk_dist_penalty": risk_dist_penalty,
        "consecutive_negative_updates": consecutive_negative,
        "consecutive_delays": consecutive_delays,
        "rate_of_deterioration": rate_of_deterioration,
        "days_since_last_update": days_since_last_update,
        "data_points": n_updates + len(alerts) + 6,
    }

    # risk change vs previous snapshot (0 when no history exists)
    if previous_risk_score is not None:
        features["previous_risk_score"] = previous_risk_score
        features["risk_change"] = round(current_risk - previous_risk_score, 2)
    else:
        features["previous_risk_score"] = current_risk
        features["risk_change"] = 0.0

    return features


def risk_level_mapping() -> dict:
    return {0: "LOW", 1: "LOW", 2: "LOW", 3: "MEDIUM", 4: "MEDIUM"}


def level_from_score(score: float) -> str:
    if score >= 76:
        return "CRITICAL"
    if score >= 51:
        return "HIGH"
    if score >= 26:
        return "MEDIUM"
    return "LOW"