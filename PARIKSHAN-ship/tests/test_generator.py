"""Tests for the synthetic panel generator (PRD §4, §5, Phase 1)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from paimana import config
from paimana.data import schema
from paimana.data.generator import generate_synthetic_panel

# Small n for fast unit tests; full-scale generation is exercised by
# scripts/run_generate.py as part of the Phase 1 DoD.
SMALL_N = 150


@pytest.fixture(scope="module")
def small_generated():
    return generate_synthetic_panel(n_projects=SMALL_N, seed=config.RANDOM_SEED)


def test_reproducibility_same_seed_gives_identical_output():
    a = generate_synthetic_panel(n_projects=50, seed=123)
    b = generate_synthetic_panel(n_projects=50, seed=123)
    pd.testing.assert_frame_equal(a.projects, b.projects)
    pd.testing.assert_frame_equal(a.panel, b.panel)


def test_different_seeds_give_different_output():
    a = generate_synthetic_panel(n_projects=50, seed=1)
    b = generate_synthetic_panel(n_projects=50, seed=2)
    assert not a.projects["original_cost_cr"].equals(b.projects["original_cost_cr"])


def test_projects_grain_and_columns(small_generated):
    projects = small_generated.projects
    assert len(projects) == SMALL_N
    assert projects["project_id"].nunique() == SMALL_N
    expected_cols = set(schema.STATIC_COLUMNS) | set(schema.TARGET_COLUMNS)
    assert expected_cols <= set(projects.columns)


def test_panel_grain_matches_projects(small_generated):
    panel = small_generated.panel
    projects = small_generated.projects
    assert set(panel["project_id"].unique()) == set(projects["project_id"].unique())
    # Every project contributes at least one snapshot row.
    assert panel.groupby("project_id").size().min() >= 1


def test_panel_columns_match_contract(small_generated):
    panel = small_generated.panel
    assert set(schema.ALL_PANEL_COLUMNS) <= set(panel.columns)


def test_sector_and_state_values_are_valid(small_generated):
    projects = small_generated.projects
    assert set(projects["sector"].unique()) <= set(config.SECTORS)
    assert set(projects["state"].unique()) <= set(config.STATES)
    assert set(projects["funding_mode"].unique()) <= set(config.FUNDING_MODES)
    assert set(projects["implementing_agency_type"].unique()) <= set(config.AGENCY_TYPES)


def test_original_cost_respects_threshold(small_generated):
    assert (small_generated.projects["original_cost_cr"] >= config.COST_THRESHOLD_CR).all()


def test_censoring_is_consistent_with_target_nulling(small_generated):
    projects = small_generated.projects
    censored = projects[projects["is_censored"] == True]  # noqa: E712
    completed = projects[projects["is_censored"] == False]  # noqa: E712

    assert censored["final_cost_cr"].isna().all()
    assert censored["cost_overrun_pct"].isna().all()
    assert censored["project_status"].eq("Ongoing").all()

    assert completed["final_cost_cr"].notna().all()
    assert completed["cost_overrun_pct"].notna().all()
    assert completed["project_status"].eq("Completed").all()


def test_censored_projects_have_no_snapshots_after_today(small_generated):
    panel = small_generated.panel
    censored_panel = panel[panel["is_censored"] == True]  # noqa: E712
    assert (pd.to_datetime(censored_panel["as_of_date"]) <= pd.Timestamp(config.SIMULATION_TODAY)).all()


def test_physical_progress_is_non_decreasing_within_project():
    # Use a fresh, small, seed-fixed generation with missingness disabled
    # in spirit by checking only non-null consecutive pairs.
    generated = generate_synthetic_panel(n_projects=80, seed=7)
    panel = generated.panel.sort_values(["project_id", "as_of_date"])
    for _, group in panel.groupby("project_id"):
        series = group["physical_progress_pct"].dropna().to_numpy()
        if len(series) > 1:
            assert (np.diff(series) >= -1e-6).all(), "physical_progress_pct must be non-decreasing"


def test_missingness_rate_within_documented_band(small_generated):
    panel = small_generated.panel
    for field in ["physical_progress_pct", "expenditure_to_date_cr", "financial_progress_pct"]:
        rate = panel[field].isna().mean()
        assert 0.0 <= rate <= 0.20, f"{field} missingness {rate:.2%} outside plausible band"


def test_y_severe_implies_at_least_one_threshold_breach(small_generated):
    completed = small_generated.projects[small_generated.projects["is_censored"] == False]  # noqa: E712
    severe = completed[completed["y_severe"] == True]  # noqa: E712
    if len(severe):
        breach = (severe["cost_overrun_pct"] > config.SEVERE_COST_OVERRUN_THRESHOLD_PCT) | (
            severe["time_overrun_months"] > config.SEVERE_TIME_OVERRUN_THRESHOLD_MONTHS
        )
        assert breach.all()
