"""Data source adapter — PRD §4.3.4.

`load_panel()` is the one switch between synthetic and real CUF data. The
"real" branch is intentionally unimplemented: it names exactly the columns
a real extract must provide (the §5 contract) so a reviewer can see the
socket a genuine CUF export would plug into, rather than the switch being
hidden or absent.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd

from paimana import config
from paimana.data import schema
from paimana.data.generator import generate_synthetic_panel

SourceType = Literal["synthetic", "real"]


def load_panel(source: SourceType = "synthetic") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load (projects, panel) dataframes from the requested source.

    Returns
    -------
    projects : pd.DataFrame
        One row per project: static attributes (§5.2) + terminal targets (§5.4).
    panel : pd.DataFrame
        One row per project-quarter snapshot: static + time-varying (§5.3) +
        terminal targets (§5.4) joined back on. Terminal targets are FORBIDDEN
        as model features — see `features/leakage.py` (Phase 2).
    """
    if source == "synthetic":
        generated = generate_synthetic_panel()
        return generated.projects, generated.panel
    if source == "real":
        raise NotImplementedError(
            "Real CUF data adapter not yet implemented. To wire it up, provide a "
            "loader that returns two DataFrames matching the schema in "
            "paimana.data.schema:\n"
            f"  projects: {list(schema.STATIC_COLUMNS)} + {list(schema.TARGET_COLUMNS)}\n"
            f"  panel:    {list(schema.ALL_PANEL_COLUMNS)}\n"
            "at grain: one row per project x one quarter-end snapshot (PRD §5.1)."
        )
    raise ValueError(f"Unknown source: {source!r}. Expected 'synthetic' or 'real'.")


def load_processed_panel() -> pd.DataFrame:
    """Read the already-generated panel from disk (fast path for downstream
    phases that don't need to regenerate data)."""
    if not config.PANEL_PARQUET.exists():
        raise FileNotFoundError(
            f"{config.PANEL_PARQUET} not found. Run `python scripts/run_generate.py` first."
        )
    return pd.read_parquet(config.PANEL_PARQUET)


def load_processed_projects() -> pd.DataFrame:
    """Read the already-generated project-level table from disk."""
    if not config.PROJECTS_PARQUET.exists():
        raise FileNotFoundError(
            f"{config.PROJECTS_PARQUET} not found. Run `python scripts/run_generate.py` first."
        )
    return pd.read_parquet(config.PROJECTS_PARQUET)


def load_processed_features() -> pd.DataFrame:
    """Read the already-built feature table from disk (Phase 2+)."""
    if not config.FEATURES_PARQUET.exists():
        raise FileNotFoundError(
            f"{config.FEATURES_PARQUET} not found. Run `python scripts/run_features.py` first."
        )
    return pd.read_parquet(config.FEATURES_PARQUET)
