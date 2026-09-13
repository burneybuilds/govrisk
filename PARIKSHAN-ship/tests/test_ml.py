"""Tests for the ML models (PRD §6.3, §7/Phase 4).

Uses a small synthetic generation for speed. Individual model-family
functions are tested directly (fast); `run_all_ml_models` — the full
orchestrator across 3 families x 5 targets — is exercised in exactly one
integration test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from paimana import config
from paimana.data.generator import generate_synthetic_panel
from paimana.features.build import build_feature_table, select_features
from paimana.models.evaluate import completed_labelled_rows
from paimana.models.ml import (
    CLASSIFICATION_TARGETS,
    MODEL_FAMILIES,
    REGRESSION_TARGETS,
    classifier_oof_calibrated,
    fit_quantile_model,
    make_classifier,
    make_regressor,
    regressor_oof,
    run_all_ml_models,
    select_hyperparameters,
)

SMALL_PARAMS = {"n_estimators": 50, "max_depth": 4}


@pytest.fixture(scope="module")
def small_completed_df():
    generated = generate_synthetic_panel(n_projects=250, seed=42)
    features_df = build_feature_table(generated.panel, generated.projects)
    return completed_labelled_rows(features_df)


@pytest.mark.parametrize("family", MODEL_FAMILIES)
def test_make_regressor_fits_and_predicts(small_completed_df, family):
    X = select_features(small_completed_df)
    y = small_completed_df["cost_overrun_pct"].astype(float)
    model = make_regressor(family, SMALL_PARAMS)
    model.fit(X.iloc[:150], y.iloc[:150])
    preds = model.predict(X.iloc[150:200])
    assert len(preds) == 50
    assert np.all(np.isfinite(preds))


@pytest.mark.parametrize("family", MODEL_FAMILIES)
def test_make_classifier_fits_and_predicts_valid_probabilities(small_completed_df, family):
    X = select_features(small_completed_df)
    y = small_completed_df["y_severe"].astype(int)
    model = make_classifier(family, SMALL_PARAMS)
    model.fit(X.iloc[:150], y.iloc[:150])
    prob = model.predict_proba(X.iloc[150:200])[:, 1]
    assert len(prob) == 50
    assert np.all((prob >= 0) & (prob <= 1))


@pytest.mark.parametrize("family", MODEL_FAMILIES)
def test_regressor_oof_covers_every_row_with_finite_predictions(small_completed_df, family):
    y_true, oof_pred = regressor_oof(small_completed_df, "cost_overrun_pct", family, SMALL_PARAMS)
    assert len(y_true) == len(oof_pred) == len(small_completed_df)
    assert np.all(np.isfinite(oof_pred))  # every row must land in exactly one test fold


@pytest.mark.parametrize("family", MODEL_FAMILIES)
def test_classifier_oof_calibrated_produces_valid_probabilities(small_completed_df, family):
    y_true, oof_prob = classifier_oof_calibrated(small_completed_df, "y_severe", family, SMALL_PARAMS)
    assert len(y_true) == len(oof_prob) == len(small_completed_df)
    assert np.all(np.isfinite(oof_prob))
    assert np.all((oof_prob >= 0) & (oof_prob <= 1))


def test_select_hyperparameters_returns_one_config_per_family_per_task(small_completed_df):
    chosen = select_hyperparameters(small_completed_df, n_splits=2)
    assert set(chosen) == {"regression", "classification"}
    for task in ("regression", "classification"):
        assert set(chosen[task]) == set(MODEL_FAMILIES)
        for family in MODEL_FAMILIES:
            assert isinstance(chosen[task][family], dict)


def test_fit_quantile_model_returns_ordered_quantiles(small_completed_df):
    result = fit_quantile_model(small_completed_df, "cost_overrun_pct")
    assert {"quantiles", "observed_coverage_test", "mean_interval_width_test", "final_model"} <= set(result)
    assert result["mean_interval_width_test"] >= 0  # p90 prediction must not be below p10 on average
    assert 0.0 <= result["observed_coverage_test"] <= 1.0

    # The final model must predict p10 <= p50 <= p90 for actual rows (a
    # basic quantile-crossing sanity check).
    X = select_features(small_completed_df).iloc[:20]
    preds = result["final_model"].predict(X)
    assert (preds[:, 0] <= preds[:, 1] + 1e-6).all()
    assert (preds[:, 1] <= preds[:, 2] + 1e-6).all()


def test_run_all_ml_models_full_orchestration(small_completed_df):
    """The one slow, full-pipeline integration test: every family, every
    target, hyperparameter search, calibration, quantile models."""
    results = run_all_ml_models(small_completed_df)

    for target in REGRESSION_TARGETS:
        assert set(results.metrics[target]) == set(MODEL_FAMILIES)
        assert results.best_family[target] in MODEL_FAMILIES
        assert target in results.final_models
        assert target in results.quantile_results

    for target in CLASSIFICATION_TARGETS:
        assert set(results.metrics[target]) == set(MODEL_FAMILIES)
        assert results.best_family[target] in MODEL_FAMILIES
        assert target in results.final_models


def test_no_ml_model_exceeds_sanity_gate_on_small_fixture(small_completed_df):
    """PRD §4.3.5: a model this good on noisy synthetic data is evidence of
    a leakage bug — belt-and-braces alongside the full-scale check in
    scripts/run_models.py itself."""
    results = run_all_ml_models(small_completed_df)
    for target in REGRESSION_TARGETS:
        for family, m in results.metrics[target].items():
            assert m["r2"] < config.MAX_PLAUSIBLE_R2, f"{target}/{family} R2={m['r2']} too high"
    for target in CLASSIFICATION_TARGETS:
        for family, m in results.metrics[target].items():
            if not np.isnan(m["pr_auc"]):
                assert m["pr_auc"] < config.MAX_PLAUSIBLE_PR_AUC, (
                    f"{target}/{family} PR-AUC={m['pr_auc']} too high"
                )


def test_regressor_oof_reproducible_with_fixed_seed(small_completed_df):
    y1, pred1 = regressor_oof(small_completed_df, "cost_overrun_pct", "random_forest", SMALL_PARAMS)
    y2, pred2 = regressor_oof(small_completed_df, "cost_overrun_pct", "random_forest", SMALL_PARAMS)
    pd.testing.assert_series_equal(pd.Series(pred1), pd.Series(pred2))
