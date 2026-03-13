import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.engine import Engine

BASE_DIR = Path(__file__).resolve().parent.parent


def _build_sqlite_url() -> str:
    # keep local default stable + cross-platform
    return f"sqlite:///{(BASE_DIR / 'app.db').as_posix()}"


def _normalize_database_url(url: str) -> str:
    """
    Normalizes common provider URL formats to SQLAlchemy-supported ones.
    - Some providers supply postgres:// which SQLAlchemy expects as postgresql://
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def _create_engine(database_url: str) -> Engine:
    """
    Creates a SQLAlchemy engine that supports:
    - Local SQLite (default)
    - Remote Postgres (Supabase / Neon / etc.) via DATABASE_URL
    """
    database_url = _normalize_database_url(database_url)

    if database_url.startswith("sqlite"):
        # Needed for FastAPI + SQLAlchemy with SQLite (single file DB)
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )

    # Postgres: no SQLite threading args. Pooling defaults are usually fine.
    # If your Supabase project requires SSL, include it in DATABASE_URL (recommended).
    # Example: postgresql+psycopg2://user:pass@host:5432/dbname?sslmode=require
    return create_engine(database_url, pool_pre_ping=True)


# 1) Read DATABASE_URL from environment; fallback to local SQLite for dev
DATABASE_URL = os.getenv("DATABASE_URL") or _build_sqlite_url()

# 2) Create shared engine + session factory
engine = _create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
