import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

PROJECT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_DIR / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set in the environment or .env")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@contextmanager
def get_db():
    """Context manager with auto-commit and rollback-on-exception."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_dependency():
    """FastAPI dependency (generator-based, no auto-commit)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def query_rows(sql: str, params: dict = None) -> list[dict]:
    """Execute raw SQL and return list of dicts."""
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        columns = result.keys()
        return [dict(zip(columns, row)) for row in result]
