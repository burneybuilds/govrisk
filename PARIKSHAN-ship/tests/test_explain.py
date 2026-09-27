"""Tests for SHAP explainability (PRD §6.6, §7/Phase 4 task 3)."""

from __future__ import annotations

import numpy as np
import pytest

from paimana.data.generator import generate_synthetic_panel
from paimana.features.build import build_feature_table
from paimana.models.evaluate import completed_labelled_rows
from paimana.models.explain import build_shap_artifacts, latest_snapshot_per_project, top_reason_codes

SMALL_PARAMS = {"n_estimators": 60, "max_depth": 5, "min_samples_leaf": 5}


@pytest.fixture(scope="module")
def small_panel_and_completed():
    generated = generate_synthetic_panel(n_projects=200, seed=42)
    features_df = build_feature_table(generated.panel, generated.projects)
    completed = completed_labelled_rows(features_df)
    return features_df, completed


def test_latest_snapshot_has_exactly_one_row_per_project(small_panel_and_completed):
    panel_df, _ = small_panel_and_completed
    latest = latest_snapshot_per_project(panel_df)
    assert latest["project_id"].nunique() == len(latest)
    assert set(latest["project_id"]) == set(panel_df["project_id"])


def test_latest_snapshot_picks_the_max_as_of_date(small_panel_and_completed):
    panel_df, _ = small_panel_and_completed
    latest = latest_snapshot_per_project(panel_df)
    true_max = panel_df.groupby("project_id")["as_of_date"].max()
    picked = latest.set_index("project_id")["as_of_date"]
    assert (picked.sort_index() == true_max.sort_index()).all()


def test_latest_snapshot_is_dramatically_smaller_than_full_panel(small_panel_and_completed):
    """The whole point of the scope correction: ~1 row/project, not the
    full quarterly history (found necessary during Phase 4 — see
    HANDOFF.md — after SHAP over the full panel proved intractably slow)."""
    panel_df, _ = small_panel_and_completed
    latest = latest_snapshot_per_project(panel_df)
    assert len(latest) < len(panel_df) / 5  # at least 5x smaller at this small scale


def test_build_shap_artifacts_returns_expected_shapes(small_panel_and_completed):
    panel_df, completed = small_panel_and_completed
    latest = latest_snapshot_per_project(panel_df)
    artifacts, pipeline = build_shap_artifacts(latest, completed, "random_forest", SMALL_PARAMS)

    assert set(artifacts) == {"global", "per_row"}
    assert "feature" in artifacts["global"].columns
    assert "mean_abs_shap" in artifacts["global"].columns
    assert len(artifacts["per_row"]) == len(latest)
    assert "project_id" in artifacts["per_row"].columns
    assert "as_of_date" in artifacts["per_row"].columns
    assert pipeline is not None


def test_global_importance_is_sorted_descending(small_panel_and_completed):
    panel_df, completed = small_panel_and_completed
    latest = latest_snapshot_per_project(panel_df)
    artifacts, _pipeline = build_shap_artifacts(latest, completed, "random_forest", SMALL_PARAMS)
    values = artifacts["global"]["mean_abs_shap"].to_numpy()
    assert np.all(values[:-1] >= values[1:])


def test_top_reason_codes_returns_k_signed_features(small_panel_and_completed):
    panel_df, completed = small_panel_and_completed
    latest = latest_snapshot_per_project(panel_df)
    artifacts, _pipeline = build_shap_artifacts(latest, completed, "random_forest", SMALL_PARAMS)
    feature_cols = [c for c in artifacts["per_row"].columns if c not in ("project_id", "as_of_date")]
    row = artifacts["per_row"].iloc[0]

    codes = top_reason_codes(row, feature_cols, k=3)
    assert len(codes) == 3
    for code in codes:
        assert {"feature", "shap_value"} == set(code)
        assert isinstance(code["shap_value"], float)

    # Sorted by |shap_value| descending.
    magnitudes = [abs(c["shap_value"]) for c in codes]
    assert magnitudes == sorted(magnitudes, reverse=True)
