"""Shared dashboard utilities: cached data loading and the synthetic-data
banner every screen must show (PRD §4.3.1).

DELIBERATELY imports only pandas/numpy/json/streamlit and `paimana.config`
(pure constants) — never `paimana.models.ml`/`explain`/`baselines` (which
pull in xgboost/lightgbm/shap/statsmodels) and never `joblib.load()` on the
235MB serialized models. Every screen reads a precomputed parquet/JSON
artifact; nothing in the app trains, predicts, or explains at request time
(PRD §7/Phase 6 non-negotiable) — that keeps cold start fast regardless of
how large the model artifacts on disk are.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from paimana import config

SYNTHETIC_BANNER_MD = (
    "⚠️ **SYNTHETIC DATA** — generated to match published PAIMANA aggregate statistics, "
    "not sourced from a real CUF export. Every number on this page validates a "
    "**methodology and pipeline**, not a real-world accuracy claim. "
    "See `docs/DATA_METHODOLOGY.md` for the full generative assumptions."
)


def render_synthetic_banner() -> None:
    """The persistent amber banner PRD §4.3.1 requires on every screen."""
    st.warning(SYNTHETIC_BANNER_MD, icon="⚠️")


def latest_snapshot_per_project(df: pd.DataFrame) -> pd.DataFrame:
    """One row per project: its most recent quarterly snapshot. A small,
    dependency-free reimplementation of `explain.latest_snapshot_per_project`
    — kept local so the app never imports `paimana.models.explain` (which
    imports `shap` at module level, adding avoidable cold-start cost).
    """
    return (
        df.sort_values("as_of_date")
        .groupby("project_id", as_index=False)
        .last()
        .reset_index(drop=True)
    )


@st.cache_data
def load_risk_scores() -> pd.DataFrame:
    return pd.read_parquet(config.RISK_SCORES_PARQUET)


@st.cache_data
def load_alerts() -> pd.DataFrame:
    return pd.read_parquet(config.ALERTS_PARQUET)


@st.cache_data
def load_projects() -> pd.DataFrame:
    return pd.read_parquet(config.PROJECTS_PARQUET)


@st.cache_data
def load_quantile_predictions() -> pd.DataFrame:
    return pd.read_parquet(config.DATA_PROCESSED_DIR / "quantile_predictions.parquet")


@st.cache_data
def load_shap_global() -> pd.DataFrame:
    return pd.read_parquet(config.ARTIFACTS_METRICS_DIR / "shap_global.parquet")


@st.cache_data
def load_shap_values() -> pd.DataFrame:
    return pd.read_parquet(config.ARTIFACTS_METRICS_DIR / "shap_values.parquet")


@st.cache_data
def load_alert_backtest_lead_times() -> pd.DataFrame:
    return pd.read_parquet(config.ARTIFACTS_METRICS_DIR / "alert_backtest_lead_times.parquet")


@st.cache_data
def load_json(filename: str) -> dict:
    path = config.ARTIFACTS_METRICS_DIR / filename
    return json.loads(Path(path).read_text(encoding="utf-8"))


@st.cache_data
def load_comparison() -> dict:
    return load_json("comparison.json")


@st.cache_data
def load_calibration_curves() -> dict:
    return load_json("calibration_curves.json")


@st.cache_data
def load_pr_curves() -> dict:
    return load_json("pr_curves.json")


@st.cache_data
def load_precision_at_k_curves() -> dict:
    return load_json("precision_at_k_curves.json")


def risk_band_color(band: str) -> str:
    return {"Green": "#2e7d32", "Amber": "#f9a825", "Red": "#c62828"}.get(band, "#757575")


def severity_color(severity: str) -> str:
    return {"Medium": "#f9a825", "High": "#ef6c00", "Critical": "#c62828"}.get(severity, "#757575")
