"""Engine + session for the authentication database (`auth.db`)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from config import AUTH_DATABASE_URL

_engine_kwargs = {"pool_pre_ping": True}
if AUTH_DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

auth_engine = create_engine(AUTH_DATABASE_URL, **_engine_kwargs)
AuthSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=auth_engine)
AuthBase = declarative_base()


def get_auth_db():
    db = AuthSessionLocal()
    try:
        yield db
    finally:
        db.close()
