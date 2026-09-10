"""Idempotent schema migrations for the existing govrisk.db.

SQLAlchemy create_all() only creates missing tables and does not add
new columns to existing tables. This module adds newly introduced
columns to the projects table without touching existing rows.
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

PROJECT_COLUMNS = {
    "district": "TEXT",
    "description": "TEXT",
    "nodal_officer": "TEXT",
    "contact_info": "TEXT",
    "financial_progress": "FLOAT",
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