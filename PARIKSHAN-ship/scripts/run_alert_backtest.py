#!/usr/bin/env python
"""The lead-time backtest — PRD §7/Phase 5 task 4, "the money slide".

"If we had run this in the past, what share of eventual severe-overrun
projects would we have flagged at least 4 quarters before commissioning?"

Deliberately uses OUT-OF-FOLD predictions (recomputed here via the same
GroupKFold-protected functions Phase 4 already tested), NOT the final
in-sample-fit models serialized to artifacts/models/. Evaluating a backtest
against a model that was partly trained on the very same historical rows
would overstate how early the system would genuinely have caught each
project — the honest question is "would a model that had NEVER seen this
project have flagged it," which is exactly what OOF answers.

Usage: python scripts/run_alert_backtest.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from paimana import config  # noqa: E402
from paimana.data.loader import load_processed_features  # noqa: E402
from paimana.features.splits import HORIZON_LABELS, horizon_bucket  # noqa: E402
from paimana.models.evaluate import completed_labelled_rows, precision_at_k  # noqa: E402
from paimana.models.ml import classifier_oof_calibrated, regressor_oof  # noqa: E402
from paimana.risk.alerts import compute_rule_triggers  # noqa: E402
from paimana.risk.score import momentum_penalty, normalized_magnitude, risk_band_for_score  # noqa: E402


def _load_chosen_hyperparameters() -> dict:
    path = config.ARTIFACTS_METRICS_DIR / "comparison.json"
    comparison = json.loads(path.read_text(encoding="utf-8"))
    return {
        target: {"family": entry["ml_model"], "params": entry["chosen_hyperparameters"]}
        for target, entry in comparison["targets"].items()
    }


def _compute_oof_risk_scores(completed: pd.DataFrame, chosen: dict) -> pd.DataFrame:
    """Honest, leakage-safe risk score for every COMPLETED row, built from
    OOF predictions — the same composite formula as `risk.score`, just fed
    by OOF rather than in-sample-fit predictions."""
    print("  recomputing OOF y_cost_overrun probabilities...")
    _, p_cost = classifier_oof_calibrated(
        completed, "y_cost_overrun", chosen["y_cost_overrun"]["family"], chosen["y_cost_overrun"]["params"]
    )
    print("  recomputing OOF y_time_overrun probabilities...")
    _, p_time = classifier_oof_calibrated(
        completed, "y_time_overrun", chosen["y_time_overrun"]["family"], chosen["y_time_overrun"]["params"]
    )
    print("  recomputing OOF cost_overrun_pct predictions...")
    cost_reg_choice = chosen["cost_overrun_pct"]
    _, pred_cost_pct = regressor_oof(
        completed, "cost_overrun_pct", cost_reg_choice["family"], cost_reg_choice["params"]
    )
    print("  recomputing OOF time_overrun_months predictions...")
    _, pred_time_months = regressor_oof(
        completed,
        "time_overrun_months",
        chosen["time_overrun_months"]["family"],
        chosen["time_overrun_months"]["params"],
    )

    magnitude = normalized_magnitude(pred_cost_pct, pred_time_months)
    momentum = momentum_penalty(completed["stalled_quarters"], completed["velocity_ratio"])
    risk_score = 100.0 * (
        config.RISK_WEIGHT_P_COST_OVERRUN * p_cost
        + config.RISK_WEIGHT_P_TIME_OVERRUN * p_time
        + config.RISK_WEIGHT_MAGNITUDE * magnitude
        + config.RISK_WEIGHT_MOMENTUM * momentum
    )
    risk_score = np.clip(risk_score, 0.0, 100.0)

    out = completed[
        [
            "project_id", "as_of_date", "elapsed_months", "velocity_ratio", "progress_gap_pp",
            "stalled_quarters", "elapsed_frac", "physical_progress_pct", "n_reasons_active",
            "revisions_to_date", "y_severe", "months_to_completion",
        ]
    ].copy()
    out["pred_cost_overrun_pct"] = pred_cost_pct
    out["risk_score"] = risk_score
    out["risk_band"] = risk_band_for_score(risk_score)
    return out


def _lead_time_analysis(oof_risk_df: pd.DataFrame) -> pd.DataFrame:
    """For every severe project, find the first quarter ANY signal (rule or
    model score) fired, how many quarters before actual completion that
    was, and WHICH rule(s) caught it first — the core "would we have caught
    it early, and via what" question. The "which rule" breakdown matters:
    if only MODEL-01 (composite score) ever fired first, the lead time
    would be suspect for the same reason Precision@K is (MODEL-01 tends to
    fire late — see the horizon-stratified Precision@K above); if the
    explicit behavioural rules (EW-01..EW-07) catch it first, that is
    genuine independent early-warning value, not just the aggregate score
    restated.
    """
    rule_cols = list(compute_rule_triggers(oof_risk_df).columns.difference(["project_id", "as_of_date"]))
    triggers = compute_rule_triggers(oof_risk_df)
    any_signal = triggers[rule_cols].any(axis=1)
    triggers = triggers.assign(any_signal=any_signal)

    merged = oof_risk_df.merge(
        triggers[["project_id", "as_of_date", "any_signal", *rule_cols]], on=["project_id", "as_of_date"]
    )
    severe = merged[merged["y_severe"] == True].sort_values(["project_id", "as_of_date"])  # noqa: E712

    records = []
    for project_id, group in severe.groupby("project_id"):
        final_duration = group["months_to_completion"].iloc[0]
        first_signal = group[group["any_signal"]]
        if first_signal.empty:
            records.append({"project_id": project_id, "flagged": False, "lead_time_quarters": np.nan})
            continue
        first_row = first_signal.iloc[0]
        first_rules = [r for r in rule_cols if first_row[r]]
        lead_time_months = final_duration - first_row["elapsed_months"]
        records.append(
            {
                "project_id": project_id,
                "first_rules": ",".join(sorted(first_rules)),
                "flagged": True,
                "lead_time_quarters": lead_time_months / 3.0,
                "flagged_at_elapsed_months": first_row["elapsed_months"],
            }
        )
    return pd.DataFrame(records)


def main() -> None:
    features_df = load_processed_features()
    completed = completed_labelled_rows(features_df)
    print(f"completed rows: {len(completed):,} across {completed['project_id'].nunique():,} projects")

    chosen = _load_chosen_hyperparameters()

    print("\nRecomputing OOF-based risk scores (honest, leakage-safe — see module docstring)...")
    oof_risk_df = _compute_oof_risk_scores(completed, chosen)

    print("\n--- Precision@K, ALL QUARTERS BLENDED (OOF risk_score vs. actual y_severe) ---")
    print(
        "CAVEAT: this blends easy late-stage snapshots with hard early ones — see the "
        "horizon-stratified numbers below for the honest early-warning picture (PRD §6.2.3)."
    )
    y_true = oof_risk_df["y_severe"].astype(int).to_numpy()
    y_score = oof_risk_df["risk_score"].to_numpy()
    base_rate = y_true.mean()
    print(f"Portfolio base rate (share severe): {base_rate:.1%}")
    for k in (25, 50, 100):
        p_at_k = precision_at_k(y_true, y_score, k)
        lift = p_at_k / base_rate if base_rate > 0 else float("nan")
        print(f"  Precision@{k}: {p_at_k:.1%}  (lift {lift:.2f}x over random)")

    print("\n--- Precision@K BY HORIZON (the honest early-warning picture) ---")
    print("A snapshot at 90%+ elapsed showing trouble is barely a finding; 0-25% is the hard, valuable case.")
    buckets = horizon_bucket(oof_risk_df["elapsed_frac"])
    for label in HORIZON_LABELS:
        mask = (buckets == label).to_numpy()
        n_bucket = int(mask.sum())
        if n_bucket < 25:
            print(f"  {label:>8s}: n={n_bucket} (too few rows for a stable Precision@25)")
            continue
        bucket_true = y_true[mask]
        bucket_score = y_score[mask]
        bucket_base_rate = bucket_true.mean()
        p25 = precision_at_k(bucket_true, bucket_score, 25)
        lift25 = p25 / bucket_base_rate if bucket_base_rate > 0 else float("nan")
        print(
            f"  {label:>8s} (n={n_bucket:,}, base rate {bucket_base_rate:.1%}): "
            f"Precision@25 = {p25:.1%} (lift {lift25:.2f}x)"
        )

    print("\n--- Lead-time analysis (the money slide) ---")
    lead_times = _lead_time_analysis(oof_risk_df)
    n_severe = len(lead_times)
    n_flagged = int(lead_times["flagged"].sum())
    print(f"Severe (eventually) projects in the completed portfolio: {n_severe}")
    print(f"  ...of which flagged by ANY signal at some point: {n_flagged} ({n_flagged / n_severe:.1%})")

    flagged = lead_times[lead_times["flagged"]]
    if len(flagged):
        median_lead = flagged["lead_time_quarters"].median()
        print(f"  Median lead time among flagged severe projects: {median_lead:.1f} quarters before")

    min_lead = config.BACKTEST_MIN_LEAD_QUARTERS
    early_enough = lead_times["flagged"] & (lead_times["lead_time_quarters"] >= min_lead)
    recall_early = early_enough.sum() / n_severe if n_severe else float("nan")
    print(
        f"  Recall @ >= {config.BACKTEST_MIN_LEAD_QUARTERS} quarters lead time: "
        f"{early_enough.sum()}/{n_severe} = {recall_early:.1%} of all eventual severe overruns "
        f"would have been flagged at least {config.BACKTEST_MIN_LEAD_QUARTERS} quarters before completion."
    )

    print(
        "\n  Which signal caught it FIRST, among flagged severe projects "
        "(sanity check: is the lead time coming from genuine early behavioural rules,\n"
        "  or just the late-firing composite score restated)?"
    )
    if len(flagged):
        rule_counts = flagged["first_rules"].str.split(",").explode().value_counts()
        for rule_id, count in rule_counts.items():
            has_rule = flagged["first_rules"].str.contains(rule_id, regex=False)
            avg_lead = flagged.loc[has_rule, "lead_time_quarters"].mean()
            print(f"    {rule_id:>10s}: first-caught {count:>3d} projects, avg lead time {avg_lead:.1f}q")

    config.ARTIFACTS_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    lead_times.to_parquet(config.ARTIFACTS_METRICS_DIR / "alert_backtest_lead_times.parquet", index=False)
    print(f"\nWrote {config.ARTIFACTS_METRICS_DIR / 'alert_backtest_lead_times.parquet'}")


if __name__ == "__main__":
    main()
