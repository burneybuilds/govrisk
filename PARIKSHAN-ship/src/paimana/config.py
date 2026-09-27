"""Central configuration: paths, seeds, calibration anchors, risk weights.

PRD reference: §4.4 (Calibration anchors), §6.7 (Risk score weights).
No magic numbers belong in pipeline logic — they belong here, named, with
their provenance recorded. Anchors marked ASSUMPTION are unverified against
the current published PAIMANA Flash Report (see PRD Open Item O-1) and must
be treated as adjustable parameters, not facts.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Final

# --------------------------------------------------------------------------
# Reproducibility
# --------------------------------------------------------------------------
RANDOM_SEED: Final[int] = 42

# "Today" for the simulation — the point at which any project not yet
# completed is right-censored. Fixed (not datetime.today()) so a re-run
# months from now reproduces the exact same dataset.
SIMULATION_TODAY: Final[date] = date(2026, 9, 12)

# --------------------------------------------------------------------------
# Paths (all relative to repo root; pathlib everywhere, no string concat)
# --------------------------------------------------------------------------
REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]

DATA_DIR: Final[Path] = REPO_ROOT / "data"
DATA_RAW_DIR: Final[Path] = DATA_DIR / "raw"
DATA_INTERIM_DIR: Final[Path] = DATA_DIR / "interim"
DATA_PROCESSED_DIR: Final[Path] = DATA_DIR / "processed"

ARTIFACTS_DIR: Final[Path] = REPO_ROOT / "artifacts"
ARTIFACTS_MODELS_DIR: Final[Path] = ARTIFACTS_DIR / "models"
ARTIFACTS_METRICS_DIR: Final[Path] = ARTIFACTS_DIR / "metrics"
ARTIFACTS_METRICS_CARDS_DIR: Final[Path] = ARTIFACTS_METRICS_DIR / "cards"
ARTIFACTS_FIGURES_DIR: Final[Path] = ARTIFACTS_DIR / "figures"

DOCS_DIR: Final[Path] = REPO_ROOT / "docs"

PANEL_PARQUET: Final[Path] = DATA_PROCESSED_DIR / "panel.parquet"
PROJECTS_PARQUET: Final[Path] = DATA_PROCESSED_DIR / "projects.parquet"
FEATURES_PARQUET: Final[Path] = DATA_PROCESSED_DIR / "features.parquet"
RISK_SCORES_PARQUET: Final[Path] = DATA_PROCESSED_DIR / "risk_scores.parquet"
ALERTS_PARQUET: Final[Path] = DATA_PROCESSED_DIR / "alerts.parquet"

# --------------------------------------------------------------------------
# Portfolio structure (GIVEN — from the MoSPI problem statement, not assumed)
# --------------------------------------------------------------------------
N_PROJECTS: Final[int] = 1_981
N_SECTORS: Final[int] = 22
COST_THRESHOLD_CR: Final[float] = 150.0  # Rs crore; projects below this are out of PAIMANA scope

SECTORS: Final[list[str]] = [
    "Railways", "Road Transport & Highways", "Petroleum", "Power", "Coal",
    "Atomic Energy", "Civil Aviation", "Telecommunications", "Steel", "Mines",
    "Shipping & Ports", "Water Resources", "Health & Family Welfare",
    "Urban Development", "Fertilizers", "Chemicals & Petrochemicals",
    "Heavy Industries", "Defence", "Higher Education",
    "Information & Broadcasting", "Textiles", "Food & Public Distribution",
]
assert len(SECTORS) == N_SECTORS, "SECTORS list must match N_SECTORS (PRD §5.2)"

STATES: Final[list[str]] = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal", "Andaman & Nicobar Islands", "Chandigarh",
    "Dadra & Nagar Haveli and Daman & Diu", "Delhi", "Jammu & Kashmir",
    "Ladakh", "Lakshadweep", "Puducherry",
]

FUNDING_MODES: Final[list[str]] = ["Budgetary", "IEBR", "EAP", "PPP"]
AGENCY_TYPES: Final[list[str]] = ["CPSU", "Department", "JV", "SPV"]
COST_BANDS: Final[list[str]] = ["150-500", "500-1000", "1000-5000", ">5000"]

DELAY_REASONS: Final[list[str]] = [
    "land_acquisition", "forest_env_clearance", "funds_constraint",
    "contractor_issues", "tendering_delay", "litigation", "r_and_r",
    "law_and_order", "geological_surprise", "equipment_supply",
    "statutory_clearance", "force_majeure",
]

# --------------------------------------------------------------------------
# Calibration anchors — PRD §4.4. ASSUMPTION unless flagged GIVEN.
# Sourced from indicative public commentary on MoSPI infrastructure
# monitoring reports; NOT verified against a specific dated Flash Report.
# See PRD Open Item O-1. Change these in one place to re-calibrate.
# --------------------------------------------------------------------------
ANCHOR_N_PROJECTS: Final[int] = N_PROJECTS  # GIVEN
ANCHOR_N_SECTORS: Final[int] = N_SECTORS  # GIVEN
ANCHOR_COST_THRESHOLD_CR: Final[float] = COST_THRESHOLD_CR  # GIVEN

ANCHOR_SHARE_COST_OVERRUN: Final[float] = 0.20  # ASSUMPTION — verify (O-1)
ANCHOR_SHARE_TIME_OVERRUN: Final[float] = 0.40  # ASSUMPTION — verify (O-1)
ANCHOR_AGGREGATE_COST_OVERRUN_PCT: Final[float] = 20.0  # ASSUMPTION — verify (O-1)
ANCHOR_SHARE_ONGOING_CENSORED: Final[float] = 0.35  # ASSUMPTION — still-executing projects

# Tolerance band for validate.py's aggregate-fidelity check (relative, e.g.
# 0.20 means generated value must fall within +/-20% of the anchor).
ANCHOR_TOLERANCE: Final[float] = 0.25

# --------------------------------------------------------------------------
# Panel generation parameters
# --------------------------------------------------------------------------
PANEL_START_YEAR: Final[int] = 2006  # ~two decades of history per problem statement
PANEL_END_YEAR: Final[int] = 2026
MISSINGNESS_RATE_MIN: Final[float] = 0.05
MISSINGNESS_RATE_MAX: Final[float] = 0.12
REGIME_SHIFT_YEAR: Final[int] = 2020  # global disruption window (generic, not COVID-specific claim)
REGIME_SHIFT_DURATION_QUARTERS: Final[int] = 8

# --------------------------------------------------------------------------
# Target definitions (PRD §5.4)
# --------------------------------------------------------------------------
COST_OVERRUN_CLASSIFICATION_THRESHOLD_PCT: Final[float] = 10.0
TIME_OVERRUN_CLASSIFICATION_THRESHOLD_MONTHS: Final[float] = 6.0
SEVERE_COST_OVERRUN_THRESHOLD_PCT: Final[float] = 25.0
SEVERE_TIME_OVERRUN_THRESHOLD_MONTHS: Final[float] = 24.0

# --------------------------------------------------------------------------
# Risk score weights — PRD §6.7. A policy choice, displayed in the UI.
# --------------------------------------------------------------------------
RISK_WEIGHT_P_COST_OVERRUN: Final[float] = 0.35
RISK_WEIGHT_P_TIME_OVERRUN: Final[float] = 0.35
RISK_WEIGHT_MAGNITUDE: Final[float] = 0.15
RISK_WEIGHT_MOMENTUM: Final[float] = 0.15
assert abs(
    RISK_WEIGHT_P_COST_OVERRUN
    + RISK_WEIGHT_P_TIME_OVERRUN
    + RISK_WEIGHT_MAGNITUDE
    + RISK_WEIGHT_MOMENTUM
    - 1.0
) < 1e-9, "Risk weights must sum to 1.0 (PRD §6.7)"

RISK_BAND_GREEN_MAX: Final[int] = 39
RISK_BAND_AMBER_MAX: Final[int] = 69
# Red band is anything above RISK_BAND_AMBER_MAX, up to 100.

# Normalisation caps for the risk score's "magnitude" term (PRD §6.7): a
# predicted overrun at or beyond these caps is treated as maximally risky
# (normalised to 1.0). Chosen as multiples of the SEVERE_* thresholds above
# so the whole risk-score policy is internally consistent and auditable
# from one file, not two unrelated constants.
RISK_MAGNITUDE_COST_CAP_PCT: Final[float] = 4 * SEVERE_COST_OVERRUN_THRESHOLD_PCT  # 100%
RISK_MAGNITUDE_TIME_CAP_MONTHS: Final[float] = 2 * SEVERE_TIME_OVERRUN_THRESHOLD_MONTHS  # 48 months

# Momentum-term caps (PRD §6.7's "stall + velocity_ratio shortfall"): a
# project stalled this many consecutive quarters is treated as maximally
# risky on that component, independent of the velocity-ratio component.
RISK_MOMENTUM_STALL_CAP_QUARTERS: Final[int] = 4

# Early-warning rule thresholds (PRD §6.8) — named constants so a judge (or
# a future tuning pass) can see and defend every trigger value in one place.
EW_VELOCITY_RATIO_THRESHOLD: Final[float] = 0.5
EW_PROGRESS_GAP_THRESHOLD_PP: Final[float] = 20.0
EW_STALLED_QUARTERS_THRESHOLD: Final[int] = 3
EW_RISK_SCORE_RED_THRESHOLD: Final[int] = 70
EW_RISK_SCORE_RISE_THRESHOLD: Final[int] = 15
EW_LATE_ELAPSED_FRAC_THRESHOLD: Final[float] = 0.8
EW_LATE_PHYSICAL_PROGRESS_THRESHOLD_PCT: Final[float] = 60.0
EW_MANY_REASONS_THRESHOLD: Final[int] = 3
EW_MANY_REVISIONS_THRESHOLD: Final[int] = 2

# Lead-time backtest (PRD §7/Phase 5 task 4): an alert firing at least this
# many quarters before actual completion counts as "caught early enough to
# act on."
BACKTEST_MIN_LEAD_QUARTERS: Final[int] = 4

# --------------------------------------------------------------------------
# Model sanity gates (PRD §4.3.5) — a model exceeding these is treated as a
# leakage bug, not a success, and the run must fail.
# --------------------------------------------------------------------------
MAX_PLAUSIBLE_R2: Final[float] = 0.85
MAX_PLAUSIBLE_PR_AUC: Final[float] = 0.95
