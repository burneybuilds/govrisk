"""ML artifact smoke test: load every PARIKSHAN .joblib model and run a
placeholder prediction on a dummy 1-row DataFrame with the exact 37-feature
contract. Used to prove the trained artifacts load under this Python/env.

Run from anywhere:
    python scripts/smoke_ml_models.py
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = REPO_ROOT / "PARIKSHAN-ship" / "artifacts" / "models"

NUMERIC_FEATURES = [
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
]

REASON_FEATURES = [
    "reason_land_acquisition",
    "reason_forest_env_clearance",
    "reason_funds_constraint",
    "reason_contractor_issues",
    "reason_tendering_delay",
    "reason_litigation",
    "reason_r_and_r",
    "reason_law_and_order",
    "reason_geological_surprise",
    "reason_equipment_supply",
    "reason_statutory_clearance",
    "reason_force_majeure",
]

CATEGORICAL_FEATURES = [
    "sector",
    "state",
    "funding_mode",
    "implementing_agency_type",
    "cost_band",
]

BOOLEAN_FEATURES = ["is_multi_state"]

AGENCY_FEATURES = [
    "agency_prior_completed_count",
    "agency_prior_avg_cost_overrun_pct",
    "agency_prior_avg_time_overrun_months",
    "agency_prior_severe_rate",
]

ALL_FEATURES = (
    NUMERIC_FEATURES + REASON_FEATURES + CATEGORICAL_FEATURES + BOOLEAN_FEATURES + AGENCY_FEATURES
)

assert len(ALL_FEATURES) == 37, f"Expected 37 features, got {len(ALL_FEATURES)}"


def build_dummy_row() -> pd.DataFrame:
    row: dict = {}
    for col in NUMERIC_FEATURES:
        row[col] = 0.0
    for col in REASON_FEATURES:
        row[col] = 0
    for col in BOOLEAN_FEATURES:
        row[col] = 0
    for col in AGENCY_FEATURES:
        row[col] = float("nan")

    row.update(
        {
            "expenditure_to_date_cr": 100.0,
            "original_cost_cr": 500.0,
            "physical_progress_pct": 40.0,
            "elapsed_frac": 0.5,
        }
    )
    row.update(
        {
            "sector": "Railways",
            "state": "Maharashtra",
            "funding_mode": "Budgetary",
            "implementing_agency_type": "CPSU",
            "cost_band": "500-1000",
        }
    )
    return pd.DataFrame([row])


def main() -> int:
    print(f"python      : {sys.version.split()[0]}")
    print(f"numpy       : {np.__version__}")
    print(f"pandas      : {pd.__version__}")
    print(f"sklearn     : {importlib.import_module('sklearn').__version__}")
    print(f"xgboost     : {importlib.import_module('xgboost').__version__}")
    try:
        print(f"joblib      : {importlib.import_module('joblib').__version__}")
    except Exception as exc:
        print(f"joblib      : <error {exc}>")
    print(f"artifact dir: {ARTIFACTS_DIR}\n")

    import joblib

    tasks: list[tuple[str, str]] = [
        ("y_cost_overrun_classifier_calibrated.joblib", "classifier"),
        ("y_time_overrun_classifier_calibrated.joblib", "classifier"),
        ("y_severe_classifier_calibrated.joblib", "classifier"),
        ("cost_overrun_pct_regressor.joblib", "regressor"),
        ("time_overrun_months_regressor.joblib", "regressor"),
        ("cost_overrun_pct_quantile.joblib", "quantile"),
        ("time_overrun_months_quantile.joblib", "quantile"),
        ("y_severe_shap_base_model.joblib", "classifier"),
    ]

    X = build_dummy_row()

    ok, failed = 0, 0
    for fname, kind in tasks:
        path = ARTIFACTS_DIR / fname
        try:
            model = joblib.load(path)
            if kind == "classifier":
                proba = model.predict_proba(X)
                pred = model.predict(X)
                n_out = proba.shape
            elif kind == "quantile":
                pred = model.predict(X)
                n_out = pred.shape
            else:
                pred = model.predict(X)
                n_out = pred.shape
            print(f"[OK] {fname:<48} {kind:<10} predict={np.asarray(pred).shape} proba={n_out}")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {fname:<48} {kind:<10} {type(exc).__name__}: {exc}")
            failed += 1

    print(f"\nSummary: {ok} loaded and predicted, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())