#!/usr/bin/env python
"""Build the leakage-safe as-of-t feature table and write it to disk.

Usage: python scripts/run_features.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paimana import config  # noqa: E402
from paimana.data.loader import load_processed_panel, load_processed_projects  # noqa: E402
from paimana.features.build import build_feature_table, select_features  # noqa: E402


def main() -> None:
    panel = load_processed_panel()
    projects = load_processed_projects()
    print(f"loaded panel: {panel.shape[0]:,} rows x {panel.shape[1]} cols")

    features_df = build_feature_table(panel, projects)

    config.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    features_df.to_parquet(config.FEATURES_PARQUET, index=False)
    print(
        f"features: {features_df.shape[0]:,} rows x {features_df.shape[1]} cols "
        f"-> {config.FEATURES_PARQUET}"
    )

    X = select_features(features_df)
    print(f"model-ready X: {X.shape[0]:,} rows x {X.shape[1]} feature cols (leakage check passed)")

    with_track_record = (features_df["agency_prior_completed_count"] > 0).sum()
    print(f"rows with at least one prior agency completion on record: {with_track_record:,}")


if __name__ == "__main__":
    main()
