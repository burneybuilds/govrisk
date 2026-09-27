"""The leakage build gate — PRD §5.5. Must be 100% green from Phase 2 onward.

If anything in this file fails, every downstream model result is suspect.
"""

from __future__ import annotations

import pandas as pd
import pytest

from paimana.data import schema
from paimana.features.leakage import (
    FORBIDDEN_COLUMNS,
    assert_no_leakage,
    find_leaking_columns,
    is_forbidden,
)


def test_forbidden_columns_matches_schema_target_columns():
    assert FORBIDDEN_COLUMNS == frozenset(schema.TARGET_COLUMNS)


@pytest.mark.parametrize("column", list(schema.TARGET_COLUMNS))
def test_every_target_column_is_forbidden(column):
    assert is_forbidden(column)


@pytest.mark.parametrize(
    "column",
    [
        "revised_cost_cr",  # not in this generator's schema, but PRD §5.5 forbids it
        "anticipated_doc",
        "final_anything",
        "y_made_up_target",
        "target_something",
    ],
)
def test_regex_catches_forward_compatible_forbidden_names(column):
    assert is_forbidden(column)


@pytest.mark.parametrize(
    "column",
    [
        "physical_progress_pct",
        "expenditure_to_date_cr",
        "financial_progress_pct",
        "progress_gap_pp",
        "velocity_ratio",
        "sector",
        "original_cost_cr",
        "agency_prior_completed_count",
        "agency_prior_avg_cost_overrun_pct",
        "revisions_to_date",  # must NOT be caught by the "revised_" pattern
        "months_since_last_revision",
    ],
)
def test_legitimate_feature_columns_are_not_forbidden(column):
    assert not is_forbidden(column)


def test_find_leaking_columns_on_clean_dataframe():
    df = pd.DataFrame({"sector": ["Railways"], "original_cost_cr": [500.0]})
    assert find_leaking_columns(df) == []


def test_find_leaking_columns_on_dirty_dataframe():
    df = pd.DataFrame(
        {
            "sector": ["Railways"],
            "cost_overrun_pct": [12.5],
            "y_severe": [True],
        }
    )
    leaking = find_leaking_columns(df)
    assert set(leaking) == {"cost_overrun_pct", "y_severe"}


def test_assert_no_leakage_raises_on_dirty_dataframe():
    df = pd.DataFrame({"sector": ["Railways"], "final_cost_cr": [600.0]})
    with pytest.raises(AssertionError, match="LEAKAGE DETECTED"):
        assert_no_leakage(df)


def test_assert_no_leakage_passes_on_clean_dataframe():
    df = pd.DataFrame({"sector": ["Railways"], "original_cost_cr": [500.0]})
    assert_no_leakage(df)  # must not raise
