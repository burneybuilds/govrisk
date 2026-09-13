"""Tests for the composite risk score (PRD §6.7) — hand-built fixtures,
known inputs to known outputs, not a real trained model."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from paimana import config
from paimana.risk.score import momentum_penalty, normalized_magnitude, risk_band_for_score


# --------------------------------------------------------------------------
# normalized_magnitude
# --------------------------------------------------------------------------
def test_normalized_magnitude_zero_is_zero():
    result = normalized_magnitude(np.array([0.0]), np.array([0.0]))
    assert result[0] == pytest.approx(0.0)


def test_normalized_magnitude_at_caps_is_one():
    result = normalized_magnitude(
        np.array([config.RISK_MAGNITUDE_COST_CAP_PCT]),
        np.array([config.RISK_MAGNITUDE_TIME_CAP_MONTHS]),
    )
    assert result[0] == pytest.approx(1.0)


def test_normalized_magnitude_beyond_cap_is_clipped_to_one():
    result = normalized_magnitude(
        np.array([config.RISK_MAGNITUDE_COST_CAP_PCT * 5]),
        np.array([config.RISK_MAGNITUDE_TIME_CAP_MONTHS * 5]),
    )
    assert result[0] == pytest.approx(1.0)


def test_normalized_magnitude_negative_prediction_clipped_to_zero():
    # A model can predict a small negative overrun (e.g. slight underrun);
    # this must not produce a negative risk contribution.
    result = normalized_magnitude(np.array([-10.0]), np.array([-5.0]))
    assert result[0] == pytest.approx(0.0)


def test_normalized_magnitude_is_average_of_the_two_components():
    cost_cap = config.RISK_MAGNITUDE_COST_CAP_PCT
    result = normalized_magnitude(np.array([cost_cap / 2]), np.array([0.0]))
    assert result[0] == pytest.approx(0.25)  # (0.5 + 0.0) / 2


# --------------------------------------------------------------------------
# momentum_penalty
# --------------------------------------------------------------------------
def test_momentum_penalty_no_stall_on_pace_is_zero():
    result = momentum_penalty(pd.Series([0]), pd.Series([1.0]))
    assert result[0] == pytest.approx(0.0)


def test_momentum_penalty_max_stall_and_zero_velocity_is_one():
    result = momentum_penalty(
        pd.Series([config.RISK_MOMENTUM_STALL_CAP_QUARTERS]), pd.Series([0.0])
    )
    assert result[0] == pytest.approx(1.0)


def test_momentum_penalty_ahead_of_pace_contributes_zero_velocity_component():
    # velocity_ratio > 1 (ahead of pace) must not REDUCE the score below the
    # stall component's own contribution — only < 1 penalises.
    behind = momentum_penalty(pd.Series([0]), pd.Series([0.5]))
    ahead = momentum_penalty(pd.Series([0]), pd.Series([2.0]))
    assert behind[0] > ahead[0]
    assert ahead[0] == pytest.approx(0.0)


def test_momentum_penalty_nan_velocity_ratio_treated_as_neutral():
    result = momentum_penalty(pd.Series([0]), pd.Series([np.nan]))
    assert np.isfinite(result[0])
    assert result[0] == pytest.approx(0.0)  # neutral (on-pace) contributes 0


def test_momentum_penalty_inf_velocity_ratio_treated_as_neutral():
    result = momentum_penalty(pd.Series([0]), pd.Series([np.inf]))
    assert np.isfinite(result[0])


# --------------------------------------------------------------------------
# risk_band_for_score
# --------------------------------------------------------------------------
def test_risk_band_boundaries():
    scores = np.array(
        [0, config.RISK_BAND_GREEN_MAX, config.RISK_BAND_GREEN_MAX + 1, config.RISK_BAND_AMBER_MAX,
         config.RISK_BAND_AMBER_MAX + 1, 100]
    )
    bands = risk_band_for_score(scores)
    assert list(bands) == ["Green", "Green", "Amber", "Amber", "Red", "Red"]


# --------------------------------------------------------------------------
# compute_risk_scores — hand-built stub models, exact expected composite
# --------------------------------------------------------------------------
class _StubClassifier:
    """A fake calibrated classifier returning a FIXED probability for every row."""

    def __init__(self, positive_prob: float):
        self.positive_prob = positive_prob

    def predict_proba(self, X):
        n = len(X)
        return np.column_stack([np.full(n, 1 - self.positive_prob), np.full(n, self.positive_prob)])


class _StubRegressor:
    """A fake regressor returning a FIXED prediction for every row."""

    def __init__(self, value: float):
        self.value = value

    def predict(self, X):
        return np.full(len(X), self.value)


@pytest.fixture
def one_row_panel():
    """A single hand-built project-quarter row with every field the risk
    scorer and rule engine touch."""
    return pd.DataFrame(
        [
            {
                "project_id": "PRJ-TEST",
                "project_name": "Test Project",
                "sector": "Railways",
                "state": "Kerala",
                "as_of_date": pd.Timestamp("2020-01-01"),
                "elapsed_frac": 0.5,
                "original_cost_cr": 500.0,
                "original_duration_months": 36,
                "velocity_ratio": 1.0,
                "progress_gap_pp": 5.0,
                "stalled_quarters": 0,
                "physical_progress_pct": 50.0,
                "n_reasons_active": 0,
                "revisions_to_date": 0,
                "sector_dummy_feature": 0,  # placeholder so select_features doesn't choke on missing cols
            }
        ]
    )


def test_compute_risk_scores_matches_manual_formula(one_row_panel, monkeypatch):
    """With every component pinned to a known value, the composite score
    must equal the PRD §6.7 formula computed by hand — not approximately,
    exactly (to floating-point precision)."""
    # Patch select_features to just return the numeric columns this test
    # cares about, since the stub models don't care about real feature
    # columns — only compute_risk_scores' own arithmetic is under test here.
    import paimana.risk.score as score_module

    monkeypatch.setattr(score_module, "select_features", lambda df: df)

    p_cost, p_time = 0.4, 0.6
    pred_cost_pct, pred_time_months = config.RISK_MAGNITUDE_COST_CAP_PCT, 0.0  # magnitude = 0.5
    # stalled_quarters=0, velocity_ratio=1.0 -> momentum = 0.0

    risk_df = score_module.compute_risk_scores(
        one_row_panel,
        _StubClassifier(p_cost),
        _StubClassifier(p_time),
        _StubRegressor(pred_cost_pct),
        _StubRegressor(pred_time_months),
    )

    expected = 100.0 * (
        config.RISK_WEIGHT_P_COST_OVERRUN * p_cost
        + config.RISK_WEIGHT_P_TIME_OVERRUN * p_time
        + config.RISK_WEIGHT_MAGNITUDE * 0.5
        + config.RISK_WEIGHT_MOMENTUM * 0.0
    )
    assert risk_df.loc[0, "risk_score"] == pytest.approx(expected)
    assert risk_df.loc[0, "p_cost_overrun"] == pytest.approx(p_cost)
    assert risk_df.loc[0, "p_time_overrun"] == pytest.approx(p_time)


def test_compute_risk_scores_output_is_clipped_to_0_100(one_row_panel, monkeypatch):
    import paimana.risk.score as score_module

    monkeypatch.setattr(score_module, "select_features", lambda df: df)
    risk_df = score_module.compute_risk_scores(
        one_row_panel,
        _StubClassifier(1.0),
        _StubClassifier(1.0),
        _StubRegressor(config.RISK_MAGNITUDE_COST_CAP_PCT * 10),
        _StubRegressor(config.RISK_MAGNITUDE_TIME_CAP_MONTHS * 10),
    )
    assert 0.0 <= risk_df.loc[0, "risk_score"] <= 100.0
