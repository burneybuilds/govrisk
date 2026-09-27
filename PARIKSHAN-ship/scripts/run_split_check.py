#!/usr/bin/env python
"""Prove zero project_id leakage across CV folds; report the temporal split.

Usage: python scripts/run_split_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from paimana.data.loader import load_processed_features  # noqa: E402
from paimana.features.build import select_features  # noqa: E402
from paimana.features.splits import (  # noqa: E402
    assert_no_group_overlap,
    grouped_cv,
    horizon_bucket,
    temporal_split,
)


def main() -> None:
    df = load_processed_features()
    # Classification-ready rows only (severe-overrun label requires a
    # completed project) — mirrors how Phase 3/4 will actually consume this.
    labelled = df.dropna(subset=["y_severe"]).reset_index(drop=True)

    X = select_features(labelled)
    y = labelled["y_severe"].astype(int)
    groups = labelled["project_id"]

    print(f"labelled rows: {len(labelled):,} across {groups.nunique():,} projects")
    print("\n--- GroupKFold(project_id, n_splits=5) ---")
    all_ok = True
    for i, (train_idx, test_idx) in enumerate(grouped_cv(X, y, groups, n_splits=5)):
        ok = assert_no_group_overlap(groups.to_numpy(), train_idx, test_idx)
        all_ok = all_ok and ok
        print(f"fold {i}: train={len(train_idx):,} test={len(test_idx):,} fold ok {ok}")

    print("\n--- Temporal split (cut_year=2018) ---")
    train_idx, test_idx = temporal_split(labelled, cut_year=2018)
    print(f"train (sanctioned <2018): {len(train_idx):,} rows")
    print(f"test  (sanctioned >=2018): {len(test_idx):,} rows")

    print("\n--- Horizon buckets ---")
    print(horizon_bucket(labelled["elapsed_frac"]).value_counts().sort_index())

    if not all_ok:
        print("\nFAILED: at least one fold had project_id overlap between train and test.")
        sys.exit(1)
    print("\nAll folds ok: zero project_id overlap between train and test.")


if __name__ == "__main__":
    main()
