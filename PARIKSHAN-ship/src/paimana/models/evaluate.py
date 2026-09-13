"""The metric suite — PRD §6.4.

Shared by every model in this project (baselines here in Phase 3, ML models
in Phase 4) so every reported number is computed the same way. Bootstrap
significance testing (comparing two models' metrics) is deliberately NOT
here — that is a Phase 4 "bake-off harness" concern (PRD §6.5) and lives in
`models/ml.py` / a dedicated bake-off module once Phase 4 needs it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    mean_absolute_error,
    roc_auc_score,
)

from paimana.features.splits import HORIZON_LABELS, horizon_bucket


def completed_labelled_rows(df: pd.DataFrame, regression_target: str = "cost_overrun_pct") -> pd.DataFrame:
    """Rows with a realised terminal outcome (PRD §5.4) — censored rows have
    null targets by design (docs/DATA_METHODOLOGY.md §7). Shared by every
    model module (statistical baselines, Phase 3; ML models, Phase 4) so
    "which rows count as labelled" is defined in exactly one place.
    """
    return df[df["is_censored"] == False].dropna(subset=[regression_target]).reset_index(drop=True)  # noqa: E712


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """MAE, RMSE, R^2, and a zero-guarded MAPE (PRD §6.4)."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")

    # MAPE is guarded against near-zero denominators (cost/time overrun can
    # legitimately be ~0%), which would otherwise blow up to infinity.
    denom = np.where(np.abs(y_true) < 1.0, np.nan, y_true)
    mape = float(np.nanmean(np.abs((y_true - y_pred) / denom)) * 100)

    return {"mae": mae, "rmse": rmse, "r2": r2, "mape_pct": mape, "n": int(len(y_true))}


def _best_f1_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> tuple[float, float]:
    """Scan thresholds and return (best_threshold, best_f1)."""
    thresholds = np.unique(np.clip(y_prob, 1e-6, 1 - 1e-6))
    if len(thresholds) > 200:  # subsample for speed on large fold sizes
        thresholds = np.quantile(thresholds, np.linspace(0, 1, 200))
    best_thr, best_f1 = 0.5, -1.0
    for thr in thresholds:
        f1 = f1_score(y_true, (y_prob >= thr).astype(int), zero_division=0)
        if f1 > best_f1:
            best_thr, best_f1 = float(thr), float(f1)
    return best_thr, best_f1


def classification_metrics(y_true: np.ndarray, y_prob: np.ndarray) -> dict[str, float]:
    """PR-AUC (primary), ROC-AUC, Brier score, and F1 at a tuned threshold (PRD §6.4)."""
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)

    base_rate = float(y_true.mean())
    pr_auc = float(average_precision_score(y_true, y_prob)) if 0 < base_rate < 1 else float("nan")
    roc_auc = float(roc_auc_score(y_true, y_prob)) if 0 < base_rate < 1 else float("nan")
    brier = float(brier_score_loss(y_true, y_prob))
    best_thr, best_f1 = _best_f1_threshold(y_true, y_prob)

    return {
        "pr_auc": pr_auc,
        "roc_auc": roc_auc,
        "brier": brier,
        "f1_at_best_threshold": best_f1,
        "best_threshold": best_thr,
        "base_rate": base_rate,
        "n": int(len(y_true)),
    }


def precision_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int) -> float:
    """Of the top-`k` highest-scored rows, what share are true positives?

    This is the alert-queue metric (PRD §1.3, §6.4): MoSPI's real constraint
    is reviewer bandwidth, not information, so "of the 50 projects we'd
    flag, how many actually overrun?" matters more than a blended AUC.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    k = min(k, len(y_true))
    if k == 0:
        return float("nan")
    top_k_idx = np.argsort(-y_score)[:k]
    return float(y_true[top_k_idx].mean())


def lift_at_k(y_true: np.ndarray, y_score: np.ndarray, k: int) -> float:
    """precision_at_k / portfolio base rate — "how much better than random"."""
    base_rate = float(np.asarray(y_true).mean())
    if base_rate == 0:
        return float("nan")
    return precision_at_k(y_true, y_score, k) / base_rate


def reliability_curve(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> dict[str, list[float]]:
    """Bin predicted probabilities and compare to observed frequency —
    the calibration curve data consumed by the Model Lab dashboard screen
    (Phase 6) and checked against SC-3 (Brier score) in the PRD.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    bins = np.linspace(0, 1, n_bins + 1)
    bin_idx = np.clip(np.digitize(y_prob, bins) - 1, 0, n_bins - 1)

    bin_centers, observed_freq, counts = [], [], []
    for b in range(n_bins):
        mask = bin_idx == b
        if mask.sum() == 0:
            continue
        bin_centers.append(float(y_prob[mask].mean()))
        observed_freq.append(float(y_true[mask].mean()))
        counts.append(int(mask.sum()))

    return {"predicted": bin_centers, "observed": observed_freq, "count": counts}


def horizon_stratified_metrics(
    df: pd.DataFrame,
    y_true_col: str,
    y_pred_col: str,
    elapsed_frac_col: str = "elapsed_frac",
    task: str = "regression",
) -> dict[str, dict[str, float]]:
    """Report metrics separately by how far through its plan a project was
    at prediction time (PRD §6.2.3) — early-horizon prediction is the hard,
    valuable case; late-horizon is easy and should not be allowed to hide a
    model's weakness earlier in a project's life by averaging over both.
    """
    buckets = horizon_bucket(df[elapsed_frac_col])
    out: dict[str, dict[str, float]] = {}
    for label in HORIZON_LABELS:
        mask = (buckets == label).to_numpy()
        if mask.sum() == 0:
            continue
        y_true = df.loc[mask, y_true_col].to_numpy()
        y_pred = df.loc[mask, y_pred_col].to_numpy()
        if task == "regression":
            out[label] = regression_metrics(y_true, y_pred)
        else:
            out[label] = classification_metrics(y_true, y_pred)
    return out
