#!/usr/bin/env python
"""Fit every Phase 3 conventional baseline and write metrics + model cards.

Usage: python scripts/run_baselines.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paimana import config  # noqa: E402
from paimana.data.loader import load_processed_features, load_processed_projects  # noqa: E402
from paimana.models.baselines import run_all_baselines  # noqa: E402
from paimana.models.survival import run_survival_models  # noqa: E402


def _print_summary_table(results: dict) -> None:
    print(f"\n{'Model':<10} {'Target':<20} {'Key metric':<16} {'Value':>10} {'n':>8}")
    print("-" * 68)
    for model_name in ("naive", "ols", "logit"):
        for target, metrics in results[model_name].items():
            if "r2" in metrics:
                key, val = "r2", metrics["r2"]
            else:
                key, val = "pr_auc", metrics["pr_auc"]
            print(f"{model_name:<10} {target:<20} {key:<16} {val:>10.4f} {metrics['n']:>8,}")
    for model_name in ("weibull_aft", "cox_ph"):
        m = results[model_name]
        print(
            f"{model_name:<10} {'months_to_completion':<20} {'c_index(test)':<16} "
            f"{m['concordance_index_test']:>10.4f} {m['n_test']:>8,}"
        )


def _write_model_cards(results: dict, cards_dir: Path) -> None:
    cards_dir.mkdir(parents=True, exist_ok=True)

    ols_summary = results["ols"]["cost_overrun_pct"].get("summary_text", "")
    (cards_dir / "ols_cost_overrun.md").write_text(
        "# Model Card — OLS: log(cost ratio) ~ sector fixed effects\n\n"
        "**Task:** regression, target `cost_overrun_pct` (via `log(1 + cost_overrun_pct/100)`)\n\n"
        "**Scope:** sector fixed effects ONLY (PRD §6.3) — a simple, interpretable "
        "conventional baseline, not the full feature set. Evaluated out-of-fold via "
        "GroupKFold(project_id, n_splits=5); the summary table below is a full-sample "
        "in-sample fit for interpretability, not the evaluation.\n\n"
        f"**Out-of-fold R2 (original scale):** {results['ols']['cost_overrun_pct']['r2']:.4f}\n"
        f"**Out-of-fold MAE:** {results['ols']['cost_overrun_pct']['mae']:.2f} pp\n\n"
        "**Note on back-transformation:** predictions are back-transformed from log-scale "
        "using Duan's (1983) smearing estimator (mean of exp(training-fold residuals)), not "
        "a plain `exp()`. A plain exp() back-transform is biased downward by Jensen's "
        "inequality and, uncorrected, made this model score WORSE than the naive sector-mean "
        "baseline it should beat — not because sector carries no signal, but purely from "
        "retransformation bias. Fixed during Phase 3; see HANDOFF.md.\n\n"
        "**Honest read of the R2 itself:** it is small (a few tenths of a percent to ~3% "
        "in-sample). Sector alone is a genuinely weak predictor of an individual project's "
        "cost overrun in this dataset — by design (PRD §4.3.5), most of the variance is "
        "project- and agency-level idiosyncratic risk, not sector membership. This is the "
        "correct, PRD-scoped conventional baseline (sector fixed effects only); the fairer "
        "full-feature-set conventional comparison against Phase 4's ML models is the "
        "logistic regression cards below, not this one.\n\n"
        "**Caveat:** fit only on completed (non-censored) projects — cost_overrun_pct is "
        "undefined for still-executing projects. If completed projects are systematically "
        "different from ongoing ones (e.g. faster-moving, lower-risk), this is a selection "
        "effect worth keeping in mind when interpreting the coefficients below.\n\n"
        "## statsmodels summary (full-sample fit)\n\n```\n" + ols_summary + "\n```\n",
        encoding="utf-8",
    )

    for target in ("y_cost_overrun", "y_time_overrun", "y_severe"):
        m = results["logit"][target]
        (cards_dir / f"logit_{target}.md").write_text(
            f"# Model Card — Logistic Regression: {target}\n\n"
            "**Task:** binary classification, L2-regularised, FULL feature set "
            "(37 columns after encoding) — a genuine conventional-ML competitor to "
            "Phase 4's tree ensembles, not a sector-only toy.\n\n"
            "**Evaluation:** out-of-fold via GroupKFold(project_id, n_splits=5).\n\n"
            f"| Metric | Value |\n|---|---|\n"
            f"| PR-AUC | {m['pr_auc']:.4f} |\n"
            f"| ROC-AUC | {m['roc_auc']:.4f} |\n"
            f"| Brier score | {m['brier']:.4f} |\n"
            f"| F1 @ best threshold ({m['best_threshold']:.3f}) | {m['f1_at_best_threshold']:.4f} |\n"
            f"| Base rate | {m['base_rate']:.4f} |\n"
            f"| n | {m['n']:,} |\n",
            encoding="utf-8",
        )

    for model_name in ("weibull_aft", "cox_ph"):
        m = results[model_name]
        title = "Weibull AFT" if model_name == "weibull_aft" else "Cox Proportional Hazards"
        ablation_note = ""
        if "concordance_index_test_excl_duration_covariate" in m:
            excl = m["concordance_index_test_excl_duration_covariate"]
            ablation_note = (
                "\n**Interpretive note, not a leakage concern:** `original_duration_months` "
                "is a legitimate at-sanction covariate, but absolute months-to-completion is "
                "mechanically dominated by a project's planned SCALE — a 200-month project "
                f"takes longer in absolute terms than a 20-month one almost regardless of "
                f"relative overrun risk. Concordance drops from **{m['concordance_index_test']:.4f}** "
                f"to **{excl:.4f}** when that one covariate is excluded, showing how much of the "
                "headline number is \"the model knows the project's size\" rather than genuine "
                "risk discrimination. This is exactly why `y_time_overrun`/`time_overrun_months` "
                "(relative to plan) are the harder, more decision-relevant Phase 4 targets, not "
                "raw time-to-completion.\n"
            )
        (cards_dir / f"{model_name}.md").write_text(
            f"# Model Card — {title}: time-to-commissioning\n\n"
            "**Task:** survival analysis on `months_to_completion`, right-censored for "
            "still-ongoing projects. Project grain (one row per project), static "
            "covariates only (sector, cost_band, funding_mode, original_cost_cr, "
            "original_duration_months).\n\n"
            f"**Evaluation:** temporal split, sanctioned before {m['cut_year']} = train, "
            "on/after = test — the honest simulation-of-deployment backtest (PRD §6.2.2).\n\n"
            f"| Metric | Value |\n|---|---|\n"
            f"| Concordance index (train) | {m['concordance_index_train']:.4f} |\n"
            f"| Concordance index (test) | {m['concordance_index_test']:.4f} |\n"
            f"| n train / events | {m['n_train']:,} / {m['n_events_train']:,} |\n"
            f"| n test / events | {m['n_test']:,} / {m['n_events_test']:,} |\n"
            f"{ablation_note}",
            encoding="utf-8",
        )


def main() -> None:
    features_df = load_processed_features()
    projects_df = load_processed_projects()

    print("Fitting naive / OLS / logistic baselines (OOF via GroupKFold)...")
    results = run_all_baselines(features_df)

    print("Fitting Weibull AFT / Cox PH survival models (temporal split)...")
    results.update(run_survival_models(projects_df))

    config.ARTIFACTS_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.ARTIFACTS_METRICS_DIR / "baselines.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    _write_model_cards(results, config.ARTIFACTS_METRICS_CARDS_DIR)

    _print_summary_table(results)
    print(f"\nWrote {config.ARTIFACTS_METRICS_DIR / 'baselines.json'}")
    print(f"Wrote model cards to {config.ARTIFACTS_METRICS_CARDS_DIR}")


if __name__ == "__main__":
    main()
