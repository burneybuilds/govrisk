#!/usr/bin/env python
"""Precompute dashboard-support artifacts that Phases 4-5 didn't cache.

The dashboard (Phase 6) must NEVER train a model or run inference at
request time (PRD §7/Phase 6 non-negotiable) — every chart reads a
precomputed artifact. Two things the app needs weren't cached yet:

1. Quantile predictions (p10/p50/p90) for every panel row, for the
   Project Deep-Dive's "predicted vs. approved cost with uncertainty
   band" chart — Phase 4 serialized the quantile MODELS but never ran
   them over the panel to cache actual predictions.
2. PR-curve points and a Precision@K-vs-K curve for the three
   classification targets, for the Model Lab screen — Phase 4 only cached
   AGGREGATE metrics (comparison.json), not the raw curve data needed to
   plot a PR curve or a Precision@K line chart.

(2) requires OOF predictions, recomputed here via Phase 4's already-tested
`classifier_oof_calibrated` with the saved best hyperparameters — the same
honest, leakage-safe approach Phase 5's backtest used, not the final
in-sample-fit models.

Usage: python scripts/run_dashboard_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import joblib  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.metrics import precision_recall_curve  # noqa: E402

from paimana import config  # noqa: E402
from paimana.data.loader import load_processed_features  # noqa: E402
from paimana.features.build import select_features  # noqa: E402
from paimana.models.evaluate import completed_labelled_rows, precision_at_k  # noqa: E402
from paimana.models.ml import CLASSIFICATION_TARGETS, classifier_oof_calibrated  # noqa: E402


def _precompute_quantile_predictions() -> None:
    print("Precomputing quantile predictions (p10/p50/p90) for the full panel...")
    panel = load_processed_features()
    X = select_features(panel)

    out = panel[["project_id", "as_of_date", "original_cost_cr", "original_duration_months"]].copy()
    for target, col_prefix in (("cost_overrun_pct", "cost"), ("time_overrun_months", "time")):
        model = joblib.load(config.ARTIFACTS_MODELS_DIR / f"{target}_quantile.joblib")
        preds = model.predict(X)  # shape (n, 3): p10, p50, p90
        out[f"{col_prefix}_p10"] = preds[:, 0]
        out[f"{col_prefix}_p50"] = preds[:, 1]
        out[f"{col_prefix}_p90"] = preds[:, 2]

    out["predicted_final_cost_p10_cr"] = out["original_cost_cr"] * (1 + out["cost_p10"] / 100.0)
    out["predicted_final_cost_p50_cr"] = out["original_cost_cr"] * (1 + out["cost_p50"] / 100.0)
    out["predicted_final_cost_p90_cr"] = out["original_cost_cr"] * (1 + out["cost_p90"] / 100.0)

    path = config.DATA_PROCESSED_DIR / "quantile_predictions.parquet"
    out.to_parquet(path, index=False)
    print(f"  wrote {len(out):,} rows -> {path}")


def _load_chosen_hyperparameters() -> dict:
    comparison = json.loads((config.ARTIFACTS_METRICS_DIR / "comparison.json").read_text(encoding="utf-8"))
    return {
        target: {"family": entry["ml_model"], "params": entry["chosen_hyperparameters"]}
        for target, entry in comparison["targets"].items()
    }


def _precompute_pr_curves_and_precision_at_k() -> None:
    print("\nRecomputing OOF probabilities for PR-curve / Precision@K data (Model Lab)...")
    features_df = load_processed_features()
    completed = completed_labelled_rows(features_df)
    chosen = _load_chosen_hyperparameters()

    pr_curves: dict[str, dict] = {}
    precision_at_k_curves: dict[str, dict] = {}

    for target in CLASSIFICATION_TARGETS:
        print(f"  {target}...")
        y_true, y_prob = classifier_oof_calibrated(
            completed, target, chosen[target]["family"], chosen[target]["params"]
        )
        precision, recall, thresholds = precision_recall_curve(y_true, y_prob)
        # Subsample to ~200 points for a light JSON file — a PR curve chart
        # does not need every one of tens of thousands of threshold steps.
        idx = np.linspace(0, len(precision) - 1, min(200, len(precision))).astype(int)
        pr_curves[target] = {
            "precision": precision[idx].tolist(),
            "recall": recall[idx].tolist(),
        }

        k_values = list(range(10, 310, 10))
        precision_at_k_curves[target] = {
            "k": k_values,
            "precision": [precision_at_k(y_true, y_prob, k) for k in k_values],
            "base_rate": float(y_true.mean()),
        }

    config.ARTIFACTS_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.ARTIFACTS_METRICS_DIR / "pr_curves.json", "w", encoding="utf-8") as f:
        json.dump(pr_curves, f)
    with open(config.ARTIFACTS_METRICS_DIR / "precision_at_k_curves.json", "w", encoding="utf-8") as f:
        json.dump(precision_at_k_curves, f)
    print(f"  wrote pr_curves.json and precision_at_k_curves.json -> {config.ARTIFACTS_METRICS_DIR}")


def main() -> None:
    _precompute_quantile_predictions()
    _precompute_pr_curves_and_precision_at_k()


if __name__ == "__main__":
    main()
