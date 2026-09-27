"""The leakage guard — PRD §5.5. The single most important file in this project.

Every feature matrix, in every phase from here on, must pass through
`assert_no_leakage()` before it touches a model. A model that reports
suspiciously good numbers is far more likely to have this check skipped
somewhere than to be genuinely that good (PRD §4.3.5) — this module is what
makes "suspiciously good" a build failure instead of a demo slide.
"""

from __future__ import annotations

import re

import pandas as pd

from paimana.data import schema

# Exact terminal-outcome column names that must never enter a training
# matrix (PRD §5.5) — the full set is the data contract's TARGET_COLUMNS.
FORBIDDEN_COLUMNS: frozenset[str] = frozenset(schema.TARGET_COLUMNS)

# Defensive pattern, forward-compatible with a real CUF extract: this
# generator's schema only ever produces `final_*` / `y_*` columns, but PRD
# §5.5 explicitly also forbids `revised_*` / `anticipated_*` / `target_*`
# naming that a genuine PAIMANA export is likely to use. Catching the
# pattern now means the real-data adapter (PRD §4.3.4) can't silently
# reintroduce leakage just because a column wasn't in FORBIDDEN_COLUMNS by
# exact name.
FORBIDDEN_PATTERN = re.compile(r"^(final_|revised_|anticipated_|y_|target_)")


def is_forbidden(column: str) -> bool:
    """True if `column` is a known target column or matches the forbidden pattern."""
    return column in FORBIDDEN_COLUMNS or bool(FORBIDDEN_PATTERN.match(column))


def find_leaking_columns(df_or_columns: pd.DataFrame | list[str]) -> list[str]:
    """Return every forbidden column name present in a DataFrame or column list."""
    columns = df_or_columns.columns if hasattr(df_or_columns, "columns") else df_or_columns
    return [c for c in columns if is_forbidden(c)]


def assert_no_leakage(X: pd.DataFrame) -> None:
    """Raise AssertionError listing every forbidden column found in `X`.

    Call this immediately before fitting or predicting with ANY model, on
    the exact matrix that will be passed to `.fit()`/`.predict()` — not on
    an earlier, wider dataframe. This is the build gate protecting every
    downstream phase from target leakage (PRD §5.5).
    """
    leaking = find_leaking_columns(X)
    if leaking:
        raise AssertionError(
            f"LEAKAGE DETECTED: forbidden column(s) present in feature matrix: {leaking}. "
            "See PRD §5.5 — these are terminal-outcome columns (or match the forbidden "
            "naming pattern) and must never be model inputs."
        )
