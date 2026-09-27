"""The early-warning alert engine — PRD §6.8.

Combines the seven explicit EW rules with one model-driven rule (risk score
in the Red band) into a single alert per (project, quarter):

- **Edge-triggered, not level-triggered**: a rule fires an alert only on the
  quarter it newly becomes true, not on every quarter it stays true — the
  standard alerting pattern to avoid burying reviewers in repeat noise for
  a condition they already know about.
- **Severity ranking**: when multiple rules trigger on the same quarter,
  the alert is reported once, at the HIGHEST severity among them, with
  every triggered rule id still listed.
- **Reason codes from cached SHAP** when available (Phase 4 only cached
  SHAP for each project's LATEST snapshot — see `explain.py`), falling back
  to the panel's own active delay-reason flags otherwise.
- **A recommended action** mapped from the dominant driver.
"""

from __future__ import annotations

import pandas as pd

from paimana import config

SEVERITY_RANK: dict[str, int] = {"Medium": 1, "High": 2, "Critical": 3}

RULE_SEVERITY: dict[str, str] = {
    "EW-01": "High",
    "EW-02": "High",
    "EW-03": "Critical",
    "EW-04": "Critical",
    "EW-05": "High",
    "EW-06": "Medium",
    "EW-07": "Medium",
    "MODEL-01": "High",
}
RULE_IDS: tuple[str, ...] = tuple(RULE_SEVERITY)

RULE_DESCRIPTIONS: dict[str, str] = {
    "EW-01": f"Velocity ratio below {config.EW_VELOCITY_RATIO_THRESHOLD} for 2 consecutive quarters",
    "EW-02": f"Spending-vs-progress gap exceeds {config.EW_PROGRESS_GAP_THRESHOLD_PP:.0f}pp",
    "EW-03": f"Stalled for {config.EW_STALLED_QUARTERS_THRESHOLD}+ consecutive quarters",
    "EW-04": (
        f"Risk score in the Red band and rose {config.EW_RISK_SCORE_RISE_THRESHOLD}+ "
        "points in 2 quarters"
    ),
    "EW-05": (
        f"Past {config.EW_LATE_ELAPSED_FRAC_THRESHOLD:.0%} of planned duration with "
        f"<{config.EW_LATE_PHYSICAL_PROGRESS_THRESHOLD_PCT:.0f}% physical progress"
    ),
    "EW-06": f"{config.EW_MANY_REASONS_THRESHOLD}+ delay reasons active simultaneously",
    "EW-07": f"{config.EW_MANY_REVISIONS_THRESHOLD}+ prior revisions with a rising predicted overrun",
    "MODEL-01": f"Model-predicted risk score >= {config.EW_RISK_SCORE_RED_THRESHOLD} (Red band)",
}

# Dominant-active-delay-reason -> recommended action (PRD §6.8 example).
REASON_ACTIONS: dict[str, str] = {
    "land_acquisition": (
        "Escalate to the State Land Acquisition Cell; convene an inter-departmental review."
    ),
    "forest_env_clearance": (
        "Expedite the pending forest/environmental clearance with the relevant ministry."
    ),
    "funds_constraint": "Review budgetary allocation and release schedule with the finance wing.",
    "contractor_issues": (
        "Initiate a contractor performance review; consider penalty clauses or re-tendering."
    ),
    "tendering_delay": "Escalate the tendering process; review procurement bottlenecks.",
    "litigation": "Engage the legal cell for expedited resolution; assess settlement options.",
    "r_and_r": "Accelerate rehabilitation & resettlement package disbursement with affected parties.",
    "law_and_order": "Coordinate with local administration/police for site security.",
    "geological_surprise": "Commission a fresh geotechnical assessment; revise the engineering plan.",
    "equipment_supply": "Diversify or expedite the equipment/material supply chain.",
    "statutory_clearance": "Follow up with the statutory authority; escalate if beyond SLA.",
    "force_majeure": "Assess force-majeure impact; revise timeline with documented justification.",
}
assert set(REASON_ACTIONS) == set(config.DELAY_REASONS)

# Dominant SHAP feature -> recommended action, for when a reason code is
# available but isn't one of the explicit delay-reason flags above.
FEATURE_ACTIONS: dict[str, str] = {
    "progress_gap_pp": (
        "Reconcile disbursed funds against verified physical progress before the next release."
    ),
    "velocity_ratio": (
        "Review execution pace against the revised schedule; identify the bottleneck activity."
    ),
    "stalled_quarters": "Convene a site-level review to unblock stalled execution.",
    "n_reasons_active": (
        "Multiple concurrent issues — prioritise a joint resolution meeting across stakeholders."
    ),
    "revisions_to_date": (
        "Frequent revisions — review the original scope and cost/time estimation quality."
    ),
    "months_since_last_revision": (
        "Review whether a formal revision is now overdue given current progress."
    ),
    "agency_prior_avg_cost_overrun_pct": (
        "Agency has a weak cost-overrun track record — increase monitoring frequency."
    ),
    "agency_prior_avg_time_overrun_months": (
        "Agency has a weak schedule track record — increase monitoring frequency."
    ),
    "agency_prior_severe_rate": (
        "Agency has a high severe-overrun track record — flag for portfolio-level review."
    ),
    "agency_prior_completed_count": (
        "Agency has limited track record on file — apply standard heightened oversight."
    ),
    "original_cost_cr": "Large-scale project — ensure phased, milestone-based monitoring.",
    "original_duration_months": (
        "Long-duration project — schedule periodic independent progress audits."
    ),
    "financial_progress_pct": "Verify financial progress against an independent physical-progress check.",
    "physical_progress_pct": "Independently verify reported physical progress on site.",
}
DEFAULT_ACTION = "Monitor — no single dominant driver identified; review at the next scheduled review point."


def compute_rule_triggers(risk_df: pd.DataFrame) -> pd.DataFrame:
    """Boolean EW-01..EW-07 and MODEL-01 trigger columns for every row of a
    risk-score-augmented panel (see `risk.score.compute_risk_scores`).

    `risk_df` need not be pre-sorted; this sorts by (project_id, as_of_date)
    itself so the lag-based rules (EW-01, EW-04, EW-07) see the correct
    quarter-over-quarter history.
    """
    df = risk_df.sort_values(["project_id", "as_of_date"]).reset_index(drop=True)
    g = df.groupby("project_id")

    velocity_ratio_prev = g["velocity_ratio"].shift(1)
    risk_score_2q_ago = g["risk_score"].shift(2)
    pred_cost_prev = g["pred_cost_overrun_pct"].shift(1)

    triggers = pd.DataFrame(index=df.index)
    triggers["EW-01"] = (df["velocity_ratio"] < config.EW_VELOCITY_RATIO_THRESHOLD) & (
        velocity_ratio_prev < config.EW_VELOCITY_RATIO_THRESHOLD
    )
    triggers["EW-02"] = df["progress_gap_pp"] > config.EW_PROGRESS_GAP_THRESHOLD_PP
    triggers["EW-03"] = df["stalled_quarters"] >= config.EW_STALLED_QUARTERS_THRESHOLD
    triggers["EW-04"] = (df["risk_score"] >= config.EW_RISK_SCORE_RED_THRESHOLD) & (
        (df["risk_score"] - risk_score_2q_ago) >= config.EW_RISK_SCORE_RISE_THRESHOLD
    )
    triggers["EW-05"] = (df["elapsed_frac"] > config.EW_LATE_ELAPSED_FRAC_THRESHOLD) & (
        df["physical_progress_pct"] < config.EW_LATE_PHYSICAL_PROGRESS_THRESHOLD_PCT
    )
    triggers["EW-06"] = df["n_reasons_active"] >= config.EW_MANY_REASONS_THRESHOLD
    triggers["EW-07"] = (df["revisions_to_date"] >= config.EW_MANY_REVISIONS_THRESHOLD) & (
        df["pred_cost_overrun_pct"] > pred_cost_prev
    )
    triggers["MODEL-01"] = df["risk_score"] >= config.EW_RISK_SCORE_RED_THRESHOLD
    triggers = triggers.fillna(False)

    return pd.concat([df[["project_id", "as_of_date"]], triggers], axis=1)


def _dedupe_edge_triggered(triggers: pd.DataFrame) -> pd.DataFrame:
    """Keep a rule's trigger only on the quarter it newly becomes true
    (rising edge) — the level itself may persist for many quarters, but the
    ALERT should not re-fire every one of them."""
    df = triggers.sort_values(["project_id", "as_of_date"]).reset_index(drop=True)
    g = df.groupby("project_id")
    edge = pd.DataFrame(index=df.index)
    for rule_id in RULE_IDS:
        prev = g[rule_id].shift(1, fill_value=False)  # fill_value keeps bool dtype (vs. shift().fillna())
        edge[rule_id] = df[rule_id] & ~prev
    return pd.concat([df[["project_id", "as_of_date"]], edge], axis=1)


def _recommend_action(
    row: pd.Series, shap_reason_codes: dict[str, list[dict]] | None
) -> tuple[str, list[dict] | None]:
    codes = (shap_reason_codes or {}).get(row["project_id"]) if row.get("_is_latest_snapshot") else None
    if codes:
        # Strip the ColumnTransformer's "num__"/"cat__..." prefix to match
        # the raw feature names FEATURE_ACTIONS/REASON_ACTIONS are keyed by.
        top_feature = codes[0]["feature"].split("__", 1)[-1]
        if top_feature in FEATURE_ACTIONS:
            return FEATURE_ACTIONS[top_feature], codes
        for reason in config.DELAY_REASONS:
            if top_feature == f"reason_{reason}":
                return REASON_ACTIONS[reason], codes

    active = [r for r in config.DELAY_REASONS if row.get(f"reason_{r}", False)]
    if active:
        return REASON_ACTIONS[active[0]], codes
    return DEFAULT_ACTION, codes


def build_alerts(
    risk_df: pd.DataFrame, shap_reason_codes: dict[str, list[dict]] | None = None
) -> pd.DataFrame:
    """One row per (project_id, as_of_date) with >=1 newly-triggered rule.

    `shap_reason_codes`: optional {project_id: [{"feature":..., "shap_value":...}, ...]},
    only ever available for each project's latest snapshot (Phase 4 scope) —
    historical alert rows simply fall back to the active delay-reason flags.
    """
    triggers = compute_rule_triggers(risk_df)
    edge_triggers = _dedupe_edge_triggered(triggers)

    any_trigger = edge_triggers[list(RULE_IDS)].any(axis=1)
    fired = edge_triggers.loc[any_trigger].copy()
    if fired.empty:
        return pd.DataFrame(
            columns=[
                "project_id", "project_name", "sector", "as_of_date", "severity",
                "triggered_rules", "risk_score", "recommended_action", "reason_codes",
            ]
        )

    fired["triggered_rules"] = fired[list(RULE_IDS)].apply(
        lambda row: [r for r in RULE_IDS if row[r]], axis=1
    )
    fired["severity"] = fired["triggered_rules"].apply(
        lambda rules: max(rules, key=lambda r: SEVERITY_RANK[RULE_SEVERITY[r]])
    ).map(RULE_SEVERITY)

    # SHAP reason codes are only ever valid for the snapshot they were
    # computed on (each project's LATEST, per Phase 4's scope) — attaching
    # them to an older alert row would silently show that alert "why it
    # fired" using information from years in its future. `_is_latest_snapshot`
    # gates the SHAP lookup in `_recommend_action` to the one row per
    # project where it is actually correct to use.
    risk_df = risk_df.copy()
    latest_date = risk_df.groupby("project_id")["as_of_date"].transform("max")
    risk_df["_is_latest_snapshot"] = risk_df["as_of_date"] == latest_date

    context_cols = ["project_id", "as_of_date", "risk_score", "_is_latest_snapshot"]
    optional_cols = ["project_name", "sector"]
    reason_flag_cols = [c for c in risk_df.columns if c.startswith("reason_")]
    merge_cols = context_cols + [c for c in optional_cols + reason_flag_cols if c in risk_df.columns]

    fired = fired[["project_id", "as_of_date", "triggered_rules", "severity"]].merge(
        risk_df[merge_cols], on=["project_id", "as_of_date"], how="left"
    )

    recs = fired.apply(lambda row: _recommend_action(row, shap_reason_codes), axis=1)
    fired["recommended_action"] = recs.apply(lambda t: t[0])
    fired["reason_codes"] = recs.apply(lambda t: t[1])

    fired = fired.sort_values(["as_of_date", "project_id"]).reset_index(drop=True)
    keep_cols = [c for c in ("project_id", "project_name", "sector") if c in fired.columns]
    output_cols = [
        "as_of_date", "severity", "triggered_rules", "risk_score", "recommended_action", "reason_codes",
    ]
    return fired[keep_cols + output_cols]
