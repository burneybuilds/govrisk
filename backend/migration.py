"""Idempotent schema migrations for the existing govrisk.db.

SQLAlchemy create_all() only creates missing tables and does not add
new columns to existing tables. This module adds newly introduced
columns to the projects table without touching existing rows, then
refreshes the cached risk columns with the deterministic risk engine
so historical rows are consistent with the current engine (single
source of truth).
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

PROJECT_COLUMNS = {
    "district": "TEXT",
    "description": "TEXT",
    "nodal_officer": "TEXT",
    "contact_info": "TEXT",
    "financial_progress": "FLOAT",
    "risk_inputs": "TEXT",
    "risk_confidence": "FLOAT",
    "risk_report": "TEXT",
    "created_at": "TEXT",
    "updated_at": "TEXT",
}


def run_migrations(engine: Engine) -> None:
    try:
        with engine.connect() as conn:
            existing = {
                row[1]
                for row in conn.execute(text("PRAGMA table_info(projects)"))
            }
            for column, ddl in PROJECT_COLUMNS.items():
                if column not in existing:
                    conn.execute(
                        text(f"ALTER TABLE projects ADD COLUMN {column} {ddl}")
                    )
            conn.commit()
    except Exception:
        # The projects table may not exist yet (fresh database); create_all
        # in main.py handles that case with the full model definition.
        pass

    _backfill_risk(engine)


def _backfill_risk(engine: Engine) -> None:
    """Recompute cached risk columns for existing rows using the risk engine.

    Keeps every row consistent with the deterministic engine even before the
    app first serves a request. Never fabricates values - it recomputes from
    the same inputs the API uses.
    """
    try:
        from sqlalchemy.orm import Session
        from models import Project
        from services.risk_service import apply_assessment

        with Session(bind=engine) as session:
            for project in session.query(Project).all():
                try:
                    apply_assessment(project)
                except Exception:
                    continue
            session.commit()
    except Exception:
        return