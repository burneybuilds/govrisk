"""Leakage-safe cross-validation and temporal splitting — PRD §6.2.

Three mechanisms, each guarding against a different way a naive split would
inflate every downstream metric:

1. `grouped_cv` — GroupKFold by `project_id`. A random row-level split would
   let the same project's snapshots straddle train and test, letting a
   model "cheat" by memorising a project it has partially seen.
2. `temporal_split` — train on projects sanctioned before a cut year, test
   on those sanctioned on/after. The honest simulation of deployment: a
   real system only ever has the past to learn from.
3. `horizon_bucket` — buckets rows by how far through their planned
   duration they are. Predicting a severe overrun at 10% elapsed is a
   genuinely hard, valuable problem; predicting it at 95% elapsed is nearly
   free. Reporting one blended metric across both hides this entirely.
"""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

HORIZON_BINS: tuple[float, ...] = (-np.inf, 0.25, 0.5, 0.75, np.inf)
HORIZON_LABELS: tuple[str, ...] = ("0-25%", "25-50%", "50-75%", "75%+")


def grouped_cv(
    X: pd.DataFrame, y: pd.Series, groups: pd.Series, n_splits: int = 5
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Yield (train_idx, test_idx) index arrays, grouped by `groups` (PRD §6.2.1).

    No value in `groups` (i.e. no project_id) can appear in both the train
    and test index arrays of any single fold.
    """
    gkf = GroupKFold(n_splits=n_splits)
    yield from gkf.split(X, y, groups=groups)


def temporal_split(
    df: pd.DataFrame, cut_year: int, date_column: str = "sanction_date"
) -> tuple[np.ndarray, np.ndarray]:
    """Return (train_idx, test_idx): sanctioned-before-cut_year vs. on/after (PRD §6.2.2)."""
    dates = pd.to_datetime(df[date_column])
    train_mask = (dates.dt.year < cut_year).to_numpy()
    train_idx = np.nonzero(train_mask)[0]
    test_idx = np.nonzero(~train_mask)[0]
    return train_idx, test_idx


def horizon_bucket(elapsed_frac: pd.Series) -> pd.Series:
    """Bucket `elapsed_frac` into planned-duration-progress quartiles (PRD §6.2.3).

    Values above 1.0 (a project already past its original planned duration)
    fall into the open-ended "75%+" bucket along with the 75-100% band —
    both represent "late in or past the plan" for stratified reporting.
    """
    return pd.cut(elapsed_frac, bins=list(HORIZON_BINS), labels=list(HORIZON_LABELS), right=True)


def assert_no_group_overlap(groups: np.ndarray, train_idx: np.ndarray, test_idx: np.ndarray) -> bool:
    """True iff no group value appears in both `train_idx` and `test_idx` rows."""
    groups = np.asarray(groups)
    return len(set(groups[train_idx]) & set(groups[test_idx])) == 0
