"""GovRisk infrastructure project ingestion package.

Sources are cleanly isolated per adapter (`ingest/sources/*`), each adapter
only implements `fetch` (raw rows) + `parse` (raw -> RawProject). The shared
pipeline in `ingest/base.py` validates, normalizes, deduplicates and audits
every record. See `ingest/run.py --help` for the CLI.

Records below the MEDIUM threshold (< INR 100 Cr) are skipped; costs are
NEVER invented - missing values stay NULL and are flagged by confidence.
"""

from .contract import (
    DataConfidence,
    FundingSource,
    ProjectScale,
    ProjectStatus,
    RawProject,
)

__all__ = [
    "DataConfidence",
    "FundingSource",
    "ProjectScale",
    "ProjectStatus",
    "RawProject",
]