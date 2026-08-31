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
    from app.database import models  


    Base.metadata.create_all(bind=engine)
    _migrate_documents_table()


def _migrate_documents_table() -> None:
    """
    create_all() only creates tables that don't exist yet — it never alters
    an existing table. This project has no migration tool (Alembic, etc.),
    so if you're upgrading from a pkos.db created before the status/
    file_path/size_bytes/error_message columns existed, patch them in here
    instead of losing already-uploaded documents. Only handles SQLite (the
    default); other databases should use a real migration tool.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return

    with engine.connect() as conn:
        existing_columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(documents)")}

        statements = []
        if "status" not in existing_columns:
            statements.append("ALTER TABLE documents ADD COLUMN status VARCHAR NOT NULL DEFAULT 'indexed'")
        if "file_path" not in existing_columns:
            statements.append("ALTER TABLE documents ADD COLUMN file_path VARCHAR")
        if "size_bytes" not in existing_columns:
            statements.append("ALTER TABLE documents ADD COLUMN size_bytes INTEGER")
        if "error_message" not in existing_columns:
            statements.append("ALTER TABLE documents ADD COLUMN error_message TEXT")

        for statement in statements:
            conn.exec_driver_sql(statement)
        if statements:
            conn.commit()
