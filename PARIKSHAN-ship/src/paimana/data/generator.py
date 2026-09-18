"""Synthetic CUF panel generator — PRD §4, §5, Phase 1 task 5.

Generates a defensible, honestly-labelled synthetic dataset that mirrors the
real Common Upload Form (CUF) schema and is calibrated to the aggregate
statistics documented in `config.py` (§4.4 anchors). See
`docs/DATA_METHODOLOGY.md` for the full generative methodology and every
assumption made here.

Design principle (PRD §4.3.5): the simulation must NOT be trivially
learnable. Outcomes are driven by latent sector/agency/project effects plus
substantial idiosyncratic noise, so no downstream model can approach a
deterministic fit. A model that does is treated as a leakage bug (Phase 4
sanity gate), not a success.

Censoring (~35% of the portfolio, PRD §4.4) arises NATURALLY here, not from
an artificial coin-flip: every project's true completion date is simulated,
and a project is right-censored if that true date falls after
`config.SIMULATION_TODAY`. This is the correct mechanism for survival
analysis and is what makes recently-sanctioned projects disproportionately
likely to be "ongoing" — exactly as in the real portfolio.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from paimana import config
from paimana.data import schema

# --------------------------------------------------------------------------
# Small date helpers (stdlib only — no dateutil dependency)
# --------------------------------------------------------------------------


def _add_months(d: date, months: int) -> date:
    """Return `d` shifted by `months`, clamping the day to the target month."""
    total = d.month - 1 + months
    year = d.year + total // 12
    month = total % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _months_between(start: date, end: date) -> int:
    """Whole calendar months between two dates (end - start), day-adjusted."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return months


# --------------------------------------------------------------------------
# Sector-level shaping — makes projects look like their real-world sectors
# rather than uniform random noise. Values are illustrative synthetic
# calibration knobs, not sourced statistics (see DATA_METHODOLOGY.md).
# --------------------------------------------------------------------------

# (relative sampling weight, cost scale in Rs crore for lognormal median,
#  typical duration in months for lognormal median, multi-state probability,
#  baseline sector risk in [-1, 1])
_SECTOR_PROFILE: dict[str, tuple[float, float, float, float, float]] = {
    "Railways": (1.6, 900, 60, 0.55, 0.55),
    "Road Transport & Highways": (1.8, 700, 42, 0.60, 0.45),
    "Power": (1.3, 1400, 54, 0.20, 0.35),
    "Petroleum": (0.7, 2200, 48, 0.10, 0.10),
    "Coal": (0.6, 600, 40, 0.10, 0.30),
    "Atomic Energy": (0.3, 3500, 96, 0.05, 0.40),
    "Civil Aviation": (0.5, 800, 45, 0.15, 0.20),
    "Telecommunications": (0.7, 500, 30, 0.30, -0.10),
    "Steel": (0.5, 1200, 42, 0.05, 0.15),
    "Mines": (0.4, 450, 36, 0.10, 0.20),
    "Shipping & Ports": (0.6, 650, 42, 0.15, 0.25),
    "Water Resources": (0.9, 550, 54, 0.35, 0.50),
    "Health & Family Welfare": (0.6, 300, 30, 0.05, -0.05),
    "Urban Development": (0.9, 400, 36, 0.10, 0.15),
    "Fertilizers": (0.4, 900, 42, 0.05, 0.05),
    "Chemicals & Petrochemicals": (0.4, 800, 40, 0.05, 0.05),
    "Heavy Industries": (0.4, 600, 40, 0.05, 0.10),
    "Defence": (0.7, 1500, 60, 0.10, 0.30),
    "Higher Education": (0.5, 250, 30, 0.05, -0.10),
    "Information & Broadcasting": (0.3, 200, 24, 0.05, -0.15),
    "Textiles": (0.3, 250, 30, 0.05, 0.00),
    "Food & Public Distribution": (0.4, 300, 30, 0.10, 0.00),
}
assert set(_SECTOR_PROFILE) == set(config.SECTORS)

_FUNDING_MODE_WEIGHTS: dict[str, float] = {
    "Budgetary": 0.45,
    "IEBR": 0.30,
    "EAP": 0.10,
    "PPP": 0.15,
}

_AGENCY_TYPE_WEIGHTS: dict[str, float] = {
    "CPSU": 0.40,
    "Department": 0.35,
    "JV": 0.10,
    "SPV": 0.15,
}

# Base per-quarter onset probability for each delay reason (before the
# project's risk propensity multiplier is applied).
_REASON_BASE_ONSET_PROB: dict[str, float] = {
    "land_acquisition": 0.045,
    "forest_env_clearance": 0.030,
    "funds_constraint": 0.035,
    "contractor_issues": 0.040,
    "tendering_delay": 0.025,
    "litigation": 0.020,
    "r_and_r": 0.020,
    "law_and_order": 0.012,
    "geological_surprise": 0.010,
    "equipment_supply": 0.025,
    "statutory_clearance": 0.028,
    "force_majeure": 0.008,
}
_REASON_RESOLVE_PROB = 0.35  # per-quarter probability an active reason resolves

N_AGENCIES_PER_SECTOR = 6

# Global stretch applied to the per-sector duration medians in
# _SECTOR_PROFILE (see its use in _sample_static_attributes for why).
_DURATION_SCALE_MULT = 1.75


@dataclass(frozen=True)
class GeneratedPanel:
    """Container for the two output tables of the synthetic generator."""

    projects: pd.DataFrame
    panel: pd.DataFrame


def _sample_static_attributes(rng: np.random.Generator, n_projects: int) -> pd.DataFrame:
    """Sample static project attributes with sector-conditioned realism (PRD §5.2)."""
    sectors = list(_SECTOR_PROFILE)
    weights = np.array([_SECTOR_PROFILE[s][0] for s in sectors])
    weights = weights / weights.sum()
    sector_choices = rng.choice(sectors, size=n_projects, p=weights)

    # Agencies: a fixed pool per sector so agency-level latent skill is
    # persistent and meaningful (agencies specialise by sector).
    agency_pool: dict[str, list[str]] = {
        s: [f"AGY-{s[:3].upper()}-{i:02d}" for i in range(N_AGENCIES_PER_SECTOR)] for s in sectors
    }

    rows = []
    for i in range(n_projects):
        sector = sector_choices[i]
        _, cost_scale, dur_scale, multi_state_p, _risk = _SECTOR_PROFILE[sector]

        original_cost_cr = float(
            np.clip(rng.lognormal(mean=np.log(cost_scale), sigma=0.65), config.COST_THRESHOLD_CR, 50_000)
        )
        # _DURATION_SCALE_MULT stretches the illustrative per-sector medians
        # above: large sanctioned infrastructure programmes routinely run
        # 5-8+ years end to end, and longer per-project histories are also
        # what give the panel enough quarterly depth for genuine time-series
        # modelling (PRD §5.1 expects tens of thousands of panel rows).
        original_duration_months = int(
            np.clip(
                round(rng.lognormal(mean=np.log(dur_scale * _DURATION_SCALE_MULT), sigma=0.35)), 18, 260
            )
        )

        # Sanction dates spread across ~two decades, skewed toward more
        # recent years so that a realistic ~35% of the portfolio is still
        # genuinely mid-execution as of SIMULATION_TODAY (right-censored),
        # while enough early-sanctioned projects have completed histories
        # to support the full two-decade methodology narrative.
        span_days = (date(config.PANEL_END_YEAR - 1, 1, 1) - date(config.PANEL_START_YEAR, 1, 1)).days
        offset_days = int(rng.beta(a=1.8, b=1.6) * span_days)
        sanction_date = date(config.PANEL_START_YEAR, 1, 1)
        sanction_date = _add_months(sanction_date, 0)
        sanction_date = date.fromordinal(sanction_date.toordinal() + offset_days)

        original_doc = _add_months(sanction_date, original_duration_months)

        is_multi_state = bool(rng.random() < multi_state_p)
        state = rng.choice(config.STATES)
        agency_id = rng.choice(agency_pool[sector])
        agency_type = rng.choice(
            list(_AGENCY_TYPE_WEIGHTS), p=list(_AGENCY_TYPE_WEIGHTS.values())
        )
        funding_mode = rng.choice(
            list(_FUNDING_MODE_WEIGHTS), p=list(_FUNDING_MODE_WEIGHTS.values())
        )

        if original_cost_cr < 500:
            cost_band = "150-500"
        elif original_cost_cr < 1000:
            cost_band = "500-1000"
        elif original_cost_cr < 5000:
            cost_band = "1000-5000"
        else:
            cost_band = ">5000"

        rows.append(
            {
                "project_id": f"PRJ-{i + 1:05d}",
                "project_name": f"{sector} Infrastructure Project {i + 1:05d}",
                "ministry": f"Ministry of {sector}",
                "sector": sector,
                "state": state,
                "is_multi_state": is_multi_state,
                "implementing_agency_type": agency_type,
                "agency_id": agency_id,
                "original_cost_cr": round(original_cost_cr, 2),
                "sanction_date": sanction_date,
                "original_doc": original_doc,
                "original_duration_months": original_duration_months,
                "funding_mode": funding_mode,
                "cost_band": cost_band,
            }
        )

    df = pd.DataFrame(rows)
    assert list(df.columns) == list(schema.STATIC_COLUMNS)
    return df


def _sample_latent_effects(
    rng: np.random.Generator, projects: pd.DataFrame
) -> tuple[dict[str, float], dict[str, float], np.ndarray]:
    """Sector, agency, and per-project idiosyncratic latent risk effects.

    Returned project-level risk propensity is squashed to (0, 1) via a
    logistic transform and is the single scalar that drives delay-onset
    hazard and eventual overrun magnitude for that project.
    """
    sector_latent = {s: _SECTOR_PROFILE[s][4] + rng.normal(0, 0.15) for s in _SECTOR_PROFILE}
    agency_ids = sorted(projects["agency_id"].unique())
    agency_latent = {a: rng.normal(0, 0.35) for a in agency_ids}
    project_noise = rng.normal(0, 0.6, size=len(projects))

    raw = (
        projects["sector"].map(sector_latent).to_numpy() * 0.55
        + projects["agency_id"].map(agency_latent).to_numpy() * 0.45
        + project_noise
    )
    risk_propensity = 1.0 / (1.0 + np.exp(-raw))  # logistic squash to (0, 1)
    return sector_latent, agency_latent, risk_propensity


def _simulate_project_panel(
    rng: np.random.Generator,
    project: pd.Series,
    risk_propensity: float,
    cost_risk_percentile: float,
) -> tuple[list[dict], dict]:
    """Simulate one project's full quarterly history through TRUE completion.

    Returns (list of raw snapshot dicts, true-outcome dict). Snapshots run
    through the project's true simulated completion regardless of
    `SIMULATION_TODAY` — censoring truncation is applied by the caller so the
    "true" generative process stays independent of the cutoff date.
    """
    original_cost_cr = float(project["original_cost_cr"])
    original_duration_months = int(project["original_duration_months"])
    sanction_date: date = project["sanction_date"]

    required_rate_per_quarter = 100.0 / max(original_duration_months / 3.0, 1.0)

    physical = 0.0
    active_reasons: set[str] = set()
    stalled_quarters = 0
    revisions_to_date = 0
    months_since_last_revision = 0
    velocity_history: list[float] = []

    horizon_months = min(int(original_duration_months * 3.2), 340)
    n_quarters_horizon = max(horizon_months // 3, 4)

    records: list[dict] = []
    completion_month: int | None = None

    for k in range(1, n_quarters_horizon + 1):
        elapsed_months = 3 * k
        as_of_date = _add_months(sanction_date, elapsed_months)
        elapsed_frac = elapsed_months / original_duration_months

        # Regime shift: a universal, non-project-specific velocity penalty
        # applied to every active project during the disruption window.
        shift_start = date(config.REGIME_SHIFT_YEAR, 1, 1)
        shift_end = _add_months(shift_start, 3 * config.REGIME_SHIFT_DURATION_QUARTERS)
        regime_mult = 0.75 if shift_start <= as_of_date < shift_end else 1.0

        # Stochastic delay-reason onset/resolution.
        for reason in config.DELAY_REASONS:
            if reason in active_reasons:
                if rng.random() < _REASON_RESOLVE_PROB:
                    active_reasons.discard(reason)
            else:
                # Centred so an average-risk project (risk_propensity ~ 0.5)
                # sees roughly baseline onset rates; only genuinely high-risk
                # projects accumulate materially more concurrent reasons.
                onset_prob = _REASON_BASE_ONSET_PROB[reason] * (0.3 + 1.4 * risk_propensity)
                if rng.random() < onset_prob:
                    active_reasons.add(reason)
        n_reasons_active = len(active_reasons)
        reason_penalty = 1.0 - min(0.85, 0.14 * n_reasons_active)

        # Bell-shaped construction-phase multiplier (slow-fast-slow S-curve).
        # `phase_p` is FROZEN at 1.0 once a project passes its original
        # planned duration — using uncapped elapsed_frac here would drive
        # this bell curve negative past the deadline, collapsing velocity
        # toward zero and creating a runaway "never finishes" spiral for any
        # project even slightly behind at its deadline. Freezing means a
        # delayed project keeps a sustained (floor 0.55x) closing-out pace
        # instead, which is what lets it actually complete.
        phase_p = min(elapsed_frac, 1.0)
        phase_mult = 0.55 + 0.85 * 4.0 * phase_p * (1.0 - phase_p)

        noise = float(rng.normal(1.0, 0.18))
        velocity = required_rate_per_quarter * phase_mult * reason_penalty * regime_mult * max(noise, 0.0)
        velocity = max(velocity, 0.0)
        physical = float(np.clip(physical + velocity, 0.0, 100.0))

        velocity_history.append(velocity)
        velocity_3q = float(np.mean(velocity_history[-3:]))

        if velocity < 0.5:
            stalled_quarters += 1
        else:
            stalled_quarters = 0

        # Financial progress frontloads relative to physical progress; the
        # gap is the classic early leading indicator of trouble. Nonlinear
        # in risk_propensity (not linear) so the portfolio is right-skewed
        # the way real overrun distributions are: most projects cluster
        # near their plan, a high-risk minority frontloads heavily and
        # drags the aggregate mean up.
        gap = -8.0 + 30.0 * (risk_propensity**2.2) + float(rng.normal(0, 3.0))
        financial = float(np.clip(physical + gap, 0.0, 135.0))
        expenditure_to_date_cr = round(financial / 100.0 * original_cost_cr, 2)

        remaining_frac = max(100.0 - physical, 0.0)
        remaining_quarters = max(n_quarters_horizon - k, 1)
        required_velocity = remaining_frac / remaining_quarters if remaining_frac > 0 else 0.01
        velocity_ratio = velocity_3q / required_velocity if required_velocity > 0 else np.nan

        # Formal cost/date revision events — more likely as trouble compounds.
        months_since_last_revision += 3
        revision_prob = 0.02 + 0.10 * risk_propensity * (n_reasons_active > 0)
        if rng.random() < revision_prob:
            revisions_to_date += 1
            months_since_last_revision = 0

        record = {
            "project_id": project["project_id"],
            "as_of_date": as_of_date,
            "elapsed_months": elapsed_months,
            "elapsed_frac": round(elapsed_frac, 4),
            "physical_progress_pct": round(physical, 2),
            "expenditure_to_date_cr": expenditure_to_date_cr,
            "financial_progress_pct": round(financial, 2),
            "progress_velocity_3q": round(velocity_3q, 3),
            "progress_gap_pp": round(financial - physical, 2),
            "required_velocity": round(required_velocity, 3),
            "velocity_ratio": round(velocity_ratio, 3) if not np.isnan(velocity_ratio) else np.nan,
            "stalled_quarters": stalled_quarters,
            **{f"reason_{r}": (r in active_reasons) for r in config.DELAY_REASONS},
            "n_reasons_active": n_reasons_active,
            "revisions_to_date": revisions_to_date,
            "months_since_last_revision": months_since_last_revision,
        }
        records.append(record)

        if physical >= 100.0 and completion_month is None:
            completion_month = elapsed_months
            break

    if completion_month is None:
        completion_month = records[-1]["elapsed_months"] if records else original_duration_months

    final_duration_months = completion_month
    time_overrun_months = float(final_duration_months - original_duration_months)

    # Final cost outcome is DELIBERATELY decoupled from the mid-execution
    # `financial_progress_pct` trail above: the latter is a noisy LEADING
    # INDICATOR feature (a project can look frontloaded and still close out
    # near budget, or vice versa), while this is the terminal ground truth.
    #
    # cost_risk_percentile (this project's RANK within the whole portfolio's
    # risk_propensity, not the raw score) drives a strongly right-skewed
    # outcome: real cost-overrun distributions cluster most projects near
    # zero while a risk-weighted minority blows out to a large multiple of
    # approved cost. Coefficients were fitted by Monte Carlo against the
    # actual generated risk_propensity population to land the portfolio
    # average and the classification-threshold share on the PRD §4.4
    # anchors simultaneously (see HANDOFF.md Phase 1 report) — a single
    # moment (the mean) cannot pin down a skewed distribution's shape.
    systematic_overrun_pct = -10.0 + 600.0 * (cost_risk_percentile**18)
    cost_overrun_pct = round(systematic_overrun_pct + float(rng.normal(0, 6.0)), 2)
    final_cost_cr = round(original_cost_cr * (1.0 + cost_overrun_pct / 100.0), 2)
    final_cost_cr = float(np.clip(final_cost_cr, original_cost_cr * 0.80, original_cost_cr * 6.0))
    cost_overrun_pct = round((final_cost_cr - original_cost_cr) / original_cost_cr * 100.0, 2)

    true_outcome = {
        "project_id": project["project_id"],
        "true_completion_date": _add_months(sanction_date, final_duration_months),
        "final_cost_cr": final_cost_cr,
        "final_duration_months": final_duration_months,
        "cost_overrun_pct": cost_overrun_pct,
        "time_overrun_months": time_overrun_months,
        "revisions_to_date": revisions_to_date,
    }
    return records, true_outcome


def _apply_censoring_and_targets(
    projects: pd.DataFrame,
    all_records: list[dict],
    true_outcomes: list[dict],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Truncate panels at SIMULATION_TODAY for still-ongoing projects and
    attach terminal target columns (masked to NaN where censored)."""
    today = config.SIMULATION_TODAY
    outcomes_by_id = {o["project_id"]: o for o in true_outcomes}

    panel_rows: list[dict] = []
    project_target_rows: list[dict] = []

    records_by_project: dict[str, list[dict]] = {}
    for rec in all_records:
        records_by_project.setdefault(rec["project_id"], []).append(rec)

    for _, project in projects.iterrows():
        pid = project["project_id"]
        outcome = outcomes_by_id[pid]
        is_censored = outcome["true_completion_date"] > today

        recs = records_by_project[pid]
        if is_censored:
            visible_recs = [r for r in recs if r["as_of_date"] <= today]
            if not visible_recs:
                visible_recs = recs[:1]
            months_to_completion = float(_months_between(project["sanction_date"], today))
            target_row = {
                "project_id": pid,
                "final_cost_cr": np.nan,
                "final_doc": pd.NaT,
                "cost_overrun_pct": np.nan,
                "y_cost_overrun": pd.NA,
                "time_overrun_months": np.nan,
                "y_time_overrun": pd.NA,
                "y_severe": pd.NA,
                "months_to_completion": months_to_completion,
                "is_censored": True,
                "project_status": "Ongoing",
            }
        else:
            visible_recs = recs
            final_doc = outcome["true_completion_date"]
            cost_overrun_pct = outcome["cost_overrun_pct"]
            time_overrun_months = outcome["time_overrun_months"]
            target_row = {
                "project_id": pid,
                "final_cost_cr": outcome["final_cost_cr"],
                "final_doc": final_doc,
                "cost_overrun_pct": cost_overrun_pct,
                "y_cost_overrun": bool(cost_overrun_pct > config.COST_OVERRUN_CLASSIFICATION_THRESHOLD_PCT),
                "time_overrun_months": time_overrun_months,
                "y_time_overrun": bool(
                    time_overrun_months > config.TIME_OVERRUN_CLASSIFICATION_THRESHOLD_MONTHS
                ),
                "y_severe": bool(
                    cost_overrun_pct > config.SEVERE_COST_OVERRUN_THRESHOLD_PCT
                    or time_overrun_months > config.SEVERE_TIME_OVERRUN_THRESHOLD_MONTHS
                ),
                "months_to_completion": float(outcome["final_duration_months"]),
                "is_censored": False,
                "project_status": "Completed",
            }

        project_target_rows.append(target_row)
        for rec in visible_recs:
            panel_rows.append({**rec, **target_row})

    targets_df = pd.DataFrame(project_target_rows)
    panel_df = pd.DataFrame(panel_rows)
    return targets_df, panel_df


def _inject_missingness(rng: np.random.Generator, panel: pd.DataFrame) -> pd.DataFrame:
    """Independently null out 5-12% of values in reporting-prone progress
    fields, simulating realistic quarterly non-reporting gaps."""
    panel = panel.copy()
    fields = ["physical_progress_pct", "expenditure_to_date_cr", "financial_progress_pct"]
    for field in fields:
        rate = rng.uniform(config.MISSINGNESS_RATE_MIN, config.MISSINGNESS_RATE_MAX)
        mask = rng.random(len(panel)) < rate
        panel.loc[mask, field] = np.nan
    return panel


def generate_synthetic_panel(
    n_projects: int = config.N_PROJECTS, seed: int = config.RANDOM_SEED
) -> GeneratedPanel:
    """Top-level orchestrator: static attrs -> latents -> quarterly sim ->
    censoring/targets -> missingness. Deterministic for a fixed seed."""
    rng = np.random.default_rng(seed)

    projects = _sample_static_attributes(rng, n_projects)
    _sector_latent, _agency_latent, risk_propensity = _sample_latent_effects(rng, projects)
    # Portfolio-relative rank of each project's risk, used only to shape the
    # terminal cost outcome distribution (see _simulate_project_panel) —
    # keeps the skew calibration robust to the absolute range risk_propensity
    # happens to occupy rather than depending on its raw logistic scale.
    cost_risk_percentile = pd.Series(risk_propensity).rank(pct=True).to_numpy()

    all_records: list[dict] = []
    true_outcomes: list[dict] = []
    for idx, (_, project) in enumerate(projects.iterrows()):
        recs, outcome = _simulate_project_panel(
            rng, project, float(risk_propensity[idx]), float(cost_risk_percentile[idx])
        )
        all_records.extend(recs)
        true_outcomes.append(outcome)

    targets, panel = _apply_censoring_and_targets(projects, all_records, true_outcomes)
    panel = _inject_missingness(rng, panel)

    projects_full = projects.merge(targets, on="project_id", how="left")

    panel = panel.merge(
        projects[list(schema.STATIC_COLUMNS)], on="project_id", how="left", suffixes=("", "_static")
    )
    # Drop duplicate static columns from the record dicts if any crept in.
    panel = panel.loc[:, ~panel.columns.duplicated()]
    # Column order fixed by the schema contract, computed AFTER the merge
    # above so the just-joined static columns are actually present.
    ordered_panel_cols = [c for c in schema.ALL_PANEL_COLUMNS if c in panel.columns]
    panel = panel[ordered_panel_cols]

    return GeneratedPanel(projects=projects_full, panel=panel)
