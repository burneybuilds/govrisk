"""Smoke tests for the Streamlit dashboard — PRD §7/Phase 6 DoD.

Imports every page module (proving each one runs top-to-bottom without an
exception — Streamlit's `st.*` calls no-op safely outside a real session,
so this genuinely exercises each page's data loading and chart-building
logic) and separately asserts every artifact file a page depends on is
actually present on disk.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from paimana import config

APP_DIR = Path(__file__).resolve().parents[1] / "src" / "paimana" / "app"

PAGE_FILES = [
    APP_DIR / "Home.py",
    APP_DIR / "pages" / "2_Early_Warning_Centre.py",
    APP_DIR / "pages" / "3_Project_Deep_Dive.py",
    APP_DIR / "pages" / "4_Model_Lab.py",
    APP_DIR / "pages" / "5_Assistant.py",
]


def _import_page(path: Path) -> None:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


@pytest.mark.parametrize("page_path", PAGE_FILES, ids=lambda p: p.name)
def test_page_module_imports_without_exception(page_path):
    _import_page(page_path)


def test_required_data_artifacts_exist():
    required = [
        config.RISK_SCORES_PARQUET,
        config.ALERTS_PARQUET,
        config.PROJECTS_PARQUET,
        config.DATA_PROCESSED_DIR / "quantile_predictions.parquet",
    ]
    missing = [str(p) for p in required if not p.exists()]
    assert not missing, f"missing dashboard data artifact(s): {missing}"


def test_required_metrics_artifacts_exist():
    required = [
        config.ARTIFACTS_METRICS_DIR / "comparison.json",
        config.ARTIFACTS_METRICS_DIR / "calibration_curves.json",
        config.ARTIFACTS_METRICS_DIR / "pr_curves.json",
        config.ARTIFACTS_METRICS_DIR / "precision_at_k_curves.json",
        config.ARTIFACTS_METRICS_DIR / "shap_global.parquet",
        config.ARTIFACTS_METRICS_DIR / "shap_values.parquet",
    ]
    missing = [str(p) for p in required if not p.exists()]
    assert not missing, f"missing dashboard metrics artifact(s): {missing}"


def test_reason_codes_survive_the_real_parquet_round_trip():
    """Regression guard for a real bug found by clicking through the running
    app, not by unit-testing in-memory data: pyarrow reads a parquet
    list-of-struct column back as `numpy.ndarray`, not a native Python
    `list`. An `isinstance(c, list)` check (the natural thing to write)
    silently matches NOTHING once alerts.parquet is read back from disk —
    the Early Warning Centre's "reason codes" section showed "none
    available" even though 256 real alerts had cached SHAP explanations.
    This loads the ACTUAL alerts.parquet (not a hand-built in-memory
    fixture) specifically because the bug only exists post-round-trip.
    """
    import pandas as pd

    alerts = pd.read_parquet(config.ALERTS_PARQUET)
    non_null = alerts[alerts["reason_codes"].notna()]
    assert len(non_null) > 0, "fixture assumption broken: expected some alerts with cached reason codes"

    sample = non_null.iloc[0]["reason_codes"]
    assert not isinstance(sample, list), (
        "if this now fails, pyarrow's round-trip behaviour changed — re-check whether "
        "_has_reason_codes()'s len()-based check (not isinstance(list)) is still needed"
    )

    page_path = APP_DIR / "pages" / "2_Early_Warning_Centre.py"
    spec = importlib.util.spec_from_file_location(page_path.stem, page_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._has_reason_codes(sample) is True
    assert module._has_reason_codes(None) is False

    codes_df = pd.DataFrame(list(sample))
    assert {"feature", "shap_value"} <= set(codes_df.columns), (
        "pd.DataFrame() must be given list(...) of the round-tripped array, not the "
        "ndarray directly, or it produces one column of raw dict objects instead of "
        "expanding feature/shap_value into columns"
    )


def test_app_never_imports_heavy_ml_modules():
    """Cold-start guard (PRD §7/Phase 6 non-negotiable + the 235MB model
    artifact concern flagged in the Phase 4/5 Handoff reports): the app
    must only ever read precomputed parquet/JSON, never train, predict, or
    explain at request time. Importing xgboost/lightgbm/shap/statsmodels
    or joblib-loading a serialized model would silently reintroduce that
    cost on every page load.
    """
    import sys

    forbidden_prefixes = ("xgboost", "lightgbm", "shap", "statsmodels", "sklearn")
    for page_path in PAGE_FILES:
        before = {m for m in sys.modules if m.startswith(forbidden_prefixes)}
        _import_page(page_path)
        after = {m for m in sys.modules if m.startswith(forbidden_prefixes)}
        newly_imported = after - before
        assert not newly_imported, f"{page_path.name} imported heavy ML module(s): {newly_imported}"
