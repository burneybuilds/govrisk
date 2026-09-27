"""The CUF (Common Upload Form) data contract — PRD §5.

This module is the SINGLE SOURCE OF TRUTH for column names and row grain
across the entire pipeline. `generator.py`, `features/build.py`,
`features/leakage.py`, and every model module import column-name lists
from here rather than re-typing string literals — a typo in a column name
should be a single edit here, not a hunt across a dozen files.

Grain (PRD §5.1): one row = one project x one quarter-end snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from paimana import config

# --------------------------------------------------------------------------
# Enums (functional API keeps these in lockstep with config.py lists)
# --------------------------------------------------------------------------
Sector = Enum("Sector", {s.upper().replace(" ", "_").replace("&", "AND"): s for s in config.SECTORS})
FundingMode = Enum("FundingMode", {m.upper(): m for m in config.FUNDING_MODES})
AgencyType = Enum("AgencyType", {a.upper(): a for a in config.AGENCY_TYPES})
CostBand = Enum("CostBand", {c.upper().replace(">", "GT").replace("-", "_"): c for c in config.COST_BANDS})
DelayReason = Enum("DelayReason", {r.upper(): r for r in config.DELAY_REASONS})

# --------------------------------------------------------------------------
# Column name contracts (PRD §5.2 - §5.4)
# --------------------------------------------------------------------------
STATIC_COLUMNS: tuple[str, ...] = (
    "project_id",
    "project_name",
    "ministry",
    "sector",
    "state",
    "is_multi_state",
    "implementing_agency_type",
    "agency_id",
    "original_cost_cr",
    "sanction_date",
    "original_doc",
    "original_duration_months",
    "funding_mode",
    "cost_band",
)

SNAPSHOT_KEY_COLUMNS: tuple[str, ...] = ("project_id", "as_of_date")

SNAPSHOT_COLUMNS: tuple[str, ...] = (
    "as_of_date",
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
    *(f"reason_{r}" for r in config.DELAY_REASONS),
    "n_reasons_active",
    "revisions_to_date",
    "months_since_last_revision",
)

# Terminal outcome columns, joined back onto every snapshot of a project.
# These are exactly the columns that must NEVER enter a training feature
# matrix (see features/leakage.py, built in Phase 2) — as-of-t features
# only. Listed here because they are part of the data contract; the
# enforcement mechanism lives in Phase 2.
TARGET_COLUMNS: tuple[str, ...] = (
    "final_cost_cr",
    "final_doc",
    "cost_overrun_pct",
    "y_cost_overrun",
    "time_overrun_months",
    "y_time_overrun",
    "y_severe",
    "months_to_completion",
    "is_censored",
    "project_status",
)

ALL_PANEL_COLUMNS: tuple[str, ...] = STATIC_COLUMNS + SNAPSHOT_COLUMNS + TARGET_COLUMNS


# --------------------------------------------------------------------------
# Typed row contracts (used by the generator for construction & by tests
# for round-trip validation; pandas/parquet remains the runtime storage)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class StaticProjectAttributes:
    """Fields known at sanction — PRD §5.2. One instance per project."""

    project_id: str
    project_name: str
    ministry: str
    sector: str
    state: str
    is_multi_state: bool
    implementing_agency_type: str
    agency_id: str
    original_cost_cr: float
    sanction_date: date
    original_doc: date
    original_duration_months: int
    funding_mode: str
    cost_band: str


@dataclass(frozen=True)
class PanelSnapshot:
    """A single project-quarter observation — PRD §5.3."""

    project_id: str
    as_of_date: date
    elapsed_months: int
    elapsed_frac: float
    physical_progress_pct: float
    expenditure_to_date_cr: float
    financial_progress_pct: float
    progress_velocity_3q: float
    progress_gap_pp: float
    required_velocity: float
    velocity_ratio: float
    stalled_quarters: int
    reason_flags: dict[str, bool] = field(default_factory=dict)
    n_reasons_active: int = 0
    revisions_to_date: int = 0
    months_since_last_revision: int = 0


@dataclass(frozen=True)
class ProjectOutcome:
    """Terminal outcome for a project — PRD §5.4. FORBIDDEN as model input."""

    project_id: str
    final_cost_cr: float
    final_doc: date | None
    cost_overrun_pct: float
    y_cost_overrun: bool
    time_overrun_months: float
    y_time_overrun: bool
    y_severe: bool
    months_to_completion: float
    is_censored: bool
    project_status: str
