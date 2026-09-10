import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

AUTH_DATABASE_URL = os.getenv("AUTH_DATABASE_URL", "sqlite:///./auth.db")

auth_engine = create_engine(AUTH_DATABASE_URL, connect_args={"check_same_thread": False})
AuthSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=auth_engine)
AuthBase = declarative_base()


def get_auth_db():
    db = AuthSessionLocal()
    try:
        yield db
    finally:
        db.close()
