"""Whitelisted pandas tools — PRD §6.9.

Every function here returns a JSON-serialisable dict/list built ONLY from
already-cached artifacts — the SAME files the Streamlit dashboard reads
(`risk_scores.parquet`, `alerts.parquet`, `projects.parquet`,
`comparison.json`, the Phase 5 backtest's lead-time table). None of them
train a model, call `.predict()`, or invent a number. `llm.py`'s system
prompt instructs the model to narrate EXACTLY these values and nothing
else; `retriever.py` maps a natural-language question to one of these
functions by name.

A tool that can't find what's asked (an unknown project ID, an unknown
sector) raises `ValueError` with a clear message — the caller (retriever/
llm) is expected to catch this and respond gracefully, not to have the
tool silently return an empty or misleading result.
"""

from __future__ import annotations

import json

import pandas as pd

from paimana import config

# --------------------------------------------------------------------------
# Cached-artifact loaders (deliberately NOT @st.cache_data — this module is
# usable outside Streamlit too, e.g. from scripts/run_assistant_eval.py)
# --------------------------------------------------------------------------


def _latest_snapshot_per_project(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.sort_values("as_of_date").groupby("project_id", as_index=False).last().reset_index(drop=True)
    )


def _load_risk_scores() -> pd.DataFrame:
    return pd.read_parquet(config.RISK_SCORES_PARQUET)


def _load_alerts() -> pd.DataFrame:
    return pd.read_parquet(config.ALERTS_PARQUET)


def _load_projects() -> pd.DataFrame:
    return pd.read_parquet(config.PROJECTS_PARQUET)


def _load_comparison() -> dict:
    return json.loads((config.ARTIFACTS_METRICS_DIR / "comparison.json").read_text(encoding="utf-8"))


def _load_lead_times() -> pd.DataFrame:
    return pd.read_parquet(config.ARTIFACTS_METRICS_DIR / "alert_backtest_lead_times.parquet")


# --------------------------------------------------------------------------
# 1. portfolio_summary
# --------------------------------------------------------------------------
def portfolio_summary() -> dict:
    """High-level KPIs for the whole portfolio — matches the dashboard's
    Portfolio Overview screen exactly (same source data, same
    latest-snapshot logic)."""
    risk = _latest_snapshot_per_project(_load_risk_scores())
    projects = _load_projects()

    n_projects = int(risk["project_id"].nunique())
    n_ongoing = int((projects["is_censored"] == True).sum())  # noqa: E712
    total_outlay_cr = float(projects["original_cost_cr"].sum())
    band_counts = risk["risk_band"].value_counts().to_dict()
    n_at_risk = int((risk["risk_band"] != "Green").sum())

    return {
        "n_projects": n_projects,
        "n_ongoing": n_ongoing,
        "n_completed": n_projects - n_ongoing,
        "total_approved_outlay_cr": round(total_outlay_cr, 1),
        "n_at_risk_amber_or_red": n_at_risk,
        "share_at_risk": round(n_at_risk / n_projects, 4) if n_projects else None,
        "risk_band_counts": {k: int(v) for k, v in band_counts.items()},
        "avg_predicted_cost_overrun_pct": round(float(risk["pred_cost_overrun_pct"].mean()), 2),
        "avg_predicted_time_overrun_months": round(float(risk["pred_time_overrun_months"].mean()), 2),
    }


# --------------------------------------------------------------------------
# 2. sector_risk_summary
# --------------------------------------------------------------------------
def sector_risk_summary(sector: str | None = None) -> dict:
    """Risk summary for one named sector, or ALL sectors ranked by mean
    risk score (worst first) if `sector` is omitted."""
    risk = _latest_snapshot_per_project(_load_risk_scores())

    if sector is None:
        grouped = (
            risk.groupby("sector")
            .agg(
                n_projects=("project_id", "count"),
                mean_risk_score=("risk_score", "mean"),
                n_at_risk=("risk_band", lambda s: int((s != "Green").sum())),
                mean_predicted_cost_overrun_pct=("pred_cost_overrun_pct", "mean"),
            )
            .sort_values("mean_risk_score", ascending=False)
            .reset_index()
        )
        grouped["mean_risk_score"] = grouped["mean_risk_score"].round(1)
        grouped["mean_predicted_cost_overrun_pct"] = grouped["mean_predicted_cost_overrun_pct"].round(2)
        return {"all_sectors_ranked_by_risk": grouped.to_dict(orient="records")}

    if sector not in config.SECTORS:
        raise ValueError(f"Unknown sector: {sector!r}. Valid sectors: {config.SECTORS}")

    subset = risk[risk["sector"] == sector]
    if subset.empty:
        raise ValueError(f"No projects found in sector {sector!r}")

    return {
        "sector": sector,
        "n_projects": int(len(subset)),
        "mean_risk_score": round(float(subset["risk_score"].mean()), 1),
        "n_at_risk_amber_or_red": int((subset["risk_band"] != "Green").sum()),
        "risk_band_counts": {k: int(v) for k, v in subset["risk_band"].value_counts().to_dict().items()},
        "mean_predicted_cost_overrun_pct": round(float(subset["pred_cost_overrun_pct"].mean()), 2),
    }


# --------------------------------------------------------------------------
# 3. state_risk_summary
# --------------------------------------------------------------------------
def state_risk_summary(state: str | None = None) -> dict:
    """Risk summary for one named state, or the top-10 states by number of
    at-risk projects if `state` is omitted."""
    risk = _latest_snapshot_per_project(_load_risk_scores())

    if state is None:
        grouped = (
            risk.groupby("state")
            .agg(
                n_projects=("project_id", "count"),
                n_at_risk=("risk_band", lambda s: int((s != "Green").sum())),
                mean_risk_score=("risk_score", "mean"),
            )
            .sort_values("n_at_risk", ascending=False)
            .head(10)
            .reset_index()
        )
        grouped["mean_risk_score"] = grouped["mean_risk_score"].round(1)
        return {"top_10_states_by_at_risk_count": grouped.to_dict(orient="records")}

    if state not in config.STATES:
        raise ValueError(f"Unknown state: {state!r}. Valid states: {config.STATES}")

    subset = risk[risk["state"] == state]
    if subset.empty:
        raise ValueError(f"No projects found in state {state!r}")

    return {
        "state": state,
        "n_projects": int(len(subset)),
        "n_at_risk_amber_or_red": int((subset["risk_band"] != "Green").sum()),
        "mean_risk_score": round(float(subset["risk_score"].mean()), 1),
    }


# --------------------------------------------------------------------------
# 4. top_risk_projects
# --------------------------------------------------------------------------
def top_risk_projects(k: int = 10) -> dict:
    """The top-K currently highest-risk projects (by latest risk_score) —
    the exact ranking the Early Warning Centre / alert queue is built on."""
    k = max(1, min(int(k), 100))
    risk = _latest_snapshot_per_project(_load_risk_scores())
    top = risk.nlargest(k, "risk_score")[
        ["project_id", "project_name", "sector", "state", "risk_score", "risk_band"]
    ].copy()
    top["risk_score"] = top["risk_score"].round(1)
    return {"k": k, "projects": top.to_dict(orient="records")}


# --------------------------------------------------------------------------
# 5. project_detail
# --------------------------------------------------------------------------
def project_detail(project_id: str) -> dict:
    """Full detail for one project: static attributes, current risk score
    and band, predicted overrun, and outcome if completed."""
    projects = _load_projects()
    row = projects[projects["project_id"] == project_id]
    if row.empty:
        raise ValueError(f"Unknown project_id: {project_id!r}")
    row = row.iloc[0]

    risk = _latest_snapshot_per_project(_load_risk_scores())
    risk_row = risk[risk["project_id"] == project_id]

    detail = {
        "project_id": project_id,
        "project_name": row["project_name"],
        "sector": row["sector"],
        "state": row["state"],
        "original_cost_cr": round(float(row["original_cost_cr"]), 1),
        "original_duration_months": int(row["original_duration_months"]),
        "status": "Ongoing" if row["is_censored"] else "Completed",
    }
    if not risk_row.empty:
        r = risk_row.iloc[0]
        detail.update(
            {
                "current_risk_score": round(float(r["risk_score"]), 1),
                "current_risk_band": r["risk_band"],
                "predicted_cost_overrun_pct": round(float(r["pred_cost_overrun_pct"]), 2),
                "predicted_time_overrun_months": round(float(r["pred_time_overrun_months"]), 2),
            }
        )
    if not row["is_censored"]:
        detail.update(
            {
                "actual_final_cost_cr": round(float(row["final_cost_cr"]), 1),
                "actual_cost_overrun_pct": round(float(row["cost_overrun_pct"]), 2),
                "actual_time_overrun_months": round(float(row["time_overrun_months"]), 1),
            }
        )
    return detail


# --------------------------------------------------------------------------
# 6. alert_digest
# --------------------------------------------------------------------------
def alert_digest(severity: str | None = None, limit: int = 10) -> dict:
    """The most recent `limit` alerts, optionally filtered to one severity
    (Critical/High/Medium)."""
    alerts = _load_alerts()
    if severity is not None:
        if severity not in ("Critical", "High", "Medium"):
            raise ValueError(f"Unknown severity: {severity!r}. Expected Critical/High/Medium.")
        alerts = alerts[alerts["severity"] == severity]

    limit = max(1, min(int(limit), 100))
    recent = alerts.sort_values("as_of_date", ascending=False).head(limit)[
        ["project_id", "project_name", "sector", "as_of_date", "severity", "risk_score", "recommended_action"]
    ].copy()
    recent["risk_score"] = recent["risk_score"].round(1)
    recent["as_of_date"] = recent["as_of_date"].astype(str)
    return {
        "severity_filter": severity,
        "n_matching_total": int(len(alerts)),
        "alerts": recent.to_dict(orient="records"),
    }


# --------------------------------------------------------------------------
# 7. compare_sectors
# --------------------------------------------------------------------------
def compare_sectors(sector_a: str, sector_b: str) -> dict:
    """Side-by-side risk comparison of two named sectors."""
    return {"sector_a": sector_risk_summary(sector_a), "sector_b": sector_risk_summary(sector_b)}


# --------------------------------------------------------------------------
# 8. model_bakeoff_summary
# --------------------------------------------------------------------------
def model_bakeoff_summary(target: str | None = None) -> dict:
    """The Phase 4 bake-off result for one target, or the overall headline
    + every target's verdict if `target` is omitted."""
    comparison = _load_comparison()
    if target is None:
        return {
            "headline": comparison["headline"],
            "best_ml": comparison["best_ml"],
            "targets": {
                t: {
                    "task": e["task"],
                    "conventional_model": e["conventional_model"],
                    "ml_model": e["ml_model"],
                    "significant": e["bootstrap"]["ci_excludes_zero"],
                    "ml_better": e["bootstrap"]["ci_excludes_zero"] and e["bootstrap"]["mean_diff"] > 0,
                }
                for t, e in comparison["targets"].items()
            },
        }
    if target not in comparison["targets"]:
        raise ValueError(f"Unknown target: {target!r}. Valid targets: {list(comparison['targets'])}")
    entry = comparison["targets"][target]
    ci_bounds = [entry["bootstrap"]["ci_lower"], entry["bootstrap"]["ci_upper"]]
    return {
        "target": target,
        "task": entry["task"],
        "conventional_model": entry["conventional_model"],
        "ml_model": entry["ml_model"],
        "bootstrap_95pct_ci_ml_minus_conventional": ci_bounds,
        "significant": entry["bootstrap"]["ci_excludes_zero"],
    }


# --------------------------------------------------------------------------
# 9. backtest_summary
# --------------------------------------------------------------------------
def backtest_summary() -> dict:
    """The Phase 5 lead-time backtest headline: how early the system would
    have caught eventual severe overruns."""
    lead_times = _load_lead_times()
    n_severe = int(len(lead_times))
    flagged = lead_times[lead_times["flagged"]]
    n_flagged = int(len(flagged))
    median_lead = float(flagged["lead_time_quarters"].median()) if n_flagged else None
    early_enough = flagged["lead_time_quarters"] >= config.BACKTEST_MIN_LEAD_QUARTERS
    return {
        "n_eventually_severe_projects": n_severe,
        "n_flagged_by_any_signal": n_flagged,
        "share_flagged": round(n_flagged / n_severe, 4) if n_severe else None,
        "median_lead_time_quarters_among_flagged": round(median_lead, 1) if median_lead is not None else None,
        "min_lead_quarters_threshold": config.BACKTEST_MIN_LEAD_QUARTERS,
        "n_flagged_early_enough": int(early_enough.sum()),
        "recall_at_min_lead_quarters": round(int(early_enough.sum()) / n_severe, 4) if n_severe else None,
    }


# --------------------------------------------------------------------------
# 10. delay_reason_breakdown
# --------------------------------------------------------------------------
def delay_reason_breakdown() -> dict:
    """Portfolio-wide count of currently-active delay reasons (latest
    snapshot per project) — "what's going wrong right now, and how often"."""
    risk = _latest_snapshot_per_project(_load_risk_scores())
    reason_cols = [c for c in risk.columns if c.startswith("reason_")]
    counts = {c.replace("reason_", ""): int(risk[c].sum()) for c in reason_cols}
    counts = dict(sorted(counts.items(), key=lambda kv: kv[1], reverse=True))
    return {"n_projects_considered": int(len(risk)), "active_reason_counts": counts}


TOOL_REGISTRY: dict[str, dict] = {
    "portfolio_summary": {
        "fn": portfolio_summary,
        "params": [],
        "description": (
            "Overall portfolio KPIs: project counts, total approved outlay, "
            "risk-band distribution, average predicted overrun."
        ),
    },
    "sector_risk_summary": {
        "fn": sector_risk_summary,
        "params": ["sector"],
        "description": (
            "Risk summary for one named sector, or all sectors ranked by risk if no sector is named."
        ),
    },
    "state_risk_summary": {
        "fn": state_risk_summary,
        "params": ["state"],
        "description": "Risk summary for one named state, or the top states by at-risk project count.",
    },
    "top_risk_projects": {
        "fn": top_risk_projects,
        "params": ["k"],
        "description": "The top-K highest-risk projects right now, ranked by risk score.",
    },
    "project_detail": {
        "fn": project_detail,
        "params": ["project_id"],
        "description": "Full detail for one specific project by its project_id (e.g. PRJ-00123).",
    },
    "alert_digest": {
        "fn": alert_digest,
        "params": ["severity", "limit"],
        "description": (
            "The most recent early-warning alerts, optionally filtered to Critical/High/Medium severity."
        ),
    },
    "compare_sectors": {
        "fn": compare_sectors,
        "params": ["sector_a", "sector_b"],
        "description": "Side-by-side risk comparison between two named sectors.",
    },
    "model_bakeoff_summary": {
        "fn": model_bakeoff_summary,
        "params": ["target"],
        "description": (
            "The ML-vs-conventional-statistics bake-off result: which model won, "
            "and whether it was statistically significant."
        ),
    },
    "backtest_summary": {
        "fn": backtest_summary,
        "params": [],
        "description": (
            "How early the early-warning system would have caught eventual severe "
            "cost/time overruns (the lead-time backtest)."
        ),
    },
    "delay_reason_breakdown": {
        "fn": delay_reason_breakdown,
        "params": [],
        "description": (
            "Portfolio-wide count of currently active delay reasons "
            "(land acquisition, funds constraint, etc.)."
        ),
    },
}
