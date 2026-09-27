"""Tests for the bake-off harness — paired bootstrap and DeLong's test
(PRD §6.5).
"""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from paimana.data.generator import generate_synthetic_panel
from paimana.features.build import build_feature_table
from paimana.models.bakeoff import _pr_auc as _PR_AUC  # noqa: N811 - reuse the fixed, fast metric fn
from paimana.models.bakeoff import delong_test, paired_bootstrap_ci, run_bakeoff
from paimana.models.evaluate import completed_labelled_rows
from paimana.models.ml import CLASSIFICATION_TARGETS, REGRESSION_TARGETS, run_all_ml_models


# --------------------------------------------------------------------------
# DeLong's test
# --------------------------------------------------------------------------
def test_delong_auc_matches_sklearn():
    rng = np.random.default_rng(0)
    n = 1000
    y = rng.integers(0, 2, n)
    prob_a = np.clip(y * 0.6 + rng.normal(0, 0.3, n), 0, 1)
    prob_b = np.clip(y * 0.2 + rng.normal(0, 0.3, n), 0, 1)

    result = delong_test(y, prob_a, prob_b)
    assert result["auc_a"] == pytest.approx(roc_auc_score(y, prob_a), abs=1e-9)
    assert result["auc_b"] == pytest.approx(roc_auc_score(y, prob_b), abs=1e-9)


def test_delong_identical_predictions_give_zero_diff_and_pvalue_one():
    rng = np.random.default_rng(1)
    n = 500
    y = rng.integers(0, 2, n)
    prob = np.clip(y * 0.5 + rng.normal(0, 0.3, n), 0, 1)
    result = delong_test(y, prob, prob)
    assert result["auc_diff"] == pytest.approx(0.0, abs=1e-9)
    assert result["p_value"] == pytest.approx(1.0, abs=1e-9)


def test_delong_detects_a_clear_difference_with_low_pvalue():
    rng = np.random.default_rng(2)
    n = 2000
    y = rng.integers(0, 2, n)
    strong = np.clip(y * 0.7 + rng.normal(0, 0.2, n), 0, 1)
    weak = rng.uniform(0, 1, n)  # pure noise, no signal
    result = delong_test(y, strong, weak)
    assert result["auc_diff"] > 0.1
    assert result["p_value"] < 0.01


def test_delong_handles_single_class_gracefully():
    y = np.ones(20, dtype=int)
    prob_a = np.random.default_rng(0).uniform(0, 1, 20)
    result = delong_test(y, prob_a, prob_a)
    assert np.isnan(result["p_value"])  # undefined, must not raise


# --------------------------------------------------------------------------
# Paired, project-level bootstrap
# --------------------------------------------------------------------------
def test_paired_bootstrap_identical_predictions_give_zero_width_ci():
    rng = np.random.default_rng(0)
    n = 400
    y = rng.integers(0, 2, n)
    prob = rng.uniform(0, 1, n)
    groups = np.repeat(np.arange(n // 4), 4)

    result = paired_bootstrap_ci(y, prob, prob, groups, _PR_AUC, n_boot=100)
    assert result["mean_diff"] == pytest.approx(0.0, abs=1e-9)
    assert result["ci_lower"] == pytest.approx(0.0, abs=1e-9)
    assert result["ci_upper"] == pytest.approx(0.0, abs=1e-9)
    assert result["ci_excludes_zero"] is False


def test_paired_bootstrap_detects_a_clear_winner():
    rng = np.random.default_rng(3)
    n = 800
    y = rng.integers(0, 2, n)
    better = np.clip(y * 0.7 + rng.normal(0, 0.15, n), 0, 1)
    worse = rng.uniform(0, 1, n)
    groups = np.repeat(np.arange(n // 4), 4)

    result = paired_bootstrap_ci(y, better, worse, groups, _PR_AUC, n_boot=200)
    assert result["mean_diff"] > 0
    assert result["ci_excludes_zero"] is True
    assert result["ci_lower"] > 0  # the whole interval should favour "better"


def test_paired_bootstrap_completes_quickly_at_realistic_scale():
    """Regression guard for a real Phase 4 performance bug: using the full
    `evaluate.classification_metrics` (which scans ~200 F1 thresholds) as
    the bootstrap's per-iteration metric function made the production
    bake-off (n_boot=1000, ~34k rows, 3 classification targets) take
    multiple HOURS instead of seconds — found by watching the run stall,
    not by benchmarking ahead of time. `_pr_auc` must stay a lightweight,
    single-sklearn-call metric; this test fails fast (loose bound, 10s) if
    that regresses rather than silently costing hours again.
    """
    import time

    rng = np.random.default_rng(5)
    n_groups = 1500
    rows_per_group = 20
    groups = np.repeat(np.arange(n_groups), rows_per_group)
    n = len(groups)
    y = rng.integers(0, 2, n)
    prob_a = np.clip(y * 0.5 + rng.normal(0, 0.3, n), 0, 1)
    prob_b = np.clip(y * 0.3 + rng.normal(0, 0.3, n), 0, 1)

    start = time.monotonic()
    paired_bootstrap_ci(y, prob_a, prob_b, groups, _PR_AUC, n_boot=1000)
    elapsed = time.monotonic() - start

    assert elapsed < 30.0, (
        f"paired_bootstrap_ci took {elapsed:.1f}s at realistic scale — "
        "check that the metric_fn passed in is lightweight, not the full "
        "classification_metrics()/regression_metrics()."
    )


def test_paired_bootstrap_respects_group_structure():
    """A project's rows must always move together in a resample — verified
    indirectly: n_groups reported must match the true number of unique
    groups, not the row count."""
    rng = np.random.default_rng(4)
    n_groups_true = 50
    groups = np.repeat(np.arange(n_groups_true), 6)
    n = len(groups)
    y = rng.integers(0, 2, n)
    prob = rng.uniform(0, 1, n)

    result = paired_bootstrap_ci(y, prob, prob, groups, _PR_AUC, n_boot=50)
    assert result["n_groups"] == n_groups_true


# --------------------------------------------------------------------------
# Full orchestration
# --------------------------------------------------------------------------
def test_run_bakeoff_covers_every_target_with_valid_structure():
    generated = generate_synthetic_panel(n_projects=250, seed=42)
    features_df = build_feature_table(generated.panel, generated.projects)
    completed = completed_labelled_rows(features_df)

    ml_results = run_all_ml_models(completed)
    comparison = run_bakeoff(completed, ml_results, n_boot=100)

    expected_targets = set(REGRESSION_TARGETS) | set(CLASSIFICATION_TARGETS)
    assert set(comparison) == expected_targets

    for target in REGRESSION_TARGETS:
        entry = comparison[target]
        assert entry["task"] == "regression"
        assert "bootstrap" in entry
        assert {"mean_diff", "ci_lower", "ci_upper", "ci_excludes_zero"} <= set(entry["bootstrap"])

    for target in CLASSIFICATION_TARGETS:
        entry = comparison[target]
        assert entry["task"] == "classification"
        assert "bootstrap" in entry
        assert "delong" in entry
        assert 0.0 <= entry["delong"]["auc_a"] <= 1.0 or np.isnan(entry["delong"]["auc_a"])
