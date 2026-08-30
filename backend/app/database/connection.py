"""
Database connection and session management.

Uses SQLite by default (zero setup, works out of the box). Set
DATABASE_URL in backend/.env to point at PostgreSQL (or anything else
SQLAlchemy supports) later without touching any other file.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pkos.db")

# SQLite needs this because FastAPI can use a session across threads
# (it doesn't for a single request, but the default test client / some
# ASGI setups do). Any other database ignores this.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """SQLite ignores ON DELETE CASCADE unless this pragma is set."""
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

# All ORM models inherit from this Base.
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create any tables that don't exist yet. Safe to call on every startup."""
    from app.database import models  # noqa: F401  (registers models on Base)

    Base.metadata.create_all(bind=engine)
