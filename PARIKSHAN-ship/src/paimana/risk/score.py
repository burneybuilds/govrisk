"""Composite risk scoring — PRD §6.7.

    risk_score = 100 * (
        0.35 * P(cost_overrun)
      + 0.35 * P(time_overrun)
      + 0.15 * normalised_magnitude
      + 0.15 * momentum_penalty
    )

Computed for EVERY project-quarter in the panel — not just the latest
snapshot. Unlike Phase 4's SHAP caching (expensive per-row tree traversal,
correctly scoped down to one row per project), risk scoring is just a
handful of `.predict()`/`.predict_proba()` calls, cheap even across the
full ~50k-row panel — which is exactly what's needed to show a project's
RISK TRAJECTORY over time (PRD §6.1), the dashboard's most persuasive chart.

Weights and normalisation caps are named constants in `config.py`, not
inline magic numbers — a government-facing system must be arguable, not
just accurate (PRD §6.7).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from paimana import config
from paimana.features.build import select_features

CONTEXT_COLUMNS: tuple[str, ...] = (
    "project_id",
    "project_name",
    "sector",
    "state",
    "as_of_date",
    "elapsed_frac",
    "original_cost_cr",
    "original_duration_months",
)
RULE_INPUT_COLUMNS: tuple[str, ...] = (
    "velocity_ratio",
    "progress_gap_pp",
    "stalled_quarters",
    "physical_progress_pct",
    "n_reasons_active",
    "revisions_to_date",
)
MODEL_OUTPUT_COLUMNS: tuple[str, ...] = (
    "p_cost_overrun",
    "p_time_overrun",
    "pred_cost_overrun_pct",
    "pred_time_overrun_months",
    "normalized_magnitude",
    "momentum_penalty",
    "risk_score",
    "risk_band",
)


def normalized_magnitude(
    pred_cost_overrun_pct: np.ndarray, pred_time_overrun_months: np.ndarray
) -> np.ndarray:
    """Winsorised [0, 1] blend of predicted cost- and time-overrun size.

    Each component is min-max scaled against its `config.RISK_MAGNITUDE_*`
    cap (chosen as a multiple of the SEVERE_* threshold, PRD §5.4) and
    clipped — a predicted overrun at or beyond the cap reads as maximally
    risky on this term rather than distorting the scale further.
    """
    cost_cap, time_cap = config.RISK_MAGNITUDE_COST_CAP_PCT, config.RISK_MAGNITUDE_TIME_CAP_MONTHS
    cost_component = np.clip(np.clip(pred_cost_overrun_pct, 0, None) / cost_cap, 0, 1)
    time_component = np.clip(np.clip(pred_time_overrun_months, 0, None) / time_cap, 0, 1)
    return (cost_component + time_component) / 2.0


def momentum_penalty(stalled_quarters: pd.Series, velocity_ratio: pd.Series) -> np.ndarray:
    """[0, 1] blend of "how long stalled" and "how far behind pace".

    `velocity_ratio` can be NaN/inf near completion (near-zero remaining
    work in the denominator) — treated as neutral (on-pace, contributing 0
    penalty) rather than propagating NaN into the composite score.
    """
    stall_cap = config.RISK_MOMENTUM_STALL_CAP_QUARTERS
    stall_component = np.clip(stalled_quarters.to_numpy(dtype=float) / stall_cap, 0, 1)

    vr = velocity_ratio.to_numpy(dtype=float)
    vr = np.where(np.isnan(vr) | np.isinf(vr), 1.0, vr)
    velocity_component = np.clip(1.0 - vr, 0, 1)  # only behind-pace (vr<1) contributes; vr>=1 -> 0

    return (stall_component + velocity_component) / 2.0


def risk_band_for_score(risk_score: np.ndarray) -> np.ndarray:
    """Green/Amber/Red band for each score (PRD §6.7 bands)."""
    arr = np.asarray(risk_score, dtype=float)
    amber_or_red = np.where(arr <= config.RISK_BAND_AMBER_MAX, "Amber", "Red")
    return np.where(arr <= config.RISK_BAND_GREEN_MAX, "Green", amber_or_red)


def compute_risk_scores(
    panel_df: pd.DataFrame,
    cost_overrun_classifier,
    time_overrun_classifier,
    cost_overrun_regressor,
    time_overrun_regressor,
) -> pd.DataFrame:
    """Score every row of `panel_df` (any subset of the CUF panel schema —
    the full panel for risk trajectories, or a single project's history).

    Returns a new DataFrame: context columns + rule-input columns (carried
    through for the alert engine) + the model outputs (§6.7 components,
    the composite `risk_score`, and its `risk_band`).
    """
    X = select_features(panel_df)

    p_cost = cost_overrun_classifier.predict_proba(X)[:, 1]
    p_time = time_overrun_classifier.predict_proba(X)[:, 1]
    pred_cost_pct = cost_overrun_regressor.predict(X)
    pred_time_months = time_overrun_regressor.predict(X)

    magnitude = normalized_magnitude(pred_cost_pct, pred_time_months)
    momentum = momentum_penalty(panel_df["stalled_quarters"], panel_df["velocity_ratio"])

    risk_score = 100.0 * (
        config.RISK_WEIGHT_P_COST_OVERRUN * p_cost
        + config.RISK_WEIGHT_P_TIME_OVERRUN * p_time
        + config.RISK_WEIGHT_MAGNITUDE * magnitude
        + config.RISK_WEIGHT_MOMENTUM * momentum
    )
    risk_score = np.clip(risk_score, 0.0, 100.0)

    context_cols = [c for c in CONTEXT_COLUMNS if c in panel_df.columns]
    rule_input_cols = [c for c in RULE_INPUT_COLUMNS if c in panel_df.columns]
    reason_cols = [c for c in panel_df.columns if c.startswith("reason_")]

    out = panel_df[context_cols + rule_input_cols + reason_cols].copy().reset_index(drop=True)
    out["p_cost_overrun"] = p_cost
    out["p_time_overrun"] = p_time
    out["pred_cost_overrun_pct"] = pred_cost_pct
    out["pred_time_overrun_months"] = pred_time_months
    out["normalized_magnitude"] = magnitude
    out["momentum_penalty"] = momentum
    out["risk_score"] = risk_score
    out["risk_band"] = risk_band_for_score(risk_score)
    return out
