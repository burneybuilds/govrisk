#!/usr/bin/env python
"""Fit ML models, calibrate, compute SHAP, run the bake-off, serialize
artifacts, and write comparison.json + BAKEOFF.md.

Usage: python scripts/run_models.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import joblib  # noqa: E402
import numpy as np  # noqa: E402

from paimana import config  # noqa: E402
from paimana.data.loader import load_processed_features  # noqa: E402
from paimana.models import bakeoff, explain  # noqa: E402
from paimana.models.evaluate import completed_labelled_rows, reliability_curve  # noqa: E402
from paimana.models.ml import (  # noqa: E402
    CLASSIFICATION_TARGETS,
    REGRESSION_TARGETS,
    MLResults,
    run_all_ml_models,
)


def _check_sanity_gate(ml_results: MLResults) -> list[str]:
    """PRD §4.3.5 / Phase 4 task 6: a model this good on synthetic data
    calibrated to be noisy is evidence of a leakage bug, not a win."""
    violations = []
    for target in REGRESSION_TARGETS:
        for family, m in ml_results.metrics[target].items():
            if m["r2"] > config.MAX_PLAUSIBLE_R2:
                violations.append(f"{target}/{family}: R2={m['r2']:.4f} exceeds {config.MAX_PLAUSIBLE_R2}")
    for target in CLASSIFICATION_TARGETS:
        for family, m in ml_results.metrics[target].items():
            if not np.isnan(m["pr_auc"]) and m["pr_auc"] > config.MAX_PLAUSIBLE_PR_AUC:
                violations.append(
                    f"{target}/{family}: PR-AUC={m['pr_auc']:.4f} exceeds {config.MAX_PLAUSIBLE_PR_AUC}"
                )
    return violations


def _serialize_models(ml_results: MLResults, shap_pipeline) -> None:
    config.ARTIFACTS_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for target in REGRESSION_TARGETS:
        joblib.dump(
            ml_results.final_models[target], config.ARTIFACTS_MODELS_DIR / f"{target}_regressor.joblib"
        )
        joblib.dump(
            ml_results.quantile_results[target]["final_model"],
            config.ARTIFACTS_MODELS_DIR / f"{target}_quantile.joblib",
        )
    for target in CLASSIFICATION_TARGETS:
        joblib.dump(
            ml_results.final_models[target],
            config.ARTIFACTS_MODELS_DIR / f"{target}_classifier_calibrated.joblib",
        )
    joblib.dump(shap_pipeline, config.ARTIFACTS_MODELS_DIR / "y_severe_shap_base_model.joblib")


def _build_comparison(ml_results: MLResults, bakeoff_results: dict) -> dict:
    comparison: dict = {"targets": {}}
    for target, entry in bakeoff_results.items():
        task_key = "regression" if entry["task"] == "regression" else "classification"
        best_family = ml_results.best_family[target]
        comparison["targets"][target] = {
            **entry,
            "all_ml_family_metrics": ml_results.metrics[target],
            "chosen_hyperparameters": ml_results.chosen_hyperparameters[task_key][best_family],
        }
    for target, qr in ml_results.quantile_results.items():
        comparison["targets"][target]["quantile_interval"] = {
            k: v for k, v in qr.items() if k != "final_model"
        }

    # Overall "best_ml" summary: the classification target with the highest
    # ML PR-AUC (this project's primary classification metric, PRD §6.4).
    clf_candidates = {t: comparison["targets"][t]["ml_pr_auc"] for t in CLASSIFICATION_TARGETS}
    best_target = max(clf_candidates, key=lambda t: clf_candidates[t])
    comparison["best_ml"] = {
        "target": best_target,
        "family": comparison["targets"][best_target]["ml_model"],
        "pr_auc": clf_candidates[best_target],
    }

    n_targets = len(comparison["targets"])
    wins = sum(
        1
        for t in comparison["targets"].values()
        if t["bootstrap"]["ci_excludes_zero"] and t["bootstrap"]["mean_diff"] > 0
    )
    losses = sum(
        1
        for t in comparison["targets"].values()
        if t["bootstrap"]["ci_excludes_zero"] and t["bootstrap"]["mean_diff"] < 0
    )
    ties = n_targets - wins - losses
    comparison["headline"] = (
        f"ML significantly beat the conventional baseline on {wins}/{n_targets} targets, "
        f"significantly lost on {losses}, and showed no significant difference on {ties}."
    )
    return comparison


def _write_bakeoff_md(comparison: dict) -> None:
    lines = ["# PARIKSHAN — Phase 4 Bake-Off: Conventional Statistics vs. Machine Learning", ""]
    lines.append(f"**Headline:** {comparison['headline']}")
    lines.append("")
    lines.append(
        "| Target | Task | Conventional | ML (best) | Conventional score | ML score | "
        "Bootstrap 95% CI (ML - conv) | Significant? |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for target, entry in comparison["targets"].items():
        if entry["task"] == "regression":
            conv_score, ml_score = f"{entry['conventional_r2']:.4f}", f"{entry['ml_r2']:.4f}"
        else:
            conv_score, ml_score = f"{entry['conventional_pr_auc']:.4f}", f"{entry['ml_pr_auc']:.4f}"
        ci = entry["bootstrap"]
        sig = "YES" if ci["ci_excludes_zero"] else "no"
        lines.append(
            f"| {target} | {entry['task']} | {entry['conventional_model']} | {entry['ml_model']} | "
            f"{conv_score} | {ml_score} | [{ci['ci_lower']:.4f}, {ci['ci_upper']:.4f}] | {sig} |"
        )

    lines += ["", "## DeLong test (ROC-AUC significance, classification targets only)", ""]
    lines.append("| Target | AUC (ML) | AUC (conventional) | z | p-value |")
    lines.append("|---|---|---|---|---|")
    for target, entry in comparison["targets"].items():
        if "delong" in entry:
            d = entry["delong"]
            lines.append(
                f"| {target} | {d['auc_a']:.4f} | {d['auc_b']:.4f} | "
                f"{d['z_statistic']:.3f} | {d['p_value']:.4g} |"
            )

    lines += ["", "## Prediction interval coverage (XGBoost quantile models, 10th-90th percentile)", ""]
    lines.append("| Target | Target coverage | Observed coverage (temporal test) | Mean interval width |")
    lines.append("|---|---|---|---|")
    for target, entry in comparison["targets"].items():
        qi = entry.get("quantile_interval")
        if qi:
            lines.append(
                f"| {target} | {qi['target_coverage']:.0%} | {qi['observed_coverage_test']:.1%} | "
                f"{qi['mean_interval_width_test']:.2f} |"
            )

    lines += ["", "## Full per-family metrics", ""]
    for target, entry in comparison["targets"].items():
        lines.append(f"### {target}")
        key_metric = "r2" if entry["task"] == "regression" else "pr_auc"
        lines.append(f"| Family | {key_metric} |")
        lines.append("|---|---|")
        for fam, m in entry["all_ml_family_metrics"].items():
            lines.append(f"| {fam} | {m[key_metric]:.4f} |")
        lines.append("")

    lines += [
        "## Calibration curves",
        "",
        "Reliability-curve data (predicted vs. observed frequency, 10 bins) for each "
        "classification target's best ML model is cached at "
        "`artifacts/metrics/calibration_curves.json` for the Phase 6 dashboard's Model Lab "
        "screen to render.",
        "",
        "## Plain-English verdict",
        "",
    ]
    for target, entry in comparison["targets"].items():
        ci = entry["bootstrap"]
        if ci["ci_excludes_zero"] and ci["mean_diff"] > 0:
            verdict = (
                f"ML (**{entry['ml_model']}**) SIGNIFICANTLY beats the conventional baseline "
                f"(**{entry['conventional_model']}**)."
            )
        elif ci["ci_excludes_zero"] and ci["mean_diff"] < 0:
            verdict = (
                f"The conventional baseline (**{entry['conventional_model']}**) SIGNIFICANTLY beats "
                f"ML (**{entry['ml_model']}**) — an honest result, reported as-is, not hidden."
            )
        else:
            verdict = (
                f"NO statistically significant difference between ML (**{entry['ml_model']}**) and "
                f"the conventional baseline (**{entry['conventional_model']}**)."
            )
        lines.append(f"- **{target}**: {verdict}")

    config.ARTIFACTS_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    (config.ARTIFACTS_METRICS_DIR / "BAKEOFF.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    features_df = load_processed_features()
    completed = completed_labelled_rows(features_df)
    print(f"completed rows: {len(completed):,} across {completed['project_id'].nunique():,} projects")

    print("Selecting hyperparameters + fitting RF/XGBoost/LightGBM (OOF via GroupKFold)...")
    ml_results = run_all_ml_models(completed)

    violations = _check_sanity_gate(ml_results)
    if violations:
        print("LEAKAGE SUSPECTED — the following exceeded the plausibility ceiling (PRD §4.3.5):")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)

    print("Running the bake-off (paired project-level bootstrap + DeLong test)...")
    bakeoff_results = bakeoff.run_bakeoff(completed, ml_results)
    comparison = _build_comparison(ml_results, bakeoff_results)

    print("Computing SHAP explanations for y_severe (latest snapshot per project, incl. ongoing)...")
    latest_panel = explain.latest_snapshot_per_project(features_df)
    print(f"  explaining {len(latest_panel):,} rows, one per project (panel has {len(features_df):,})")
    best_severe_family = ml_results.best_family["y_severe"]
    severe_params = ml_results.chosen_hyperparameters["classification"][best_severe_family]
    shap_artifacts, shap_pipeline = explain.build_shap_artifacts(
        latest_panel, completed, best_severe_family, severe_params
    )
    explain.save_shap_artifacts(shap_artifacts)

    print("Computing calibration curves...")
    calibration_curves = {}
    for target in CLASSIFICATION_TARGETS:
        y_true_ml, ml_prob = ml_results.oof[target][ml_results.best_family[target]]
        calibration_curves[f"{target}__ml_{ml_results.best_family[target]}"] = reliability_curve(
            y_true_ml, ml_prob
        )
    config.ARTIFACTS_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.ARTIFACTS_METRICS_DIR / "calibration_curves.json", "w", encoding="utf-8") as f:
        json.dump(calibration_curves, f, indent=2)

    print("Serializing models...")
    _serialize_models(ml_results, shap_pipeline)

    with open(config.ARTIFACTS_METRICS_DIR / "comparison.json", "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    _write_bakeoff_md(comparison)

    print(f"\n{comparison['headline']}")
    print(f"Wrote {config.ARTIFACTS_METRICS_DIR / 'comparison.json'}")
    print(f"Wrote {config.ARTIFACTS_METRICS_DIR / 'BAKEOFF.md'}")
    print(f"Serialized models to {config.ARTIFACTS_MODELS_DIR}")


if __name__ == "__main__":
    main()
