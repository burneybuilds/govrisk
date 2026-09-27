#!/usr/bin/env python
"""Build the assistant's project-narrative search index — PRD §3.1/§6.9.

Generates a one-line natural-language narrative per project from already-
cached data (no new facts, nothing an LLM invents) and embeds all ~1,981 of
them ONCE with a local MiniLM model, caching both to disk. This is what
lets the assistant resolve a question like "the fertilizer project in
Kerala that's behind schedule" to a project_id via brute-force numpy
cosine similarity (PRD §3.1 — no vector DB; see Phase 1 HANDOFF.md for why
ChromaDB was dropped) — without ever re-embedding the whole portfolio at
request time.

Usage: python scripts/run_assistant_index.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# sentence_transformers (torch) MUST be imported before numpy/pandas on
# this machine — see paimana/assistant/retriever.py's top-of-file comment
# for the DLL-conflict this avoids. `ruff --fix` WILL alphabetise this back
# to numpy/pandas/sentence_transformers and reintroduce the bug if this
# `noqa: I001` is ever removed and --fix is run on this file — don't.
from sentence_transformers import SentenceTransformer  # noqa: E402, I001

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from paimana import config  # noqa: E402
from paimana.data.loader import load_processed_projects  # noqa: E402

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def _latest_snapshot_per_project(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values("as_of_date").groupby("project_id", as_index=False).last().reset_index(drop=True)


def build_project_narratives(projects: pd.DataFrame, risk: pd.DataFrame) -> pd.DataFrame:
    """One factual sentence per project, built entirely from cached fields
    — a search index, not generated prose from an LLM."""
    latest_risk = _latest_snapshot_per_project(risk).set_index("project_id")

    rows = []
    for _, p in projects.iterrows():
        pid = p["project_id"]
        status = "ongoing" if p["is_censored"] else "completed"
        band = latest_risk.loc[pid, "risk_band"] if pid in latest_risk.index else "unknown"
        narrative = (
            f"{p['project_id']}: a {p['sector']} sector project in {p['state']}, "
            f"implemented by a {p['implementing_agency_type']}, with an approved cost of "
            f"Rs {p['original_cost_cr']:.0f} crore and a planned duration of "
            f"{p['original_duration_months']} months. Funding mode: {p['funding_mode']}. "
            f"Status: {status}, current risk band: {band}."
        )
        rows.append({"project_id": pid, "narrative": narrative})
    return pd.DataFrame(rows)


def main() -> None:
    print("Loading cached project and risk data...")
    projects = load_processed_projects()
    risk = pd.read_parquet(config.RISK_SCORES_PARQUET)

    print("Building project narratives...")
    narratives = build_project_narratives(projects, risk)
    print(f"  built {len(narratives):,} narratives")

    print(f"Loading embedding model ({EMBEDDING_MODEL_NAME})...")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)

    print("Encoding narratives (one-time cost)...")
    embeddings = model.encode(narratives["narrative"].tolist(), show_progress_bar=True, batch_size=64)
    embeddings = np.asarray(embeddings, dtype=np.float32)
    # Pre-normalise so retrieval is a plain dot product (cosine similarity
    # for unit vectors) — cheaper per query than re-normalising every time.
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / np.clip(norms, 1e-8, None)

    config.ARTIFACTS_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    narratives.to_parquet(config.ARTIFACTS_METRICS_DIR / "project_narratives.parquet", index=False)
    np.save(config.ARTIFACTS_METRICS_DIR / "project_narrative_embeddings.npy", embeddings)

    print(f"Wrote project_narratives.parquet and project_narrative_embeddings.npy ({embeddings.shape})")


if __name__ == "__main__":
    main()
