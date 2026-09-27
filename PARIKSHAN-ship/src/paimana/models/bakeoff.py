"""The bake-off harness — PRD §6.5, §7/Phase 4 task 4.

"XGBoost got 0.78 vs. logit 0.74" is not a finding. This module produces the
two things that make a comparison honest:

1. **Paired, project-level bootstrap** (n=1000): resample PROJECT IDs (not
   rows) with replacement — so a project's several quarterly snapshots move
   together, respecting the same grouping structure as GroupKFold — and
   report a 95% CI on the *difference* in a metric between two models
   evaluated on the SAME resampled rows. A CI that excludes zero is a real
   finding either direction; one that includes zero means "no significant
   difference," which is a legitimate, honest result this project reports
   rather than hides (PRD §6.5).
2. **DeLong's test** for the ROC-AUC difference specifically — the standard
   parametric test for two correlated ROC curves on the same samples (Sun &
   Xu 2014's fast implementation), giving a p-value alongside the
   bootstrap's CI.

Both require the two models' predictions to be aligned row-for-row on the
SAME data, which holds here because `paimana.features.splits.grouped_cv`
(sklearn's `GroupKFold`) is deterministic — no shuffling — given the same
input order, so Phase 3's baseline OOF predictions and Phase 4's ML OOF
predictions land on identical rows without any extra bookkeeping.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import average_precision_score

from paimana import config
from paimana.models import evaluate
from paimana.models.baselines import (
    CLASSIFICATION_TARGETS,
    REGRESSION_TARGET,
    _logistic_oof_predictions,
    _naive_oof_predictions,
    _ols_oof_predictions,
)
from paimana.models.ml import MLResults

# --------------------------------------------------------------------------
# Paired, project-level bootstrap (PRD §6.5)
# --------------------------------------------------------------------------


def paired_bootstrap_ci(
    y_true: np.ndarray,
    pred_a: np.ndarray,
    pred_b: np.ndarray,
    groups: np.ndarray,
    metric_fn: Callable[[np.ndarray, np.ndarray], float],
    n_boot: int = 1000,
    seed: int = config.RANDOM_SEED,
    ci: float = 0.95,
) -> dict:
    """95% CI on metric_fn(y_true, pred_a) - metric_fn(y_true, pred_b),
    resampled at the PROJECT level (n_boot resamples of unique `groups`
    values, with replacement) so a project's quarters move together.
    """
    rng = np.random.default_rng(seed)
    groups = np.asarray(groups)
    unique_groups = np.unique(groups)
    group_to_indices = {g: np.where(groups == g)[0] for g in unique_groups}

    diffs = np.empty(n_boot)
    for b in range(n_boot):
        sampled_groups = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        idx = np.concatenate([group_to_indices[g] for g in sampled_groups])
        diffs[b] = metric_fn(y_true[idx], pred_a[idx]) - metric_fn(y_true[idx], pred_b[idx])

    alpha = (1 - ci) / 2
    lower, upper = float(np.percentile(diffs, alpha * 100)), float(np.percentile(diffs, (1 - alpha) * 100))
    return {
        "mean_diff": float(np.mean(diffs)),
        "ci_lower": lower,
        "ci_upper": upper,
        "ci_excludes_zero": bool(lower > 0 or upper < 0),
        "n_boot": n_boot,
        "n_groups": int(len(unique_groups)),
    }


# --------------------------------------------------------------------------
# DeLong's test for two correlated ROC-AUCs (Sun & Xu, 2014 fast algorithm)
# --------------------------------------------------------------------------


def _compute_midrank(x: np.ndarray) -> np.ndarray:
    """Midranks, accounting for ties — the building block of fast DeLong."""
    order = np.argsort(x)
    z = x[order]
    n = len(x)
    ranks = np.zeros(n, dtype=float)
    i = 0
    while i < n:
        j = i
        while j < n and z[j] == z[i]:
            j += 1
        ranks[i:j] = 0.5 * (i + j - 1) + 1
        i = j
    out = np.empty(n, dtype=float)
    out[order] = ranks
    return out


def _fast_delong(preds_sorted_transposed: np.ndarray, m: int) -> tuple[np.ndarray, np.ndarray]:
    """Sun & Xu (2014). `preds_sorted_transposed`: shape (k models, n rows),
    columns ordered so the m positive examples come first. Returns
    (aucs of shape (k,), covariance matrix of shape (k, k))."""
    n = preds_sorted_transposed.shape[1] - m
    positive = preds_sorted_transposed[:, :m]
    negative = preds_sorted_transposed[:, m:]
    k = preds_sorted_transposed.shape[0]

    tx = np.empty([k, m])
    ty = np.empty([k, n])
    tz = np.empty([k, m + n])
    for r in range(k):
        tx[r, :] = _compute_midrank(positive[r, :])
        ty[r, :] = _compute_midrank(negative[r, :])
        tz[r, :] = _compute_midrank(preds_sorted_transposed[r, :])

    aucs = tz[:, :m].sum(axis=1) / m / n - (m + 1.0) / (2.0 * n)
    v01 = (tz[:, :m] - tx) / n
    v10 = 1.0 - (tz[:, m:] - ty) / m
    sx = np.cov(v01)
    sy = np.cov(v10)
    delongcov = sx / m + sy / n
    return aucs, delongcov


def delong_test(y_true: np.ndarray, prob_a: np.ndarray, prob_b: np.ndarray) -> dict:
    """DeLong's test for the significance of the ROC-AUC difference between
    two models scored on the SAME samples (PRD §6.5)."""
    y_true = np.asarray(y_true, dtype=int)
    order = np.argsort(-y_true, kind="stable")  # positives (y=1) first
    m = int(y_true.sum())
    if m == 0 or m == len(y_true):
        nan = float("nan")
        return {"auc_a": nan, "auc_b": nan, "auc_diff": nan, "p_value": nan}

    preds = np.vstack([np.asarray(prob_a)[order], np.asarray(prob_b)[order]])
    aucs, cov = _fast_delong(preds, m)
    auc_diff = float(aucs[0] - aucs[1])
    var = cov[0, 0] + cov[1, 1] - 2 * cov[0, 1]
    z = 0.0 if var <= 0 else auc_diff / np.sqrt(var)
    p_value = float(2 * (1 - norm.cdf(abs(z))))

    return {
        "auc_a": float(aucs[0]),
        "auc_b": float(aucs[1]),
        "auc_diff": auc_diff,
        "z_statistic": float(z),
        "p_value": p_value,
    }


# --------------------------------------------------------------------------
# Orchestration — conventional baseline vs. best ML model, per target
# --------------------------------------------------------------------------

def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Lightweight R^2 for the bootstrap's inner loop — the same formula as
    `evaluate.regression_metrics`, but without building its whole metrics
    dict, since this runs thousands of times (n_boot x 2 models x targets).
    """
    y_true = np.asarray(y_true, dtype=float)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    return float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")


def _pr_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Lightweight PR-AUC for the bootstrap's inner loop.

    Deliberately NOT `evaluate.classification_metrics` — that function also
    scans up to 200 candidate thresholds for the best F1 score, ~400x more
    expensive per call (measured: ~2.7ms vs ~6us) and entirely wasted work
    here since only the PR-AUC value is used. Using the full function made
    the bake-off's bootstrap (n_boot=1000 x 2 models x 3 classification
    targets = 6,000 calls) take multiple HOURS instead of seconds — found by
    watching the Phase 4 production run stall, not by benchmarking ahead of
    time. See HANDOFF.md.
    """
    base_rate = float(np.asarray(y_true).mean())
    if not (0 < base_rate < 1):
        return float("nan")
    return float(average_precision_score(y_true, y_prob))


_R2 = _r2
_PR_AUC = _pr_auc


def run_bakeoff(completed_df: pd.DataFrame, ml_results: MLResults, n_boot: int = 1000) -> dict:
    """Compare each target's best conventional baseline against the best ML
    model on the SAME out-of-fold predictions. Returns the structure written
    to `artifacts/metrics/comparison.json` / rendered into `BAKEOFF.md`.
    """
    groups = completed_df["project_id"].to_numpy()
    comparison: dict[str, dict] = {}

    # --- cost_overrun_pct: OLS (conventional) vs best ML ---
    y_true_ols, ols_pred = _ols_oof_predictions(completed_df)
    best_reg_family = ml_results.best_family[REGRESSION_TARGET]
    y_true_ml, ml_pred = ml_results.oof[REGRESSION_TARGET][best_reg_family]
    assert np.array_equal(y_true_ols, y_true_ml), "OOF row alignment broke between OLS and ML"
    comparison[REGRESSION_TARGET] = {
        "task": "regression",
        "conventional_model": "ols_sector_fe",
        "conventional_r2": evaluate.regression_metrics(y_true_ols, ols_pred)["r2"],
        "ml_model": ml_results.best_family[REGRESSION_TARGET],
        "ml_r2": evaluate.regression_metrics(y_true_ml, ml_pred)["r2"],
        "bootstrap": paired_bootstrap_ci(y_true_ml, ml_pred, ols_pred, groups, _R2, n_boot=n_boot),
    }

    # --- time_overrun_months: naive (conventional) vs best ML — PRD §6.3
    # scopes OLS to cost only; naive is the only Phase-3 regression baseline
    # available for this target (see HANDOFF.md).
    y_true_naive, naive_pred = _naive_oof_predictions(completed_df, "time_overrun_months")
    best_time_family = ml_results.best_family["time_overrun_months"]
    y_true_ml2, ml_pred2 = ml_results.oof["time_overrun_months"][best_time_family]
    assert np.array_equal(y_true_naive, y_true_ml2), "OOF row alignment broke for time_overrun_months"
    comparison["time_overrun_months"] = {
        "task": "regression",
        "conventional_model": "naive_sector_mean",
        "conventional_r2": evaluate.regression_metrics(y_true_naive, naive_pred)["r2"],
        "ml_model": ml_results.best_family["time_overrun_months"],
        "ml_r2": evaluate.regression_metrics(y_true_ml2, ml_pred2)["r2"],
        "bootstrap": paired_bootstrap_ci(y_true_ml2, ml_pred2, naive_pred, groups, _R2, n_boot=n_boot),
    }

    # --- classification targets: logistic (conventional) vs best ML ---
    for target in CLASSIFICATION_TARGETS:
        y_true_log, log_prob = _logistic_oof_predictions(completed_df, target)
        y_true_ml3, ml_prob = ml_results.oof[target][ml_results.best_family[target]]
        assert np.array_equal(y_true_log, y_true_ml3), f"OOF row alignment broke for {target}"

        comparison[target] = {
            "task": "classification",
            "conventional_model": "logistic_regression",
            "conventional_pr_auc": evaluate.classification_metrics(y_true_log, log_prob)["pr_auc"],
            "ml_model": ml_results.best_family[target],
            "ml_pr_auc": evaluate.classification_metrics(y_true_ml3, ml_prob)["pr_auc"],
            "bootstrap": paired_bootstrap_ci(y_true_ml3, ml_prob, log_prob, groups, _PR_AUC, n_boot=n_boot),
            "delong": delong_test(y_true_log, ml_prob, log_prob),
        }

    return comparison
