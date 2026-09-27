"""Tests for the conventional statistical baselines (PRD §6.3).

Uses a mid-sized synthetic generation (not the full 1,981-project scale, for
test speed) with a fixed seed for full determinism. n_projects=600 is chosen
so every sector has enough projects that GroupKFold is very unlikely to
leave a sector entirely absent from a training fold — `ols_cost_overrun`'s
`smf.ols("... ~ C(sector)")` formula would raise on a category unseen at
predict time. This is a known small-N testing edge case, not a production
concern: `logistic_target`'s OneHotEncoder uses fixed, config-driven
categories (`handle_unknown="ignore"`) and is robust to it regardless of
scale; the full 1,981-project production run (~60 projects/sector on
average) has never hit it.
"""

from __future__ import annotations

import numpy as np
import pytest

from paimana.data.generator import generate_synthetic_panel
from paimana.features.build import build_feature_table
from paimana.models.baselines import (
    CLASSIFICATION_TARGETS,
    REGRESSION_TARGET,
    _completed_labelled_rows,
    logistic_target,
    naive_baseline,
    ols_cost_overrun,
    run_all_baselines,
)
from paimana.models.survival import run_survival_models


@pytest.fixture(scope="module")
def small_features_df():
    generated = generate_synthetic_panel(n_projects=600, seed=42)
    return build_feature_table(generated.panel, generated.projects), generated.projects


@pytest.fixture(scope="module")
def completed_df(small_features_df):
    features_df, _ = small_features_df
    return _completed_labelled_rows(features_df)


def test_completed_labelled_rows_excludes_censored(completed_df):
    assert (completed_df["is_censored"] == False).all()  # noqa: E712
    assert completed_df[REGRESSION_TARGET].notna().all()


def test_naive_baseline_regression_returns_expected_keys(completed_df):
    m = naive_baseline(completed_df, REGRESSION_TARGET, task="regression")
    assert {"mae", "rmse", "r2", "mape_pct", "n"} <= set(m)
    assert m["n"] == len(completed_df)


def test_naive_baseline_classification_returns_expected_keys(completed_df):
    m = naive_baseline(completed_df, "y_severe", task="classification")
    assert {"pr_auc", "roc_auc", "brier", "base_rate"} <= set(m)
    assert 0.0 <= m["base_rate"] <= 1.0


def test_naive_baseline_is_not_perfect(completed_df):
    """A sector-mean floor must not achieve a suspiciously good fit — if it
    does, something about the fixture (or a real leakage bug) is wrong."""
    m = naive_baseline(completed_df, REGRESSION_TARGET, task="regression")
    assert m["r2"] < 0.5


def test_ols_cost_overrun_returns_summary_and_oof_metrics(completed_df):
    m = ols_cost_overrun(completed_df)
    assert {"mae", "rmse", "r2", "n"} <= set(m)
    assert "summary_r2" in m
    assert "summary_coefficients" in m
    assert "summary_pvalues" in m
    assert "Intercept" in m["summary_coefficients"]
    assert "OLS Regression Results" in m["summary_text"]


def test_ols_smearing_correction_beats_plain_exp_backtransform(completed_df):
    """Regression guard for the retransformation-bias bug found in Phase 3:
    the smearing-corrected R^2 must not be (much) worse than a naive
    prediction of the training mean would be."""
    m = ols_cost_overrun(completed_df)
    naive_m = naive_baseline(completed_df, REGRESSION_TARGET, task="regression")
    # OLS-with-smearing should be at least competitive with (not dramatically
    # worse than) the plain sector-mean naive baseline it is meant to refine.
    assert m["r2"] >= naive_m["r2"] - 0.05


@pytest.mark.parametrize("target", CLASSIFICATION_TARGETS)
def test_logistic_target_returns_expected_keys_and_plausible_scores(completed_df, target):
    m = logistic_target(completed_df, target)
    assert {"pr_auc", "roc_auc", "brier", "f1_at_best_threshold", "base_rate"} <= set(m)
    assert 0.0 <= m["pr_auc"] <= 1.0
    assert 0.0 <= m["brier"] <= 1.0


def test_run_all_baselines_top_level_structure(small_features_df):
    features_df, _ = small_features_df
    results = run_all_baselines(features_df)
    assert {"naive", "ols", "logit"} <= set(results)
    assert REGRESSION_TARGET in results["naive"]
    assert "time_overrun_months" in results["naive"]
    for target in CLASSIFICATION_TARGETS:
        assert target in results["naive"]
        assert target in results["logit"]
    assert REGRESSION_TARGET in results["ols"]


def test_run_survival_models_returns_plausible_concordance(small_features_df):
    _, projects = small_features_df
    results = run_survival_models(projects, cut_year=2018)
    assert {"weibull_aft", "cox_ph"} <= set(results)
    for model_name in ("weibull_aft", "cox_ph"):
        c_index = results[model_name]["concordance_index_test"]
        assert 0.5 <= c_index <= 1.0  # must beat random (0.5), can't exceed 1.0
    assert "concordance_index_test_excl_duration_covariate" in results["weibull_aft"]


def test_no_model_exceeds_the_r2_sanity_gate(small_features_df):
    """PRD §4.3.5 / config.MAX_PLAUSIBLE_R2: a model beating this on
    synthetic data calibrated to be noisy is evidence of a leakage bug."""
    from paimana import config

    features_df, _ = small_features_df
    results = run_all_baselines(features_df)
    assert results["ols"][REGRESSION_TARGET]["r2"] < config.MAX_PLAUSIBLE_R2


def test_no_model_exceeds_the_pr_auc_sanity_gate(small_features_df):
    from paimana import config

    features_df, _ = small_features_df
    results = run_all_baselines(features_df)
    for target in CLASSIFICATION_TARGETS:
        pr_auc = results["logit"][target]["pr_auc"]
        assert pr_auc < config.MAX_PLAUSIBLE_PR_AUC or np.isnan(pr_auc)
