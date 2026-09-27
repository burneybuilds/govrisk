"""SHAP explainability — PRD §6.6, §7/Phase 4 task 3.

SHAP values become the "reason codes" attached to every alert in Phase 5
and the per-project waterfall in Phase 6's dashboard — this is the
prescriptive layer the problem statement asks for, not just a diagnostic.

Computed on the `y_severe` model — the alert-driving target — using
whichever model family the bake-off found best for it. Two deliberate
scope choices:

1. SHAP is computed on the base (uncalibrated) tree model, not the
   isotonic-calibrated wrapper. Isotonic calibration is a monotonic
   rescaling of the output probability; it does not change which features
   drove a prediction or by how much in the underlying tree structure, and
   `shap.TreeExplainer` needs direct access to a tree ensemble's structure
   (a `CalibratedClassifierCV` wrapper does not expose one uniformly).
2. Explanations are computed for each project's MOST RECENT snapshot only
   (`latest_snapshot_per_project`) — including ongoing (censored) projects,
   not just the completed ones the model was trained on. Training only ever
   uses labelled (completed) rows, but the whole point of an early-warning
   system is to explain why a CURRENTLY ONGOING project is flagged TODAY —
   that is the "as of now" population Phase 5's alert engine and Phase 6's
   deep-dive screen actually need, not a full historical trail of every
   past quarter for every project. This also turns a computation over the
   full ~50k-row panel (found, during Phase 4, to take an unbounded amount
   of time with a large/deep forest — the exact algorithmic cost of exact
   TreeSHAP scales with rows x trees x leaves) into one over ~2,000 rows —
   a ~25x reduction that is a genuine scope correction, not a shortcut: a
   project's PAST quarters cannot receive new alerts anyway.

Precomputed and cached to parquet (PRD §7/Phase 4 task 3) — computing SHAP
live inside the Streamlit dashboard (Phase 6) would make the app
unusably slow; the UI must only ever read these cached artifacts.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import shap
from sklearn.pipeline import Pipeline

from paimana import config
from paimana.features.build import select_features
from paimana.models.ml import make_classifier

SEVERE_TARGET = "y_severe"


def latest_snapshot_per_project(panel_df: pd.DataFrame) -> pd.DataFrame:
    """One row per project: its most recent quarterly snapshot by `as_of_date`.

    This is the "as of today" population an early-warning system actually
    needs to explain — a project's past quarters are frozen history and
    cannot receive a new alert. Used to keep SHAP computation tractable
    (~1,981 rows instead of the full ~50k-row panel) without narrowing WHO
    gets explained: every project, completed or still ongoing, is included.
    """
    return (
        panel_df.sort_values("as_of_date")
        .groupby("project_id", as_index=False)
        .last()
        .reset_index(drop=True)
    )


def _fit_base_tree_model(completed_df: pd.DataFrame, family: str, params: dict) -> Pipeline:
    """Fit an uncalibrated tree pipeline on ALL completed rows — the model
    SHAP actually explains (see module docstring point 1)."""
    X = select_features(completed_df)
    y = completed_df[SEVERE_TARGET].astype(int)
    pipeline = make_classifier(family, params)
    pipeline.fit(X, y)
    return pipeline


def compute_shap_values(
    panel_df: pd.DataFrame, completed_df: pd.DataFrame, family: str, params: dict
) -> tuple[np.ndarray, list[str], Pipeline]:
    """Fit the base tree model on completed rows, then explain every row of
    `panel_df` — callers should pass `latest_snapshot_per_project(full_panel)`
    (see module docstring point 2), not the full historical panel, to keep
    this tractable.

    Returns (shap_values [n_rows, n_features], feature_names, the fitted
    pipeline) so callers can also serialize the model itself.
    """
    pipeline = _fit_base_tree_model(completed_df, family, params)

    preprocessor = pipeline.named_steps["preprocess"]
    tree_model = pipeline.named_steps["model"]
    feature_names = list(preprocessor.get_feature_names_out())

    X_panel_raw = select_features(panel_df)
    X_panel_transformed = preprocessor.transform(X_panel_raw)

    explainer = shap.TreeExplainer(tree_model)
    raw_shap = explainer.shap_values(X_panel_transformed)

    # Binary classifiers: some libraries return a single (n, k) array for
    # the positive class, others a list of two arrays (one per class) —
    # normalise to "the positive class's contribution" either way.
    if isinstance(raw_shap, list):
        shap_values = raw_shap[1]
    elif raw_shap.ndim == 3:
        shap_values = raw_shap[:, :, 1]
    else:
        shap_values = raw_shap

    return shap_values, feature_names, pipeline


def build_shap_artifacts(
    panel_df: pd.DataFrame, completed_df: pd.DataFrame, family: str, params: dict
) -> tuple[dict[str, pd.DataFrame], Pipeline]:
    """Return the two cacheable tables (global feature importance and
    per-row SHAP values keyed by project_id/as_of_date) AND the fitted
    pipeline — computing SHAP once, not twice: an earlier version of this
    orchestration called `compute_shap_values` a second time just to get
    the pipeline object to serialize, silently doubling an already
    expensive computation. Found during Phase 4 (see HANDOFF.md).
    """
    shap_values, feature_names, pipeline = compute_shap_values(panel_df, completed_df, family, params)

    global_importance = (
        pd.DataFrame({"feature": feature_names, "mean_abs_shap": np.abs(shap_values).mean(axis=0)})
        .sort_values("mean_abs_shap", ascending=False)
        .reset_index(drop=True)
    )

    per_row = pd.DataFrame(shap_values, columns=feature_names)
    per_row.insert(0, "project_id", panel_df["project_id"].to_numpy())
    per_row.insert(1, "as_of_date", panel_df["as_of_date"].to_numpy())

    return {"global": global_importance, "per_row": per_row}, pipeline


def top_reason_codes(per_row_shap: pd.Series, feature_names: list[str], k: int = 3) -> list[dict]:
    """The top-k features driving one row's prediction, for an alert's
    "reason codes" (PRD §6.8) — largest |SHAP value|, signed so the caller
    can tell whether a feature pushed risk up or down."""
    values = per_row_shap[feature_names].astype(float)
    top = values.abs().sort_values(ascending=False).head(k)
    return [{"feature": f, "shap_value": float(values[f])} for f in top.index]


def save_shap_artifacts(artifacts: dict[str, pd.DataFrame]) -> None:
    """Write the global and per-row SHAP tables to their configured paths."""
    config.ARTIFACTS_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    artifacts["global"].to_parquet(config.ARTIFACTS_METRICS_DIR / "shap_global.parquet", index=False)
    artifacts["per_row"].to_parquet(config.ARTIFACTS_METRICS_DIR / "shap_values.parquet", index=False)
