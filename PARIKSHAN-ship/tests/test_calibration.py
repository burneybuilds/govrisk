"""Tests for isotonic calibration and its group-safety guarantee
(PRD §7/Phase 4 task 2).

The critical property under test: calibration must be fit on a portion of
the training fold held out via a GROUP-AWARE split (by project_id), not
sklearn's default plain KFold — otherwise a project's own quarters could
appear on both sides of the fit/calibrate boundary, silently overfitting
the calibration curve.
"""

from __future__ import annotations

import numpy as np
import pytest

from paimana.data.generator import generate_synthetic_panel
from paimana.features.build import build_feature_table, select_features
from paimana.features.splits import assert_no_group_overlap
from paimana.models.evaluate import completed_labelled_rows
from paimana.models.ml import MODEL_FAMILIES, make_classifier, make_group_aware_calibrated_classifier

SMALL_PARAMS = {"n_estimators": 50, "max_depth": 4}


@pytest.fixture(scope="module")
def small_completed_df():
    generated = generate_synthetic_panel(n_projects=250, seed=42)
    features_df = build_feature_table(generated.panel, generated.projects)
    return completed_labelled_rows(features_df)


@pytest.fixture(scope="module")
def train_split(small_completed_df):
    """A single training-fold-sized slice to calibrate on, mirroring what
    `classifier_oof_calibrated` actually passes in."""
    df = small_completed_df.iloc[: int(len(small_completed_df) * 0.8)]
    X = select_features(df)
    y = df["y_severe"].astype(int)
    groups = df["project_id"].to_numpy()
    return X, y, groups


@pytest.mark.parametrize("family", MODEL_FAMILIES)
def test_inner_cv_splits_have_zero_project_overlap(train_split, family):
    """The core correctness property: whatever the inner split is, no
    project_id may appear in both its fit and calibrate portions."""
    X, y, groups = train_split
    base = make_classifier(family, SMALL_PARAMS)
    _calibrated, inner_cv = make_group_aware_calibrated_classifier(base, X, y, groups, inner_splits=3)

    assert len(inner_cv) == 3
    for fit_idx, calib_idx in inner_cv:
        assert assert_no_group_overlap(groups, fit_idx, calib_idx)
        assert set(fit_idx) & set(calib_idx) == set()


@pytest.mark.parametrize("family", MODEL_FAMILIES)
def test_calibrated_probabilities_are_valid(train_split, family):
    X, y, groups = train_split
    base = make_classifier(family, SMALL_PARAMS)
    calibrated, _ = make_group_aware_calibrated_classifier(base, X, y, groups)
    prob = calibrated.predict_proba(X)[:, 1]
    assert np.all(np.isfinite(prob))
    assert np.all((prob >= 0) & (prob <= 1))


def test_calibration_uses_isotonic_method(train_split):
    X, y, groups = train_split
    base = make_classifier("random_forest", SMALL_PARAMS)
    calibrated, _ = make_group_aware_calibrated_classifier(base, X, y, groups)
    assert calibrated.method == "isotonic"


def test_inner_splits_count_matches_requested(train_split):
    X, y, groups = train_split
    base = make_classifier("random_forest", SMALL_PARAMS)
    _calibrated, inner_cv = make_group_aware_calibrated_classifier(base, X, y, groups, inner_splits=4)
    assert len(inner_cv) == 4


def test_calibration_improves_or_maintains_brier_score_vs_uncalibrated(small_completed_df):
    """Isotonic calibration should not make probability quality WORSE on
    held-out data — a basic sanity check that calibration is doing
    something sensible, not corrupting the model."""
    from sklearn.metrics import brier_score_loss

    from paimana.features.splits import grouped_cv

    df = small_completed_df
    X = select_features(df)
    y = df["y_severe"].astype(int)
    groups = df["project_id"]

    train_idx, test_idx = next(grouped_cv(X, y, groups, n_splits=5))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    groups_train = groups.iloc[train_idx].to_numpy()

    uncalibrated = make_classifier("random_forest", SMALL_PARAMS)
    uncalibrated.fit(X_train, y_train)
    uncalibrated_prob = uncalibrated.predict_proba(X_test)[:, 1]

    base = make_classifier("random_forest", SMALL_PARAMS)
    calibrated, _ = make_group_aware_calibrated_classifier(base, X_train, y_train, groups_train)
    calibrated_prob = calibrated.predict_proba(X_test)[:, 1]

    uncalibrated_brier = brier_score_loss(y_test, uncalibrated_prob)
    calibrated_brier = brier_score_loss(y_test, calibrated_prob)
    # Allow a small tolerance — calibration trades a little variance for
    # bias correction and can occasionally be marginally worse on one fold.
    assert calibrated_brier <= uncalibrated_brier + 0.05
