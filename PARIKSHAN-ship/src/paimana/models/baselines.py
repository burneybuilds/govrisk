"""Conventional statistical baselines — PRD §6.3.

Every model here is evaluated via the SAME leakage-safe protocol: fit on a
GroupKFold(project_id) training fold ONLY — including any target-mean,
imputer, or encoder — predict on the held-out fold, and aggregate metrics
over the concatenated out-of-fold (OOF) predictions. This is what makes
Phase 4's ML-vs-statistics bake-off an apples-to-apples comparison rather
than two models scored under different protocols.

Regression and classification targets are only defined for COMPLETED
(non-censored) projects (PRD §5.4) — every function here operates on that
subset of the panel. Time-to-completion, where censoring is central, is
handled separately in `survival.py`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from paimana import config
from paimana.features.build import select_features
from paimana.features.splits import grouped_cv
from paimana.models import evaluate
from paimana.models.preprocessing import make_sklearn_preprocessor

REGRESSION_TARGET = "cost_overrun_pct"
CLASSIFICATION_TARGETS: tuple[str, ...] = ("y_cost_overrun", "y_time_overrun", "y_severe")
ALL_TARGETS: tuple[str, ...] = (REGRESSION_TARGET, "time_overrun_months", *CLASSIFICATION_TARGETS)

# Shared with ml.py (Phase 4) — see paimana.models.evaluate for the definition.
_completed_labelled_rows = evaluate.completed_labelled_rows


# --------------------------------------------------------------------------
# Naive baseline — the floor every later model (including the "conventional"
# ones below) must beat.
# --------------------------------------------------------------------------
def _naive_oof_predictions(df: pd.DataFrame, target: str) -> tuple[np.ndarray, np.ndarray]:
    """Out-of-fold naive predictions: training-fold sector mean / base rate,
    with a fallback to the training-fold global mean for any sector absent
    from that fold's training data. Returns (y_true, oof_predictions)."""
    y_all = df[target].astype(float)
    groups = df["project_id"]
    oof = np.full(len(df), np.nan)

    for train_idx, test_idx in grouped_cv(df, y_all, groups, n_splits=5):
        train_df = df.iloc[train_idx]
        global_stat = float(train_df[target].astype(float).mean())
        sector_stat = train_df[target].astype(float).groupby(train_df["sector"]).mean()

        test_sectors = df.iloc[test_idx]["sector"]
        preds = test_sectors.map(sector_stat).to_numpy(dtype=float)
        preds = np.where(np.isnan(preds), global_stat, preds)
        oof[test_idx] = preds

    return y_all.to_numpy(), oof


def naive_baseline(df: pd.DataFrame, target: str, task: str) -> dict:
    """Out-of-fold naive-baseline metrics — see `_naive_oof_predictions`."""
    y_true, oof = _naive_oof_predictions(df, target)
    if task == "regression":
        return evaluate.regression_metrics(y_true, oof)
    return evaluate.classification_metrics(y_true, oof)


# --------------------------------------------------------------------------
# OLS on log(cost_ratio) with sector fixed effects (PRD §6.3)
# --------------------------------------------------------------------------
def _ols_oof_predictions(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """OOF cost_overrun_pct predictions from the sector-FE OLS model
    (Duan-smearing corrected). Returns (y_true, oof_predictions)."""
    work = df.copy()
    work["cost_ratio"] = 1.0 + work[REGRESSION_TARGET] / 100.0
    work["log_cost_ratio"] = np.log(work["cost_ratio"].clip(lower=0.05))
    work["sector"] = pd.Categorical(work["sector"], categories=config.SECTORS)

    groups = work["project_id"]
    y_true = work[REGRESSION_TARGET].to_numpy()
    oof_pred = np.full(len(work), np.nan)

    for train_idx, test_idx in grouped_cv(work, work["log_cost_ratio"], groups, n_splits=5):
        train_df, test_df = work.iloc[train_idx], work.iloc[test_idx]
        model = smf.ols("log_cost_ratio ~ C(sector)", data=train_df).fit()
        smearing_factor = float(np.mean(np.exp(model.resid)))
        pred_log_ratio = model.predict(test_df)
        pred_ratio = np.exp(pred_log_ratio) * smearing_factor
        oof_pred[test_idx] = (pred_ratio - 1.0) * 100.0

    return y_true, oof_pred


def ols_cost_overrun(df: pd.DataFrame) -> dict:
    """Fit OLS of log(final_cost / original_cost) on sector fixed effects
    only (a simple, interpretable conventional baseline — PRD §6.3
    deliberately scopes this model to sector effects, not the full feature
    set; the full-feature-set conventional comparison is `logistic_targets`
    below and the ML models in Phase 4).

    Evaluated the same OOF way as every other model here; metrics are
    reported back on the original cost_overrun_pct scale so they are
    directly comparable to every other regression result in this project.
    """
    # OOF predictions carry Duan's (1983) smearing correction internally
    # (see `_ols_oof_predictions`): naively back-transforming a log-scale
    # prediction via plain exp() is biased downward by Jensen's inequality
    # and, uncorrected, made this model score WORSE than the naive baseline
    # it should beat — not because sector fixed effects carry no signal,
    # but purely from retransformation bias (found and fixed in Phase 3).
    y_true, oof_pred = _ols_oof_predictions(df)
    metrics = evaluate.regression_metrics(y_true, oof_pred)

    work = df.copy()
    work["cost_ratio"] = 1.0 + work[REGRESSION_TARGET] / 100.0
    work["log_cost_ratio"] = np.log(work["cost_ratio"].clip(lower=0.05))
    work["sector"] = pd.Categorical(work["sector"], categories=config.SECTORS)

    # A full-sample fit (not OOF) purely for the interpretable summary table
    # (coefficients, p-values, R^2) that PRD §7/Phase 3 task 5 asks for —
    # this is reporting, not evaluation, so in-sample is the correct choice
    # here (the OOF metrics above are the evaluation).
    full_model = smf.ols("log_cost_ratio ~ C(sector)", data=work).fit()
    metrics["summary_r2"] = float(full_model.rsquared)
    metrics["summary_r2_adj"] = float(full_model.rsquared_adj)
    metrics["summary_n_obs"] = int(full_model.nobs)
    metrics["summary_coefficients"] = {k: float(v) for k, v in full_model.params.items()}
    metrics["summary_pvalues"] = {k: float(v) for k, v in full_model.pvalues.items()}
    metrics["summary_text"] = full_model.summary().as_text()
    return metrics


# --------------------------------------------------------------------------
# Regularised logistic regression on the FULL feature set (PRD §6.3) — a
# genuine conventional-ML competitor to Phase 4's tree ensembles, not just a
# sector-effects toy.
# --------------------------------------------------------------------------
def _logistic_oof_predictions(df: pd.DataFrame, target: str) -> tuple[np.ndarray, np.ndarray]:
    """OOF predicted probabilities from the full-feature-set logistic
    regression. Returns (y_true, oof_probabilities)."""
    X = select_features(df)
    y = df[target].astype(int)
    groups = df["project_id"]
    oof_prob = np.full(len(df), np.nan)

    for train_idx, test_idx in grouped_cv(X, y, groups, n_splits=5):
        pipeline = Pipeline(
            [
                ("preprocess", make_sklearn_preprocessor()),
                ("model", LogisticRegression(penalty="l2", max_iter=2000, random_state=config.RANDOM_SEED)),
            ]
        )
        pipeline.fit(X.iloc[train_idx], y.iloc[train_idx])
        oof_prob[test_idx] = pipeline.predict_proba(X.iloc[test_idx])[:, 1]

    return y.to_numpy(), oof_prob


def logistic_target(df: pd.DataFrame, target: str) -> dict:
    """OOF-evaluated L2-regularised logistic regression for one binary target."""
    y_true, oof_prob = _logistic_oof_predictions(df, target)
    return evaluate.classification_metrics(y_true, oof_prob)


def run_all_baselines(features_df: pd.DataFrame) -> dict:
    """Orchestrate every Phase 3 non-survival baseline across every target.

    Returns a dict keyed "naive" / "ols" / "logit", each mapping target name
    to that target's metrics — the schema `scripts/run_baselines.py` writes
    to `artifacts/metrics/baselines.json`.
    """
    completed = _completed_labelled_rows(features_df)

    naive: dict[str, dict] = {}
    naive[REGRESSION_TARGET] = naive_baseline(completed, REGRESSION_TARGET, task="regression")
    naive["time_overrun_months"] = naive_baseline(completed, "time_overrun_months", task="regression")
    for target in CLASSIFICATION_TARGETS:
        naive[target] = naive_baseline(completed, target, task="classification")

    ols = {REGRESSION_TARGET: ols_cost_overrun(completed)}

    logit = {target: logistic_target(completed, target) for target in CLASSIFICATION_TARGETS}

    return {"naive": naive, "ols": ols, "logit": logit}
