"""Tests for as-of-t feature construction (PRD §5.3) and the agency
historical-performance point-in-time correctness guarantee."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from paimana.features.build import (
    ALL_FEATURE_COLUMNS,
    build_feature_table,
    select_features,
)
from paimana.features.leakage import assert_no_leakage


@pytest.fixture
def agency_fixture():
    """Agency AGY-A has two completed projects (P1, P2) and one still-ongoing
    project (P3). P4 and P5 are separate probe projects at AGY-A used to
    query the track record at various as_of_dates. AGY-B has no completions
    at all, to test the "no history" case."""
    projects = pd.DataFrame(
        [
            # project_id, agency_id, is_censored, final_doc, cost_overrun_pct, time_overrun_months, y_severe
            ("P1", "AGY-A", False, date(2010, 1, 1), 10.0, 2.0, False),
            ("P2", "AGY-A", False, date(2012, 1, 1), 30.0, 8.0, True),
            ("P3", "AGY-A", True, pd.NaT, np.nan, np.nan, pd.NA),
            ("P4", "AGY-A", True, pd.NaT, np.nan, np.nan, pd.NA),
            ("P5", "AGY-B", True, pd.NaT, np.nan, np.nan, pd.NA),
        ],
        columns=[
            "project_id",
            "agency_id",
            "is_censored",
            "final_doc",
            "cost_overrun_pct",
            "time_overrun_months",
            "y_severe",
        ],
    )

    panel = pd.DataFrame(
        [
            # Probe project P4 (AGY-A) at three points in time.
            ("P4", "AGY-A", date(2009, 1, 1)),  # before any AGY-A completion
            ("P4", "AGY-A", date(2011, 1, 1)),  # after P1, before P2
            ("P4", "AGY-A", date(2013, 1, 1)),  # after both P1 and P2
            # P1's own rows: an earlier quarter, and its own completion date.
            ("P1", "AGY-A", date(2008, 1, 1)),
            ("P1", "AGY-A", date(2010, 1, 1)),  # == P1's own final_doc: must NOT count itself
            # P2's own row before its completion: should see P1 only, not itself.
            ("P2", "AGY-A", date(2011, 6, 1)),
            # Probe project P5 at an agency with zero completions ever.
            ("P5", "AGY-B", date(2015, 1, 1)),
        ],
        columns=["project_id", "agency_id", "as_of_date"],
    )
    return panel, projects


def test_no_prior_history_before_any_completion(agency_fixture):
    panel, projects = agency_fixture
    out = build_feature_table(panel, projects)
    row = out[(out["project_id"] == "P4") & (out["as_of_date"] == date(2009, 1, 1))].iloc[0]
    assert row["agency_prior_completed_count"] == 0
    assert np.isnan(row["agency_prior_avg_cost_overrun_pct"])


def test_one_prior_completion_counted_correctly(agency_fixture):
    panel, projects = agency_fixture
    out = build_feature_table(panel, projects)
    row = out[(out["project_id"] == "P4") & (out["as_of_date"] == date(2011, 1, 1))].iloc[0]
    assert row["agency_prior_completed_count"] == 1
    assert row["agency_prior_avg_cost_overrun_pct"] == pytest.approx(10.0)
    assert row["agency_prior_avg_time_overrun_months"] == pytest.approx(2.0)
    assert row["agency_prior_severe_rate"] == pytest.approx(0.0)


def test_two_prior_completions_averaged_correctly(agency_fixture):
    panel, projects = agency_fixture
    out = build_feature_table(panel, projects)
    row = out[(out["project_id"] == "P4") & (out["as_of_date"] == date(2013, 1, 1))].iloc[0]
    assert row["agency_prior_completed_count"] == 2
    assert row["agency_prior_avg_cost_overrun_pct"] == pytest.approx((10.0 + 30.0) / 2)
    assert row["agency_prior_avg_time_overrun_months"] == pytest.approx((2.0 + 8.0) / 2)
    assert row["agency_prior_severe_rate"] == pytest.approx(0.5)


def test_project_never_counts_its_own_completion_as_prior(agency_fixture):
    """The critical self-leakage check: P1's row AT its own final_doc must
    show zero prior completions, not one (itself)."""
    panel, projects = agency_fixture
    out = build_feature_table(panel, projects)

    row_before = out[(out["project_id"] == "P1") & (out["as_of_date"] == date(2008, 1, 1))].iloc[0]
    assert row_before["agency_prior_completed_count"] == 0

    row_at_completion = out[(out["project_id"] == "P1") & (out["as_of_date"] == date(2010, 1, 1))].iloc[0]
    assert row_at_completion["agency_prior_completed_count"] == 0, (
        "A project's own completion must never be counted as its own prior track record"
    )


def test_project_does_not_see_its_own_future_completion(agency_fixture):
    """P2's pre-completion row must see P1 (completed earlier) but not itself."""
    panel, projects = agency_fixture
    out = build_feature_table(panel, projects)
    row = out[(out["project_id"] == "P2") & (out["as_of_date"] == date(2011, 6, 1))].iloc[0]
    assert row["agency_prior_completed_count"] == 1
    assert row["agency_prior_avg_cost_overrun_pct"] == pytest.approx(10.0)


def test_agency_with_zero_completions_gets_nan_not_error(agency_fixture):
    panel, projects = agency_fixture
    out = build_feature_table(panel, projects)
    row = out[out["project_id"] == "P5"].iloc[0]
    assert row["agency_prior_completed_count"] == 0
    assert np.isnan(row["agency_prior_avg_cost_overrun_pct"])
    assert np.isnan(row["agency_prior_severe_rate"])


def test_select_features_returns_only_approved_columns_and_passes_leakage_check(agency_fixture):
    panel, projects = agency_fixture
    augmented = build_feature_table(panel, projects)
    X = select_features(augmented)
    assert set(X.columns) <= set(ALL_FEATURE_COLUMNS)
    assert_no_leakage(X)  # must not raise


def test_select_features_excludes_target_columns(agency_fixture):
    panel, projects = agency_fixture
    augmented = build_feature_table(panel, projects).merge(projects, on=["project_id", "agency_id"])
    X = select_features(augmented)
    assert "cost_overrun_pct" not in X.columns
    assert "y_severe" not in X.columns
    assert "final_doc" not in X.columns
