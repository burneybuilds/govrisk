#!/usr/bin/env python
"""Generate the synthetic CUF panel and write it to data/processed/.

Usage: python scripts/run_generate.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paimana import config  # noqa: E402
from paimana.data.loader import load_panel  # noqa: E402


def main() -> None:
    print(f"Generating synthetic panel (seed={config.RANDOM_SEED}, n_projects={config.N_PROJECTS})...")
    projects, panel = load_panel(source="synthetic")

    config.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    projects.to_parquet(config.PROJECTS_PARQUET, index=False)
    panel.to_parquet(config.PANEL_PARQUET, index=False)

    print(f"projects: {projects.shape[0]:,} rows x {projects.shape[1]} cols -> {config.PROJECTS_PARQUET}")
    print(f"panel:    {panel.shape[0]:,} rows x {panel.shape[1]} cols -> {config.PANEL_PARQUET}")
    print(f"unique projects in panel: {panel['project_id'].nunique():,}")
    print(f"censored (ongoing) share: {(projects['is_censored'] == True).mean():.1%}")  # noqa: E712


if __name__ == "__main__":
    main()
