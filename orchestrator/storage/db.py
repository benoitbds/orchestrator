"""Database engine and session utilities for agentic storage."""
from __future__ import annotations

from contextlib import contextmanager
import os

from sqlmodel import SQLModel, Session, create_engine

DB_URL = os.getenv("AGENTIC_DB_URL", "sqlite:///orchestrator.db")
engine = create_engine(DB_URL, echo=False)


def init_db() -> None:
    """Create tables based on SQLModel metadata."""
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session() -> Session:
    """Yield a SQLModel session."""
    with Session(engine) as session:
        yield session
