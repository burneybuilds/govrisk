"""ML models — PRD §6.3, §7/Phase 4.

RandomForest / XGBoost / LightGBM regressors and classifiers, evaluated via
the SAME out-of-fold GroupKFold(project_id) protocol as Phase 3's
conventional baselines (`baselines.py`) — required for a fair,
apples-to-apples bake-off (PRD §6.5): both sides' predictions land on
IDENTICAL rows because GroupKFold is deterministic (no shuffling) given the
same input order.

Hyperparameters are chosen via a small, time-boxed search (PRD §7/Phase 4
task 1): run ONCE per model family per task type (regression scored on
`cost_overrun_pct`, classification scored on `y_severe`) via a quick 3-fold
GroupKFold, then the winning configuration is reused across every target of
that type. This is an explicit, documented simplification given hackathon
time constraints — a production system would tune per-target. The search
uses RAW (uncalibrated) probabilities for classification scoring: PR-AUC
depends only on score ranking, and isotonic calibration is monotonic, so it
cannot change which hyperparameters win — calibration is applied only in
the final OOF reporting and serialized artifacts.

Classifiers are isotonic-calibrated via a GROUP-AWARE inner GroupKFold split
of each outer training fold (PRD §7/Phase 4 task 2) — sklearn's default
plain-KFold calibration would let a project's own quarters leak across the
fit/calibrate boundary.

ENCODING NOTE: all three families (including XGBoost/LightGBM) use the same
one-hot `make_sklearn_preprocessor()` pipeline, NOT native categorical
support. Measured during Phase 4: on this dataset, XGBoost/LightGBM's
native categorical splitting scored MEASURABLY WORSE than plain one-hot
(XGBoost R^2 0.033 vs. 0.256; LightGBM 0.122 vs. 0.242, on a representative
fold) — see `preprocessing.prepare_native_categorical`'s docstring for the
full note. One-hot is used uniformly both because it is simply the better
result here and because it keeps every family under the exact same
preprocessing for a fair bake-off.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier, XGBRegressor

from paimana import config
from paimana.features.build import select_features
from paimana.features.splits import grouped_cv, temporal_split
from paimana.models import evaluate
from paimana.models.preprocessing import make_sklearn_preprocessor

MODEL_FAMILIES: tuple[str, ...] = ("random_forest", "xgboost", "lightgbm")
REGRESSION_TARGETS: tuple[str, ...] = ("cost_overrun_pct", "time_overrun_months")
CLASSIFICATION_TARGETS: tuple[str, ...] = ("y_cost_overrun", "y_time_overrun", "y_severe")
QUANTILES: tuple[float, ...] = (0.1, 0.5, 0.9)

# Small, time-boxed hyperparameter grids (PRD §7/Phase 4 task 1) — two
# configurations per family, one conservative and one larger/more flexible.
_HYPERPARAM_GRIDS: dict[str, list[dict]] = {
    "random_forest": [
        {"n_estimators": 200, "max_depth": 8, "min_samples_leaf": 5},
        {"n_estimators": 400, "max_depth": 14, "min_samples_leaf": 2},
    ],
    "xgboost": [
        {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.1},
        {"n_estimators": 400, "max_depth": 6, "learning_rate": 0.05},
    ],
    "lightgbm": [
        {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.1, "num_leaves": 15},
        {"n_estimators": 400, "max_depth": -1, "learning_rate": 0.05, "num_leaves": 31},
    ],
}


# --------------------------------------------------------------------------
# Model factories — every family wrapped in the SAME one-hot preprocessing
# pipeline (see module docstring for why native categorical support was
# measured and rejected for this dataset).
# --------------------------------------------------------------------------
def make_regressor(family: str, params: dict):
    if family == "random_forest":
        estimator = RandomForestRegressor(**params, random_state=config.RANDOM_SEED, n_jobs=-1)
    elif family == "xgboost":
        estimator = XGBRegressor(**params, random_state=config.RANDOM_SEED, tree_method="hist", n_jobs=-1)
    elif family == "lightgbm":
        estimator = LGBMRegressor(**params, random_state=config.RANDOM_SEED, verbosity=-1, n_jobs=-1)
    else:
        raise ValueError(f"Unknown model family: {family!r}")
    return Pipeline([("preprocess", make_sklearn_preprocessor()), ("model", estimator)])


def make_classifier(family: str, params: dict):
    if family == "random_forest":
        estimator = RandomForestClassifier(**params, random_state=config.RANDOM_SEED, n_jobs=-1)
    elif family == "xgboost":
        estimator = XGBClassifier(
            **params, random_state=config.RANDOM_SEED, tree_method="hist", n_jobs=-1, eval_metric="logloss"
        )
    elif family == "lightgbm":
        estimator = LGBMClassifier(**params, random_state=config.RANDOM_SEED, verbosity=-1, n_jobs=-1)
    else:
        raise ValueError(f"Unknown model family: {family!r}")
    return Pipeline([("preprocess", make_sklearn_preprocessor()), ("model", estimator)])


# --------------------------------------------------------------------------
# Small, time-boxed hyperparameter search (PRD §7/Phase 4 task 1)
# --------------------------------------------------------------------------
def select_hyperparameters(
    df: pd.DataFrame,
    regression_representative: str = "cost_overrun_pct",
    classification_representative: str = "y_severe",
    n_splits: int = 3,
) -> dict[str, dict[str, dict]]:
    """Return {"regression": {family: best_params}, "classification": {family: best_params}}.

    Scored via a quick `n_splits`-fold GroupKFold on ONE representative
    target per task type; the winner is reused for every target of that
    type (see module docstring for why this is a deliberate simplification).
    """
    X = select_features(df)
    groups = df["project_id"]

    reg_y = df[regression_representative].astype(float)
    clf_y = df[classification_representative].astype(int)

    chosen: dict[str, dict[str, dict]] = {"regression": {}, "classification": {}}

    for family, grid in _HYPERPARAM_GRIDS.items():
        best_score, best_params = -np.inf, grid[0]
        for params in grid:
            fold_scores = []
            for train_idx, test_idx in grouped_cv(X, reg_y, groups, n_splits=n_splits):
                X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
                model = make_regressor(family, params)
                model.fit(X_train, reg_y.iloc[train_idx])
                preds = model.predict(X_test)
                fold_scores.append(evaluate.regression_metrics(reg_y.iloc[test_idx].to_numpy(), preds)["r2"])
            score = float(np.mean(fold_scores))
            if score > best_score:
                best_score, best_params = score, params
        chosen["regression"][family] = best_params

    for family, grid in _HYPERPARAM_GRIDS.items():
        best_score, best_params = -np.inf, grid[0]
        for params in grid:
            fold_scores = []
            for train_idx, test_idx in grouped_cv(X, clf_y, groups, n_splits=n_splits):
                X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
                model = make_classifier(family, params)
                model.fit(X_train, clf_y.iloc[train_idx])
                prob = model.predict_proba(X_test)[:, 1]
                fold_scores.append(
                    evaluate.classification_metrics(clf_y.iloc[test_idx].to_numpy(), prob)["pr_auc"]
                )
            score = float(np.nanmean(fold_scores))
            if score > best_score:
                best_score, best_params = score, params
        chosen["classification"][family] = best_params

    return chosen


# --------------------------------------------------------------------------
# Out-of-fold evaluation (PRD §6.2.1) — the reporting protocol
# --------------------------------------------------------------------------
def regressor_oof(df: pd.DataFrame, target: str, family: str, params: dict) -> tuple[np.ndarray, np.ndarray]:
    """Returns (y_true, oof_predictions) for one (family, target) pair."""
    X = select_features(df)
    y = df[target].astype(float)
    groups = df["project_id"]
    oof = np.full(len(df), np.nan)

    for train_idx, test_idx in grouped_cv(X, y, groups, n_splits=5):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        model = make_regressor(family, params)
        model.fit(X_train, y.iloc[train_idx])
        oof[test_idx] = model.predict(X_test)

    return y.to_numpy(), oof


def make_group_aware_calibrated_classifier(
    base_estimator, X_train: pd.DataFrame, y_train: pd.Series, groups_train: np.ndarray, inner_splits: int = 3
) -> tuple[CalibratedClassifierCV, list[tuple[np.ndarray, np.ndarray]]]:
    """Fit an isotonic-calibrated classifier using a GROUP-AWARE inner
    GroupKFold split (PRD §7/Phase 4 task 2) — sklearn's default plain-KFold
    calibration would let a project's own quarters land on both sides of the
    fit/calibrate boundary. Returns (fitted calibrator, the inner_cv splits
    actually used) so callers/tests can verify the group-safety directly
    (e.g. with `paimana.features.splits.assert_no_group_overlap`) rather
    than trusting the docstring.
    """
    inner_cv = list(GroupKFold(n_splits=inner_splits).split(X_train, y_train, groups=groups_train))
    calibrated = CalibratedClassifierCV(estimator=base_estimator, method="isotonic", cv=inner_cv)
    calibrated.fit(X_train, y_train)
    return calibrated, inner_cv


def classifier_oof_calibrated(
    df: pd.DataFrame, target: str, family: str, params: dict, inner_splits: int = 3
) -> tuple[np.ndarray, np.ndarray]:
    """Returns (y_true, oof_calibrated_probabilities) for one (family, target)
    pair, isotonic-calibrated via a group-aware INNER GroupKFold split of
    each outer training fold (PRD §7/Phase 4 task 2)."""
    X = select_features(df)
    y = df[target].astype(int)
    groups = df["project_id"]
    oof_prob = np.full(len(df), np.nan)

    for train_idx, test_idx in grouped_cv(X, y, groups, n_splits=5):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train = y.iloc[train_idx]
        groups_train = groups.iloc[train_idx].to_numpy()

        base = make_classifier(family, params)
        calibrated, _inner_cv = make_group_aware_calibrated_classifier(
            base, X_train, y_train, groups_train, inner_splits
        )
        oof_prob[test_idx] = calibrated.predict_proba(X_test)[:, 1]

    return y.to_numpy(), oof_prob


# --------------------------------------------------------------------------
# XGBoost quantile models — prediction intervals (PRD §6.3)
# --------------------------------------------------------------------------
def fit_quantile_model(df: pd.DataFrame, target: str, quantiles: tuple[float, ...] = QUANTILES) -> dict:
    """Fit one multi-output XGBoost quantile regressor (10th/50th/90th
    percentile in a single model via `quantile_alpha=[...]`), evaluated for
    honest interval coverage on a temporal train/test split (PRD §6.2.2),
    then refit on ALL completed data as the shipped artifact.
    """
    X_full = select_features(df)
    y_full = df[target].astype(float)

    train_idx, test_idx = temporal_split(df, cut_year=2018)
    X_train, X_test = X_full.iloc[train_idx], X_full.iloc[test_idx]
    y_train, y_test = y_full.iloc[train_idx], y_full.iloc[test_idx]

    def _make_model() -> Pipeline:
        estimator = XGBRegressor(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            objective="reg:quantileerror",
            quantile_alpha=list(quantiles),
            tree_method="hist",
            random_state=config.RANDOM_SEED,
            n_jobs=-1,
        )
        return Pipeline([("preprocess", make_sklearn_preprocessor()), ("model", estimator)])

    eval_model = _make_model()
    eval_model.fit(X_train, y_train)
    test_preds = eval_model.predict(X_test)  # shape (n_test, len(quantiles))

    lower, upper = test_preds[:, 0], test_preds[:, -1]
    coverage = float(np.mean((y_test.to_numpy() >= lower) & (y_test.to_numpy() <= upper)))
    interval_width = float(np.mean(upper - lower))

    final_model = _make_model()
    final_model.fit(X_full, y_full)

    return {
        "quantiles": list(quantiles),
        "target_coverage": quantiles[-1] - quantiles[0],
        "observed_coverage_test": coverage,
        "mean_interval_width_test": interval_width,
        "n_train": int(len(y_train)),
        "n_test": int(len(y_test)),
        "final_model": final_model,
    }


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
@dataclass
class MLResults:
    """Everything Phase 4's bake-off and artifact serialization need."""

    # {target: {family: metrics}}
    metrics: dict[str, dict[str, dict]] = field(default_factory=dict)
    # {target: {family: (y_true, oof_pred)}}
    oof: dict[str, dict[str, tuple[np.ndarray, np.ndarray]]] = field(default_factory=dict)
    # {target: family}
    best_family: dict[str, str] = field(default_factory=dict)
    # {target: fitted estimator on ALL completed data}
    final_models: dict[str, object] = field(default_factory=dict)
    # {target: quantile info incl. final_model}
    quantile_results: dict[str, dict] = field(default_factory=dict)
    chosen_hyperparameters: dict[str, dict[str, dict]] = field(default_factory=dict)


def run_all_ml_models(completed_df: pd.DataFrame) -> MLResults:
    """Fit RF/XGBoost/LightGBM for every regression and classification
    target, evaluate OOF, pick the best family per target, refit that best
    family on all completed data, and fit the XGBoost quantile models.
    `completed_df` must already be filtered to labelled rows (see
    `evaluate.completed_labelled_rows`).
    """
    results = MLResults()
    results.chosen_hyperparameters = select_hyperparameters(completed_df)

    for target in REGRESSION_TARGETS:
        results.metrics[target] = {}
        results.oof[target] = {}
        for family in MODEL_FAMILIES:
            params = results.chosen_hyperparameters["regression"][family]
            y_true, oof_pred = regressor_oof(completed_df, target, family, params)
            results.oof[target][family] = (y_true, oof_pred)
            results.metrics[target][family] = evaluate.regression_metrics(y_true, oof_pred)

        best = max(results.metrics[target], key=lambda f: results.metrics[target][f]["r2"])
        results.best_family[target] = best
        X_full = select_features(completed_df)
        final_model = make_regressor(best, results.chosen_hyperparameters["regression"][best])
        final_model.fit(X_full, completed_df[target].astype(float))
        results.final_models[target] = final_model

    for target in CLASSIFICATION_TARGETS:
        results.metrics[target] = {}
        results.oof[target] = {}
        for family in MODEL_FAMILIES:
            params = results.chosen_hyperparameters["classification"][family]
            y_true, oof_prob = classifier_oof_calibrated(completed_df, target, family, params)
            results.oof[target][family] = (y_true, oof_prob)
            results.metrics[target][family] = evaluate.classification_metrics(y_true, oof_prob)

        best = max(results.metrics[target], key=lambda f: results.metrics[target][f]["pr_auc"])
        results.best_family[target] = best
        X_full = select_features(completed_df)
        y_full = completed_df[target].astype(int)
        groups_full = completed_df["project_id"].to_numpy()
        base = make_classifier(best, results.chosen_hyperparameters["classification"][best])
        calibrated, _inner_cv = make_group_aware_calibrated_classifier(base, X_full, y_full, groups_full)
        results.final_models[target] = calibrated

    for target in REGRESSION_TARGETS:
        results.quantile_results[target] = fit_quantile_model(completed_df, target)

    return results
