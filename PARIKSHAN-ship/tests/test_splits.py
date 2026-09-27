"""Tests for leakage-safe splitting (PRD §6.2)."""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from paimana.features.splits import (
    assert_no_group_overlap,
    grouped_cv,
    horizon_bucket,
    temporal_split,
)


def _synthetic_panel(n_projects: int = 20, rows_per_project: int = 5) -> pd.DataFrame:
    rows = []
    for p in range(n_projects):
        for _q in range(rows_per_project):
            rows.append({"project_id": f"P{p:03d}", "value": np.random.rand()})
    return pd.DataFrame(rows)


def test_grouped_cv_never_splits_a_project_across_train_and_test():
    df = _synthetic_panel(n_projects=30, rows_per_project=6)
    X = df[["value"]]
    y = np.random.randint(0, 2, size=len(df))
    groups = df["project_id"]

    for train_idx, test_idx in grouped_cv(X, y, groups, n_splits=5):
        assert assert_no_group_overlap(groups.to_numpy(), train_idx, test_idx)
        assert set(train_idx) | set(test_idx) == set(range(len(df)))
        assert set(train_idx) & set(test_idx) == set()


def test_grouped_cv_produces_requested_number_of_folds():
    df = _synthetic_panel(n_projects=25, rows_per_project=4)
    X = df[["value"]]
    y = np.zeros(len(df))
    folds = list(grouped_cv(X, y, df["project_id"], n_splits=5))
    assert len(folds) == 5


def test_assert_no_group_overlap_detects_a_real_overlap():
    groups = np.array(["A", "A", "B", "B", "C"])
    train_idx = np.array([0, 1, 2])
    test_idx = np.array([2, 3, 4])  # index 2 (group "B") appears in both
    assert not assert_no_group_overlap(groups, train_idx, test_idx)


def test_assert_no_group_overlap_passes_clean_split():
    groups = np.array(["A", "A", "B", "B", "C"])
    train_idx = np.array([0, 1])
    test_idx = np.array([2, 3, 4])
    assert assert_no_group_overlap(groups, train_idx, test_idx)


def test_temporal_split_separates_by_sanction_year():
    df = pd.DataFrame(
        {
            "sanction_date": [
                date(2015, 6, 1),
                date(2017, 12, 31),
                date(2018, 1, 1),
                date(2020, 3, 15),
            ]
        }
    )
    train_idx, test_idx = temporal_split(df, cut_year=2018)
    assert set(train_idx) == {0, 1}
    assert set(test_idx) == {2, 3}


def test_temporal_split_covers_every_row_exactly_once():
    df = pd.DataFrame({"sanction_date": [date(2010 + i, 1, 1) for i in range(15)]})
    train_idx, test_idx = temporal_split(df, cut_year=2018)
    assert len(train_idx) + len(test_idx) == len(df)
    assert set(train_idx) & set(test_idx) == set()


def test_horizon_bucket_assigns_expected_labels():
    elapsed_frac = pd.Series([0.1, 0.3, 0.6, 0.9, 1.4])
    buckets = horizon_bucket(elapsed_frac)
    assert list(buckets) == ["0-25%", "25-50%", "50-75%", "75%+", "75%+"]


def test_horizon_bucket_handles_boundary_values():
    elapsed_frac = pd.Series([0.25, 0.5, 0.75])
    buckets = horizon_bucket(elapsed_frac)
    # right=True: boundary values fall into the LOWER bucket (e.g. 0.25 -> "0-25%")
    assert list(buckets) == ["0-25%", "25-50%", "50-75%"]
