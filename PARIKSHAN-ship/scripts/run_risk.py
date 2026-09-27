#!/usr/bin/env python
"""Score every project-quarter, build the early-warning alert queue.

Usage: python scripts/run_risk.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import joblib  # noqa: E402
import pandas as pd  # noqa: E402

from paimana import config  # noqa: E402
from paimana.data.loader import load_processed_features  # noqa: E402
from paimana.models.explain import top_reason_codes  # noqa: E402
from paimana.risk.alerts import build_alerts  # noqa: E402
from paimana.risk.score import compute_risk_scores  # noqa: E402


def _load_shap_reason_codes() -> dict[str, list[dict]]:
    """Build {project_id: [top-3 reason codes]} from Phase 4's cached SHAP
    values — only ever available for each project's LATEST snapshot."""
    path = config.ARTIFACTS_METRICS_DIR / "shap_values.parquet"
    if not path.exists():
        print(f"  (no {path.name} found — alerts will fall back to active delay reasons only)")
        return {}
    shap_df = pd.read_parquet(path)
    feature_cols = [c for c in shap_df.columns if c not in ("project_id", "as_of_date")]
    return {
        row["project_id"]: top_reason_codes(row, feature_cols, k=3) for _, row in shap_df.iterrows()
    }


def main() -> None:
    panel = load_processed_features()
    print(f"loaded panel: {panel.shape[0]:,} rows x {panel.shape[1]} cols")

    cost_clf = joblib.load(config.ARTIFACTS_MODELS_DIR / "y_cost_overrun_classifier_calibrated.joblib")
    time_clf = joblib.load(config.ARTIFACTS_MODELS_DIR / "y_time_overrun_classifier_calibrated.joblib")
    cost_reg = joblib.load(config.ARTIFACTS_MODELS_DIR / "cost_overrun_pct_regressor.joblib")
    time_reg = joblib.load(config.ARTIFACTS_MODELS_DIR / "time_overrun_months_regressor.joblib")

    print("Scoring every project-quarter (risk trajectory)...")
    risk_df = compute_risk_scores(panel, cost_clf, time_clf, cost_reg, time_reg)

    config.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    risk_df.to_parquet(config.RISK_SCORES_PARQUET, index=False)
    print(f"risk_scores: {risk_df.shape[0]:,} rows -> {config.RISK_SCORES_PARQUET}")
    print(risk_df["risk_band"].value_counts())

    print("\nBuilding the alert queue (7 EW rules + model-driven, edge-triggered)...")
    shap_reason_codes = _load_shap_reason_codes()
    alerts_df = build_alerts(risk_df, shap_reason_codes)
    alerts_df.to_parquet(config.ALERTS_PARQUET, index=False)
    print(f"alerts: {alerts_df.shape[0]:,} rows -> {config.ALERTS_PARQUET}")
    print(alerts_df["severity"].value_counts())


if __name__ == "__main__":
    main()
