from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from examgen.core.models import Base


def get_engine(db_path: Path) -> Engine:
    """Return a SQLite engine for the given database path."""
    return create_engine(f"sqlite:///{db_path}", echo=False, future=True)


def init_db(engine: Engine) -> None:
    """Create all tables if they do not exist."""
    Base.metadata.create_all(engine)
