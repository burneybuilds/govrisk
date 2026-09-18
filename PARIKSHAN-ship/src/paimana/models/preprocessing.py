"""Shared feature-encoding utilities for every model in this project.

Extracted from `baselines.py` in Phase 4 so ML models (`ml.py`) and the
statistical baselines use the exact same category vocabulary and sklearn
preprocessing pipeline — one definition, not two copies that could silently
drift apart.
"""

from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from paimana import config
from paimana.features.build import CATEGORICAL_FEATURE_COLUMNS, NUMERIC_FEATURE_COLUMNS

# The closed, known vocabulary for every categorical feature (PRD §5.2) —
# used both for sklearn's OneHotEncoder (fixed `categories=`, so a column
# never depends on what happened to appear in a given fold) and for casting
# to pandas `category` dtype for XGBoost/LightGBM's native categorical
# support (see `prepare_native_categorical`).
FEATURE_CATEGORIES: dict[str, list[str]] = {
    "sector": config.SECTORS,
    "state": config.STATES,
    "funding_mode": config.FUNDING_MODES,
    "implementing_agency_type": config.AGENCY_TYPES,
    "cost_band": config.COST_BANDS,
}


def make_sklearn_preprocessor() -> ColumnTransformer:
    """One-hot + median-impute/scale pipeline for sklearn estimators
    (logistic regression, random forest) that cannot take raw categoricals
    or NaN directly. Fit fresh inside every CV fold — never on the full
    dataset — so no fold-dependent information leaks through the encoder.
    """
    categorical_cols = list(CATEGORICAL_FEATURE_COLUMNS)
    numeric_cols = list(NUMERIC_FEATURE_COLUMNS)
    categories = [FEATURE_CATEGORIES[c] for c in categorical_cols]

    return ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(categories=categories, handle_unknown="ignore"), categorical_cols),
            (
                "num",
                Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]),
                numeric_cols,
            ),
        ]
    )


def prepare_native_categorical(X: pd.DataFrame) -> pd.DataFrame:
    """Cast categorical feature columns to pandas `category` dtype with the
    FULL known vocabulary (not inferred from `X`) for XGBoost/LightGBM's
    native categorical support.

    NOT USED by `models/ml.py` — kept for documentation and any future
    experimentation. Measured during Phase 4 (see HANDOFF.md): on this
    dataset's scale and category cardinalities, native categorical splitting
    performed MEASURABLY WORSE than plain one-hot encoding for both
    libraries (XGBoost R^2 0.033 vs. 0.256; LightGBM R^2 0.122 vs. 0.242, on
    a representative fold) — one-hot's simpler indicator features seem to be
    more sample-efficient here than the libraries' partition-search-based
    categorical splitting. Every model family in this project therefore uses
    the SAME `make_sklearn_preprocessor()` one-hot pipeline, both for
    fairness in the bake-off and because it is simply the better result.
    """
    X = X.copy()
    for col, categories in FEATURE_CATEGORIES.items():
        if col in X.columns:
            X[col] = pd.Categorical(X[col], categories=categories)
    return X
