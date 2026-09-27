"""Tests for the shared metric suite (PRD §6.4)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from paimana.models.evaluate import (
    classification_metrics,
    horizon_stratified_metrics,
    lift_at_k,
    precision_at_k,
    regression_metrics,
    reliability_curve,
)


def test_regression_metrics_perfect_prediction():
    y = np.array([10.0, 20.0, 30.0, 40.0])
    m = regression_metrics(y, y.copy())
    assert m["mae"] == pytest.approx(0.0)
    assert m["rmse"] == pytest.approx(0.0)
    assert m["r2"] == pytest.approx(1.0)
    assert m["n"] == 4


def test_regression_metrics_constant_prediction_at_mean_gives_zero_r2():
    y = np.array([10.0, 20.0, 30.0, 40.0])
    pred = np.full_like(y, y.mean())
    m = regression_metrics(y, pred)
    assert m["r2"] == pytest.approx(0.0, abs=1e-9)


def test_regression_metrics_mape_guards_near_zero_denominator():
    y = np.array([0.1, -0.1, 50.0])
    pred = np.array([5.0, 5.0, 55.0])
    m = regression_metrics(y, pred)
    assert np.isfinite(m["mape_pct"])  # must not be inf/nan from the near-zero entries


def test_classification_metrics_perfect_separation():
    y = np.array([0, 0, 1, 1])
    prob = np.array([0.01, 0.02, 0.98, 0.99])
    m = classification_metrics(y, prob)
    assert m["pr_auc"] == pytest.approx(1.0)
    assert m["roc_auc"] == pytest.approx(1.0)
    assert m["brier"] < 0.01


def test_classification_metrics_handles_single_class_gracefully():
    y = np.array([1, 1, 1, 1])
    prob = np.array([0.5, 0.6, 0.7, 0.8])
    m = classification_metrics(y, prob)
    assert np.isnan(m["pr_auc"])  # undefined with no negative class; must not raise
    assert np.isnan(m["roc_auc"])


def test_precision_at_k_basic():
    y = np.array([0, 0, 1, 1, 0])
    score = np.array([0.1, 0.2, 0.9, 0.8, 0.3])
    # top 2 by score: indices 2 (0.9, y=1) and 3 (0.8, y=1) -> precision@2 = 1.0
    assert precision_at_k(y, score, k=2) == pytest.approx(1.0)


def test_precision_at_k_with_noise_in_ranking():
    y = np.array([1, 0, 0, 0, 0])
    score = np.array([0.1, 0.9, 0.8, 0.7, 0.6])
    # top 1 by score is index 1 (y=0) -> precision@1 = 0.0
    assert precision_at_k(y, score, k=1) == pytest.approx(0.0)


def test_precision_at_k_clips_k_to_available_rows():
    y = np.array([1, 0])
    score = np.array([0.9, 0.1])
    assert precision_at_k(y, score, k=100) == pytest.approx(0.5)  # k clipped to n=2


def test_lift_at_k_is_precision_over_base_rate():
    y = np.array([1, 1, 0, 0])  # base rate 0.5
    score = np.array([0.9, 0.8, 0.2, 0.1])
    # top 2: both positive -> precision@2 = 1.0 -> lift = 1.0 / 0.5 = 2.0
    assert lift_at_k(y, score, k=2) == pytest.approx(2.0)


def test_reliability_curve_perfectly_calibrated():
    rng = np.random.default_rng(0)
    prob = rng.uniform(0, 1, 2000)
    y = (rng.uniform(0, 1, 2000) < prob).astype(int)  # y ~ Bernoulli(prob): well-calibrated by construction
    curve = reliability_curve(y, prob, n_bins=10)
    for pred, obs in zip(curve["predicted"], curve["observed"], strict=True):
        assert abs(pred - obs) < 0.15  # loose bound; stochastic data


def test_horizon_stratified_metrics_splits_by_bucket():
    df = pd.DataFrame(
        {
            "elapsed_frac": [0.1, 0.1, 0.6, 0.6, 0.9, 0.9],
            "y_true": [10.0, 12.0, 20.0, 22.0, 30.0, 28.0],
            "y_pred": [10.0, 12.0, 25.0, 27.0, 30.0, 28.0],
        }
    )
    out = horizon_stratified_metrics(df, "y_true", "y_pred", task="regression")
    assert "0-25%" in out
    assert "50-75%" in out
    assert out["0-25%"]["r2"] == pytest.approx(1.0)  # perfect predictions in that bucket
    assert out["0-25%"]["n"] == 2
