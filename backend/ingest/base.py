"""Ingestion pipeline shared by every data source.

Flow: fetch() -> parse() -> validate -> normalize -> deduplicate -> upsert ->
audit. Adapters implement `fetch` and `parse`; everything downstream is
data-source-agnostic, so adding a portal is one new adapter file, not a change
to the pipeline or the map.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Sequence

from sqlalchemy import func
from sqlalchemy.orm import Session

from .contract import DataConfidence, RawProject
from .normalize import canonical_sector, canonical_state, derive_scale, to_iso_date

logger = logging.getLogger("govrisk.ingest")

ACTION_INSERT = "INSERT"
ACTION_UPDATE = "UPDATE"
ACTION_SKIP = "SKIP"
ACTION_REJECT = "REJECT"


class IngestSummary:
    def __init__(self, source: str) -> None:
        self.source = source
        self.total = 0
        self.inserted = 0
        self.updated = 0
        self.skipped = 0
        self.rejected = 0

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "total": self.total,
            "inserted": self.inserted,
            "updated": self.updated,
            "skipped": self.skipped,
            "rejected": self.rejected,
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class BaseIngestor:
    """Adapter base class. Subclasses implement `fetch` and `parse` only."""

    source_name = "base"
    source_url: Optional[str] = None
    confidence = DataConfidence.UNVERIFIED

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    def fetch(self) -> List[dict]:
        raise NotImplementedError

    def parse(self, rows: Sequence[dict]) -> List[RawProject]:
        raise NotImplementedError

    # -- Model mapping (deterministic, source-agnostic) ----------------------
    def _build_record(self, p: RawProject) -> dict:
        """DB column dict (no `id`) from a validated RawProject."""
        scale = derive_scale(p.costEstimateCr)
        expected = p.plannedEndDate or ""
        ts = now_iso()
        return {
            "name": p.name.strip(),
            "ministry": (p.ministry or p.implementingAgency or "Unknown").strip(),
            "sector": canonical_sector(p.sector),
            "state": canonical_state(p.stateName),
            "agency": (p.implementingAgency or p.ministry or "Unknown").strip(),
            "district": p.districtName,
            "description": p.description,
            "original_cost": p.costEstimateCr or 0.0,
            "current_cost": p.costEstimateCr or 0.0,
            "expenditure": 0.0,
            "physical_progress": 0.0,
            "financial_progress": None,
            "planned_progress": 0.0,
            "start_date": p.startDate or "",
            "expected_completion": expected,
            "predicted_completion": expected,
            "cost_overrun_probability": 0.0,
            "delay_probability": 0.0,
            "implementation_risk": 0.0,
            "risk_score": 0.0,
            "risk_level": "LOW",
            "milestones_total": 0,
            "milestones_delayed": 0,
            "lat": p.lat or 0.0,
            "lng": p.lng or 0.0,
            "risk_factors": json.dumps([]),
            "recommendations": json.dumps([]),
            "risk_inputs": json.dumps({}),
            "risk_confidence": None,
            "risk_report": None,
            "created_at": ts,
            "updated_at": ts,
            "status": p.status.value,
            "scale": scale.value if scale else None,
            "funding_source": p.fundingSource.value if p.fundingSource else None,
            "external_ref": p.externalRef,
            "source_name": self.source_name,
            "source_url": p.sourceUrl,
            "retrieved_date": to_iso_date(p.retrievedDate) or p.retrievedDate,
            "data_confidence": p.confidence.value,
            "last_synced_at": ts,
        }

    @staticmethod
    def _populate_risk(project) -> None:
        """Recompute cached risk columns with the deterministic risk engine.

        Without added data the score is based only on cost scale and schedule
        placeholders - never on invented inputs. A failed assessment leaves the
        honest all-zero default row in place.
        """
        try:
            from services.risk_service import apply_assessment

            apply_assessment(project)
        except Exception:
            pass

    # -- Dedup ----------------------------------------------------------------
    def _find_existing(self, db: Session, p: RawProject):
        from models import Project

        if p.externalRef:
            return (
                db.query(Project)
                .filter(Project.external_ref == p.externalRef)
                .first()
            )
        return (
            db.query(Project)
            .filter(
                func.lower(Project.name) == p.name.strip().lower(),
                func.lower(Project.state) == canonical_state(p.stateName).lower(),
            )
            .first()
        )

    def _out_of_scope(self, p: RawProject) -> Optional[str]:
        """Reason when a record is explicitly out of scope (medium/large only)."""
        if p.costEstimateCr is not None and p.costEstimateCr < 100:
            return "Below MEDIUM threshold (< INR 100 Cr) - out of scope"
        return None

    # -- Audit ----------------------------------------------------------------
    def _audit(self, db: Session, action: str, project_id: Optional[str], detail: str) -> None:
        if self.dry_run:
            return
        from models import IngestAuditLog

        db.add(
            IngestAuditLog(
                source=self.source_name,
                project_id=project_id,
                action=action,
                detail=detail[:2000],
                created_at=now_iso(),
            )
        )

    # -- Run ------------------------------------------------------------------
    def run(self, db: Session) -> IngestSummary:
        """Validate -> dedupe -> upsert every fetched record."""
        from services.project_service import next_project_id
        from models import Project

        summary = IngestSummary(self.source_name)
        rows = self.fetch() or []
        summary.total = len(rows)

        parsed: List[RawProject] = []
        for row in rows:
            try:
                parsed.extend(self.parse([row]))
            except Exception as exc:  # a source-specific parse never kills the run
                summary.rejected += 1
                logger.warning("Rejected raw row (parse): %s", exc)
                self._audit(db, ACTION_REJECT, None, f"Parse error: {exc}")

        for p in parsed:
            reason = self._out_of_scope(p)
            if reason:
                summary.skipped += 1
                self._audit(db, ACTION_SKIP, None, f"{p.name.strip()}: {reason}")
                continue

            existing = self._find_existing(db, p)
            if existing is not None:
                diff = self._apply(db, existing, p)
                summary.updated += 1
                action = ACTION_UPDATE if diff else ACTION_SKIP
                detail = (
                    f"{p.name.strip()}: updated {len(diff)} fields"
                    if diff
                    else f"{p.name.strip()}: up-to-date"
                )
                self._audit(db, action, existing.id, detail)
                continue

            if self.dry_run:
                summary.inserted += 1
                continue

            project = Project(id=next_project_id(db), **self._build_record(p))
            self._populate_risk(project)
            db.add(project)
            db.flush()
            summary.inserted += 1
            self._audit(db, ACTION_INSERT, project.id, f"Inserted {p.name.strip()}")

        if not self.dry_run:
            db.commit()
        return summary

    def _apply(self, db: Session, project, p: RawProject) -> List[str]:
        """Overwrite tracked columns with fresher source values; return changed."""
        record = self._build_record(p)
        changed: List[str] = []
        for key, value in record.items():
            current = getattr(project, key, None)
            if current != value:
                if not self.dry_run:
                    setattr(project, key, value)
                changed.append(key)
        if changed and not self.dry_run:
            project.last_synced_at = record["last_synced_at"]
            self._populate_risk(project)
        return changed


__all__ = [
    "BaseIngestor",
    "IngestSummary",
    "ACTION_INSERT",
    "ACTION_UPDATE",
    "ACTION_SKIP",
    "ACTION_REJECT",
    "now_iso",
]