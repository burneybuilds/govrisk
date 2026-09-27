"""Survival analysis for time-to-commissioning — PRD §6.3.

Unlike the other Phase 3 baselines, this operates at PROJECT grain (one row
per project: `months_to_completion`, `is_censored`, static covariates) —
NOT the quarterly panel. Right-censoring is central here (~1/3 of the
portfolio is still executing), and Weibull AFT / Cox PH are the statistically
correct tools for that: fitting a plain regression on completed-project
durations only would be survivorship bias, silently dropping exactly the
projects most likely to be badly delayed.

Evaluated via a TEMPORAL train/test split (PRD §6.2.2) rather than in-sample
concordance, which would look artificially good — a real deployment only
ever has the past to learn from.
"""

from __future__ import annotations

import pandas as pd
from lifelines import CoxPHFitter, WeibullAFTFitter
from lifelines.utils import concordance_index

from paimana.features.splits import temporal_split

# Static covariates only — no per-quarter panel fields exist at project
# grain, and no high-cardinality identifiers (state, agency_id) that a
# parametric survival model would struggle to fit stably on ~2,000 rows.
SURVIVAL_CATEGORICAL_COVARIATES: tuple[str, ...] = ("sector", "cost_band", "funding_mode")
SURVIVAL_NUMERIC_COVARIATES: tuple[str, ...] = ("original_cost_cr", "original_duration_months")
DURATION_COL = "months_to_completion"
EVENT_COL = "event_observed"  # 1 = completed (event observed), 0 = censored


def _prepare_survival_frame(projects: pd.DataFrame) -> pd.DataFrame:
    """Select covariates + duration/event columns and one-hot encode the
    categoricals (lifelines expects a fully numeric design matrix)."""
    work = projects[
        [
            "project_id",
            "sanction_date",
            DURATION_COL,
            "is_censored",
            *SURVIVAL_CATEGORICAL_COVARIATES,
            *SURVIVAL_NUMERIC_COVARIATES,
        ]
    ].copy()
    work[EVENT_COL] = (~work["is_censored"]).astype(int)
    # lifelines needs a strictly positive duration for the Weibull AFT model.
    work[DURATION_COL] = work[DURATION_COL].clip(lower=0.5)

    encoded = pd.get_dummies(work, columns=list(SURVIVAL_CATEGORICAL_COVARIATES), drop_first=True)
    return encoded


def _predicted_score(model, df: pd.DataFrame, covariate_cols: list[str]):
    """A score where HIGHER means "predicted to survive/take longer" — the
    convention `lifelines.utils.concordance_index` expects.

    Cox PH is a proportional-hazards model: its natural output is a hazard
    ratio, so the score must be NEGATED (higher hazard = shorter survival).
    Numerically integrating Cox's `predict_expectation` is slow and can be
    unstable near the tail of the baseline hazard; ranking by hazard is the
    standard, robust choice for concordance. Weibull AFT's expectation is
    closed-form (no numerical integration), so it's used directly.
    """
    if isinstance(model, CoxPHFitter):
        return -model.predict_partial_hazard(df[covariate_cols]).to_numpy().ravel()
    return model.predict_expectation(df[covariate_cols]).to_numpy().ravel()


def _fit_and_score(
    model, train_df: pd.DataFrame, test_df: pd.DataFrame, model_covariate_cols: list[str]
) -> dict:
    model.fit(
        train_df[[*model_covariate_cols, DURATION_COL, EVENT_COL]],
        duration_col=DURATION_COL,
        event_col=EVENT_COL,
    )

    train_risk = _predicted_score(model, train_df, model_covariate_cols)
    test_risk = _predicted_score(model, test_df, model_covariate_cols)

    train_c = concordance_index(train_df[DURATION_COL], train_risk, train_df[EVENT_COL])
    test_c = concordance_index(test_df[DURATION_COL], test_risk, test_df[EVENT_COL])

    return {
        "concordance_index_train": float(train_c),
        "concordance_index_test": float(test_c),
        "n_train": int(len(train_df)),
        "n_test": int(len(test_df)),
        "n_events_train": int(train_df[EVENT_COL].sum()),
        "n_events_test": int(test_df[EVENT_COL].sum()),
    }


def run_survival_models(projects: pd.DataFrame, cut_year: int = 2018) -> dict:
    """Fit Weibull AFT and Cox PH on a temporal train/test split of the
    project-grain table. Returns {"weibull_aft": {...}, "cox_ph": {...}}."""
    encoded = _prepare_survival_frame(projects)
    covariate_cols = [c for c in encoded.columns if c not in ("project_id", "sanction_date", "is_censored")]
    covariate_cols = [c for c in covariate_cols if c not in (DURATION_COL, EVENT_COL)]
    no_scale_cols = [c for c in covariate_cols if c != "original_duration_months"]

    train_idx, test_idx = temporal_split(projects.reset_index(drop=True), cut_year=cut_year)
    train_df = encoded.iloc[train_idx].reset_index(drop=True)
    test_df = encoded.iloc[test_idx].reset_index(drop=True)

    results = {}

    aft = WeibullAFTFitter(penalizer=0.01)
    results["weibull_aft"] = _fit_and_score(aft, train_df, test_df, covariate_cols)
    results["weibull_aft"]["cut_year"] = cut_year

    cph = CoxPHFitter(penalizer=0.01)
    results["cox_ph"] = _fit_and_score(cph, train_df, test_df, covariate_cols)
    results["cox_ph"]["cut_year"] = cut_year

    # Interpretive ablation, not a leakage check: `original_duration_months`
    # is a legitimate at-sanction covariate, but absolute months-to-completion
    # is mechanically dominated by planned project SCALE (a 200-month project
    # takes longer in absolute terms than a 20-month one almost regardless of
    # relative overrun risk). Reporting concordance without it shows how much
    # of the headline number is "the model knows how big the project is"
    # versus genuine risk discrimination — see the model card for the numbers.
    aft_no_scale = WeibullAFTFitter(penalizer=0.01)
    ablation = _fit_and_score(aft_no_scale, train_df, test_df, no_scale_cols)
    results["weibull_aft"]["concordance_index_test_excl_duration_covariate"] = ablation[
        "concordance_index_test"
    ]

    return results
