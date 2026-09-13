"""As-of-t feature construction — PRD §5.3, Phase 2 task 2.

Most as-of-t signals (velocities, gaps, ratios, stall counters, reason
multi-hots) already exist as raw columns on the panel by construction in
the Phase 1 generator (see `paimana.data.schema.SNAPSHOT_COLUMNS`). The
genuinely new engineering work here is the AGENCY HISTORICAL-PERFORMANCE
features: for each project-quarter row, "how has this implementing agency
performed on ITS OTHER projects, using only what was already known (i.e.
already completed) as of this row's `as_of_date`?"

That "as of" qualifier is a second, subtler leakage trap distinct from the
target-column blacklist in `leakage.py`: it would be leakage to let a
project's agency-performance feature reflect a sibling project that hadn't
completed yet as of the row's snapshot date, or the project's own eventual
outcome. See `_add_agency_track_record` for how this is enforced.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from paimana import config
from paimana.features.leakage import assert_no_leakage

# Columns already present on the panel (Phase 1) that are legitimate as-of-t
# model inputs without further engineering.
BASE_NUMERIC_FEATURES: tuple[str, ...] = (
    "elapsed_months",
    "elapsed_frac",
    "physical_progress_pct",
    "expenditure_to_date_cr",
    "financial_progress_pct",
    "progress_velocity_3q",
    "progress_gap_pp",
    "required_velocity",
    "velocity_ratio",
    "stalled_quarters",
    "n_reasons_active",
    "revisions_to_date",
    "months_since_last_revision",
    "original_cost_cr",
    "original_duration_months",
)
REASON_FEATURES: tuple[str, ...] = tuple(f"reason_{r}" for r in config.DELAY_REASONS)
CATEGORICAL_FEATURES: tuple[str, ...] = (
    "sector",
    "state",
    "funding_mode",
    "implementing_agency_type",
    "cost_band",
)
BOOLEAN_FEATURES: tuple[str, ...] = ("is_multi_state",)

# New in Phase 2 — see module docstring and _add_agency_track_record.
AGENCY_TRACK_RECORD_FEATURES: tuple[str, ...] = (
    "agency_prior_completed_count",
    "agency_prior_avg_cost_overrun_pct",
    "agency_prior_avg_time_overrun_months",
    "agency_prior_severe_rate",
)

ALL_FEATURE_COLUMNS: tuple[str, ...] = (
    BASE_NUMERIC_FEATURES
    + REASON_FEATURES
    + CATEGORICAL_FEATURES
    + BOOLEAN_FEATURES
    + AGENCY_TRACK_RECORD_FEATURES
)

# Encoding split used consistently by every model from Phase 3 onward
# (statsmodels/sklearn baselines here, tree ensembles in Phase 4): which
# columns need one-hot/categorical encoding vs. which are already numeric
# (reason_* and is_multi_state are boolean 0/1, safe to treat as numeric).
NUMERIC_FEATURE_COLUMNS: tuple[str, ...] = (
    BASE_NUMERIC_FEATURES + REASON_FEATURES + BOOLEAN_FEATURES + AGENCY_TRACK_RECORD_FEATURES
)
CATEGORICAL_FEATURE_COLUMNS: tuple[str, ...] = CATEGORICAL_FEATURES


def _add_agency_track_record(panel: pd.DataFrame, projects: pd.DataFrame) -> pd.DataFrame:
    """Attach agency historical-performance features to every panel row.

    For a row (project P, agency A, as_of_date T), the feature is computed
    over agency A's OTHER completed projects with `final_doc < T` — strictly
    before, using `np.searchsorted(..., side="left")` per agency. This is
    what guarantees no self-leakage: a project's own panel rows only ever
    exist up to and including its own completion quarter, so its own
    `final_doc` can never be strictly less than its own `as_of_date` — the
    self-exclusion falls out of the date ordering rather than needing an
    explicit per-row check (verified in tests/test_features.py with a
    hand-built fixture).
    """
    panel = panel.copy()
    n = len(panel)
    prior_count = np.zeros(n, dtype=np.int64)
    prior_avg_cost = np.full(n, np.nan)
    prior_avg_time = np.full(n, np.nan)
    prior_severe_rate = np.full(n, np.nan)

    completed = (
        projects.loc[
            projects["is_censored"] == False,  # noqa: E712
            ["agency_id", "final_doc", "cost_overrun_pct", "time_overrun_months", "y_severe"],
        ]
        .dropna(subset=["final_doc"])
        .sort_values("final_doc")
    )

    panel_as_of = pd.to_datetime(panel["as_of_date"]).to_numpy()
    row_positions_by_agency = panel.groupby("agency_id").indices  # agency_id -> int array

    for agency_id, grp in completed.groupby("agency_id"):
        positions = row_positions_by_agency.get(agency_id)
        if positions is None or len(positions) == 0:
            continue

        dates = pd.to_datetime(grp["final_doc"]).to_numpy()
        cost_cumsum = np.concatenate([[0.0], np.cumsum(grp["cost_overrun_pct"].to_numpy())])
        time_cumsum = np.concatenate([[0.0], np.cumsum(grp["time_overrun_months"].to_numpy())])
        severe_cumsum = np.concatenate([[0.0], np.cumsum(grp["y_severe"].astype(float).to_numpy())])

        query_dates = panel_as_of[positions]
        idx = np.searchsorted(dates, query_dates, side="left")  # strictly-before count

        has_prior = idx > 0
        safe_idx = np.maximum(idx, 1)

        prior_count[positions] = idx
        prior_avg_cost[positions] = np.where(has_prior, cost_cumsum[idx] / safe_idx, np.nan)
        prior_avg_time[positions] = np.where(has_prior, time_cumsum[idx] / safe_idx, np.nan)
        prior_severe_rate[positions] = np.where(has_prior, severe_cumsum[idx] / safe_idx, np.nan)

    panel["agency_prior_completed_count"] = prior_count
    panel["agency_prior_avg_cost_overrun_pct"] = prior_avg_cost
    panel["agency_prior_avg_time_overrun_months"] = prior_avg_time
    panel["agency_prior_severe_rate"] = prior_severe_rate
    return panel


def build_feature_table(panel: pd.DataFrame, projects: pd.DataFrame) -> pd.DataFrame:
    """Augment the raw panel with engineered features.

    Returns the FULL augmented table (keys + features + target columns) —
    matching the Phase 1 convention that panel-level tables carry targets
    alongside features so labels are available for training. Target columns
    must still be stripped via `select_features()` before anything touches
    a model.
    """
    return _add_agency_track_record(panel, projects)


def select_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return only the columns approved as model inputs (PRD §5.3/§5.5).

    Asserts the result contains no forbidden column — this is the point
    every downstream phase should call to get its `X` matrix.
    """
    cols = [c for c in ALL_FEATURE_COLUMNS if c in df.columns]
    X = df[cols].copy()
    assert_no_leakage(X)
    return X
